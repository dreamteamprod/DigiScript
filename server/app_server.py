from tornado.web import Application, StaticFileHandler
from tornado_sqlalchemy import SQLAlchemy

from env_parser import EnvParser
from logger import get_logger
from route import Route
from utils import Singleton

import controllers


@Singleton
class DigiScriptServer(Application):

    def __init__(self, debug=False):
        env_parser: EnvParser = EnvParser.instance()

        get_logger().info(f'Using {env_parser.db_path} as DB path')
        self.db = SQLAlchemy(env_parser.db_path)

        handlers = Route.routes()
        handlers.append((
            r'/(.*)',
            StaticFileHandler,
            {'path': 'static', 'default_filename': 'index.html'},
        ))
        super().__init__(handlers=handlers, debug=debug, db=self.db, websocket_ping_interval=5)

    def get_db(self) -> SQLAlchemy:
        return self.db
