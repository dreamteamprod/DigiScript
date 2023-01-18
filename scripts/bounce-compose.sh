#!/usr/bin/env sh

docker-compose down -v --remove-orphans
docker-compose up --build --force-recreate --no-deps