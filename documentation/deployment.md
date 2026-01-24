# Deploying DigiScript

## Server Deployment

### Running Locally

This starts the web server listening on port 8080:

```shell
cd server
./main.py
```

### Running using Docker

This will start DigiScript running, and map port 8080 locally to 8080 on the container:

```shell
docker build -t digiscript:latest .
docker-compose up -d
```

### Pre-built Server Executables

Pre-built server executables are available from [GitHub Releases](https://github.com/dreamteamprod/DigiScript/releases):

- **Linux**: `DigiScript-linux.zip`
- **Windows**: `DigiScript-windows.zip`
- **macOS**: `DigiScript-macos.zip`

These are standalone PyInstaller executables with the web frontend bundled.

## Electron Desktop Application

The Electron app is a standalone desktop client that connects to a DigiScript server over the network. It provides the same interface as the web client but runs as a native desktop application.

### Installation

Download the appropriate installer from [GitHub Releases](https://github.com/dreamteamprod/DigiScript/releases):

| Platform | File | Installation |
|----------|------|--------------|
| Windows | `DigiScript-*.exe` | Run the installer |
| macOS | `DigiScript-*.zip` | Extract and move to Applications |
| Linux (Debian/Ubuntu) | `digiscript_*.deb` | `sudo dpkg -i digiscript_*.deb` |
| Linux (RedHat/Fedora) | `digiscript-*.rpm` | `sudo rpm -i digiscript-*.rpm` |

### Connecting to a Server

On first launch, the Electron app will prompt for server connection details:

1. **mDNS Discovery**: The app can automatically discover DigiScript servers on your local network
2. **Manual Entry**: Enter the server URL directly (e.g., `http://192.168.1.100:8080`)

### Version Compatibility

The Electron client requires an **exact version match** with the server. If versions don't match, the app will display a warning and prevent connection to avoid compatibility issues.