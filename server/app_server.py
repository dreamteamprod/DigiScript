from tornado.web import Application
from tornado_sqlalchemy import SQLAlchemy

from utils.env_parser import EnvParser
from utils.logger import get_logger
from models import db, Session
from route import Route
from settings import Settings
from utils.singleton import Singleton

# Controller imports (needed to trigger the decorator)
from controllers import controllers


@Singleton
class DigiScriptServer(Application):

    def __init__(self, debug=False, settings_path=None):
        env_parser: EnvParser = EnvParser.instance()

        self.digi_settings = Settings(settings_path)
        self.clients = []

        get_logger().info(f'Using {env_parser.db_path} as DB path')
        self.db = db
        self.db.create_all()

        # Clear out all sessions since we are starting the app up
        with self.db.sessionmaker() as session:
            get_logger().debug('Emptying out sessions table!')
            session.query(Session).delete()
            session.commit()

        handlers = Route.routes()
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
