import { spawn, execFileSync } from 'child_process';
import fs from 'fs';
import net from 'net';
import path from 'path';

import { SERVER_PORT, HEALTH_URL, RUN_DIR, STATE_FILE, SERVER_LOG_FILE, RunState } from './env.js';

export default async function globalSetup(): Promise<void> {
  fs.mkdirSync(RUN_DIR, { recursive: true });

  // Reap our own leftover server from a previous run that crashed before
  // teardown ran. We only ever kill a PID we can positively identify as
  // ours — never whatever happens to be listening on the port.
  await reapOwnStaleServer();
  await assertPortFree();

  const tempDir = fs.mkdtempSync(path.join(RUN_DIR, 'run-'));
  const configPath = path.join(tempDir, 'digiscript.json');
  const dbPath = path.join(tempDir, 'digiscript.sqlite');

  fs.writeFileSync(
    configPath,
    JSON.stringify({
      db_path: `sqlite:///${dbPath}`,
      mdns_advertising: false,
      log_path: path.join(tempDir, 'digiscript.log'),
      db_log_path: path.join(tempDir, 'digiscript_db.log'),
      client_log_path: path.join(tempDir, 'digiscript_client.log'),
      compiled_script_path: path.join(tempDir, 'compiled_scripts'),
      draft_script_path: path.join(tempDir, 'draft_scripts'),
    })
  );

  // server/ is a sibling of client-v3/ — process.cwd() is client-v3/ when
  // invoked via "npm run test:e2e" or with working-directory: ./client-v3 in CI
  const serverDir = path.resolve(process.cwd(), '..', 'server');

  const serverLog = fs.openSync(SERVER_LOG_FILE, 'a');
  const server = spawn(
    'python3',
    ['main.py', `--port=${SERVER_PORT}`, `--settings_path=${configPath}`, '--debug=false'],
    {
      cwd: serverDir,
      detached: true,
      stdio: ['ignore', serverLog, serverLog],
    }
  );

  if (server.pid === undefined) {
    throw new Error('Failed to start DigiScript test server');
  }

  const state: RunState = { pid: server.pid, tempDir, startedAt: new Date().toISOString() };
  fs.writeFileSync(STATE_FILE, JSON.stringify(state));
  server.unref();

  try {
    await waitForServer();
  } catch (err) {
    const log = fs.existsSync(SERVER_LOG_FILE) ? fs.readFileSync(SERVER_LOG_FILE, 'utf-8') : '';
    throw new Error(`${(err as Error).message}\n--- server log (${SERVER_LOG_FILE}) ---\n${log}`, {
      cause: err,
    });
  }
  console.log(`DigiScript test server ready on port ${SERVER_PORT}`);
}

/**
 * PIDs of live processes whose command line unmistakably identifies them as
 * a DigiScript test server for *this* port (`main.py ... --port=<port>`).
 * Matching on process identity, rather than trusting `state.json`'s recorded
 * PID, also catches a server left behind by a crashed run whose state file
 * was already removed — e.g. a race between db-snapshot.ts's retry-restart
 * hook and Playwright's own globalTeardown.
 */
function findOwnServerPids(): number[] {
  let out: string;
  try {
    // BSD/GNU `ps` both support this form; not available on Windows.
    out = execFileSync('ps', ['-eo', 'pid=,command='], { encoding: 'utf-8' });
  } catch {
    return [];
  }

  const needle = `--port=${SERVER_PORT}`;
  return out
    .split('\n')
    .filter((line) => line.includes('main.py') && line.includes(needle))
    .map((line) => parseInt(line.trim().split(/\s+/)[0], 10))
    .filter((pid) => !isNaN(pid));
}

/**
 * Kill any live process that is unmistakably our own leftover test server
 * for this port, and best-effort clean up the state file it left behind.
 * Anything else is left alone.
 */
async function reapOwnStaleServer(): Promise<void> {
  const pids = findOwnServerPids();
  for (const pid of pids) {
    try {
      process.kill(pid, 'SIGKILL');
    } catch {
      // already gone
    }
  }
  if (pids.length > 0) {
    await new Promise((r) => setTimeout(r, 500));
  }

  if (!fs.existsSync(STATE_FILE)) return;
  try {
    const state: RunState = JSON.parse(fs.readFileSync(STATE_FILE, 'utf-8'));
    fs.rmSync(state.tempDir, { recursive: true, force: true });
  } catch {
    // malformed state file or tempDir already gone — best-effort
  }
  fs.rmSync(STATE_FILE, { force: true });
}

/**
 * Fail fast and loudly if SERVER_PORT is already taken by something we
 * don't own, instead of silently colliding or killing a foreign process.
 */
async function assertPortFree(): Promise<void> {
  const inUse = await new Promise<boolean>((resolve) => {
    const tester = net.createServer();
    tester.once('error', () => resolve(true));
    tester.once('listening', () => tester.close(() => resolve(false)));
    // No host argument: bind all interfaces, same as Tornado's app.listen(port)
    // in main.py. Probing a specific address (e.g. 127.0.0.1) can spuriously
    // succeed even when something else already holds the port on the
    // wildcard address, producing a false "port free" result.
    tester.listen(SERVER_PORT);
  });

  if (inUse) {
    throw new Error(
      `Port ${SERVER_PORT} is already in use by another process (not a stale DigiScript ` +
        `E2E server from this checkout). If this is a false positive, set E2E_PORT to a ` +
        `free port and retry.`
    );
  }
}

export async function waitForServer(timeoutMs = 30_000): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(HEALTH_URL);
      if (res.ok) return;
    } catch {
      // server not ready yet
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`DigiScript test server did not become healthy within ${timeoutMs}ms`);
}
