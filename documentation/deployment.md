# Deploying DigiScript

## Server Deployment

### Running Locally

This starts the web server listening on port 8080:

```shell
cd server
./main.py
```

### Running using Docker

This will start DigiScript running, and map port 8080 locally to 8080 on the container:

```shell
docker build -t digiscript:latest .
docker-compose up -d
```

`docker-compose up -d` starts the DigiScript server only. For metrics dashboards see
[Monitoring](#monitoring) below.

### Monitoring

An optional compose overlay adds Prometheus and Grafana, pre-provisioned with a
"DigiScript Overview" dashboard and basic alert rules:

```shell
export GF_SECURITY_ADMIN_PASSWORD='choose-a-strong-password'
docker compose -f docker-compose.yaml -f docker-compose.monitoring.yaml up -d
```

`GF_SECURITY_ADMIN_PASSWORD` is required (there is no default); compose refuses to
start without it.

| Service    | URL                     | Notes                                   |
|------------|-------------------------|-----------------------------------------|
| Grafana    | `http://localhost:3000` | Log in as `admin` with the password set |
| Prometheus | `http://localhost:9090` | Scrapes `server:8080/debug/metrics`     |

Both ports are published on `127.0.0.1` only. To expose them set `GRAFANA_BIND` /
`PROMETHEUS_BIND` (e.g. `GRAFANA_BIND=0.0.0.0`) and put a TLS-terminating reverse proxy
in front. The scrape path is configured in `monitoring/prometheus/prometheus.yml`.

**Security:** `/debug/metrics` is currently unauthenticated. Do not expose DigiScript's
port 8080 to the public internet without a reverse proxy that restricts this path.

Application logs can be viewed in-app via the log viewer.

#### Health check

`GET /api/v1/health` is an unauthenticated liveness/readiness probe, suitable for load
balancer or container health checks. The Docker image uses it for its built-in
`HEALTHCHECK` (every 30s, 5s timeout, 30s start period, 3 retries). Requests to it are
not written to the access log.

It runs `SELECT 1` against the database (3s timeout) and checks that the directories
holding the log files, the draft script path and the compiled script path are writable.

| Condition | HTTP status | `status` |
|---|---|---|
| Database and storage checks pass | `200` | `ok` |
| Either check fails or the database times out | `503` | `degraded` |

Example healthy response:

```json
{
  "version": "0.35.2",
  "status": "ok",
  "checks": { "database": "ok", "storage": "ok" },
  "uptime_seconds": 1234
}
```

A failing check is reported as `"fail"` in `checks`. The response never includes error
text or file paths; the detail is written to the server log instead (`ERROR` for the
database, `WARNING` for storage), so look there to find out why a probe is failing.

#### Metrics reference

| Metric | Type | Meaning |
|--------|------|---------|
| `python_*`, `process_*` | various | Python runtime and process stats |
| `tornado_http_requests_total` | counter | HTTP requests by method, handler and status |
| `tornado_http_request_duration_seconds` | histogram | HTTP request latency |
| `digiscript_http_request_body_bytes` | histogram | Size of HTTP request bodies, by handler and method |
| `digiscript_ws_message_bytes` | histogram | Size of inbound WebSocket messages |
| `digiscript_ws_connections` | gauge | Open WebSocket connections |
| `digiscript_ws_messages_total{op}` | counter | WebSocket messages by operation |
| `digiscript_collab_rooms` | gauge | Active collaborative editing rooms |
| `digiscript_show_session_active` | gauge | 1 if a live show session is running, else 0 |
| `digiscript_info{version}` | gauge | Always 1; carries the server version label |
| `digiscript_auth_events_total{event,result}` | counter | Authentication events by type and result |
| `digiscript_unhandled_errors_total{source}` | counter | Unhandled errors by source |

Note: older releases do not expose all of these metrics (for example the `tornado_http_*`
series and the newer `digiscript_*` gauges and counters). Dashboard panels for metrics
your server version does not expose show "No data".

### Pre-built Server Executables

Pre-built server executables are available from [GitHub Releases](https://github.com/dreamteamprod/DigiScript/releases):

- **Linux**: `DigiScript-linux.zip`
- **Windows**: `DigiScript-windows.zip`
- **macOS**: `DigiScript-macos.zip`

These are standalone PyInstaller executables with the web frontend bundled.
