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
