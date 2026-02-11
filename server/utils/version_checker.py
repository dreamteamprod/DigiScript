from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from tornado.httpclient import AsyncHTTPClient, HTTPClientError
from tornado.ioloop import PeriodicCallback

from digi_server.logger import get_logger
from digi_server.settings import get_version


if TYPE_CHECKING:
    from digi_server.app_server import DigiScriptServer


class VersionStatus:
    def __init__(
        self,
        current_version: str,
        latest_version: Optional[str] = None,
        update_available: bool = False,
        release_url: Optional[str] = None,
        last_checked: Optional[datetime] = None,
        check_error: Optional[str] = None,
    ):
        self.current_version = current_version
        self.latest_version = latest_version
        self.update_available = update_available
        self.release_url = release_url
        self.last_checked = last_checked
        self.check_error = check_error

    def as_json(self) -> dict:
        """
        Serialize version status to JSON-compatible dictionary.

        :returns: Dictionary with version status fields.
        """
        return {
            "current_version": self.current_version,
            "latest_version": self.latest_version,
            "update_available": self.update_available,
            "release_url": self.release_url,
            "last_checked": (
                self.last_checked.isoformat() if self.last_checked else None
            ),
            "check_error": self.check_error,
        }


class VersionChecker:
    GITHUB_API_URL = (
        "https://api.github.com/repos/dreamteamprod/DigiScript/releases/latest"
    )
    DEFAULT_CHECK_INTERVAL_MS = 60 * 60 * 1000

    def __init__(
        self,
        application: "DigiScriptServer",
        check_interval_ms: Optional[int] = None,
    ):
        """
        Initialize the version checker.

        :param application: The DigiScript server application instance.
        :param check_interval_ms: Interval between checks in milliseconds.
            Defaults to 1 hour.
        """
        self._application = application
        self._check_interval_ms = check_interval_ms or self.DEFAULT_CHECK_INTERVAL_MS
        self._logger = get_logger(name="version_checker")
        self._http_client = AsyncHTTPClient()
        self._periodic_callback: Optional[PeriodicCallback] = None

        # Initialize status with current version
        self._status = VersionStatus(current_version=get_version())

    @property
    def status(self) -> VersionStatus:
        """Get the current version status."""
        return self._status

    async def start(self) -> None:
        """
        Start the version checker.

        Performs an initial check and schedules periodic checks.
        """
        self._logger.info("Starting version checker service")

        # Perform initial check
        await self.check_for_updates()

        # Schedule periodic checks
        self._periodic_callback = PeriodicCallback(
            self.check_for_updates,
            self._check_interval_ms,
        )
        self._periodic_callback.start()

        self._logger.info(
            f"Version checker started (interval: {self._check_interval_ms // 1000}s)"
        )

    async def stop(self) -> None:
        """Stop the version checker and cancel periodic checks."""
        if self._periodic_callback:
            self._periodic_callback.stop()
            self._periodic_callback = None

        if self._http_client:
            self._http_client.close()
            self._http_client = None

        self._logger.info("Version checker stopped")

    async def check_for_updates(self) -> VersionStatus:
        """
        Check GitHub for the latest release version.

        :returns: Updated VersionStatus with check results.
        """
        self._logger.debug("Checking for updates...")

        current_version = get_version()

        try:
            response = await self._http_client.fetch(
                self.GITHUB_API_URL,
                headers={
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": f"DigiScript/{current_version}",
                },
                request_timeout=10.0,
            )

            release_data = json.loads(response.body.decode("utf-8"))
            latest_version = release_data.get("tag_name", "").lstrip("v")
            release_url = release_data.get("html_url")

            # Compare versions
            update_available = self._is_newer_version(latest_version, current_version)

            self._status = VersionStatus(
                current_version=current_version,
                latest_version=latest_version,
                update_available=update_available,
                release_url=release_url,
                last_checked=datetime.now(timezone.utc),
                check_error=None,
            )

            if update_available:
                self._logger.info(
                    f"Update available: {current_version} -> {latest_version}"
                )
            else:
                self._logger.debug(f"Running latest version: {current_version}")

        except HTTPClientError as e:
            error_msg = f"HTTP error checking for updates: {e.code}"
            self._logger.warning(error_msg)
            self._status = VersionStatus(
                current_version=current_version,
                latest_version=self._status.latest_version,
                update_available=self._status.update_available,
                release_url=self._status.release_url,
                last_checked=datetime.now(timezone.utc),
                check_error=error_msg,
            )

        except Exception as e:
            error_msg = f"Unable to check for updates: {str(e)}"
            self._logger.warning(error_msg)
            self._status = VersionStatus(
                current_version=current_version,
                latest_version=self._status.latest_version,
                update_available=self._status.update_available,
                release_url=self._status.release_url,
                last_checked=datetime.now(timezone.utc),
                check_error=error_msg,
            )

        return self._status

    def _is_newer_version(self, latest: str, current: str) -> bool:
        """
        Compare version strings to determine if an update is available.

        Uses simple semantic version comparison (major.minor.patch).
        Handles pre-release suffixes (e.g., "1.0.0-beta") by stripping them.

        :param latest: The latest version string from GitHub.
        :param current: The current running version string.
        :returns: True if latest is newer than current.
        """
        try:
            # Strip pre-release suffixes (everything after -)
            latest_clean = latest.split("-", maxsplit=1)[0]
            current_clean = current.split("-", maxsplit=1)[0]

            latest_parts = [int(x) for x in latest_clean.split(".")]
            current_parts = [int(x) for x in current_clean.split(".")]

            # Pad shorter version with zeros
            max_len = max(len(latest_parts), len(current_parts))
            latest_parts.extend([0] * (max_len - len(latest_parts)))
            current_parts.extend([0] * (max_len - len(current_parts)))

            return latest_parts > current_parts
        except (ValueError, AttributeError):
            # If parsing fails, assume no update available
            self._logger.warning(
                f"Failed to parse versions: latest={latest}, current={current}"
            )
            return False
