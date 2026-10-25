import asyncio
import os
import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Optional

from sqlalchemy import text

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

# A single dedicated worker so a hung probe can never occupy more than one
# thread, nor starve the shared default executor.
_PROBE_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="health-probe")
_probe: Optional[Future] = None


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
        """Read the schema table of the database on a pooled connection.

        Querying ``sqlite_master`` forces SQLite to read the database file
        header and schema, so a locked or corrupt file fails here, unlike a
        bare ``SELECT 1`` which may never touch the file.

        :raises Exception: Any database error, handled by the caller.
        """
        with self.make_session() as session:
            session.execute(text("SELECT 1 FROM sqlite_master LIMIT 1"))

    async def _check_database(self) -> bool:
        """Probe the database off the event loop with a bounded wait.

        Probes are single-flight on a dedicated one-thread executor: a timed
        out probe cannot be cancelled (its thread keeps running), so while one
        is in flight, overlapping callers await that same probe (shielded, so
        one caller's timeout never cancels it) rather than starting another.
        This caps leaked threads and connections at one without reporting a
        healthy database as failed for merely overlapping polls. Every caller
        is still bounded by its own timeout.

        :returns: ``True`` if the query succeeded in time.
        """
        global _probe  # noqa: PLW0603
        if _probe is None or _probe.done():
            _probe = _PROBE_EXECUTOR.submit(self._check_database_sync)
        probe = _probe
        try:
            await asyncio.wait_for(
                asyncio.shield(asyncio.wrap_future(probe)),
                timeout=DB_CHECK_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            get_logger().error(
                f"Health check: database probe timed out after "
                f"{DB_CHECK_TIMEOUT_SECONDS}s"
            )
            return False
        except Exception as e:
            get_logger().error(
                f"Health check: database probe failed: {e!r}", exc_info=True
            )
            return False
        return True

    @staticmethod
    def _setting(settings, key: str) -> Optional[str]:
        """Read a setting without raising for unknown keys.

        :param settings: The application settings object.
        :param key: Setting name.
        :returns: The setting value, or ``None`` if the setting is not defined.
        """
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
        try:
            storage_ok = self._check_storage()
        except Exception:
            get_logger().error("Health check: storage check raised", exc_info=True)
            storage_ok = False
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

    def write_error(self, status_code: int, **kwargs) -> None:
        """Never serve a traceback or error text, even with ``serve_traceback`` on.

        Server errors become a minimal degraded body; client errors (such as
        405) keep Tornado's default handling.

        :param status_code: HTTP status of the error.
        """
        if status_code < 500:
            super().write_error(status_code, **kwargs)
            return
        self.set_status(503)
        self.finish(
            {
                "version": get_version(),
                "status": "degraded",
                "checks": {"database": "unknown", "storage": "unknown"},
            }
        )
