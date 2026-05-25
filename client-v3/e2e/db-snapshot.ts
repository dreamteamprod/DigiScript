import fs from 'fs';
import path from 'path';
import { spawn } from 'child_process';
import { PID_FILE, TMPDIR_FILE, SERVER_PORT, waitForServer } from './global-setup.js';

function getPaths() {
  const tempDir = fs.readFileSync(TMPDIR_FILE, 'utf-8').trim();
  return {
    db: path.join(tempDir, 'digiscript.sqlite'),
    dbSnapshot: path.join(tempDir, 'digiscript.sqlite.snapshot'),
    config: path.join(tempDir, 'digiscript.json'),
    configSnapshot: path.join(tempDir, 'digiscript.json.snapshot'),
    serverDir: path.resolve(process.cwd(), '..', 'server'),
  };
}

export function snapshotExists(): boolean {
  const { dbSnapshot } = getPaths();
  return fs.existsSync(dbSnapshot);
}

/** Copy the DB and config to snapshot files. Call after each passing test. */
export function snapshotState(): void {
  const { db, dbSnapshot, config, configSnapshot } = getPaths();
  fs.copyFileSync(db, dbSnapshot);
  fs.copyFileSync(config, configSnapshot);
}

/**
 * Restore DB and config from the last snapshot, then restart the server.
 * Call at the start of a retry to bring the backend back to last known-good state.
 */
export async function restoreStateAndRestartServer(): Promise<void> {
  const { db, dbSnapshot, config, configSnapshot, serverDir } = getPaths();

  // Kill existing server
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

  // Restore DB and config from snapshot
  fs.copyFileSync(dbSnapshot, db);
  fs.copyFileSync(configSnapshot, config);

  // Respawn server with the restored config
  const server = spawn(
    'python3',
    ['main.py', `--port=${SERVER_PORT}`, `--settings_path=${config}`, '--debug=false'],
    { cwd: serverDir, detached: true, stdio: 'ignore' }
  );
  fs.writeFileSync(PID_FILE, String(server.pid!));
  server.unref();

  await waitForServer();
}
