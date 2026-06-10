FROM node:24-bookworm AS build_v2

RUN mkdir -p /server/static
COPY /client/package.json /client/package.json
COPY /client/package-lock.json /client/package-lock.json
COPY /client/.npmrc /client/.npmrc
WORKDIR /client
RUN npm ci
COPY /client /client
RUN npm run build

FROM node:24-bookworm AS build_v3

RUN mkdir -p /server/static
COPY /client-v3/package.json /client-v3/package.json
COPY /client-v3/package-lock.json /client-v3/package-lock.json
WORKDIR /client-v3
RUN npm ci
COPY /client-v3 /client-v3
COPY /docs /docs
RUN npm run build

FROM python:3.13-bookworm

COPY /server/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

RUN apt update
RUN apt install -y nano

COPY /server /server
COPY --from=build_v2 /server/static /server/static
COPY --from=build_v3 /server/static /server/static
WORKDIR /server
RUN mkdir conf
EXPOSE 8080
ENTRYPOINT ["python3", "main.py"]
