# DigiScript E2E Tests

End-to-end tests for the Vue 3 frontend, written with [Playwright](https://playwright.dev/).
Tests run against a real backend instance with a clean SQLite database, covering every major user-facing workflow.

## Prerequisites

* Node 24.x with dependencies installed (`npm ci` in `client-v3/`)
* Python 3.13.x with dependencies installed (`pip install -r requirements.txt` in `server/`)
* A production build of the frontend (`npm run build` in `client-v3/`)

The global setup script starts and stops the backend automatically — no manual server management required.

## Running the tests

```bash
# Chromium only (default, fastest)
npm run test:e2e

# Firefox only
npm run test:e2e:firefox

# Both browsers
npm run test:e2e:all

# Open the HTML report from the last run
npm run test:e2e:report
```

## How it works

Before the suite runs, `e2e/global-setup.ts` launches the Python backend on port 8888 with a
temporary SQLite database. After the suite finishes, `e2e/global-teardown.ts` stops the server
and cleans up the database file. All tests share this single server instance and database.

## Spec files

Tests are numbered to enforce a specific run order. Each spec depends on the database state
left by earlier specs.

| File | Area |
|------|------|
| `01-first-run.spec.ts` | Initial server setup wizard |
| `02-auth.spec.ts` | Login, logout, session handling |
| `03-system-config.spec.ts` | System Config: show creation, users, settings, system info, logs, backups |
| `04-show-config-show.spec.ts` | Show Config: show details |
| `05-show-config-acts-scenes.spec.ts` | Show Config: acts and scenes CRUD |
| `06-show-config-characters.spec.ts` | Show Config: characters CRUD |
| `07-show-config-stage.spec.ts` | Show Config: props, scenery, crew, stage manager allocations |
| `08-show-config-cues.spec.ts` | Show Config: cue types CRUD |
| `09-show-config-mics.spec.ts` | Show Config: microphones, allocations, timeline |
| `10-show-config-script.spec.ts` | Show Config: script editing, saving, stage direction styles, cue add/edit/delete |
| `11-show-config-revisions.spec.ts` | Show Config: script revisions |
| `12-show-config-sessions.spec.ts` | Show Config: live show sessions |
| `13-live-show.spec.ts` | Live show display and cue triggering |
| `14-user-settings.spec.ts` | User settings and profile |

> **Important**: specs must always be run as a full suite. Running individual spec files in
> isolation will fail because each spec relies on database state created by earlier specs.
> Never use `--grep` or file-specific invocations in CI or local development.

## Debugging

Failed test runs produce an HTML report and screenshots/videos under `playwright-report/`.
Open the report with:

```bash
npm run test:e2e:report
```

Trace files (recorded on failure) can be inspected with the Playwright Trace Viewer.

## CI

The GitHub Actions workflow (`.github/workflows/playwright-test.yml`) runs the full suite against
both Chromium and Firefox on every pull request. The workflow builds the frontend, installs
Playwright browsers, runs the suite, and uploads the HTML report as an artifact.
