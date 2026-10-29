## Anonymous Usage Telemetry

DigiScript periodically sends a small, anonymous usage report to the DigiScript project, to help
guide development priorities — which versions are actually in use, roughly how big installs tend
to be, and which optional features see real adoption. This is enabled by default, and can be
turned off at any time.

### What is sent

Every check-in (roughly once a day, with a random delay so many installs don't all report at the
same moment) sends:

- A randomly generated **anonymous instance ID**, created once on first check-in and never tied
  to a person, username, or show.
- **DigiScript version**, **OS platform/architecture**, and **deployment method** (Docker vs.
  bare metal).
- **Days since first check-in** and a **check-in count**.
- A **count of unhandled errors** since the last check-in (a number only — no error message,
  stack trace, or file path).
- **Bucketed** counts of shows, users, and sessions (e.g. `"1"`, `"2-5"`, `"6+"`) — never exact
  numbers.
- Whether **RBAC** is being used to manage more than one person's access, and whether the
  **collaborative script editor** has been used — both as plain `true`/`false`.

### What is never sent

Show or script content, usernames, email addresses, passwords or tokens, raw IP addresses, file
paths, or error messages/stack traces. The anonymous instance ID cannot be used to identify a
person or a specific installation's content.

### How it's collected

Reports are sent to a small, purpose-built collector (`telemetry.digiscript.dreamteamprod.co.uk`)
run by the DigiScript project on Cloudflare's infrastructure, which stores only the fields listed
above.

### Turning it off

Two ways to disable telemetry, either of which is sufficient on its own:

- **In the app**: System Config → System → Settings, under the **Telemetry** category, toggle
  **Enable Anonymous Usage Telemetry** off.
- **At deployment time**: set the `DIGISCRIPT_TELEMETRY` environment variable to `0`, `false`,
  `no`, `off`, `disabled`, or `n` (case-insensitive) before starting the server. This takes
  priority over the in-app setting — if both are set, telemetry stays off even if the setting
  shows as enabled.
