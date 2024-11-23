from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

from tornado.locks import Lock

from digi_server.logger import get_logger
from utils.file_watcher import IOLoopFileWatcher

if TYPE_CHECKING:
    from digi_server.app_server import DigiScriptServer


class SettingsObject:  # pylint: disable=too-many-instance-attributes
    def __init__(self, key, val_type, default, can_edit=True, callback_fn=None, nullable=False,
                 display_name: str = "", help_text: str = ""):
        if val_type not in [str, bool, int]:
            raise RuntimeError(f'Invalid type {val_type} for {key}. Allowed options are: '
                               f'[str, int, bool]')

        self.key = key
        self.val_type = val_type
        self.value = None
        self.default = default
        self.can_edit = can_edit
        self._callback_fn = callback_fn
        self._nullable = nullable
        self._loaded = False
        self.display_name = display_name
        self.help_text = help_text

    def set_to_default(self):
        self.value = self.default
        self._loaded = True

    def set_value(self, value, spawn_callbacks=True):
        if not isinstance(value, self.val_type):
            if value is None and not self._nullable:
                raise RuntimeError(f'Value for {self.key} cannot be None (is not nullable)')
            if value is not None:
                raise TypeError(f'Value for {self.key} of {value} is not of assigned '
                                f'type {self.val_type}')

        changed = False
        if value != self.value:
            changed = True
            self.value = value
            if self._callback_fn and spawn_callbacks:
                self._callback_fn()

        self._loaded = True
        return changed

    def get_value(self):
        return self.value

    def is_loaded(self):
        return self._loaded

    def as_json(self):
        return {
            'type': self.val_type.__name__,
            'value': self.value,
            'default': self.default,
            'can_edit': self.can_edit,
            'display_name': self.display_name,
            'help_text': self.help_text,
        }


class Settings:
    def __init__(self, application: DigiScriptServer, settings_path=None):
        self._application = application
        self.lock = Lock()
        self._base_path = os.path.join(os.path.dirname(__file__), '..', 'conf')

        if not os.path.exists(self._base_path):
            get_logger().info(f'Creating base path {self._base_path}')
            os.makedirs(self._base_path)

        if settings_path:
            self.settings_path = settings_path
        else:
            self.settings_path = os.path.join(self._base_path, 'digiscript.json')
            get_logger().info(
                f'No settings path provided, using {self.settings_path}')

        if not os.path.exists(os.path.dirname(self.settings_path)):
            get_logger().info(f'Creating settings path {os.path.dirname(self.settings_path)}')
            os.makedirs(os.path.dirname(self.settings_path))

        self.settings = {}

        db_default = f'sqlite:///{os.path.join(os.path.dirname(__file__), "../conf/digiscript.sqlite")}'
        self.define('has_admin_user', bool, False, False, nullable=False,
                    callback_fn=self._application.validate_has_admin, display_name="Has Admin User")
        self.define('db_path', str, db_default, False, nullable=False, display_name="Database Path")
        self.define('current_show', int, None, False, nullable=True,
                    callback_fn=self._application.show_changed, display_name="Current Show ID")
        self.define('debug_mode', bool, False, True, display_name="Enable Debug Mode")
        self.define('log_path', str, os.path.join(self._base_path, 'digiscript.log'), True,
                    self._application.regen_logging, display_name="Application Log Path")
        self.define('max_log_mb', int, 100, True, self._application.regen_logging, display_name="Max Log Size (MB)")
        self.define('log_backups', int, 5, True, self._application.regen_logging, display_name="Log Backups")
        self.define('db_log_enabled', bool, False, True, self._application.regen_logging,
                    display_name="Enable Database Log")
        self.define('db_log_path', str, os.path.join(self._base_path, 'digiscript_db.log'), True,
                    self._application.regen_logging, display_name="Database Log Path")
        self.define('db_max_log_mb', int, 100, True, self._application.regen_logging,
                    display_name="Max Database Log Size (MB)")
        self.define('db_log_backups', int, 5, True, self._application.regen_logging,
                    display_name="Database Log Backups")
        self.define('enable_lazy_loading', bool, True, True,
                    display_name="Enable Lazy Loading",
                    help_text="Whether the client side should load all script pages initially when connected "
                              "to a live show")
        self.define('enable_live_batching', bool, True, True,
                    display_name="Enable Live Batching",
                    help_text="Whether the live show page should only display a subsection of the script pages "
                              "at a time")

        self._load(spawn_callbacks=False)

        self._file_watcher = IOLoopFileWatcher(self.settings_path, self.auto_reload_changes, 100)
        self._file_watcher.add_error_callback(self.file_deleted)
        self._file_watcher.watch()

    def define(self, key, val_type, default, can_edit, callback_fn=None, nullable=False,
               display_name: str = "", help_text: str = ""):
        self.settings[key] = SettingsObject(key, val_type, default, can_edit, callback_fn,
                                            nullable, display_name, help_text)

    def file_deleted(self):
        get_logger().info('Settings file deleted; recreating from in memory settings')
        self._save()

    def auto_reload_changes(self):
        get_logger().info('Settings file changed; auto reloading')
        self._load(spawn_callbacks=True)

        settings_json = {}
        for key, value in self.settings.items():
            settings_json[key] = value.get_value()

        for client in self._application.clients:
            client.write_message({
                'OP': 'SETTINGS_CHANGED',
                'DATA': settings_json,
                'ACTION': 'WS_SETTINGS_CHANGED'
            })

    def _load(self, spawn_callbacks=False):
        if os.path.exists(self.settings_path):
            # Read in the settings
            with open(self.settings_path, 'r', encoding='UTF-8') as file_pointer:
                settings = json.load(file_pointer)
                for key, value in settings.items():
                    if key not in self.settings:
                        get_logger().warning(f'Setting {key} found in settings file is not '
                                             f'defined, ignoring!')
                    else:
                        self.settings[key].set_value(value, spawn_callbacks)

            # Set any missing settings to their defaults, and save if needed
            needs_saving = False
            for key, value in self.settings.items():
                if not value.is_loaded():
                    value.set_to_default()
                    needs_saving = True
            if needs_saving:
                with open(self.settings_path, 'w', encoding='UTF-8') as file_pointer:
                    json.dump(self._json(), file_pointer, indent=4)
                get_logger().info(f'Saved settings to {self.settings_path}')

            get_logger().info(f'Loaded settings from {self.settings_path}')
        else:
            # Set everything to its default value
            for key, value in self.settings.items():
                value.set_to_default()

            with open(self.settings_path, 'w', encoding='UTF-8') as file_pointer:
                json.dump(self._json(), file_pointer, indent=4)

            get_logger().info(f'Saved settings to {self.settings_path}')

    def _save(self):
        self._file_watcher.pause()
        with open(self.settings_path, 'w', encoding='UTF-8') as file_pointer:
            json.dump(self._json(), file_pointer, indent=4)
            file_pointer.flush()
            os.fsync(file_pointer.fileno())
            self._file_watcher.update_m_time()
        self._file_watcher.resume()
        get_logger().info(f'Saved settings to {self.settings_path}')

    async def get(self, key):
        async with self.lock:
            if key not in self.settings:
                raise KeyError(f'{key} is not a valid setting')
            return self.settings.get(key).get_value()

    async def set(self, key, item):
        changed = False
        async with self.lock:
            if key not in self.settings:
                get_logger().warning(f'Setting {key} found in settings file is not '
                                     f'defined, ignoring!')
            else:
                changed = self.settings[key].set_value(item)

        if changed:
            self._save()
            settings = await self.as_json()
            await self._application.ws_send_to_all('SETTINGS_CHANGED', 'WS_SETTINGS_CHANGED',
                                                   settings)

    def _json(self):
        settings_json = {}
        for key, value in self.settings.items():
            settings_json[key] = value.get_value()
        return settings_json

    async def as_json(self):
        async with self.lock:
            settings_json = {}
            for key, value in self.settings.items():
                settings_json[key] = value.get_value()
            return json.loads(json.dumps(settings_json))

    async def raw_json(self):
        async with self.lock:
            settings_json = {}
            for key, value in self.settings.items():
                settings_json[key] = value.as_json()
            return json.loads(json.dumps(settings_json))
