import fs from 'node:fs';

import { STATE_FILE, RUN_DIR, RunState } from './env.js';

export default async function globalTeardown(): Promise<void> {
  if (fs.existsSync(STATE_FILE)) {
    let state: RunState | undefined;
    try {
      state = JSON.parse(fs.readFileSync(STATE_FILE, 'utf-8'));
    } catch {
      // malformed state file — nothing to act on
    }

    if (state) {
      try {
        process.kill(state.pid, 'SIGKILL');
      } catch {
        // process may have already exited
      }
      try {
        fs.rmSync(state.tempDir, { recursive: true, force: true });
      } catch {
        // best-effort cleanup
      }
    }
  }

  // Removes state.json, the run's temp dirs, and server.stdout.log together.
  fs.rmSync(RUN_DIR, { recursive: true, force: true });
}
