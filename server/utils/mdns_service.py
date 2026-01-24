"""
mDNS Service Advertising

Advertises the DigiScript server on the local network using mDNS/Bonjour/Zeroconf.
This allows Electron desktop clients to discover the server automatically.
"""

import socket
from typing import Optional

from zeroconf import IPVersion, ServiceInfo
from zeroconf.asyncio import AsyncZeroconf

from digi_server.logger import get_logger


class MDNSAdvertiser:
    """Advertises DigiScript server via mDNS/DNS-SD for network discovery."""

    def __init__(self, port: int, server_name: Optional[str] = None):
        """
        Initialize mDNS advertiser.

        Args:
            port: HTTP server port
            server_name: Optional custom server name (defaults to hostname)
        """
        self.port = port
        self.server_name = server_name or socket.gethostname()
        self.aiozc: Optional[AsyncZeroconf] = None
        self.service_info: Optional[ServiceInfo] = None
        self._logger = get_logger(name="mdns")

    async def start(self) -> None:
        """Start advertising the DigiScript server via mDNS."""
        try:
            # Initialize AsyncZeroconf for use with asyncio event loops
            self.aiozc = AsyncZeroconf(ip_version=IPVersion.V4Only)

            # Service type: _digiscript._tcp.local.
            service_type = "_digiscript._tcp.local."

            # Service name: ServerName._digiscript._tcp.local.
            service_name = f"{self.server_name}.{service_type}"

            # Get local IP addresses
            addresses = self._get_local_addresses()

            if not addresses:
                self._logger.warning(
                    "No local IP addresses found, mDNS advertising may not work"
                )
                # Use localhost as fallback
                addresses = [socket.inet_aton("127.0.0.1")]

            # Create service info
            self.service_info = ServiceInfo(
                type_=service_type,
                name=service_name,
                port=self.port,
                addresses=addresses,
                properties={
                    "version": "1.0",  # Protocol version
                    "app": "DigiScript",
                },
                server=f"{self.server_name}.local.",
            )

            # Register service (async)
            await self.aiozc.async_register_service(self.service_info)

            self._logger.info(
                f"mDNS advertising started: {service_name} on port {self.port}"
            )
            self._logger.debug(
                f"Advertising on addresses: {[socket.inet_ntoa(addr) for addr in addresses]}"
            )

        except Exception as e:
            self._logger.exception(f"Failed to start mDNS advertising: {e}")
            # Don't fail the entire server if mDNS fails
            await self.stop()

    async def stop(self) -> None:
        """Stop advertising the DigiScript server."""
        if self.service_info and self.aiozc:
            try:
                await self.aiozc.async_unregister_service(self.service_info)
                self._logger.info("mDNS service unregistered")
            except Exception as e:
                self._logger.error(f"Error unregistering mDNS service: {e}")

        if self.aiozc:
            try:
                await self.aiozc.async_close()
                self._logger.info("mDNS advertising stopped")
            except Exception as e:
                self._logger.error(f"Error closing AsyncZeroconf: {e}")

        self.aiozc = None
        self.service_info = None

    def _get_local_addresses(self) -> list[bytes]:
        """
        Get local IP addresses for mDNS advertising.

        Returns:
            List of IP addresses in binary format
        """
        addresses = set()

        try:
            # Get hostname and resolve to IPs
            hostname = socket.gethostname()
            for addr_info in socket.getaddrinfo(hostname, None):
                family, _, _, _, sockaddr = addr_info
                if family == socket.AF_INET:  # IPv4 only
                    ip_address = sockaddr[0]
                    # Skip loopback
                    if not ip_address.startswith("127."):
                        addresses.add(socket.inet_aton(ip_address))
        except Exception as e:
            self._logger.warning(f"Error getting local addresses: {e}")

        # If no addresses found, try getting the primary network interface IP
        if not addresses:
            try:
                # Create a socket to determine the local IP
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    # Connect to a public DNS server (doesn't actually send data)
                    s.connect(("8.8.8.8", 80))
                    local_ip = s.getsockname()[0]
                    if not local_ip.startswith("127."):
                        addresses.add(socket.inet_aton(local_ip))
                finally:
                    s.close()
            except Exception as e:
                self._logger.warning(f"Error getting primary network interface: {e}")

        return list(addresses)
