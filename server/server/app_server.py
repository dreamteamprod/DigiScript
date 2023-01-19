from typing import List

from tornado.web import Application
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

        # Application logging
        log_path = self.digi_settings.settings.get('log_path').get_value()
        file_size = self.digi_settings.settings.get('max_log_mb').get_value()
        backups = self.digi_settings.settings.get('log_backups').get_value()
        if log_path:
            configure_file_logging(log_path, file_size, backups)

        # Database logging
        use_db_logging = self.digi_settings.settings.get('db_log_enabled').get_value()
        if use_db_logging:
            db_log_path = self.digi_settings.settings.get('db_log_path').get_value()
            db_file_size = self.digi_settings.settings.get('db_max_log_mb').get_value()
            db_backups = self.digi_settings.settings.get('db_log_backups').get_value()
            configure_db_logging(log_path=db_log_path, max_size_mb=db_file_size,
                                 log_backups=db_backups)

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

        handlers = Route.routes()
        handlers.append(('/favicon.ico', controllers.StaticController))
        handlers.append((r'/assets/.*', controllers.StaticController))
        handlers.append((r'/api/.*', controllers.ApiFallback))
        handlers.append((r'/(.*)', controllers.RootController))
        super().__init__(
            handlers=handlers,
            debug=debug,
            db=self._db,
            websocket_ping_interval=5)

    def get_db(self) -> DigiSQLAlchemy:
        return self._db

    async def ws_send_to_all(self, ws_op: str, ws_action: str, ws_data: dict):
        for client in self.clients:
            await client.write_message({
                'OP': ws_op,
                'DATA': ws_data,
                'ACTION': ws_action
            })
