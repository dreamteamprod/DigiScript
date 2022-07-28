# DigiScript

A digital script project for queueing theatrical shows

## Getting started

### Client

This installs and builds the client side files (nvm recommended)

```shell
cd client
npm ci
npm run build
```

### Server

This installs the Python requirements needed to run the server (pyenv recommended)

```shell
cd server
pip install -r requirements.txt
```

## Running

This starts the web server listening on port 8080

```shell
cd server
./main.py
```

### Running using docker

This will start DigiScript running, and map port 8080 locally to 8080 on the container

```shell
docker build -t digiscript:latest .
docker run -p 8080:8080 digiscript:latest
```

## Development Guide

### Websocket messaging

Websockets are used to communicate between the clients and the server.

#### Server -> Client

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

#### Client -> Server

TBD