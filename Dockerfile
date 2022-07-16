FROM node:16.5-buster AS node_build

COPY /server /server
COPY /client /client
WORKDIR /client
RUN npm ci
RUN npm run build

FROM python:3.7-buster
COPY --from=node_build /server /server
WORKDIR /server
RUN pip install -r requirements.txt
EXPOSE 8080
ENTRYPOINT ["python3", "main.py"]