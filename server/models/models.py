import importlib

from digi_server.logger import get_logger
from utils.database import DigiSQLAlchemy

# Import shared module discovery utilities
try:
    from utils.module_discovery import import_modules
except ImportError:
    # Fallback if module_discovery.py isn't available yet
    from utils.pkg_utils import find_end_modules

IMPORTED_MODELS = {}


def import_all_models():
    """Import all model modules in the application."""
    get_logger().info("Importing models...")

    try:
        # Try to use the shared module discovery utilities
        from utils.module_discovery import import_modules
        import_modules('models', IMPORTED_MODELS, __name__)
    except ImportError:
        # Fall back to the original method if the utilities aren't available
        get_logger().warning("Using legacy model discovery method")
        models = find_end_modules(".", prefix="models")
        for model in models:
            if model != __name__:
                try:
                    get_logger().debug(f"Importing model module {model}")
                    mod = importlib.import_module(model)
                    IMPORTED_MODELS[model] = mod
                except ImportError as e:
                    get_logger().error(f"Error importing model {model}: {str(e)}")

    # Log summary
    get_logger().info(f"Imported {len(IMPORTED_MODELS)} model modules")
    get_logger().debug(f"Imported models: {list(IMPORTED_MODELS.keys())}")


# Initialize the database
db = DigiSQLAlchemy()