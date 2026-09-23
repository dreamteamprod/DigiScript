# The frontend builds emit platform-independent static files, so run them on the
# native build platform rather than emulating the target arch (slow under QEMU).
FROM --platform=$BUILDPLATFORM node:24-bookworm AS build_v2

RUN corepack enable && corepack prepare pnpm@12.5.1 --activate
RUN mkdir -p /server/static
COPY /client/package.json /client/package.json
COPY /client/pnpm-lock.yaml /client/pnpm-lock.yaml
COPY /client/pnpm-workspace.yaml /client/pnpm-workspace.yaml
COPY /client/.npmrc /client/.npmrc
WORKDIR /client
RUN pnpm install --frozen-lockfile
COPY /client /client
RUN pnpm run build

FROM --platform=$BUILDPLATFORM node:24-bookworm AS build_v3

RUN corepack enable && corepack prepare pnpm@12.5.1 --activate
RUN mkdir -p /server/static
COPY /client-v3/package.json /client-v3/package.json
COPY /client-v3/pnpm-lock.yaml /client-v3/pnpm-lock.yaml
COPY /client-v3/pnpm-workspace.yaml /client-v3/pnpm-workspace.yaml
WORKDIR /client-v3
RUN pnpm install --frozen-lockfile
COPY /client-v3 /client-v3
COPY /docs /docs
RUN pnpm run build

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
