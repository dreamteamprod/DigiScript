# The frontend build emits platform-independent static files, so run it on the
# native build platform rather than emulating the target arch (slow under QEMU).
FROM --platform=$BUILDPLATFORM node:24-bookworm AS build

RUN corepack enable
RUN mkdir -p /server/static
COPY /client/package.json /client/package.json
COPY /client/pnpm-lock.yaml /client/pnpm-lock.yaml
COPY /client/pnpm-workspace.yaml /client/pnpm-workspace.yaml
WORKDIR /client
RUN pnpm install --frozen-lockfile
COPY /client /client
COPY /docs /docs
RUN pnpm run build

FROM python:3.13-bookworm

COPY /server/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

RUN apt update
RUN apt install -y nano

COPY /server /server
COPY --from=build /server/static /server/static
WORKDIR /server
RUN mkdir conf
EXPOSE 8080
# NOTE: the probe targets port 8080 (the main.py --port default). If the container
# is started with a different --port, override the check with `docker run --health-cmd`
# or the compose `healthcheck:` key, otherwise it will be reported unhealthy.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD ["python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/v1/health', timeout=4)"]
ENTRYPOINT ["python3", "main.py"]
