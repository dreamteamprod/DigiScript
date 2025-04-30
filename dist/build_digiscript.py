#!/usr/bin/env python3
"""
DigiScript Application Builder

This script builds the DigiScript application by compiling the Node.js frontend
and packaging the Python backend into a standalone executable using PyInstaller.
"""

import os
import sys
import shutil
import subprocess
import argparse
import platform

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
    print("🔨 Building frontend...")

    # The vite.config.js already outputs to server/static, so we just need to
    # check if this directory has content and if we need to rebuild
    server_static = os.path.join(SERVER_DIR, "static")

    if not force_rebuild and os.path.exists(server_static) and len(os.listdir(server_static)) > 0:
        print("✅ Frontend already built in server/static. Use --force-rebuild to rebuild.")
        return True

    # Navigate to client directory
    original_dir = os.getcwd()
    os.chdir(CLIENT_DIR)

    # Install dependencies if needed
    try:
        print("📦 Installing dependencies...")
        subprocess.run(["npm", "ci"], check=True)

        # Build the frontend - this will output directly to server/static based on vite.config.js
        print("🏗️ Building frontend application...")
        subprocess.run(["npm", "run", "build"], check=True)

        print("✅ Frontend build completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Frontend build failed: {e}")
        return False
    finally:
        # Return to original directory
        os.chdir(original_dir)


def install_python_requirements():
    """Install Python dependencies"""
    print("📦 Installing Python dependencies...")

    requirements_file = os.path.join(SERVER_DIR, "requirements.txt")
    if not os.path.exists(requirements_file):
        print(f"❌ Error: Requirements file {requirements_file} not found.")
        return False

    try:
        # Install requirements
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", requirements_file], check=True)

        # Install PyInstaller
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

        print("✅ Python dependencies installed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install Python dependencies: {e}")
        return False


def setup_pyinstaller_utils():
    """Copy PyInstaller utilities to the server utils directory"""
    print("📂 Setting up PyInstaller utilities...")

    utils_dir = os.path.join(SERVER_DIR, "utils")
    if not os.path.exists(utils_dir):
        print(f"❌ Error: Utils directory {utils_dir} does not exist.")
        return False

    source_file = os.path.join(SCRIPT_DIR, "pyinstaller_utils.py")
    target_file = os.path.join(utils_dir, "pyinstaller_utils.py")

    try:
        shutil.copy2(source_file, target_file)
        print(f"✅ Copied PyInstaller utilities to {target_file}")
        return True
    except Exception as e:
        print(f"❌ Error copying PyInstaller utilities: {e}")
        return False


def run_pyinstaller(one_file=False, output_name=None):
    """Build the executable with PyInstaller"""
    if one_file:
        print("📦 Building single-file executable with PyInstaller...")
    else:
        print("📦 Building directory-based executable with PyInstaller...")

    # Create platform-specific output directory
    current_platform = platform.system().lower()
    if current_platform == "windows":
        platform_output = WINDOWS_OUTPUT
    elif current_platform == "darwin":
        platform_output = MACOS_OUTPUT
    else:
        platform_output = LINUX_OUTPUT

    os.makedirs(platform_output, exist_ok=True)

    # Use full path to spec file
    spec_file = os.path.join(SCRIPT_DIR, "DigiScript.spec")
    if not os.path.exists(spec_file):
        print(f"❌ Error: PyInstaller spec file {spec_file} not found.")
        return False

    # Store original directory
    original_dir = os.getcwd()

    try:
        # Change to the server directory
        os.chdir(SERVER_DIR)
        print(f"Changed working directory to: {SERVER_DIR}")

        # Run PyInstaller with the spec file
        cmd = ["pyinstaller", spec_file]
        print(f"Running command: {' '.join(cmd)}")

        subprocess.run(cmd, check=True)

        # Copy the output to the platform-specific directory
        exe_ext = ".exe" if current_platform == "windows" else ""

        # Copy the appropriate output based on one_file option
        if one_file:
            source = os.path.join(SERVER_DIR, "dist", f"DigiScript-onefile{exe_ext}")
        else:
            source = os.path.join(SERVER_DIR, "dist", "DigiScript")

        # Create target path
        target_basename = os.path.basename(source)
        if output_name:
            if one_file:
                target_basename = f"{output_name}{exe_ext}"
            else:
                target_basename = output_name

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
            print(f"✅ Copied build output to {target}")
        else:
            print(f"❌ Error: Expected output {source} not found.")
            return False

        print("✅ PyInstaller build completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ PyInstaller build failed: {e}")
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
        print(f"❌ Error: Platform output directory {platform_output} does not exist.")
        return False

    if package_format == "zip":
        try:
            print("📦 Creating ZIP archive...")
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
            print(f"✅ Created package: {output_file}")
            return True
        except Exception as e:
            print(f"❌ Failed to create package: {e}")
            return False
    elif package_format == "dmg" and current_platform == "darwin":
        # macOS DMG creation would go here
        print("⚠️ DMG packaging not implemented yet")
        return False
    elif package_format == "msi" and current_platform == "windows":
        # Windows MSI creation would go here
        print("⚠️ MSI packaging not implemented yet")
        return False
    else:
        print(f"⚠️ Package format {package_format} not supported on {current_platform}")
        return False


def remove_copied_files():
    """Remove copied PyInstaller utilities from the server utils directory"""
    print("📂 Removing PyInstaller utilities...")

    utils_dir = os.path.join(SERVER_DIR, "utils")
    if not os.path.exists(utils_dir):
        print(f"❌ Error: Utils directory {utils_dir} does not exist.")
        return False

    target_file = os.path.join(utils_dir, "pyinstaller_utils.py")

    try:
        os.remove(target_file)
        print(f"✅ Removed PyInstaller utilities from {target_file}")
        return True
    except Exception as e:
        print(f"❌ Error removing PyInstaller utilities: {e}")
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
    print(f"🔍 Project root: {ROOT_DIR}")
    print(f"🔍 Client directory: {CLIENT_DIR}")
    print(f"🔍 Server directory: {SERVER_DIR}")
    print(f"🔍 Output directory: {OUTPUT_DIR}")

    # Validate directories
    if not os.path.exists(CLIENT_DIR):
        print(f"❌ Error: Client directory {CLIENT_DIR} not found.")
        return 1

    if not os.path.exists(SERVER_DIR):
        print(f"❌ Error: Server directory {SERVER_DIR} not found.")
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
        print("\n🎉 Build completed successfully!")
        return 0
    else:
        print("\n❌ Build failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())