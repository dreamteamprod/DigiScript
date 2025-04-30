# -*- mode: python ; coding: utf-8 -*-

import os
import sys
import glob
import importlib
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_all

block_cipher = None

# The working directory when running the spec file is the server directory
# So we need to adjust our paths accordingly
SERVER_DIR = os.getcwd()
ROOT_DIR = os.path.dirname(SERVER_DIR)
DIST_DIR = os.path.join(ROOT_DIR, 'dist')

print(f"Working directory: {SERVER_DIR}")
print(f"Root directory: {ROOT_DIR}")

# Create DIST_DIR if it doesn't exist
if not os.path.exists(DIST_DIR):
    os.makedirs(DIST_DIR)

def find_modules_recursively(base_path, base_package, modules_list):
    """Find all Python modules in a directory structure recursively"""
    # Add all .py files in the current directory
    for py_file in glob.glob(os.path.join(base_path, "*.py")):
        base_name = os.path.basename(py_file)
        if base_name != '__init__.py':
            module_name = f"{base_package}.{base_name[:-3]}"
            modules_list.append(module_name)
            print(f"Found module: {module_name}")

    # Recursively scan subdirectories that are Python packages (have __init__.py)
    for subdir in glob.glob(os.path.join(base_path, "*/")):
        if os.path.isfile(os.path.join(subdir, "__init__.py")):
            subpkg_name = os.path.basename(os.path.normpath(subdir))
            subpkg_full_name = f"{base_package}.{subpkg_name}"
            modules_list.append(subpkg_full_name)  # Add the package itself
            print(f"Found package: {subpkg_full_name}")
            find_modules_recursively(subdir, subpkg_full_name, modules_list)

# Discover all controller modules recursively
controller_modules = []
controllers_dir = os.path.join(SERVER_DIR, 'controllers')
find_modules_recursively(controllers_dir, 'controllers', controller_modules)
print(f"Found {len(controller_modules)} controller modules/packages")

# Discover all model modules recursively
model_modules = []
models_dir = os.path.join(SERVER_DIR, 'models')
find_modules_recursively(models_dir, 'models', model_modules)
print(f"Found {len(model_modules)} model modules/packages")

# Create a runtime hook to preload all controller and model modules
with open(os.path.join(DIST_DIR, 'preload_modules.py'), 'w') as f:
    f.write("# Runtime hook to preload modules\n")
    f.write("import importlib\n")
    f.write("import sys\n\n")

    f.write("print('Preloading modules for dynamic discovery...')\n\n")

    f.write("# Preload all controller modules\n")
    for module in controller_modules:
        f.write(f"try:\n")
        f.write(f"    importlib.import_module('{module}')\n")
        f.write(f"    print('Preloaded {module}')\n")
        f.write(f"except Exception as e:\n")
        f.write(f"    print(f'Error preloading {module}: {{e}}')\n\n")

    f.write("# Preload all model modules\n")
    for module in model_modules:
        f.write(f"try:\n")
        f.write(f"    importlib.import_module('{module}')\n")
        f.write(f"    print('Preloaded {module}')\n")
        f.write(f"except Exception as e:\n")
        f.write(f"    print(f'Error preloading {module}: {{e}}')\n\n")

    f.write("print('Module preloading complete.')\n")

# Find all necessary modules to include
digi_server_modules = collect_submodules('digi_server')
rbac_modules = collect_submodules('rbac')
registry_modules = collect_submodules('registry')
schemas_modules = collect_submodules('schemas')
util_modules = collect_submodules('utils')
logging_modules = ['logging', 'logging.config', 'logging.handlers']

# Define paths that need to be included
static_path = os.path.join(SERVER_DIR, 'static')
alembic_ini = os.path.join(SERVER_DIR, 'alembic.ini')
alembic_dir = os.path.join(SERVER_DIR, 'alembic_config')

# Collect all data files
datas = []

# Add static directory if it exists
if os.path.exists(static_path):
    datas.append((static_path, 'static'))
    print(f"Added static directory: {static_path}")
else:
    print(f"Warning: Static directory {static_path} not found.")

# Add Alembic files if they exist
if os.path.exists(alembic_ini):
    datas.append((alembic_ini, '.'))
    print(f"Added alembic.ini: {alembic_ini}")
if os.path.exists(alembic_dir):
    datas.append((alembic_dir, 'alembic'))
    print(f"Added alembic directory: {alembic_dir}")

# Include all necessary modules
hidden_imports = [
    'alembic',
    'marshmallow_sqlalchemy',
    'tornado.web',
    'bcrypt',
    'anytree',
    'tornado_prometheus',
    'python_dateutil',
    'jwt',
    'datetime',
    'logging.config',   # Explicitly include logging.config
    'logging.handlers', # Also include logging.handlers which might be needed
    'configparser',     # Needed for parsing INI files
    'controllers',      # Include the controllers package
    'models',           # Include the models package
    'pkgutil',          # Used for module discovery
    'importlib',        # Used for imports
] + controller_modules + model_modules + digi_server_modules + rbac_modules + registry_modules + schemas_modules + util_modules

a = Analysis(
    [os.path.join(SERVER_DIR, 'main.py')],
    pathex=[SERVER_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[os.path.join(DIST_DIR, 'preload_modules.py')],  # Add the runtime hook
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

# Create directory-based executable
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DigiScript',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DigiScript',
)

# Create a single-file version for easier distribution
exe_onefile = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='DigiScript-onefile',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)