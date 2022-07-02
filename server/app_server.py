from tornado.web import Application, StaticFileHandler
from tornado_sqlalchemy import SQLAlchemy

from env_parser import EnvParser
from logger import get_logger
from models import db, Session
from route import Route
from utils import Singleton

# Controller imports (needed to trigger the decorator)
from controllers import controllers
from controllers import ws_controller


@Singleton
class DigiScriptServer(Application):

    def __init__(self, debug=False):
        env_parser: EnvParser = EnvParser.instance()

        get_logger().info(f'Using {env_parser.db_path} as DB path')
        self.db = db
        self.db.create_all()

        # Clear out all sessions since we are starting the app up
        with self.db.sessionmaker() as session:
            session.query(Session).delete()
            session.commit()

        handlers = Route.routes()
        handlers.append((r'/assets/.*', controllers.StaticController))
        handlers.append((r'/(.*)', controllers.RootController))
        super().__init__(
            handlers=handlers,
            debug=debug,
            db=self.db,
            websocket_ping_interval=5)

    def get_db(self) -> SQLAlchemy:
        return self.db
