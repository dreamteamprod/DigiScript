import asyncio
import os
import time
from typing import Optional

from sqlalchemy import text
from tornado.ioloop import IOLoop

from digi_server.logger import get_logger
from digi_server.settings import get_version
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion


# Upper bound on the database probe so a locked database cannot hang the endpoint.
DB_CHECK_TIMEOUT_SECONDS = 3.0

# Settings naming a file whose parent directory must be writable.
_STORAGE_FILE_SETTINGS = ("log_path", "db_log_path", "client_log_path")
# Settings naming a directory that must be writable.
_STORAGE_DIR_SETTINGS = ("draft_script_path", "compiled_script_path")

_STARTED_AT = time.monotonic()


def _writable(path: str) -> bool:
    """Check that ``path`` (or its nearest existing ancestor) is writable.

    Directories that have not been created yet are judged by the closest
    ancestor that exists, since the server would create them on demand.

    :param path: Directory path to check.
    :returns: ``True`` if the directory could be written to.
    """
    path = os.path.abspath(path)
    while not os.path.exists(path):
        parent = os.path.dirname(path)
        if parent == path:
            return False
        path = parent
    return os.path.isdir(path) and os.access(path, os.W_OK | os.X_OK)


@ApiRoute("health", ApiVersion.V1, ignore_logging=True)
class HealthController(BaseAPIController):
    """Unauthenticated liveness/readiness probe.

    Responds ``200`` with ``status: "ok"`` when the database and storage
    locations are usable, otherwise ``503`` with ``status: "degraded"``.
    Failure detail is only ever logged server-side, never returned.
    """

    async def prepare(self):
        """Skip authentication so a broken database cannot fail the probe itself."""

    def _check_database_sync(self) -> None:
        with self.make_session() as session:
            session.execute(text("SELECT 1"))

    async def _check_database(self) -> bool:
        """Run ``SELECT 1`` off the event loop with a bounded wait.

        :returns: ``True`` if the query succeeded in time.
        """
        try:
            await asyncio.wait_for(
                IOLoop.current().run_in_executor(None, self._check_database_sync),
                timeout=DB_CHECK_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            get_logger().error(
                f"Health check: database probe timed out after "
                f"{DB_CHECK_TIMEOUT_SECONDS}s"
            )
            return False
        except Exception as e:  # noqa: BLE001
            get_logger().error(f"Health check: database probe failed: {e!r}")
            return False
        return True

    @staticmethod
    def _setting(settings, key: str) -> Optional[str]:
        try:
            return settings.get_sync(key)
        except KeyError:
            return None

    def _check_storage(self) -> bool:
        """Check the log, draft and compiled script locations are writable.

        :returns: ``True`` if every configured location is writable.
        """
        settings = self.application.digi_settings
        targets = []
        for key in _STORAGE_FILE_SETTINGS:
            value = self._setting(settings, key)
            if value:
                targets.append((key, os.path.dirname(os.path.abspath(value))))
        for key in _STORAGE_DIR_SETTINGS:
            value = self._setting(settings, key)
            if value:
                targets.append((key, value))

        ok = True
        for key, directory in targets:
            if not _writable(directory):
                get_logger().warning(
                    f"Health check: storage for '{key}' is not writable: {directory}"
                )
                ok = False
        return ok

    async def get(self):
        db_ok = await self._check_database()
        storage_ok = self._check_storage()
        healthy = db_ok and storage_ok

        if not healthy:
            self.set_status(503)
        await self.finish(
            {
                "version": get_version(),
                "status": "ok" if healthy else "degraded",
                "checks": {
                    "database": "ok" if db_ok else "fail",
                    "storage": "ok" if storage_ok else "fail",
                },
                "uptime_seconds": int(time.monotonic() - _STARTED_AT),
            }
        )
