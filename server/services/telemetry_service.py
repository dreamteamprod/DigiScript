"""Anonymous usage telemetry service.

Periodically POSTs a small envelope + DigiScript-specific metrics payload to the shared
``dreamteam-telemetry`` collector (``https://telemetry.digiscript.dreamteamprod.co.uk``). The
payload never contains show/script content, usernames, emails, or other identifying information —
just install-shape facts: version, OS, a randomly generated anonymous instance id, bucketed counts
rather than exact numbers, and feature-usage booleans. See DigiScript PR #1481 for the original
design discussion (this survives in git history; ``plans/`` itself is gitignored and does not).

The payload shape (envelope fields + the nested ``metrics`` object) must match the collector's own
``validateEnvelope`` / ``validateDigiscriptMetrics`` exactly — the collector rejects anything that
doesn't.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import platform
import random
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import func, select
from tornado.httpclient import AsyncHTTPClient, HTTPClientError
from tornado.ioloop import IOLoop, PeriodicCallback

from digi_server.logger import get_logger
from digi_server.settings import get_version
from models.session import ShowSession
from models.settings import SystemSettings
from models.show import Show
from models.user import User


if TYPE_CHECKING:
    from digi_server.app_server import DigiScriptServer


TELEMETRY_URL = "https://telemetry.digiscript.dreamteamprod.co.uk/v1/ping"


class _ErrorCountHandler(logging.Handler):
    """Counts ERROR-and-above log records emitted since the count was last read."""

    def __init__(self):
        super().__init__(level=logging.ERROR)
        self._count = 0

    def emit(self, record: logging.LogRecord) -> None:
        self._count += 1

    def pop_count(self) -> int:
        """Return the count accumulated since the last call, and reset it to zero."""
        count = self._count
        self._count = 0
        return count


class TelemetryService:
    """Builds and periodically sends the anonymous usage telemetry check-in."""

    DEFAULT_INTERVAL_MS = 24 * 60 * 60 * 1000  # ~daily
    MAX_INITIAL_JITTER_MS = (
        60 * 60 * 1000
    )  # up to 1 hour, to avoid a startup thundering herd
    REQUEST_TIMEOUT_SECONDS = 10.0
    MAX_ATTEMPTS = 3
    INITIAL_BACKOFF_SECONDS = 5

    def __init__(
        self, application: "DigiScriptServer", interval_ms: Optional[int] = None
    ):
        """
        Initialize the telemetry service.

        :param application: The DigiScript server application instance.
        :param interval_ms: Interval between check-ins in milliseconds. Defaults to ~daily.
        """
        self._application = application
        self._interval_ms = interval_ms or self.DEFAULT_INTERVAL_MS
        self._logger = get_logger(name="telemetry")
        # force_instance=True: without it, AsyncHTTPClient() returns one client cached per
        # IOLoop, which VersionChecker also constructs and uses. stop() closes this client;
        # sharing the cached instance would break VersionChecker's HTTP client too the moment
        # telemetry is toggled off while the server is running.
        self._http_client = AsyncHTTPClient(force_instance=True)
        self._periodic_callback: Optional[PeriodicCallback] = None
        self._error_handler = _ErrorCountHandler()
        self._startup_timeout_handle = None
        self._started = False
        self._stopped = False

    def start(self) -> None:
        """
        Attach the error counter and schedule check-ins, starting after a jittered delay.

        Idempotent: a second call while already started is a no-op, so callers (e.g. rapid
        enable/disable/enable via the settings toggle) can't end up with two independently
        running schedules.
        """
        if self._started:
            self._logger.debug(
                "Telemetry service already started; ignoring duplicate start()"
            )
            return
        self._started = True
        self._stopped = False

        # stop() closes and nulls this; rebuild it so a stop()-then-start() (e.g. toggling
        # the setting off then back on) actually sends check-ins again instead of silently
        # failing every attempt against a None client.
        if self._http_client is None:
            self._http_client = AsyncHTTPClient(force_instance=True)

        get_logger().addHandler(self._error_handler)

        jitter_seconds = random.uniform(0, self.MAX_INITIAL_JITTER_MS / 1000)
        self._logger.info(
            f"Telemetry service starting; first check-in in {jitter_seconds:.0f}s"
        )
        self._startup_timeout_handle = IOLoop.current().call_later(
            jitter_seconds, self._schedule_first_check_in
        )

    def _schedule_first_check_in(self) -> None:
        self._startup_timeout_handle = None
        if self._stopped:
            return
        IOLoop.current().add_callback(self._first_check_in)

    async def _first_check_in(self) -> None:
        if self._stopped:
            return
        try:
            await self.check_in()
        except Exception:
            # Backstop independent of check_in()'s own "never raises" handling: if that
            # contract is ever broken by a future change, a raise here must not silently
            # abort all future scheduling (it would otherwise be swallowed by Tornado's
            # add_callback machinery, logged under "tornado.application" rather than this
            # service's own logger, and invisible to _ErrorCountHandler).
            self._logger.exception("Unexpected error during first telemetry check-in")

        if self._stopped:
            return
        self._periodic_callback = PeriodicCallback(self.check_in, self._interval_ms)
        self._periodic_callback.start()

    def stop(self) -> None:
        """Stop the telemetry service and cancel scheduled check-ins."""
        self._stopped = True
        self._started = False

        if self._startup_timeout_handle is not None:
            IOLoop.current().remove_timeout(self._startup_timeout_handle)
            self._startup_timeout_handle = None

        if self._periodic_callback:
            self._periodic_callback.stop()
            self._periodic_callback = None

        if self._http_client:
            self._http_client.close()
            self._http_client = None

        get_logger().removeHandler(self._error_handler)
        self._logger.info("Telemetry service stopped")

    async def check_in(self) -> None:
        """
        Build the telemetry payload and send it, retrying with backoff on failure.

        Never raises — a failed check-in is logged and retried on the next scheduled cycle,
        and must never block startup or request handling.
        """
        try:
            payload = self._build_payload()
        except Exception:
            self._logger.exception(
                "Failed to build telemetry payload; skipping this check-in"
            )
            return

        body = json.dumps(payload)
        backoff_seconds = self.INITIAL_BACKOFF_SECONDS
        sent = False

        for attempt in range(self.MAX_ATTEMPTS):
            # A concurrent stop() (e.g. the retry's own asyncio.sleep below yielding to an
            # IOLoop callback that disables telemetry) nulls _http_client. Without this
            # check, the next attempt's .fetch() on None raises AttributeError, which the
            # broad except below would catch and misreport as an ordinary send failure.
            if self._stopped or self._http_client is None:
                self._logger.debug(
                    "Telemetry service stopped mid check-in; aborting remaining retries"
                )
                return

            try:
                await self._http_client.fetch(
                    TELEMETRY_URL,
                    method="POST",
                    body=body,
                    headers={"Content-Type": "application/json"},
                    request_timeout=self.REQUEST_TIMEOUT_SECONDS,
                )
                sent = True
                break
            except HTTPClientError as e:
                self._logger.warning(
                    f"Telemetry check-in failed (HTTP {e.code}), "
                    f"attempt {attempt + 1}/{self.MAX_ATTEMPTS}"
                )
            except Exception as e:
                self._logger.warning(
                    f"Telemetry check-in failed ({e}), "
                    f"attempt {attempt + 1}/{self.MAX_ATTEMPTS}"
                )

            if attempt < self.MAX_ATTEMPTS - 1:
                await asyncio.sleep(backoff_seconds)
                backoff_seconds *= 2

        if not sent:
            self._logger.warning(
                "Telemetry check-in failed after all attempts; will retry next cycle"
            )
            return

        self._logger.debug("Telemetry check-in sent successfully")

        # Deliberately outside the retry loop and its try/except above: a failure here is a
        # local DB problem, not a network one, and retrying would just re-POST the same
        # already-sent payload to the external collector — a duplicate submission that
        # retrying can't actually fix.
        try:
            with self._application.get_db().sessionmaker() as session:
                self._set_checkin_count(session, payload["checkin_count"])
        except Exception:
            self._logger.exception(
                "Telemetry check-in sent, but failed to persist checkin_count locally"
            )

    def _build_payload(self) -> dict:
        """
        Build the full check-in payload: the generic envelope plus DigiScript's own metrics.

        :returns: A dict matching the collector's validateEnvelope/validateDigiscriptMetrics
            shape exactly — envelope fields at the top level, DigiScript-specific fields
            nested under "metrics".
        """
        error_count_recent = self._error_handler.pop_count()

        with self._application.get_db().sessionmaker() as session:
            instance_id = self._get_or_create_instance_id(session)
            first_seen_at = self._get_or_create_first_seen_at(session)
            checkin_count = self._get_checkin_count(session) + 1

            shows_count = session.execute(
                select(func.count()).select_from(Show)
            ).scalar_one()
            users_count = session.execute(
                select(func.count()).select_from(User)
            ).scalar_one()
            sessions_count = session.execute(
                select(func.count()).select_from(ShowSession)
            ).scalar_one()
            rbac_enabled = self._compute_rbac_enabled(session)

        days_since_install = max(
            0,
            (datetime.now(timezone.utc) - datetime.fromisoformat(first_seen_at)).days,
        )

        return {
            "instance_id": instance_id,
            "app_version": get_version(),
            "os_platform": platform.system(),
            "os_arch": platform.machine(),
            "deployment_method": (
                "docker" if os.path.exists("/.dockerenv") else "bare-metal"
            ),
            "days_since_install": days_since_install,
            "checkin_count": checkin_count,
            "error_count_recent": error_count_recent,
            "metrics": {
                "shows_bucket": self._bucket_small(shows_count),
                "users_bucket": self._bucket_users(users_count),
                "sessions_bucket": self._bucket_small(sessions_count),
                "rbac_enabled": rbac_enabled,
                # The collaborative editor (RoomManager/ScriptDraft) exists, but drafts are
                # transient — cleaned up on save/discard — so a current-row count would read
                # near-zero even for heavy users. Needs a persistent "ever used" flag set from
                # the save path to do this properly; hardcoded until that's built.
                "collab_editing_used": False,
            },
        }

    @staticmethod
    def _get_system_setting(session, key: str) -> Optional[str]:
        row = session.scalars(
            select(SystemSettings).where(SystemSettings.key == key)
        ).first()
        return row.value if row else None

    @staticmethod
    def _set_system_setting(session, key: str, value: str) -> None:
        row = session.scalars(
            select(SystemSettings).where(SystemSettings.key == key)
        ).first()
        if row:
            row.value = value
        else:
            session.add(SystemSettings(key=key, value=value))
        session.commit()

    def _get_or_create_instance_id(self, session) -> str:
        """
        Read the persisted anonymous instance UUID, generating it on first use.

        Stored in the DB-backed SystemSettings table (like jwt_secret/cookie_secret), not the
        file-based Settings system — that system backs the editable digiscript.json, which is
        the wrong place for internal state nobody should be hand-editing.

        :param session: Open SQLAlchemy session.
        :returns: The persisted (or newly generated) instance UUID.
        """
        instance_id = self._get_system_setting(session, "telemetry_instance_id")
        if not instance_id:
            instance_id = str(uuid.uuid4())
            self._set_system_setting(session, "telemetry_instance_id", instance_id)
        return instance_id

    def _get_or_create_first_seen_at(self, session) -> str:
        """
        Read the persisted first-check-in timestamp, generating it on first use.

        Used as the anchor for ``days_since_install`` — strictly "first time telemetry ran",
        not necessarily the true install date if telemetry was initially disabled.

        :param session: Open SQLAlchemy session.
        :returns: ISO 8601 timestamp string.
        """
        first_seen_at = self._get_system_setting(session, "telemetry_first_seen_at")
        if not first_seen_at:
            first_seen_at = datetime.now(timezone.utc).isoformat()
            self._set_system_setting(session, "telemetry_first_seen_at", first_seen_at)
        return first_seen_at

    def _get_checkin_count(self, session) -> int:
        """
        :param session: Open SQLAlchemy session.
        :returns: The persisted check-in count, or 0 if none has been recorded yet.
        """
        value = self._get_system_setting(session, "telemetry_checkin_count")
        return int(value) if value else 0

    def _set_checkin_count(self, session, count: int) -> None:
        """
        :param session: Open SQLAlchemy session.
        :param count: New check-in count to persist.
        """
        self._set_system_setting(session, "telemetry_checkin_count", str(count))

    RBAC_DELIBERATE_USE_KEY = "telemetry_rbac_deliberately_used"

    def _compute_rbac_enabled(self, session) -> bool:
        """
        Whether an admin has ever deliberately granted an RBAC role via the dedicated RBAC
        management endpoint, as opposed to the automatic self-grant every cue-type creator
        gets (controllers/api/v1/show/cues.py's give_role call).

        Backed by a persisted flag (see mark_rbac_deliberately_used) rather than querying the
        rbac_* tables directly. A row-counting heuristic can't actually distinguish genuine
        RBAC administration from two unrelated people each independently creating their own
        cue type: each gets auto-granted a role on their own creation, which produces more
        than one distinct user with an active role despite zero deliberate administration —
        no row-level signal can tell those two situations apart, since neither the RBAC
        tables nor the resources they reference record how a grant was made. The flag sidesteps
        this entirely by being set only from RBACRolesGrantHandler, the sole @require_admin
        -gated role-grant code path in the app.

        :param session: Open SQLAlchemy session.
        :returns: True if an admin has ever used the RBAC grant endpoint.
        """
        return self._get_system_setting(session, self.RBAC_DELIBERATE_USE_KEY) == "1"

    @staticmethod
    def mark_rbac_deliberately_used(session) -> None:
        """
        Record that an admin has deliberately granted an RBAC role via the dedicated RBAC
        management endpoint. Call this only from that code path (RBACRolesGrantHandler) —
        never from an auto-grant call site, or it defeats the whole point of the flag.

        :param session: Open SQLAlchemy session.
        """
        TelemetryService._set_system_setting(
            session, TelemetryService.RBAC_DELIBERATE_USE_KEY, "1"
        )

    @staticmethod
    def _bucket_small(count: int) -> str:
        """Bucket a count into '1' / '2-5' / '6+'. A count of 0 is folded into '1'."""
        if count <= 1:
            return "1"
        if count <= 5:
            return "2-5"
        return "6+"

    @staticmethod
    def _bucket_users(count: int) -> str:
        """Bucket a count into '1' / '2-5' / '6-20' / '21+'. A count of 0 is folded into '1'."""
        if count <= 1:
            return "1"
        if count <= 5:
            return "2-5"
        if count <= 20:
            return "6-20"
        return "21+"
