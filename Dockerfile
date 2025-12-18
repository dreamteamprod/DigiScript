FROM node:22-bookworm AS node_build

RUN npm install npm@10 -g
RUN mkdir -p /server/static

COPY /client/package.json /client/package.json
COPY /client/package-lock.json /client/package-lock.json
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