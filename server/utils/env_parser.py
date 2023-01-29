from utils.singleton import Singleton


@Singleton
class EnvParser(object):

    def __init__(self):
        self._parse_env()

    def _parse_env(self):
        pass
