import asyncio
from asyncio import DatagramProtocol
from asyncio.transports import BaseTransport
from typing import List, Tuple, Any

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import AsyncIOOSCUDPServer

from digi_server.logger import get_logger
from utils.server_plugin import plugin, BasePlugin


def default_osc_handler(address: str, *osc_arguments: List[Any]):
    get_logger().debug(f'OSC message received with no handler. Address: {address}. '
                       f'Arguments: {osc_arguments}')


@plugin('OSC Server', default=True)
class OSCServerPlugin(BasePlugin):
    def __init__(self, application: 'DigiScriptServer'):
        self.dispatcher: Dispatcher = Dispatcher()
        self.dispatcher.set_default_handler(default_osc_handler)
        self.servers: List[AsyncIOOSCUDPServer] = []
        self.transport_pairs: List[Tuple[BaseTransport, DatagramProtocol]] = []

        super().__init__(application)

    async def start(self):
        for fd, socket in self.application.http_server._sockets.items():
            address = socket.getsockname()
            server = AsyncIOOSCUDPServer((address[0], address[1] + 1),
                                         self.dispatcher,
                                         asyncio.get_event_loop())
            transport, protocol = await server.create_serve_endpoint()
            self.servers.append(server)
            self.transport_pairs.append((transport, protocol))

    async def stop(self):
        for transport_pair in self.transport_pairs:
            transport_pair[0].close()
