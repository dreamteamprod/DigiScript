FROM node:24-bookworm AS node_build

# npm 11 bundled with Node 24, no separate install needed
RUN mkdir -p /server/static

COPY /client/package.json /client/package.json
COPY /client/package-lock.json /client/package-lock.json
COPY /client/.npmrc /client/.npmrc
WORKDIR /client
RUN npm ci
COPY /client /client
COPY /docs /docs
RUN npm run build

COPY /server /server

FROM python:3.14-bookworm

COPY /server/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

RUN apt update
RUN apt install -y nano

COPY --from=node_build /server /server
WORKDIR /server
RUN mkdir conf
EXPOSE 8080
ENTRYPOINT ["python3", "main.py"]