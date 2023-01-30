# Deploying DigiScript

## Running Locally

This starts the web server listening on port 8080

```shell
cd server
./main.py
```

## Running using docker

This will start DigiScript running, and map port 8080 locally to 8080 on the container

```shell
docker build -t digiscript:latest .
docker-compose up -d
```