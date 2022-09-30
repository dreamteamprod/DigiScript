from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

from tornado.locks import Lock

from utils.logger import get_logger
from utils.file_watcher import IOLoopFileWatcher

if TYPE_CHECKING:
    from server.server.app_server import DigiScriptServer


class Settings:
    def __init__(self, application: DigiScriptServer, settings_path=None):
        self._application = application
        self.lock = Lock()
        self._base_path = os.path.join(os.path.dirname(__file__), '..', 'conf')
        if settings_path:
            self.settings_path = settings_path
        else:
            self.settings_path = os.path.join(self._base_path, 'digiscript.json')
            get_logger().info(
                f'No settings path provided, using {self.settings_path}')
        self.settings = {}
        self._load()

        self._file_watcher = IOLoopFileWatcher(self.settings_path, self.auto_reload_changes, 100)
        self._file_watcher.add_error_callback(self.file_deleted)
        self._file_watcher.watch()

    def file_deleted(self):
        get_logger().info('Settings file deleted; recreating from in memory settings')
        self._save()

    def auto_reload_changes(self):
        get_logger().info('Settings file changed; auto reloading')
        self._load()

        for client in self._application.clients:
            client.write_message({
                'OP': 'SETTINGS_CHANGED',
                'DATA': self.settings,
                'ACTION': 'WS_SETTINGS_CHANGED'
            })

    def _load(self):
        if os.path.exists(self.settings_path):
            with open(self.settings_path, 'r') as fp:
                self.settings = json.load(fp)
            get_logger().info(f'Loaded settings from {self.settings_path}')
        else:
            self._create_defaults()
            with open(self.settings_path, 'w') as fp:
                json.dump(self.settings, fp, indent=4)
            get_logger().info(f'Saved settings to {self.settings_path}')

    def _save(self):
        self._file_watcher.pause()
        with open(self.settings_path, 'w') as fp:
            json.dump(self.settings, fp, indent=4)
            fp.flush()
            os.fsync(fp.fileno())
            self._file_watcher.update_m_time()
        self._file_watcher.resume()
        get_logger().info(f'Saved settings to {self.settings_path}')

    def _create_defaults(self):
        get_logger().warning('Creating default settings')
        self.settings = {
            'current_show': None,
            'log_path': os.path.join(self._base_path, 'digiscript.log'),
            'max_log_mb': 100,
            'log_backups': 5
        }

    async def get(self, key, default=None):
        async with self.lock:
            return self.settings.get(key, default)

    async def set(self, key, item):
        async with self.lock:
            self.settings[key] = item
            self._save()

    async def as_json(self):
        async with self.lock:
            return json.loads(json.dumps(self.settings))
