import importlib
import pkgutil
import sys

from digi_server.logger import get_logger
from utils.pkg_utils import find_end_modules

# Check if running in PyInstaller bundle
try:
    # pylint: disable=unused-import
    from utils.pyinstaller_utils import get_resource_path, is_frozen
except ImportError:

    def is_frozen():
        return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")

    def get_resource_path(path):
        return path


def discover_modules(package_name, module_name=None):
    get_logger().info(f"Discovering {package_name} modules...")

    if is_frozen():
        # In PyInstaller mode
        get_logger().info(
            f"Running in PyInstaller mode, using special discovery for {package_name}"
        )

        # Multiple discovery strategies for PyInstaller
        discovered_modules = []

        # Strategy 1: Try using pkgutil (works in some PyInstaller configs)
        try:
            get_logger().debug(f"Using pkgutil to discover {package_name} modules")
            package = importlib.import_module(package_name)

            for _finder, name, is_pkg in pkgutil.walk_packages(
                package.__path__, package.__name__ + "."
            ):
                # Skip the package itself and the current module
                if name == package_name or (module_name and name == module_name):
                    continue

                # Only include modules, not packages (unless they have code)
                if not is_pkg or has_module_code(name):
                    discovered_modules.append(name)

            get_logger().info(
                f"Found {len(discovered_modules)} {package_name} modules using pkgutil"
            )
        except Exception as e:
            get_logger().warning(f"Error using pkgutil for {package_name}: {e}")
            discovered_modules = []

        # Strategy 2: Search preloaded modules in sys.modules
        if not discovered_modules:
            get_logger().debug(f"Searching sys.modules for {package_name}")
            for name in list(sys.modules.keys()):
                if (
                    name.startswith(f"{package_name}.")
                    and name != f"{package_name}.__init__"
                    and name != module_name
                ):
                    discovered_modules.append(name)

            get_logger().info(
                f"Found {len(discovered_modules)} {package_name} modules in sys.modules"
            )

        # Return the discovered modules
        return discovered_modules

    # In source mode, use the existing find_end_modules utility
    modules = find_end_modules(".", prefix=package_name)
    get_logger().debug(f"Found {len(modules)} {package_name} modules in source mode")
    return modules


def has_module_code(module_name):
    try:
        module = importlib.import_module(module_name)
        # Check if the module has any attributes beyond standard ones
        attrs = [a for a in dir(module) if not a.startswith("__")]
        return len(attrs) > 0
    except ImportError:
        return False


def import_modules(package_name, module_dict, current_module=None):
    # Discover modules
    modules = discover_modules(package_name, current_module)

    # Import each module
    success_count = 0
    for module_name in modules:
        if module_name != current_module:
            try:
                get_logger().debug(f"Importing {package_name} module: {module_name}")
                mod = importlib.import_module(module_name)
                module_dict[module_name] = mod
                success_count += 1
            except ImportError as e:
                get_logger().error(f"Error importing {module_name}: {str(e)}")

    get_logger().info(f"Successfully imported {success_count} {package_name} modules")
    return success_count
