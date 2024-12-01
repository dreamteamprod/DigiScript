import importlib

from digi_server.logger import get_logger
from utils.database import DigiSQLAlchemy
from utils.pkg_utils import find_end_modules

IMPORTED_MODELS = {}


def import_all_models():
    models = find_end_modules('.', prefix='models')
    for model in models:
        if model != __name__:
            get_logger().debug(f'Importing model module {model}')
            mod = importlib.import_module(model)
            IMPORTED_MODELS[model] = mod


db = DigiSQLAlchemy()
