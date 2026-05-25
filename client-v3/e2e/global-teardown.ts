import fs from 'fs';
import { PID_FILE, TMPDIR_FILE } from './global-setup.js';

export default async function globalTeardown(): Promise<void> {
  if (fs.existsSync(PID_FILE)) {
    const pid = parseInt(fs.readFileSync(PID_FILE, 'utf-8').trim(), 10);
    try {
      process.kill(pid, 'SIGKILL');
    } catch {
      // process may have already exited
    }
    fs.unlinkSync(PID_FILE);
  }

  if (fs.existsSync(TMPDIR_FILE)) {
    const tempDir = fs.readFileSync(TMPDIR_FILE, 'utf-8').trim();
    try {
      fs.rmSync(tempDir, { recursive: true, force: true });
    } catch {
      // best-effort cleanup
    }
    fs.unlinkSync(TMPDIR_FILE);
  }
}
