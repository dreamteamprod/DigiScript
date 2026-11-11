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
- **Pinia state management** with feature-based stores and persisted-state plugin for reactive UIs
- **JWT authentication** with role-based access control using bitmask permissions
- **Compiled script caching** with gzip compression for fast live show performance
- **Automatic database migrations** via Alembic, checked on server startup

## Project Structure

DigiScript consists of two main components:

- **`server/`** - Python Tornado backend with SQLite database
- **`client-v3/`** - Vue.js 3 frontend, builds to `server/static/`

Refer to [DeepWiki](https://deepwiki.com/dreamteamprod/DigiScript) for detailed documentation on the architecture and design.

## Building the Web Client

The frontend uses [pnpm](https://pnpm.io/). Node 24.15 or newer is required (an older 24.x fails on transitive dependencies' engine ranges). Node 24 ships Corepack but leaves it switched off, so run `corepack enable` once; pnpm will then use the version pinned in `client-v3/package.json`'s `packageManager` field. Running `npm install` in this directory is refused on purpose (`devEngines`), so the pnpm lockfile stays the only source of truth.

```shell
cd client-v3
pnpm install
pnpm run build
```

This outputs the built frontend to `../server/static/` for serving by the Python backend.

## Contributing

Contributions are welcome! Please ensure all client and server code passes linting checks before submitting pull requests:

```shell
# Client linting and type checking
cd client-v3
pnpm run lint
pnpm run typecheck

# Server linting
cd server
ruff check server/
ruff format server/
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

On the client side, the messages are handled in [`useWebSocket.ts`](client-v3/src/composables/useWebSocket.ts):

1. `handleMessage()` switches on `OP` for direct handling
2. If an `ACTION` key is present, `dispatchAction()` is called. Dispatch is convention-based: it scans all active Pinia stores for a camelCase action matching the WS `ACTION` name (e.g. `GET_CUE_TYPES` → `getCueTypes()`) — no registration map is needed, just define the matching Pinia action

### Client -> Server

TBD
