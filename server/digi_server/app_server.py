import glob
import os
import secrets
import shutil
import sys
import time
from typing import List, Optional

import sqlalchemy
from alembic import command, script
from alembic.config import Config
from alembic.runtime import migration
from sqlalchemy import Column, String, delete, select
from tornado.ioloop import IOLoop
from tornado.web import Application, StaticFileHandler
from tornado_prometheus import PrometheusMixIn

from controllers import controllers
from controllers.ws_controller import WebSocketController
from digi_server.logger import (
    configure_db_logging,
    configure_file_logging,
    configure_log_level,
    get_logger,
)
from digi_server.settings import Settings
from models import models
from models.cue import CueType
from models.script import CompiledScript, Script
from models.script_draft import ScriptDraft
from models.session import Session, ShowSession
from models.settings import SystemSettings
from models.show import Show
from models.user import User
from rbac.rbac import RBACController
from services.user_service import UserService
from utils.database import DigiSQLAlchemy
from utils.exceptions import DatabaseTypeException, DatabaseUpgradeRequired
from utils.mdns_service import MDNSAdvertiser
from utils.module_discovery import get_resource_path, is_frozen
from utils.script_room_manager import RoomManager
from utils.version_checker import VersionChecker
from utils.web.jwt_service import JWTService
from utils.web.route import Route


class DigiScriptServer(PrometheusMixIn, Application):
    def __init__(
        self,
        port: int,
        debug=False,
        settings_path=None,
        skip_migrations=False,
        skip_migrations_check=False,
    ):
        self._port: int = port
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
        self.room_manager: Optional[RoomManager] = None
        self.mdns_advertiser: Optional[MDNSAdvertiser] = None
        self.version_checker: Optional[VersionChecker] = None

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

        # Configure the User service
        self.user_service = UserService(self)

        # On startup, perform the following checks/operations with the database:
        with self._db.sessionmaker() as session:
            # 1. Check for presence of admin user, and update settings to match
            any_admin = session.scalars(select(User).where(User.is_admin)).first()
            has_admin = any_admin is not None
            self.digi_settings.settings["has_admin_user"].set_value(has_admin, False)
            self.digi_settings._save()

            # 2. Check the show we are expecting to be loaded exists
            current_show = self.digi_settings.settings.get("current_show").get_value()
            if current_show:
                show = session.get(Show, current_show)
                if not show:
                    get_logger().warning(
                        "Current show from settings not found. Resetting."
                    )
                    self.digi_settings.settings["current_show"].set_to_default()
                    self.digi_settings._save()
                    current_show = None

            # 3. If there is a live session in progress:
            # 3.1. Clean up the current client ID
            # 3.2. Check that the revision of the script matches the current one,
            #      if not then load the revision being used
            if current_show:
                show = session.get(Show, current_show)
                if show.current_session_id:
                    show_session: ShowSession = session.get(
                        ShowSession, show.current_session_id
                    )
                    if show_session:
                        show_session.last_client_internal_id = (
                            show_session.client_internal_id
                        )

                        scripts: List[Script] = session.scalars(
                            select(Script).where(Script.show_id == show.id)
                        ).all()
                        if len(scripts) != 1:
                            get_logger().error(
                                "Unable to validate live session script revision, "
                                "show does not have exactly one script. Resetting."
                            )
                            show.current_session_id = None
                        else:
                            current_script: Script = scripts[0]
                            if (
                                show_session.script_revision_id
                                != current_script.current_revision
                            ):
                                get_logger().warning(
                                    "Live session script revision does not match "
                                    "current script revision. Updating to use "
                                    "current script revision."
                                )
                                current_script.current_revision = (
                                    show_session.script_revision_id
                                )
                    else:
                        get_logger().error("Current show session not found. Resetting.")
                        show.current_session_id = None
                    session.commit()

            # 4. Tidy up compiled scripts
            # 4.1. Remove any compiled scripts objects where the data file is missing
            # 4.2. Remove any compiled script files on disk that are not referenced
            removed_compiled_scripts = []
            compiled_scripts: List[CompiledScript] = session.scalars(
                select(CompiledScript)
            ).all()
            for compiled_script in compiled_scripts:
                if not os.path.exists(compiled_script.data_path):
                    get_logger().info(
                        f"Removing compiled script for revision {compiled_script.revision_id} "
                        f"as data file not found at {compiled_script.data_path}"
                    )
                    session.delete(compiled_script)
                    removed_compiled_scripts.append(compiled_script)
            if removed_compiled_scripts:
                session.commit()
                get_logger().info(
                    f"Removed {len(removed_compiled_scripts)} compiled script objects from the database."
                )

            compiled_script_path = self.digi_settings.settings.get(
                "compiled_script_path"
            ).get_value()
            for ds_file in glob.glob(f"{compiled_script_path}/*.ds"):
                found = False
                for compiled_script in compiled_scripts:
                    if compiled_script in removed_compiled_scripts:
                        continue
                    if compiled_script.data_path == ds_file:
                        found = True
                        break
                if not found:
                    get_logger().info(
                        f"Removing unreferenced compiled script file: {ds_file}"
                    )
                    try:
                        os.remove(ds_file)
                    except Exception:
                        get_logger().exception(
                            f"Failed to remove compiled script file: {ds_file}"
                        )

            # 4.5. Tidy up draft script files (same pattern as compiled scripts)
            draft_script_path = self.digi_settings.settings.get(
                "draft_script_path"
            ).get_value()
            os.makedirs(draft_script_path, exist_ok=True)

            removed_drafts = []
            drafts: List[ScriptDraft] = session.scalars(select(ScriptDraft)).all()
            for draft in drafts:
                if not draft.data_path or not os.path.exists(draft.data_path):
                    get_logger().info(
                        f"Removing draft record for revision {draft.revision_id} "
                        f"as data file not found at {draft.data_path}"
                    )
                    session.delete(draft)
                    removed_drafts.append(draft)
            if removed_drafts:
                session.commit()
                get_logger().info(
                    f"Removed {len(removed_drafts)} stale draft records from the database."
                )

            for draft_file in glob.glob(f"{draft_script_path}/*.yjs"):
                found = False
                for draft in drafts:
                    if draft in removed_drafts:
                        continue
                    if draft.data_path == draft_file:
                        found = True
                        break
                if not found:
                    get_logger().info(f"Removing unreferenced draft file: {draft_file}")
                    try:
                        os.remove(draft_file)
                    except Exception:
                        get_logger().exception(
                            f"Failed to remove draft file: {draft_file}"
                        )

            # 5. Clear out all sessions since we are starting the app up
            get_logger().debug("Emptying out sessions table!")
            session.execute(delete(Session))
            session.commit()

        # Initialize the RoomManager for collaborative editing
        self.room_manager = RoomManager(self)
        self.room_manager.start()

        # Get static files path - adjust for PyInstaller if needed
        if is_frozen():
            static_files_path = get_resource_path(os.path.join("static", "assets"))
            docs_files_path = get_resource_path(os.path.join("static", "docs"))
            get_logger().info(f"Using packaged static files path: {static_files_path}")
            get_logger().info(f"Using packaged docs files path: {docs_files_path}")
        else:
            static_files_path = os.path.join(
                os.path.abspath(os.path.dirname(__file__)), "..", "static", "assets"
            )
            docs_files_path = os.path.join(
                os.path.abspath(os.path.dirname(__file__)), "..", "static", "docs"
            )
            get_logger().info(f"Using relative static files path: {static_files_path}")
            get_logger().info(f"Using relative docs files path: {docs_files_path}")

        handlers = Route.routes()
        handlers.append(("/favicon.ico", controllers.StaticController))
        handlers.append(
            (r"/assets/(.*)", StaticFileHandler, {"path": static_files_path})
        )
        handlers.append((r"/docs/(.*)", StaticFileHandler, {"path": docs_files_path}))
        handlers.append((r"/api/.*", controllers.ApiFallback))
        handlers.append((r"/(.*)", controllers.RootController))
        super().__init__(
            handlers=handlers,
            debug=debug,
            db=self._db,
            websocket_ping_interval=5,
            cookie_secret=self._get_cookie_secret(),
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
                if hasattr(sys, "_MEIPASS"):
                    alt_path = os.path.join(getattr(sys, "_MEIPASS"), "alembic.ini")
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
        await self.start_mdns_advertising()
        await self.start_version_checker()

    async def _configure_logging(self):
        get_logger().info("Reconfiguring logging!")

        # Application logging
        log_path = await self.digi_settings.get("log_path")
        file_size = await self.digi_settings.get("max_log_mb")
        backups = await self.digi_settings.get("log_backups")
        log_level = await self.digi_settings.get("log_level")
        if log_path:
            self.app_log_handler = configure_file_logging(
                log_path=log_path,
                max_size_mb=file_size,
                log_backups=backups,
                handler=self.app_log_handler,
            )
        configure_log_level(log_level)

        # Database logging
        use_db_logging = await self.digi_settings.get("db_log_enabled")
        db_log_path = await self.digi_settings.get("db_log_path")
        db_file_size = await self.digi_settings.get("db_max_log_mb")
        db_backups = await self.digi_settings.get("db_log_backups")
        self.db_file_handler = configure_db_logging(
            log_path=db_log_path,
            max_size_mb=db_file_size,
            log_backups=db_backups,
            handler=self.db_file_handler,
            log_level=log_level,
            enable_db_logging=use_db_logging,
        )

    def _configure_rbac(self):
        self._db.register_delete_hook(self.rbac.rbac_db.check_object_deletion)
        self.rbac.add_mapping(User, Show, [Show.id, Show.name])
        self.rbac.add_mapping(User, CueType, [CueType.id, CueType.prefix])
        self.rbac.add_mapping(User, Script, [Script.id])

    def _configure_jwt(self) -> JWTService:
        get_logger().info("Configuring JWT service")
        with self._db.sessionmaker() as session:
            jwt_secret = session.scalars(
                select(SystemSettings).where(SystemSettings.key == "jwt_secret")
            ).first()
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

    def _get_cookie_secret(self) -> str:
        get_logger().info("Getting cookie secret")
        with self._db.sessionmaker() as session:
            cookie_secret = session.scalars(
                select(SystemSettings).where(SystemSettings.key == "cookie_secret")
            ).first()
            if cookie_secret:
                get_logger().info("Retrieved cookie secret from database")
            else:
                get_logger().info("Generating new cookie secret")
                cookie_secret = SystemSettings(
                    key="cookie_secret", value=secrets.token_urlsafe(32)
                )
                session.add(cookie_secret)
                session.commit()
                get_logger().info("Cookie secret generated and stored in database")
        return cookie_secret.value

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
            any_admin = session.scalars(select(User).where(User.is_admin)).first()
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

    async def start_mdns_advertising(self) -> None:
        """Start mDNS advertising if enabled in settings."""
        # Check if mDNS advertising is enabled
        mdns_enabled = await self.digi_settings.get("mdns_advertising")
        if not mdns_enabled:
            get_logger().info("mDNS advertising is disabled in settings")
            return

        # Initialize and start the advertiser
        if not self.mdns_advertiser:
            self.mdns_advertiser = MDNSAdvertiser(port=self._port)

        await self.mdns_advertiser.start()

    async def stop_mdns_advertising(self) -> None:
        """Stop mDNS advertising if it's running."""
        if self.mdns_advertiser:
            await self.mdns_advertiser.stop()
            self.mdns_advertiser = None

    def toggle_mdns_advertising(self) -> None:
        """
        Callback for when mdns_advertising setting changes.

        Starts or stops mDNS advertising based on the current setting value.
        """
        if not IOLoop.current():
            get_logger().error(
                "Unable to toggle mDNS advertising as there is no current IOLoop"
            )
        else:
            IOLoop.current().add_callback(self._toggle_mdns_advertising)

    async def _toggle_mdns_advertising(self) -> None:
        """Internal async implementation of toggle_mdns_advertising."""
        mdns_enabled = await self.digi_settings.get("mdns_advertising")

        if mdns_enabled:
            # Start advertising
            if not self.mdns_advertiser:
                self.mdns_advertiser = MDNSAdvertiser(port=self._port)
            await self.mdns_advertiser.start()
        else:
            # Stop advertising
            await self.stop_mdns_advertising()

    async def start_version_checker(self) -> None:
        """Start the version checker service."""
        if not self.version_checker:
            self.version_checker = VersionChecker(application=self)

        await self.version_checker.start()

    async def stop_version_checker(self) -> None:
        """Stop the version checker service if it's running."""
        if self.version_checker:
            await self.version_checker.stop()
            self.version_checker = None
