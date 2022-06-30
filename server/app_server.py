import os.path
from tornado.web import Application, StaticFileHandler
from tornado_sqlalchemy import SQLAlchemy

from logger import get_logger
from route import Route
from utils import Singleton

import controllers


@Singleton
class DigiScriptServer(Application):

    def __init__(self, debug=False, db_path=None):
        if not db_path:
            db_path = f'sqlite://{os.path.join(os.path.dirname(__file__), "digiscript.db")}'
            get_logger().info(f'No db_path provided, falling back to default: {db_path}')
        elif not os.path.exists(db_path):
            raise FileNotFoundError(f'Could not find specified DB path: {db_path}')

        self.db = SQLAlchemy(db_path)

        handlers = Route.routes()
        handlers.append((
            r'/(.*)',
            StaticFileHandler,
            {'path': 'static', 'default_filename': 'index.html'},
        ))
        super().__init__(handlers=handlers, debug=debug, db=self.db, websocket_ping_interval=5)

    def get_db(self) -> SQLAlchemy:
        return self.db
