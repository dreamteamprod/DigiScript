FROM node:18.19.1-buster AS node_build
RUN npm install npm@8 -g

COPY /client /client
WORKDIR /client
RUN npm ci
COPY /server /server
RUN npm run build

FROM python:3.10-buster

COPY /server/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

RUN apt update
RUN apt install -y nano

COPY --from=node_build /server /server
WORKDIR /server
RUN mkdir conf
EXPOSE 8080
ENTRYPOINT ["python3", "main.py"]