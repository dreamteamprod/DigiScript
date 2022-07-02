import os

from utils import Singleton


@Singleton
class EnvParser(object):

    def __init__(self):
        self.db_path = None

        self._parse_env()

    def _parse_env(self):
        self.db_path = os.getenv(
            'DIGI_DB_PATH',
            f'sqlite:///{os.path.join(os.path.dirname(__file__), "digiscript.sqlite")}')
