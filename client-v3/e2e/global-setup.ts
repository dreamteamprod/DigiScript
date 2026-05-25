import { spawn, execFileSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import os from 'os';

const SERVER_PORT = 8888;
const HEALTH_URL = `http://localhost:${SERVER_PORT}/api/v1/health`;

export const PID_FILE = path.join(os.tmpdir(), 'digiscript-e2e-server.pid');
export const TMPDIR_FILE = path.join(os.tmpdir(), 'digiscript-e2e-tmpdir.txt');

export default async function globalSetup(): Promise<void> {
  // Kill any stale server from a previous run that survived teardown
  await killStaleServer();

  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'digiscript-e2e-'));
  const configPath = path.join(tempDir, 'digiscript.json');
  const dbPath = path.join(tempDir, 'digiscript.sqlite');

  fs.writeFileSync(
    configPath,
    JSON.stringify({
      db_path: `sqlite:///${dbPath}`,
      mdns_advertising: false,
      log_path: path.join(tempDir, 'digiscript.log'),
    })
  );
  fs.writeFileSync(TMPDIR_FILE, tempDir);

  // server/ is a sibling of client-v3/ — process.cwd() is client-v3/ when
  // invoked via "npm run test:e2e" or with working-directory: ./client-v3 in CI
  const serverDir = path.resolve(process.cwd(), '..', 'server');

  const server = spawn(
    'python3',
    ['main.py', `--port=${SERVER_PORT}`, `--settings_path=${configPath}`, '--debug=false'],
    {
      cwd: serverDir,
      detached: true,
      stdio: 'ignore',
    }
  );

  if (server.pid === undefined) {
    throw new Error('Failed to start DigiScript test server');
  }

  fs.writeFileSync(PID_FILE, String(server.pid));
  server.unref();

  await waitForServer();
  console.log(`DigiScript test server ready on port ${SERVER_PORT}`);
}

/** Kill any process listening on SERVER_PORT (handles failed teardowns). */
async function killStaleServer(): Promise<void> {
  // Quick check — if port is free, nothing to do
  try {
    await fetch(HEALTH_URL, { signal: AbortSignal.timeout(1000) });
  } catch {
    return; // connection refused → port is free
  }

  // Port is in use — find and kill PIDs via lsof (macOS/Linux)
  try {
    const output = execFileSync('lsof', ['-ti', String(SERVER_PORT)], { encoding: 'utf-8' });
    const pids = output
      .trim()
      .split('\n')
      .filter(Boolean)
      .map((s) => parseInt(s, 10))
      .filter((n) => !isNaN(n));
    for (const pid of pids) {
      try {
        process.kill(pid, 'SIGKILL');
      } catch {
        // process already gone
      }
    }
    if (pids.length > 0) {
      await new Promise((r) => setTimeout(r, 1500));
    }
  } catch {
    // lsof not available (e.g. Windows) or no PIDs found — best effort
  }
}

async function waitForServer(timeoutMs = 30_000): Promise<void> {
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
