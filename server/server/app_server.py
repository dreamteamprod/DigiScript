import logging

from tornado.log import LogFormatter
from tornado.web import Application
from tornado_sqlalchemy import SQLAlchemy

from utils.env_parser import EnvParser
from utils.logger import get_logger, configure_file_logging
from models.models import db, Session
from utils.route import Route
from utils.settings import Settings

# Controller imports (needed to trigger the decorator)
from controllers import controllers
from controllers.ws_controller import WebSocketController


class DigiScriptServer(Application):

    def __init__(self, debug=False, settings_path=None):
        env_parser: EnvParser = EnvParser.instance()

        self.digi_settings = Settings(settings_path)

        log_path = self.digi_settings.settings.get('log_path', None)
        file_size = self.digi_settings.settings.get('max_log_mb', 100)
        backups = self.digi_settings.settings.get('log_backups', 5)
        if log_path:
            configure_file_logging(log_path, file_size, backups)

        self.clients = []

        get_logger().info(f'Using {env_parser.db_path} as DB path')
        self.db = db
        self.db.configure(url=env_parser.db_path)
        self.db.create_all()

        # Clear out all sessions since we are starting the app up
        with self.db.sessionmaker() as session:
            get_logger().debug('Emptying out sessions table!')
            session.query(Session).delete()
            session.commit()

        handlers = Route.routes()
        handlers.append(('/favicon.ico', controllers.StaticController))
        handlers.append((r'/assets/.*', controllers.StaticController))
        handlers.append((r'/api/.*', controllers.ApiFallback))
        handlers.append((r'/(.*)', controllers.RootController))
        super().__init__(
            handlers=handlers,
            debug=debug,
            db=self.db,
            websocket_ping_interval=5)

    def get_db(self) -> SQLAlchemy:
        return self.db

    async def ws_send_to_all(self, ws_op: str, ws_action: str, ws_data: dict):
        client: WebSocketController
        for client in self.clients:
            await client.write_message({
                'OP': ws_op,
                'DATA': ws_data,
                'ACTION': ws_action
            })
