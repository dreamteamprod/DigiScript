# Development Guide

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
