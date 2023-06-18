from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from digi_server.app_server import DigiScriptServer

registered_plugins = {}


def plugin(name, default=False):
    def decorator(cls):
        if not issubclass(cls, BasePlugin):
            raise ValueError('Class must inherit from BasePlugin.')

        if name in registered_plugins:
            raise ValueError('Name must be unique.')

        cls._default_plugin = default
        registered_plugins[name] = cls

        return cls

    return decorator


class BasePlugin:

    def __init__(self, application: 'DigiScriptServer'):
        self.application = application

    async def start(self):
        raise NotImplementedError

    async def stop(self):
        raise NotImplementedError


