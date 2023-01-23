import os
from typing import List

from tornado.ioloop import IOLoop
from tornado.web import Application, StaticFileHandler
from tornado_prometheus import PrometheusMixIn

from utils.database import DigiSQLAlchemy
from utils.env_parser import EnvParser
from utils.logger import get_logger, configure_file_logging, configure_db_logging
from models.models import db
from models.show import Show
from models.session import Session
from utils.route import Route
from utils.settings import Settings

from controllers import controllers
from controllers.ws_controller import WebSocketController


class DigiScriptServer(PrometheusMixIn, Application):

    def __init__(self, debug=False, settings_path=None):
        env_parser: EnvParser = EnvParser.instance()

        self.digi_settings: Settings = Settings(self, settings_path)
        self.app_log_handler = None
        self.db_file_handler = None

        # Controller imports (needed to trigger the decorator)
        controllers.import_all_controllers()

        self.clients: List[WebSocketController] = []

        get_logger().info(f'Using {env_parser.db_path} as DB path')
        self._db: DigiSQLAlchemy = db
        self._db.configure(url=env_parser.db_path)
        self._db.create_all()

        # Clear out all sessions since we are starting the app up
        with self._db.sessionmaker() as session:
            get_logger().debug('Emptying out sessions table!')
            session.query(Session).delete()
            session.commit()

        # Check the show we are expecting to be loaded exists
        with self._db.sessionmaker() as session:
            current_show = self.digi_settings.settings.get('current_show').get_value()
            if current_show:
                show = session.query(Show).get(current_show)
                if not show:
                    get_logger().warning('Current show from settings not found. Resetting.')
                    self.digi_settings.settings['current_show'].set_to_default()
                    self.digi_settings._save()

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
            websocket_ping_interval=5)

    async def configure_logging(self):
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

    def regen_logging(self):
        if not IOLoop.current():
            get_logger().error('Unable to regenerate logging as there is no current IOLoop')
        else:
            IOLoop.current().add_callback(self.configure_logging)

    def get_db(self) -> DigiSQLAlchemy:
        return self._db

    async def ws_send_to_all(self, ws_op: str, ws_action: str, ws_data: dict):
        for client in self.clients:
            await client.write_message({
                'OP': ws_op,
                'DATA': ws_data,
                'ACTION': ws_action
            })
