import importlib
from typing import List, TYPE_CHECKING

from digi_server.logger import get_logger
from utils.pkg_utils import find_end_modules
from utils.server_plugin import BasePlugin, registered_plugins

if TYPE_CHECKING:
    from digi_server.app_server import DigiScriptServer


class PluginManager:
    def __init__(self, application: 'DigiScriptServer'):
        self.application = application
        self.IMPORTED_PLUGINS = {}
        self.RUNNING_PLUGINS: List[BasePlugin] = []

    def import_all_plugins(self):
        plugins = find_end_modules('.', prefix='server_plugins')
        for plugin in plugins:
            if plugin != __name__:
                get_logger().debug(f'Importing plugin module {plugin}')
                mod = importlib.import_module(plugin)
                self.IMPORTED_PLUGINS[plugin] = mod

    async def start_plugin(self, name):
        get_logger().info(f'Starting plugin: {name}')
        plugin_obj = registered_plugins[name](self.application)
        await plugin_obj.start()
        self.RUNNING_PLUGINS.append(plugin_obj)

    async def start_default(self):
        for plugin_name in registered_plugins:
            if registered_plugins[plugin_name]._default_plugin:
                await self.start_plugin(plugin_name)

    async def shutdown(self):
        for plugin in self.RUNNING_PLUGINS:
            await plugin.stop()
