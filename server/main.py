#!/usr/bin/env python3
import asyncio
import logging
import os

from tornado.options import define, options, parse_command_line

# Add PyInstaller support
try:
    from utils.pyinstaller_utils import (
        configure_for_pyinstaller,
        ensure_writable_db_path,
        get_conf_dir,
        get_log_dir,
    )

    # Apply PyInstaller configurations if needed
    is_frozen = configure_for_pyinstaller()
except ImportError:
    # If the module doesn't exist yet, assume we're not frozen
    is_frozen = False

    def get_conf_dir():
        return os.path.join(os.path.dirname(__file__), "conf")

    def get_log_dir():
        return os.path.join(os.path.dirname(__file__), "logs")

    def ensure_writable_db_path(path):
        return path


from digi_server.app_server import DigiScriptServer
from digi_server.logger import add_logging_level, get_logger

add_logging_level("TRACE", logging.DEBUG - 5)
get_logger().setLevel(logging.DEBUG)

define("debug", type=bool, default=False if is_frozen else True, help="auto reload")
define("port", type=int, default=8080, help="port to listen on")
define("settings_path", type=str, default=None, help="Path to settings JSON file")
define("skip_migrations", type=bool, default=False, help="skip database migrations")


async def main():
    # Parse command-line options
    try:
        parse_command_line()
    except Exception as e:
        # In PyInstaller mode, some command-line parsing errors might occur
        # when users double-click the executable rather than run from command line
        if is_frozen:
            print(f"Warning: Command-line parsing error: {e}")
            get_logger().warning(f"Command-line parsing error: {e}")
        else:
            raise e

    # Set default settings path if not provided
    if not options.settings_path:
        conf_dir = get_conf_dir()
        os.makedirs(conf_dir, exist_ok=True)
        options.settings_path = os.path.join(conf_dir, "digiscript.json")

    # If we're running in PyInstaller mode, make sure the database path is writable
    if is_frozen:
        # Patch DigiSettings to ensure writable paths
        from digi_server.settings import Settings

        original_define = Settings.define

        def patched_define(
            self,
            key,
            val_type,
            default,
            can_edit=True,
            callback_fn=None,
            nullable=False,
            display_name="",
            help_text="",
        ):
            # For database path, adjust to a writable location if needed
            if key == "db_path" and default and isinstance(default, str):
                default = ensure_writable_db_path(default)

            # For log paths, adjust to the log directory
            if (
                (key == "log_path" or key == "db_log_path")
                and default
                and isinstance(default, str)
            ):
                log_dir = get_log_dir()
                default = os.path.join(log_dir, os.path.basename(default))

            return original_define(
                self,
                key,
                val_type,
                default,
                can_edit,
                callback_fn,
                nullable,
                display_name,
                help_text,
            )

        # Apply the patch
        Settings.define = patched_define

    app = DigiScriptServer(
        debug=options.debug,
        settings_path=options.settings_path,
        skip_migrations=options.skip_migrations,
    )
    await app.configure()

    app.listen(options.port)
    get_logger().info(f"Listening on port: {options.port}")
    if options.debug:
        get_logger().warning("Running in debug mode")
    if is_frozen:
        get_logger().info("Running as PyInstaller bundle")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
