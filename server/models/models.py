from digi_server.logger import get_logger
from utils.database import DigiSQLAlchemy
from utils.module_discovery import import_modules


IMPORTED_MODELS = {}


def import_all_models():
    get_logger().info("Importing models...")
    import_modules("models", IMPORTED_MODELS, __name__)

    # Log summary
    get_logger().info(f"Imported {len(IMPORTED_MODELS)} model modules")
    get_logger().debug(f"Imported models: {list(IMPORTED_MODELS.keys())}")


# Initialize the database
db = DigiSQLAlchemy()
