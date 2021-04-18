# DigiScript

Digital Script for Theatre Cues

## Requirements

* Node.js (>=14.x)
* npm (>=6.x)

## Development

### Setting up the environment

```sh
cd server
npm install
cd ../client
npm install
```

### Building the client side app

```sh
cd client
npm run build
```

Or, to keep the build running and react to any changes to the front end files:

```sh
cd client
npm run build -- --watch
```

### Starting the Node server

```sh
cd server
npm run dev -- --config=config.js
```

This will start the server using nodemon, which watches for changes to the files and hot reloads the server.
Useful for developing with. Once the server is started, it can be accessed at `localhost:3080`.

## Building for production

Coming soon (TM)
