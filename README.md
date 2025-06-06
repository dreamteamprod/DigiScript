# DigiScript

A digital script project for cueing theatrical shows

**Main Status:**
[![ESLint](https://github.com/dreamteamprod/DigiScript/actions/workflows/nodelint.yml/badge.svg?branch=main)](https://github.com/dreamteamprod/DigiScript/actions/workflows/nodelint.yml)
[![Pylint](https://github.com/dreamteamprod/DigiScript/actions/workflows/pylint.yml/badge.svg?branch=main)](https://github.com/dreamteamprod/DigiScript/actions/workflows/pylint.yml)

**Dev Status:**
[![ESLint](https://github.com/dreamteamprod/DigiScript/actions/workflows/nodelint.yml/badge.svg?branch=dev)](https://github.com/dreamteamprod/DigiScript/actions/workflows/nodelint.yml)
[![Pylint](https://github.com/dreamteamprod/DigiScript/actions/workflows/pylint.yml/badge.svg?branch=dev)](https://github.com/dreamteamprod/DigiScript/actions/workflows/pylint.yml)

## Getting started

### Requirements

* Node v22.x (npm 10.x)
* Python 3.13.x

### Client

This installs and builds the client side files ([nvm](https://github.com/nvm-sh/nvm) recommended)

```shell
cd client
npm ci
npm run build
```

### Server

This installs the Python requirements needed to run the server ([pyenv](https://github.com/pyenv/pyenv) recommended)

```shell
cd server
pip install -r requirements.txt
```

## Other Documentation

* **[Development Guide](./documentation/development.md)**
* **[Deployment Guide](./documentation/deployment.md)**