FROM node:18.16.0-buster AS node_build
RUN npm install npm@8 -g

COPY /server /server
COPY /client /client
WORKDIR /client
RUN npm ci
RUN npm run build

FROM python:3.10-buster
RUN apt update
RUN apt install -y nano

COPY --from=node_build /server /server
WORKDIR /server
RUN mkdir conf
RUN pip install -r requirements.txt
EXPOSE 8080
ENTRYPOINT ["python3", "main.py"]