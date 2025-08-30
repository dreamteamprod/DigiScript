# Vue 2 Frontend Build Stage
FROM node:22-bookworm AS vue2_build

RUN npm install npm@10 -g
COPY /client/package.json /client/package.json
COPY /client/package-lock.json /client/package-lock.json
WORKDIR /client
RUN npm ci
COPY /client /client
RUN npm run build

# Vue 3 Frontend Build Stage
FROM node:22-bookworm AS vue3_build

RUN npm install npm@10 -g
COPY /client-vue3/package.json /client-vue3/package.json
COPY /client-vue3/package-lock.json /client-vue3/package-lock.json
WORKDIR /client-vue3
RUN npm ci
COPY /client-vue3 /client-vue3
RUN npm run build

# Server Preparation Stage
FROM python:3.13-bookworm AS server_prep

COPY /server /server
RUN mkdir -p /server/static
RUN mkdir -p /server/static-vue3

# Copy Vue 2 build artifacts
COPY --from=vue2_build /server/static/ /server/static/
# Copy Vue 3 build artifacts  
COPY --from=vue3_build /server/static-vue3/ /server/static-vue3/

# Final Production Stage
FROM python:3.13-bookworm

COPY /server/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

RUN apt update
RUN apt install -y nano

# Copy server with both frontend builds
COPY --from=server_prep /server /server
WORKDIR /server
RUN mkdir conf
EXPOSE 8080
ENTRYPOINT ["python3", "main.py"]