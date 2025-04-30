import os
import secrets
import shutil
import time
from typing import List, Optional

import sqlalchemy
from alembic import command, script
from alembic.config import Config
from alembic.runtime import migration
from sqlalchemy import Column, String
from tornado.ioloop import IOLoop
from tornado.web import Application, StaticFileHandler
from tornado_prometheus import PrometheusMixIn

from controllers import controllers
from controllers.ws_controller import WebSocketController
from digi_server.logger import configure_db_logging, configure_file_logging, get_logger
from digi_server.settings import Settings
from models import models
from models.cue import CueType
from models.script import Script
from models.session import Session, ShowSession
from models.settings import SystemSettings
from models.show import Show
from models.user import User
from rbac.rbac import RBACController
from utils.database import DigiSQLAlchemy
from utils.exceptions import DatabaseTypeException, DatabaseUpgradeRequired
from utils.web.jwt_service import JWTService
from utils.web.route import Route

# Check if we're running in a PyInstaller bundle
try:
    from utils.pyinstaller_utils import get_resource_path, is_frozen
except ImportError:
    # Define fallback functions if not running in PyInstaller
    def get_resource_path(path):
        return path

    def is_frozen():
        return False


class DigiScriptServer(
    PrometheusMixIn, Application
):  # pylint: disable=too-many-instance-attributes

    def __init__(
        self,
        debug=False,
        settings_path=None,
        skip_migrations=False,
        skip_migrations_check=False,
    ):
        self.digi_settings: Settings = Settings(self, settings_path)
        self.app_log_handler = None
        self.db_file_handler = None

        # Controller imports (needed to trigger the decorator)
        controllers.import_all_controllers()
        # Import all the models
        models.import_all_models()

        self.clients: List[WebSocketController] = []

        self._db: DigiSQLAlchemy = models.db
        self.jwt_service: JWTService = None

        db_path: str = self.digi_settings.settings.get("db_path").get_value()
        if db_path.startswith("sqlite://"):
            db_file_path = db_path.replace("sqlite:///", "")
        else:
            raise DatabaseTypeException("Only SQLite is supported")
        # Database set up, if it doesn't exist then create it
        # Otherwise attempt to upgrade it
        if db_path.startswith("sqlite:///") and not os.path.exists(db_file_path):
            get_logger().info("Database file does not exist, creating it")
            get_logger().info(f"Using {db_path} as DB path")

            class AlembicVersion(self._db.Model):
                __tablename__ = "alembic_version"

                version_num = Column(String(32), primary_key=True)

            self._db.configure(url=db_path)
            self.rbac = RBACController(self)
            self._configure_rbac()
            self._db.create_all()

            script_ = script.ScriptDirectory.from_config(self._alembic_config)
            current_migration_head = script_.get_current_head()
            get_logger().info(
                f"Setting current migration head revision: {current_migration_head}"
            )
            with self._db.sessionmaker() as session:
                session.add(AlembicVersion(version_num=current_migration_head))
                session.commit()
        else:
            # Perform database migrations
            if not skip_migrations:
                self._run_migrations()
            else:
                get_logger().warning("Skipping performing database migrations")
                # And then check the database is up-to-date
                if not skip_migrations_check:
                    self._check_migrations()
                else:
                    get_logger().warning("Skipping database migrations check")
            # Finally, configure the database
            get_logger().info(f"Using {db_path} as DB path")
            self._db.configure(url=db_path)
            self.rbac = RBACController(self)
            self._configure_rbac()
            self._db.create_all()

        # Configure the JWT service once we have set up the database
        self.jwt_service = self._configure_jwt()

        # Check for presence of admin user, and update settings to match
        with self._db.sessionmaker() as session:
            any_admin = session.query(User).filter(User.is_admin).first()
            has_admin = any_admin is not None
            self.digi_settings.settings["has_admin_user"].set_value(has_admin, False)
            self.digi_settings._save()

        # Check the show we are expecting to be loaded exists
        with self._db.sessionmaker() as session:
            current_show = self.digi_settings.settings.get("current_show").get_value()
            if current_show:
                show = session.query(Show).get(current_show)
                if not show:
                    get_logger().warning(
                        "Current show from settings not found. Resetting."
                    )
                    self.digi_settings.settings["current_show"].set_to_default()
                    self.digi_settings._save()

        # If there is a live session in progress, clean up the current client ID
        with self._db.sessionmaker() as session:
            current_show = self.digi_settings.settings.get("current_show").get_value()
            if current_show:
                show = session.query(Show).get(current_show)
                if show and show.current_session_id:
                    show_session: ShowSession = session.query(ShowSession).get(
                        show.current_session_id
                    )
                    if show_session:
                        show_session.last_client_internal_id = (
                            show_session.client_internal_id
                        )
                    else:
                        get_logger().warning(
                            "Current show session not found. Resetting."
                        )
                        show.current_session_id = None
                    session.commit()

        # Clear out all sessions since we are starting the app up
        with self._db.sessionmaker() as session:
            get_logger().debug("Emptying out sessions table!")
            session.query(Session).delete()
            session.commit()

        # Get static files path - adjust for PyInstaller if needed
        if is_frozen():
            static_files_path = get_resource_path(os.path.join("static", "assets"))
            get_logger().info(f"Using packaged static files path: {static_files_path}")
        else:
            static_files_path = os.path.join(
                os.path.abspath(os.path.dirname(__file__)), "..", "static", "assets"
            )
            get_logger().info(f"Using relative static files path: {static_files_path}")

        handlers = Route.routes()
        handlers.append(("/favicon.ico", controllers.StaticController))
        handlers.append(
            (r"/assets/(.*)", StaticFileHandler, {"path": static_files_path})
        )
        handlers.append((r"/api/.*", controllers.ApiFallback))
        handlers.append((r"/(.*)", controllers.RootController))
        super().__init__(
            handlers=handlers,
            debug=debug,
            db=self._db,
            websocket_ping_interval=5,
            cookie_secret="DigiScriptSuperSecretValue123!",
            login_url="/login",
        )

    def log_request(self, handler):
        ignored_routes = Route.ignored_logging_routes()
        if handler.request.path in ignored_routes:
            return
        super().log_request(handler)

    @property
    def _alembic_config(self):
        # Handle path differently if running in PyInstaller bundle
        if is_frozen():
            # Look for alembic.ini in the PyInstaller bundle
            alembic_cfg_path = get_resource_path("alembic.ini")
            get_logger().info(f"Using bundled alembic.ini: {alembic_cfg_path}")
        else:
            # Use the standard path
            alembic_cfg_path = os.path.join(
                os.path.dirname(__file__), "..", "alembic.ini"
            )

        # Check if the file exists
        if not os.path.isfile(alembic_cfg_path):
            get_logger().error(f"Alembic config file not found: {alembic_cfg_path}")
            # If running in PyInstaller, try an absolute path as a fallback
            if is_frozen():
                import sys

                if hasattr(sys, "_MEIPASS"):
                    alt_path = os.path.join(sys._MEIPASS, "alembic.ini")
                    if os.path.isfile(alt_path):
                        alembic_cfg_path = alt_path
                        get_logger().info(
                            f"Found alternative alembic.ini: {alembic_cfg_path}"
                        )

        alembic_cfg = Config(alembic_cfg_path)

        # Override config options with specific ones based on this running instance
        alembic_cfg.set_main_option(
            "digiscript.config", self.digi_settings.settings_path
        )
        alembic_cfg.set_main_option("configure_logging", "False")

        # If running in PyInstaller, patch the script_location
        if is_frozen():
            # Get the script directory from the bundle
            script_location = get_resource_path("alembic")
            if os.path.isdir(script_location):
                alembic_cfg.set_main_option("script_location", script_location)
                get_logger().info(f"Set alembic script_location to: {script_location}")
            else:
                get_logger().warning(
                    f"Alembic script directory not found: {script_location}"
                )

        return alembic_cfg

    def _run_migrations(self):
        try:
            self._check_migrations()
        except DatabaseUpgradeRequired:
            get_logger().info("Running database migrations via Alembic")
            # Create a copy of the database file as a backup before performing migrations
            db_path: str = self.digi_settings.settings.get("db_path").get_value()
            if db_path.startswith("sqlite:///"):
                db_path = db_path.replace("sqlite:///", "")
            if os.path.exists(db_path) and os.path.isfile(db_path):
                get_logger().info("Creating copy of database file as backup")
                new_file_name = f"{db_path}.{int(time.time())}"
                shutil.copyfile(db_path, new_file_name)
                get_logger().info(
                    f"Created copy of database file as backup, saved to {new_file_name}"
                )
            else:
                get_logger().warning(
                    "Database connection does not appear to be a file, cannot create backup!"
                )
            # Run the upgrade on the database
            command.upgrade(self._alembic_config, "head")
        else:
            get_logger().info("No database migrations to perform")

    def _check_migrations(self):
        get_logger().info("Checking database migrations via Alembic")
        engine = sqlalchemy.create_engine(
            self.digi_settings.settings.get("db_path").get_value()
        )
        script_ = script.ScriptDirectory.from_config(self._alembic_config)
        with engine.begin() as conn:
            context = migration.MigrationContext.configure(conn)
            if context.get_current_revision() != script_.get_current_head():
                raise DatabaseUpgradeRequired("Migrations required on the database")

    async def configure(self):
        await self._configure_logging()

    async def _configure_logging(self):
        get_logger().info("Reconfiguring logging!")

        # Application logging
        log_path = await self.digi_settings.get("log_path")
        file_size = await self.digi_settings.get("max_log_mb")
        backups = await self.digi_settings.get("log_backups")
        if log_path:
            self.app_log_handler = configure_file_logging(
                log_path, file_size, backups, self.app_log_handler
            )

        # Database logging
        use_db_logging = await self.digi_settings.get("db_log_enabled")
        if use_db_logging:
            db_log_path = await self.digi_settings.get("db_log_path")
            db_file_size = await self.digi_settings.get("db_max_log_mb")
            db_backups = await self.digi_settings.get("db_log_backups")
            self.db_file_handler = configure_db_logging(
                log_path=db_log_path,
                max_size_mb=db_file_size,
                log_backups=db_backups,
                handler=self.db_file_handler,
            )

    def _configure_rbac(self):
        self._db.register_delete_hook(self.rbac.rbac_db.check_object_deletion)
        self.rbac.add_mapping(User, Show, [Show.id, Show.name])
        self.rbac.add_mapping(User, CueType, [CueType.id, CueType.prefix])
        self.rbac.add_mapping(User, Script, [Script.id])

    def _configure_jwt(self) -> JWTService:
        get_logger().info("Configuring JWT service")
        with self._db.sessionmaker() as session:
            jwt_secret = (
                session.query(SystemSettings)
                .filter(SystemSettings.key == "jwt_secret")
                .first()
            )
            if jwt_secret:
                get_logger().info("Retrieved JWT secret from database")
            else:
                get_logger().info("Generating new JWT secret")
                jwt_secret = SystemSettings(
                    key="jwt_secret", value=secrets.token_hex(32)
                )
                session.add(jwt_secret)
                session.commit()
                get_logger().info("JWT secret generated and stored in database")
        return JWTService(application=self)

    def regen_logging(self):
        if not IOLoop.current():
            get_logger().error(
                "Unable to regenerate logging as there is no current IOLoop"
            )
        else:
            IOLoop.current().add_callback(self._configure_logging)

    def validate_has_admin(self):
        if not IOLoop.current():
            get_logger().error(
                "Unable to validate admin user as there is no current IOLoop"
            )
        else:
            IOLoop.current().add_callback(self._validate_has_admin)

    def show_changed(self):
        if not IOLoop.current():
            get_logger().error(
                "Unable to initiate show change as there is no current IOLoop"
            )
        else:
            IOLoop.current().add_callback(self._show_changed)

    async def _validate_has_admin(self):
        with self.get_db().sessionmaker() as session:
            any_admin = session.query(User).filter(User.is_admin).first()
            has_admin = any_admin is not None
            await self.digi_settings.set("has_admin_user", has_admin)

    async def _show_changed(self):
        await self.ws_send_to_all("NOOP", "SHOW_CHANGED", {})

    def get_db(self) -> DigiSQLAlchemy:
        return self._db

    def get_all_ws(self, user_id: int) -> List[WebSocketController]:
        sockets = []
        for client in self.clients:
            # Check JWT-based authentication (stored in controller property)
            if hasattr(client, "current_user_id") and client.current_user_id == user_id:
                sockets.append(client)
        return sockets

    def get_ws(self, internal_uuid: str) -> Optional[WebSocketController]:
        for client in self.clients:
            if client.__getattribute__("internal_id") == internal_uuid:
                return client
        return None

    async def ws_send_to_all(self, ws_op: str, ws_action: str, ws_data: dict):
        for client in self.clients:
            await client.write_message(
                {"OP": ws_op, "DATA": ws_data, "ACTION": ws_action}
            )

    async def ws_send_to_user(
        self, user_id: int, ws_op: str, ws_action: str, ws_data: dict
    ):
        for client in self.get_all_ws(user_id):
            await client.write_message(
                {"OP": ws_op, "DATA": ws_data, "ACTION": ws_action}
            )
