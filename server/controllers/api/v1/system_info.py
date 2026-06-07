import socket

from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import api_authenticated, require_admin


# Well-known public DNS address used only to determine the local outbound interface.
# No data is ever sent — the UDP socket is closed immediately after getsockname().
_PROBE_HOST = "8.8.8.8"
_PROBE_PORT = 80


@ApiRoute("system/info", ApiVersion.V1)
class SystemInfoController(BaseAPIController):
    @api_authenticated
    @require_admin
    async def get(self):
        """
        Get server network information.

        Returns the server's fully-qualified hostname, primary outbound IP address,
        and the port it is listening on.

        :returns: JSON response with hostname, ip_address, and port.
        """
        await self.finish(
            {
                "hostname": socket.getfqdn(),
                "ip_address": _get_primary_ip(),
                "port": self.application._port,
            }
        )


def _get_primary_ip() -> str:
    """
    Return the primary outbound IP address.

    Uses the connect-to-8.8.8.8 trick: opening a UDP socket and calling connect()
    causes the OS to select the correct source address without sending any data.

    :returns: IP address string, or ``"Unknown"`` on failure.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect((_PROBE_HOST, _PROBE_PORT))
            return s.getsockname()[0]
        finally:
            s.close()
    except Exception:
        return "Unknown"
