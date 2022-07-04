import json
import os
from tornado.locks import Lock

from utils.logger import get_logger


class Settings:
    def __init__(self, settings_path=None):
        self.lock = Lock()
        if settings_path:
            self.settings_path = settings_path
        else:
            self.settings_path = os.path.join(os.path.dirname(__file__), "digiscript.json")
            get_logger().info(f'No settings path provided, using {self.settings_path}')
        self.settings = {}
        self._load()

    def _load(self):
        if os.path.exists(self.settings_path):
            with open(self.settings_path, 'r') as fp:
                self.settings = json.load(fp)
            get_logger().info(f'Loaded settings from {self.settings_path}')
        else:
            self._create_defaults()
            with open(self.settings_path, 'w') as fp:
                json.dump(self.settings, fp)
            get_logger().info(f'Saved settings to {self.settings_path}')

    async def _save(self):
        async with self.lock:
            with open(self.settings_path, 'w') as fp:
                json.dump(self.settings, fp)
            get_logger().info(f'Saved settings to {self.settings_path}')

    def _create_defaults(self):
        get_logger().warning('Creating default settings')
        self.settings = {
            'current_show': None
        }

    async def get(self, key, default=None):
        async with self.lock:
            return self.settings.get(key, default)

    async def set(self, key, item):
        async with self.lock:
            self.settings[key] = item
            await self._save()

    async def as_json(self):
        async with self.lock:
            return json.loads(json.dumps(self.settings))
