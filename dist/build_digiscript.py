#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
import argparse
import platform

# Determine if we're on Windows to handle emoji display
IS_WINDOWS = platform.system().lower() == "windows"

# Emoji dictionary - use plain text on Windows, emojis elsewhere
EMOJI = {
    "build": "🔨" if not IS_WINDOWS else "",
    "package": "📦" if not IS_WINDOWS else "",
    "working": "🏗️" if not IS_WINDOWS else "",
    "success": "✅" if not IS_WINDOWS else "",
    "error": "❌" if not IS_WINDOWS else "",
    "warning": "⚠️" if not IS_WINDOWS else "",
    "info": "ℹ️" if not IS_WINDOWS else "",
    "search": "🔍" if not IS_WINDOWS else "",
    "file": "📄" if not IS_WINDOWS else "",
    "folder": "📁" if not IS_WINDOWS else "",
    "done": "🎉" if not IS_WINDOWS else "",
}


def emoji(key, fallback=""):
    return EMOJI.get(key, fallback)


# Determine project paths relative to the script location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
CLIENT_DIR = os.path.join(ROOT_DIR, "client")
SERVER_DIR = os.path.join(ROOT_DIR, "server")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")

# Platform-specific output directories
WINDOWS_OUTPUT = os.path.join(OUTPUT_DIR, "windows")
MACOS_OUTPUT = os.path.join(OUTPUT_DIR, "macos")
LINUX_OUTPUT = os.path.join(OUTPUT_DIR, "linux")


def build_frontend(force_rebuild=False):
    """Build the Node.js frontend"""
    print(f"{emoji('build')} Building frontend...")

    # The vite.config.js already outputs to server/static, so we just need to
    # check if this directory has content and if we need to rebuild
    server_static = os.path.join(SERVER_DIR, "static")

    if not force_rebuild and os.path.exists(server_static) and len(os.listdir(server_static)) > 0:
        print(f"{emoji('success')} Frontend already built in server/static. Use --force-rebuild to rebuild.")
        return True

    # Navigate to client directory
    original_dir = os.getcwd()
    os.chdir(CLIENT_DIR)

    # Install dependencies if needed
    try:
        print(f"{emoji('package')} Installing dependencies...")
        subprocess.run(["npm", "ci"], check=True)

        # Build the frontend - this will output directly to server/static based on vite.config.js
        print(f"{emoji('working')} Building frontend application...")
        subprocess.run(["npm", "run", "build"], check=True)

        print(f"{emoji('success')} Frontend build completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"{emoji('error')} Frontend build failed: {e}")
        return False
    finally:
        # Return to original directory
        os.chdir(original_dir)


def install_python_requirements():
    """Install Python dependencies"""
    print(f"{emoji('package')} Installing Python dependencies...")

    requirements_file = os.path.join(SERVER_DIR, "requirements.txt")
    if not os.path.exists(requirements_file):
        print(f"{emoji('error')} Error: Requirements file {requirements_file} not found.")
        return False

    try:
        # Install requirements
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", requirements_file], check=True)

        # Install PyInstaller
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

        print(f"{emoji('success')} Python dependencies installed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"{emoji('error')} Failed to install Python dependencies: {e}")
        return False


def setup_pyinstaller_utils():
    """Copy PyInstaller utilities to the server utils directory"""
    print(f"{emoji('folder')} Setting up PyInstaller utilities...")

    utils_dir = os.path.join(SERVER_DIR, "utils")
    if not os.path.exists(utils_dir):
        print(f"{emoji('error')} Error: Utils directory {utils_dir} does not exist.")
        return False

    source_file = os.path.join(SCRIPT_DIR, "pyinstaller_utils.py")
    target_file = os.path.join(utils_dir, "pyinstaller_utils.py")

    try:
        shutil.copy2(source_file, target_file)
        print(f"{emoji('success')} Copied PyInstaller utilities to {target_file}")
        return True
    except Exception as e:
        print(f"{emoji('error')} Error copying PyInstaller utilities: {e}")
        return False


def run_pyinstaller(one_file=False, output_name=None):
    """Build the executable with PyInstaller"""
    if one_file:
        print(f"{emoji('package')} Building single-file executable with PyInstaller...")
    else:
        print(f"{emoji('package')} Building directory-based executable with PyInstaller...")

    # Create platform-specific output directory
    current_platform = platform.system().lower()
    if current_platform == "windows":
        platform_output = WINDOWS_OUTPUT
    elif current_platform == "darwin":
        platform_output = MACOS_OUTPUT
    else:
        platform_output = LINUX_OUTPUT

    os.makedirs(platform_output, exist_ok=True)

    # Go to server directory for PyInstaller
    original_dir = os.getcwd()
    os.chdir(SERVER_DIR)

    # Use spec file from dist directory
    spec_file = os.path.join(SCRIPT_DIR, "DigiScript.spec")
    if not os.path.exists(spec_file):
        print(f"{emoji('error')} Error: PyInstaller spec file {spec_file} not found.")
        return False

    try:
        # Run PyInstaller with the spec file
        cmd = ["pyinstaller", spec_file, "-y"]
        print(f"Running command: {' '.join(cmd)}")

        subprocess.run(cmd, check=True)

        exe_ext = ".exe" if current_platform == "windows" else ""

        # Copy the appropriate output based on one_file option
        if one_file:
            source = os.path.join(SERVER_DIR, "dist", f"DigiScript{exe_ext}")
            if not os.path.exists(source):
                print(f"{emoji('warning')} Warning: Expected output {source} not found. Checking for alternative naming...")
                # Try with the custom name if provided
                if output_name:
                    source = os.path.join(SERVER_DIR, "dist", f"{output_name}{exe_ext}")
        else:
            source = os.path.join(SERVER_DIR, "dist", "DigiScript")
            if not os.path.exists(source):
                print(f"{emoji('warning')} Warning: Expected output {source} not found. Checking for alternative naming...")
                # Try with the custom name if provided
                if output_name:
                    source = os.path.join(SERVER_DIR, "dist", output_name)

        # Create target path
        target_basename = os.path.basename(source)
        if output_name and target_basename != output_name and not target_basename.endswith(exe_ext):
            # If a custom name was provided, use it
            target_basename = f"{output_name}{exe_ext if one_file else ''}"

        target = os.path.join(platform_output, target_basename)

        if os.path.exists(source):
            if os.path.isdir(source):
                if os.path.exists(target):
                    shutil.rmtree(target)
                shutil.copytree(source, target)
            else:
                if os.path.exists(target):
                    os.remove(target)
                shutil.copy2(source, target)
            print(f"{emoji('success')} Copied build output to {target}")
        else:
            print(f"{emoji('error')} Error: Expected output {source} not found.")
            return False

        print(f"{emoji('success')} PyInstaller build completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"{emoji('error')} PyInstaller build failed: {e}")
        return False
    finally:
        # Return to original directory
        os.chdir(original_dir)


def create_platform_specific_package(package_format):
    """Create platform-specific package"""
    current_platform = platform.system().lower()

    if current_platform == "windows":
        platform_output = WINDOWS_OUTPUT
    elif current_platform == "darwin":
        platform_output = MACOS_OUTPUT
    else:
        platform_output = LINUX_OUTPUT

    if not os.path.exists(platform_output):
        print(f"{emoji('error')} Error: Platform output directory {platform_output} does not exist.")
        return False

    if package_format == "zip":
        try:
            print(f"{emoji('package')} Creating ZIP archive...")
            output_file = os.path.join(
                OUTPUT_DIR,
                f"DigiScript-{current_platform}.zip"
            )

            if os.path.exists(output_file):
                os.remove(output_file)

            shutil.make_archive(
                os.path.splitext(output_file)[0],
                "zip",
                platform_output
            )
            print(f"{emoji('success')} Created package: {output_file}")
            return True
        except Exception as e:
            print(f"{emoji('error')} Failed to create package: {e}")
            return False
    elif package_format == "dmg" and current_platform == "darwin":
        # macOS DMG creation would go here
        print(f"{emoji('warning')} DMG packaging not implemented yet")
        return False
    elif package_format == "msi" and current_platform == "windows":
        # Windows MSI creation would go here
        print(f"{emoji('warning')} MSI packaging not implemented yet")
        return False
    else:
        print(f"{emoji('warning')} Package format {package_format} not supported on {current_platform}")
        return False


def remove_copied_files():
    """Remove copied PyInstaller utilities from the server utils directory"""
    print(f"{emoji('folder')} Removing PyInstaller utilities...")

    utils_dir = os.path.join(SERVER_DIR, "utils")
    if not os.path.exists(utils_dir):
        print(f"{emoji('error')} Error: Utils directory {utils_dir} does not exist.")
        return False

    target_file = os.path.join(utils_dir, "pyinstaller_utils.py")

    try:
        os.remove(target_file)
        print(f"{emoji('success')} Removed PyInstaller utilities from {target_file}")
        return True
    except Exception as e:
        print(f"{emoji('error')} Error removing PyInstaller utilities: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Build DigiScript Application")
    parser.add_argument("--skip-frontend", action="store_true", help="Skip frontend build")
    parser.add_argument("--force-rebuild", action="store_true", help="Force rebuild of frontend")
    parser.add_argument("--onefile", action="store_true", help="Use the single-file executable")
    parser.add_argument("--name", type=str, help="Custom name for the output executable")
    parser.add_argument("--package", choices=["zip", "dmg", "msi"], help="Create a packaged distribution")

    args = parser.parse_args()

    # Show paths for verification
    print(f"{emoji('search')} Project root: {ROOT_DIR}")
    print(f"{emoji('folder')} Client directory: {CLIENT_DIR}")
    print(f"{emoji('folder')} Server directory: {SERVER_DIR}")
    print(f"{emoji('folder')} Output directory: {OUTPUT_DIR}")

    # Validate directories
    if not os.path.exists(CLIENT_DIR):
        print(f"{emoji('error')} Error: Client directory {CLIENT_DIR} not found.")
        return 1

    if not os.path.exists(SERVER_DIR):
        print(f"{emoji('error')} Error: Server directory {SERVER_DIR} not found.")
        return 1

    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    success = True
    remove_files = False

    # Build process
    if not args.skip_frontend:
        success = build_frontend(args.force_rebuild)

    if success:
        success = install_python_requirements()

    if success:
        success = setup_pyinstaller_utils()
        remove_files = success

    if success:
        success = run_pyinstaller(args.onefile, args.name)

    if success and args.package:
        success = create_platform_specific_package(args.package)

    # Always remove copied files if they were copied in the first place
    if remove_files:
        remove_copied_files()

    if success:
        print(f"\n{emoji('done')} Build completed successfully!")
        return 0
    else:
        print(f"\n{emoji('error')} Build failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())