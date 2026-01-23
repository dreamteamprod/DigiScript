# Development Guide

**Main Status:**

[![ESLint](https://github.com/dreamteamprod/DigiScript/actions/workflows/nodelint.yml/badge.svg?branch=main)](https://github.com/dreamteamprod/DigiScript/actions/workflows/nodelint.yml)

[![Pylint](https://github.com/dreamteamprod/DigiScript/actions/workflows/pylint.yml/badge.svg?branch=main)](https://github.com/dreamteamprod/DigiScript/actions/workflows/pylint.yml)

**Dev Status:**

[![ESLint](https://github.com/dreamteamprod/DigiScript/actions/workflows/nodelint.yml/badge.svg?branch=dev)](https://github.com/dreamteamprod/DigiScript/actions/workflows/nodelint.yml)

[![Pylint](https://github.com/dreamteamprod/DigiScript/actions/workflows/pylint.yml/badge.svg?branch=dev)](https://github.com/dreamteamprod/DigiScript/actions/workflows/pylint.yml)

## Architecture Highlights

DigiScript uses split front-end and back-end architecture with the following key technologies:

- **Real-time WebSocket protocol** with leader-follower architecture for synchronized multi-client operation
- **SQLAlchemy 2.0 ORM** with sophisticated revision-scoped associations for managing complex script relationships
- **Vuex state management** with modular structure and localStorage persistence for reactive UIs
- **JWT authentication** with role-based access control using bitmask permissions
- **Compiled script caching** with gzip compression for fast live show performance
- **Automatic database migrations** via Alembic, checked on server startup

## Project Structure

DigiScript consists of three main components:

- **`server/`** - Python Tornado backend with SQLite database
- **`client/`** - Vue.js 2 frontend (builds to `server/static/` for web, or `client/dist-electron/` for Electron)
- **`electron/`** - Electron desktop application wrapper

## Building the Web Client

```shell
cd client
npm ci
npm run build
```

This outputs the built frontend to `../server/static/` for serving by the Python backend.

## Building the Electron Desktop App

The Electron app is a standalone desktop client that connects to a DigiScript server over the network.

### Prerequisites

- Node.js 24.x
- npm 11.x

### Development

```shell
# Build the Electron renderer (Vue app configured for Electron)
cd client
BUILD_TARGET=electron npm run build

# Run the Electron app in development mode
cd ../electron
npm ci
npm run dev
```

### Building Installers

```shell
# Full build (renderer + installers)
cd electron
npm run build

# Or step by step:
cd client
BUILD_TARGET=electron npm run build
cd ../electron
npm run package  # Creates unpacked app
npm run make     # Creates platform installers
```

Output locations:
- **Windows**: `electron/out/make/squirrel.windows/x64/*.exe`
- **macOS**: `electron/out/make/*.zip`
- **Linux**: `electron/out/make/deb/x64/*.deb` and `electron/out/make/rpm/x64/*.rpm`

### Electron vs Web Build

The `BUILD_TARGET` environment variable controls how the Vue client is built:

| Build Target | Output Directory | Base URL | Use Case |
|--------------|------------------|----------|----------|
| (default) | `server/static/` | `/` | Web client served by Python backend |
| `electron` | `client/dist-electron/` | `./` (relative) | Electron app loads files locally |

## Contributing

Contributions are welcome! Please ensure all client and server code passes linting checks before submitting pull requests:

```shell
# Client linting
cd client
npm run lint

# Server linting
cd server
ruff check server/
ruff format server/

# Electron linting
cd electron
npm run lint
```

When creating pull requests for new features, target the `dev` branch.

## Websocket messaging

Websockets are used to communicate between the clients and the server.

### Server -> Client

Messages should be structured with the following data format:

```json
{
  "OP": "SOME_OP_CODE",
  "DATA": {},
  "ACTION": "SOME_ACTION"
}
```

On the client side, the messages are handled in 2 places (in the [Vuex store](client/src/store/store.js)):

1. Vuex mutation `SOCKET_ONMESSAGE` is called for every message, and should handle each OP code as needed
2. Vuex action `SOME_ACTION` needs to be defined, and is called only if the data contains an `ACTION` key/value pair

### Client -> Server

TBD
