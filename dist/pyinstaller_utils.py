import os
import sys
import logging
import shutil


def is_frozen():
    """Check if running in a PyInstaller bundle"""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def get_base_path():
    """
    Get the base path for resources whether running as a script or PyInstaller bundle.

    When running as a PyInstaller bundle, sys._MEIPASS is the temporary directory
    containing the extracted files.
    """
    if is_frozen():
        # Running as PyInstaller bundle
        return sys._MEIPASS
    # Running as a normal Python script
    return os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


def get_resource_path(relative_path):
    """
    Get absolute path to a resource, works for dev and for PyInstaller.

    Args:
        relative_path: Path relative to the application root

    Returns:
        Absolute path to the resource
    """
    base_path = get_base_path()
    return os.path.join(base_path, relative_path)


def get_writeable_path(app_name="DigiScript"):
    """
    Get a path where the application can write data (config, logs, etc.)
    This is different from get_resource_path because PyInstaller bundles
    are read-only.

    Args:
        app_name: Name of the application for creating subdirectories

    Returns:
        Path to a directory where the application can write data
    """
    if is_frozen():
        # We're running as a PyInstaller bundle
        if sys.platform == 'win32':
            # On Windows, use %APPDATA%
            base_dir = os.environ.get('APPDATA', os.path.expanduser('~'))
            app_dir = os.path.join(base_dir, app_name)
        elif sys.platform == 'darwin':
            # On macOS, use ~/Library/Application Support
            app_dir = os.path.expanduser(f'~/Library/Application Support/{app_name}')
        else:
            # On Linux/Unix, use ~/.config
            app_dir = os.path.expanduser(f'~/.config/{app_name}')
    else:
        # We're running in source mode, use a directory in the project
        app_dir = os.path.join(get_base_path(), 'data')

    # Ensure the directory exists
    os.makedirs(app_dir, exist_ok=True)
    return app_dir


def get_conf_dir():
    """Get the configuration directory path"""
    writeable_path = get_writeable_path()
    conf_dir = os.path.join(writeable_path, 'conf')
    os.makedirs(conf_dir, exist_ok=True)
    return conf_dir


def get_log_dir():
    """Get the log directory path"""
    writeable_path = get_writeable_path()
    log_dir = os.path.join(writeable_path, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def ensure_writable_db_path(db_path):
    """
    Ensure the database path is writable. If running from a PyInstaller bundle,
    and the path is inside the bundle, we need to use a writable location instead.

    Args:
        db_path: Original database path

    Returns:
        A writable database path
    """
    if not db_path or not isinstance(db_path, str):
        return db_path

    if not db_path.startswith('sqlite:///'):
        return db_path

    # Extract the file path from the SQLite URL
    file_path = db_path.replace('sqlite:///', '')

    # If we're running from a PyInstaller bundle, use a writable location
    if is_frozen():
        # Create a new path in the writable directory
        conf_dir = get_conf_dir()
        new_file_path = os.path.join(conf_dir, os.path.basename(file_path))

        # If the file doesn't exist in the writable location yet but exists in the bundle,
        # copy it (this is unlikely since we're not bundling the conf directory)
        if not os.path.exists(new_file_path) and os.path.exists(file_path):
            logging.info(f"Copying database from {file_path} to {new_file_path}")
            shutil.copy2(file_path, new_file_path)

        # Return the new SQLite URL
        return f"sqlite:///{new_file_path}"

    return db_path


def configure_for_pyinstaller():
    """
    Apply necessary configurations for running as a PyInstaller bundle.
    Call this early in the application startup.

    Returns:
        Boolean indicating if we're running as a PyInstaller bundle
    """
    frozen = is_frozen()

    if frozen:
        # Configure paths for logs
        log_dir = get_log_dir()

        # Configure basic logging to a file
        log_path = os.path.join(log_dir, 'digiscript.log')
        logging.basicConfig(
            filename=log_path,
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        logging.info(f"Running as PyInstaller bundle from {sys._MEIPASS}")

        # Add bundle directory to sys.path to make imports work
        if sys._MEIPASS not in sys.path:
            sys.path.insert(0, sys._MEIPASS)

    return frozen
