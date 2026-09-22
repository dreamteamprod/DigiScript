import crypto from 'crypto';
import os from 'os';
import path from 'path';

/**
 * Backend port for the E2E test server.
 *
 * Multiple E2E runs (e.g. separate git worktrees driven by parallel agent
 * jobs) must never collide on the same port. Resolution order:
 *
 * 1. `E2E_PORT` env var, if set — explicit override (also used by CI to pin
 *    a fixed port if desired).
 * 2. Otherwise, a port deterministically derived from `process.cwd()` — each
 *    checkout/worktree always gets the same port, and distinct checkouts get
 *    distinct ports, with no cross-process coordination required.
 *
 * The derived range (20000-39999) avoids the well-known/ephemeral ranges and
 * the app's own default dev ports (8080/8888).
 */
function resolvePort(): number {
  const envPort = process.env.E2E_PORT;
  if (envPort) {
    const parsed = parseInt(envPort, 10);
    if (Number.isNaN(parsed) || parsed <= 0 || parsed > 65535) {
      throw new Error(`E2E_PORT must be a valid port number, got: ${envPort}`);
    }
    return parsed;
  }

  const hash = crypto.createHash('sha1').update(process.cwd()).digest();
  const hashInt = hash.readUInt32BE(0);
  return 20000 + (hashInt % 20000);
}

export const SERVER_PORT = resolvePort();
export const BASE_URL = `http://localhost:${SERVER_PORT}`;
export const HEALTH_URL = `${BASE_URL}/api/v1/health`;

/**
 * Directory holding this run's state (server PID, temp dir pointer, log).
 * Keyed by port rather than a fixed name so two runs never share — and thus
 * never clobber — each other's state, even if both write to `os.tmpdir()`.
 */
export const RUN_DIR = path.join(os.tmpdir(), `digiscript-e2e-${SERVER_PORT}`);
export const STATE_FILE = path.join(RUN_DIR, 'state.json');
export const SERVER_LOG_FILE = path.join(RUN_DIR, 'server.stdout.log');

export interface RunState {
  pid: number;
  tempDir: string;
  startedAt: string;
}
