# Runtime hook to preload modules
import importlib
import sys

print('Preloading modules for dynamic discovery...')

# Preload all controller modules
try:
    importlib.import_module('controllers.controllers')
    print('Preloaded controllers.controllers')
except Exception as e:
    print(f'Error preloading controllers.controllers: {e}')

try:
    importlib.import_module('controllers.ws_controller')
    print('Preloaded controllers.ws_controller')
except Exception as e:
    print(f'Error preloading controllers.ws_controller: {e}')

try:
    importlib.import_module('controllers.api')
    print('Preloaded controllers.api')
except Exception as e:
    print(f'Error preloading controllers.api: {e}')

try:
    importlib.import_module('controllers.api.auth')
    print('Preloaded controllers.api.auth')
except Exception as e:
    print(f'Error preloading controllers.api.auth: {e}')

try:
    importlib.import_module('controllers.api.rbac')
    print('Preloaded controllers.api.rbac')
except Exception as e:
    print(f'Error preloading controllers.api.rbac: {e}')

try:
    importlib.import_module('controllers.api.settings')
    print('Preloaded controllers.api.settings')
except Exception as e:
    print(f'Error preloading controllers.api.settings: {e}')

try:
    importlib.import_module('controllers.api.websocket')
    print('Preloaded controllers.api.websocket')
except Exception as e:
    print(f'Error preloading controllers.api.websocket: {e}')

try:
    importlib.import_module('controllers.api.show')
    print('Preloaded controllers.api.show')
except Exception as e:
    print(f'Error preloading controllers.api.show: {e}')

try:
    importlib.import_module('controllers.api.show.cast')
    print('Preloaded controllers.api.show.cast')
except Exception as e:
    print(f'Error preloading controllers.api.show.cast: {e}')

try:
    importlib.import_module('controllers.api.show.shows')
    print('Preloaded controllers.api.show.shows')
except Exception as e:
    print(f'Error preloading controllers.api.show.shows: {e}')

try:
    importlib.import_module('controllers.api.show.sessions')
    print('Preloaded controllers.api.show.sessions')
except Exception as e:
    print(f'Error preloading controllers.api.show.sessions: {e}')

try:
    importlib.import_module('controllers.api.show.microphones')
    print('Preloaded controllers.api.show.microphones')
except Exception as e:
    print(f'Error preloading controllers.api.show.microphones: {e}')

try:
    importlib.import_module('controllers.api.show.acts')
    print('Preloaded controllers.api.show.acts')
except Exception as e:
    print(f'Error preloading controllers.api.show.acts: {e}')

try:
    importlib.import_module('controllers.api.show.scenes')
    print('Preloaded controllers.api.show.scenes')
except Exception as e:
    print(f'Error preloading controllers.api.show.scenes: {e}')

try:
    importlib.import_module('controllers.api.show.characters')
    print('Preloaded controllers.api.show.characters')
except Exception as e:
    print(f'Error preloading controllers.api.show.characters: {e}')

try:
    importlib.import_module('controllers.api.show.cues')
    print('Preloaded controllers.api.show.cues')
except Exception as e:
    print(f'Error preloading controllers.api.show.cues: {e}')

try:
    importlib.import_module('controllers.api.show.script')
    print('Preloaded controllers.api.show.script')
except Exception as e:
    print(f'Error preloading controllers.api.show.script: {e}')

try:
    importlib.import_module('controllers.api.show.script.config')
    print('Preloaded controllers.api.show.script.config')
except Exception as e:
    print(f'Error preloading controllers.api.show.script.config: {e}')

try:
    importlib.import_module('controllers.api.show.script.stage_direction_styles')
    print('Preloaded controllers.api.show.script.stage_direction_styles')
except Exception as e:
    print(f'Error preloading controllers.api.show.script.stage_direction_styles: {e}')

try:
    importlib.import_module('controllers.api.show.script.revisions')
    print('Preloaded controllers.api.show.script.revisions')
except Exception as e:
    print(f'Error preloading controllers.api.show.script.revisions: {e}')

try:
    importlib.import_module('controllers.api.show.script.script')
    print('Preloaded controllers.api.show.script.script')
except Exception as e:
    print(f'Error preloading controllers.api.show.script.script: {e}')

try:
    importlib.import_module('controllers.api.user')
    print('Preloaded controllers.api.user')
except Exception as e:
    print(f'Error preloading controllers.api.user: {e}')

try:
    importlib.import_module('controllers.api.user.settings')
    print('Preloaded controllers.api.user.settings')
except Exception as e:
    print(f'Error preloading controllers.api.user.settings: {e}')

# Preload all model modules
try:
    importlib.import_module('models.user')
    print('Preloaded models.user')
except Exception as e:
    print(f'Error preloading models.user: {e}')

try:
    importlib.import_module('models.show')
    print('Preloaded models.show')
except Exception as e:
    print(f'Error preloading models.show: {e}')

try:
    importlib.import_module('models.models')
    print('Preloaded models.models')
except Exception as e:
    print(f'Error preloading models.models: {e}')

try:
    importlib.import_module('models.session')
    print('Preloaded models.session')
except Exception as e:
    print(f'Error preloading models.session: {e}')

try:
    importlib.import_module('models.mics')
    print('Preloaded models.mics')
except Exception as e:
    print(f'Error preloading models.mics: {e}')

try:
    importlib.import_module('models.settings')
    print('Preloaded models.settings')
except Exception as e:
    print(f'Error preloading models.settings: {e}')

try:
    importlib.import_module('models.script')
    print('Preloaded models.script')
except Exception as e:
    print(f'Error preloading models.script: {e}')

try:
    importlib.import_module('models.cue')
    print('Preloaded models.cue')
except Exception as e:
    print(f'Error preloading models.cue: {e}')

print('Module preloading complete.')
