import os
from typing import List, Optional

from tornado.ioloop import IOLoop
from tornado.web import Application, StaticFileHandler
from tornado_prometheus import PrometheusMixIn

from controllers import controllers
from controllers.ws_controller import WebSocketController
from digi_server.logger import get_logger, configure_file_logging, configure_db_logging
from digi_server.settings import Settings
from models.cue import CueType
from models.models import db
from models.script import Script
from models.show import Show
from models.session import Session, ShowSession
from models.user import User
from rbac.rbac import RBACController
from utils.database import DigiSQLAlchemy
from utils.env_parser import EnvParser
from utils.web.route import Route


class DigiScriptServer(PrometheusMixIn, Application):

    def __init__(self, debug=False, settings_path=None):
        self.env_parser: EnvParser = EnvParser.instance()  # pylint: disable=no-member

        self.digi_settings: Settings = Settings(self, settings_path)
        self.app_log_handler = None
        self.db_file_handler = None

        # Controller imports (needed to trigger the decorator)
        controllers.import_all_controllers()

        self.clients: List[WebSocketController] = []

        db_path = self.digi_settings.settings.get('db_path').get_value()
        get_logger().info(f'Using {db_path} as DB path')
        self._db: DigiSQLAlchemy = db
        self._db.configure(url=db_path)

        self.rbac = RBACController(self)
        self._configure_rbac()

        self._db.create_all()

        # Clear out all sessions since we are starting the app up
        with self._db.sessionmaker() as session:
            get_logger().debug('Emptying out sessions table!')
            session.query(Session).delete()
            session.commit()

        # Check for presence of admin user, and update settings to match
        with self._db.sessionmaker() as session:
            any_admin = session.query(User).filter(User.is_admin).first()
            has_admin = any_admin is not None
            self.digi_settings.settings['has_admin_user'].set_value(has_admin, False)
            self.digi_settings._save()

        # Check the show we are expecting to be loaded exists
        with self._db.sessionmaker() as session:
            current_show = self.digi_settings.settings.get('current_show').get_value()
            if current_show:
                show = session.query(Show).get(current_show)
                if not show:
                    get_logger().warning('Current show from settings not found. Resetting.')
                    self.digi_settings.settings['current_show'].set_to_default()
                    self.digi_settings._save()

        # If there is a live session in progress, clean up the current client ID
        with self._db.sessionmaker() as session:
            current_show = self.digi_settings.settings.get('current_show').get_value()
            if current_show:
                show = session.query(Show).get(current_show)
                if show and show.current_session_id:
                    show_session: ShowSession = session.query(ShowSession).get(show.current_session_id)
                    if show_session:
                        show_session.last_client_internal_id = show_session.client_internal_id
                        show_session.client_internal_id = None
                    else:
                        get_logger().warning('Current show session not found. Resetting.')
                        show.current_session_id = None
                    session.commit()

        static_files_path = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                         '..', 'static', 'assets')
        get_logger().info(f'Using {static_files_path} as static files path')

        handlers = Route.routes()
        handlers.append(('/favicon.ico', controllers.StaticController))
        handlers.append((r'/assets/(.*)', StaticFileHandler, {'path': static_files_path}))
        handlers.append((r'/api/.*', controllers.ApiFallback))
        handlers.append((r'/(.*)', controllers.RootController))
        super().__init__(
            handlers=handlers,
            debug=debug,
            db=self._db,
            websocket_ping_interval=5,
            cookie_secret='DigiScriptSuperSecretValue123!',
            login_url='/login',
        )

    def log_request(self, handler):
        ignored_routes = Route.ignored_logging_routes()
        if handler.request.path in ignored_routes:
            return
        super().log_request(handler)

    async def configure(self):
        await self._configure_logging()

    async def _configure_logging(self):
        get_logger().info('Reconfiguring logging!')

        # Application logging
        log_path = await self.digi_settings.get('log_path')
        file_size = await self.digi_settings.get('max_log_mb')
        backups = await self.digi_settings.get('log_backups')
        if log_path:
            self.app_log_handler = configure_file_logging(log_path, file_size, backups,
                                                          self.app_log_handler)

        # Database logging
        use_db_logging = await self.digi_settings.get('db_log_enabled')
        if use_db_logging:
            db_log_path = await self.digi_settings.get('db_log_path')
            db_file_size = await self.digi_settings.get('db_max_log_mb')
            db_backups = await self.digi_settings.get('db_log_backups')
            self.db_file_handler = configure_db_logging(log_path=db_log_path,
                                                        max_size_mb=db_file_size,
                                                        log_backups=db_backups,
                                                        handler=self.db_file_handler)

    def _configure_rbac(self):
        self.rbac.add_mapping(User, Show, [Show.id, Show.name])
        self.rbac.add_mapping(User, CueType, [CueType.id, CueType.prefix])
        self.rbac.add_mapping(User, Script, [Script.id])

    def regen_logging(self):
        if not IOLoop.current():
            get_logger().error('Unable to regenerate logging as there is no current IOLoop')
        else:
            IOLoop.current().add_callback(self._configure_logging)

    def validate_has_admin(self):
        if not IOLoop.current():
            get_logger().error('Unable to validate admin user as there is no current IOLoop')
        else:
            IOLoop.current().add_callback(self._validate_has_admin)

    def show_changed(self):
        if not IOLoop.current():
            get_logger().error('Unable to initiate show change as there is no current IOLoop')
        else:
            IOLoop.current().add_callback(self._show_changed)

    async def _validate_has_admin(self):
        with self.get_db().sessionmaker() as session:
            any_admin = session.query(User).filter(User.is_admin).first()
            has_admin = any_admin is not None
            await self.digi_settings.set('has_admin_user', has_admin)

    async def _show_changed(self):
        await self.ws_send_to_all('NOOP', 'SHOW_CHANGED', {})

    def get_db(self) -> DigiSQLAlchemy:
        return self._db

    def get_all_ws(self, user_id) -> List[WebSocketController]:
        sockets = []
        for client in self.clients:
            c_user_id = client.get_secure_cookie('digiscript_user_id')
            if c_user_id is not None and int(c_user_id) == user_id:
                sockets.append(client)
        return sockets

    def get_ws(self, internal_uuid: str) -> Optional[WebSocketController]:
        for client in self.clients:
            if client.__getattribute__('internal_id') == internal_uuid:
                return client
        return None

    async def ws_send_to_all(self, ws_op: str, ws_action: str, ws_data: dict):
        for client in self.clients:
            await client.write_message({
                'OP': ws_op,
                'DATA': ws_data,
                'ACTION': ws_action
            })
