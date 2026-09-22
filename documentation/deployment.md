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
