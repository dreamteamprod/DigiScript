from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import api_authenticated, require_admin


@ApiRoute("version/status", ApiVersion.V1)
class VersionStatusController(BaseAPIController):
    @api_authenticated
    async def get(self):
        """
        Get the current version status.

        Returns information about the running version, latest available version,
        whether an update is available, and when the last check occurred.

        :returns: JSON response with version status.
        """
        version_checker = self.application.version_checker
        if not version_checker:
            await self.finish(
                {
                    "error": "Version checker not initialized",
                    "current_version": None,
                    "latest_version": None,
                    "update_available": False,
                    "release_url": None,
                    "last_checked": None,
                    "check_error": "Service not available",
                }
            )
            return

        await self.finish(version_checker.status.as_json())


@ApiRoute("version/check", ApiVersion.V1)
class VersionCheckController(BaseAPIController):
    @api_authenticated
    @require_admin
    async def post(self):
        """
        Trigger a manual version check.

        Forces an immediate check against the GitHub API, updating the
        cached version status.

        :returns: JSON response with updated version status.
        """
        version_checker = self.application.version_checker
        if not version_checker:
            self.set_status(503)
            await self.finish(
                {
                    "error": "Version checker not initialized",
                }
            )
            return

        status = await version_checker.check_for_updates()
        await self.finish(status.as_json())
