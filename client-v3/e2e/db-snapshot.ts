import fs from 'fs';
import path from 'path';
import { spawn } from 'child_process';
import { test } from '@playwright/test';
import { PID_FILE, TMPDIR_FILE, SERVER_PORT, waitForServer } from './global-setup.js';

function getPaths() {
  const tempDir = fs.readFileSync(TMPDIR_FILE, 'utf-8').trim();
  const db = path.join(tempDir, 'digiscript.sqlite');
  const config = path.join(tempDir, 'digiscript.json');
  return {
    db,
    dbSpecStart: `${db}.specstart`,
    config,
    configSpecStart: `${config}.specstart`,
    serverDir: path.resolve(process.cwd(), '..', 'server'),
  };
}

export function specStartExists(): boolean {
  return fs.existsSync(getPaths().dbSpecStart);
}

/** Copy the current DB and config to the spec-start snapshot files. */
export function snapshotSpecStart(): void {
  const { db, dbSpecStart, config, configSpecStart } = getPaths();
  fs.copyFileSync(db, dbSpecStart);
  fs.copyFileSync(config, configSpecStart);
}

/**
 * Restore DB and config from the spec-start snapshot, then restart the server.
 * This returns the backend to the state it was in before this spec's first test ran,
 * so every test in the spec can re-run cleanly without hitting its own prior side effects.
 */
export async function restoreSpecStartAndRestartServer(): Promise<void> {
  const { db, dbSpecStart, config, configSpecStart, serverDir } = getPaths();

  if (fs.existsSync(PID_FILE)) {
    const pid = parseInt(fs.readFileSync(PID_FILE, 'utf-8').trim(), 10);
    try {
      process.kill(pid, 'SIGKILL');
    } catch {
      // process already gone
    }
    await new Promise((r) => setTimeout(r, 500));
  }

  // Remove any stale journal file (server uses DELETE journal mode, not WAL)
  try {
    fs.rmSync(`${db}-journal`);
  } catch {
    // no journal file present
  }

  fs.copyFileSync(dbSpecStart, db);
  fs.copyFileSync(configSpecStart, config);

  const server = spawn(
    'python3',
    ['main.py', `--port=${SERVER_PORT}`, `--settings_path=${config}`, '--debug=false'],
    { cwd: serverDir, detached: true, stdio: 'ignore' }
  );
  fs.writeFileSync(PID_FILE, String(server.pid!));
  server.unref();

  await waitForServer();
}

/**
 * Register beforeAll hooks for retry support. Call once at the top of each spec file.
 *
 * On first run (retry=0): captures the DB state at spec start so retries have a clean baseline.
 * On retry: restores from that spec-start snapshot before tests run again, ensuring every test
 * in the spec sees the same starting conditions regardless of side effects from prior attempts.
 */
export function registerRetryHooks(): void {
  test.beforeAll(async () => {
    if (test.info().retry > 0 && specStartExists()) {
      await restoreSpecStartAndRestartServer();
    }
  });
  test.beforeAll(async () => {
    if (test.info().retry === 0) {
      snapshotSpecStart();
    }
  });
}
