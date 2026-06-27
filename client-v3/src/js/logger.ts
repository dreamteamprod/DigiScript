import log from 'loglevel';
import { makeURL } from '@/js/utils';
import { useUserStore } from '@/stores/user';
import { useSystemStore } from '@/stores/system';

let isInitialized = false;

const FLUSH_INTERVAL_MS = 1000;
const MAX_QUEUE_SIZE = 50;

interface LogEntry {
  level: string;
  message: string;
  extra: Record<string, unknown>;
}

const logQueue: LogEntry[] = [];
let flushTimer: ReturnType<typeof setTimeout> | null = null;

function enqueueLog(level: string, message: string, extra: Record<string, unknown>): void {
  logQueue.push({ level, message, extra });
  if (logQueue.length >= MAX_QUEUE_SIZE) {
    flushQueue();
    return;
  }
  clearTimeout(flushTimer ?? undefined);
  flushTimer = setTimeout(flushQueue, FLUSH_INTERVAL_MS);
}

// Uses fetch directly (not the intercepted version) to avoid infinite logging loops.
function flushQueue() {
  clearTimeout(flushTimer ?? undefined);
  flushTimer = null;
  if (logQueue.length === 0) return;

  const batch = logQueue.splice(0);

  const token = useUserStore().authToken;
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  fetch(makeURL('/api/v1/logs/batch'), {
    method: 'POST',
    headers,
    body: JSON.stringify({ batch: batch }),
  }).catch(() => {
    // Intentionally ignore errors to prevent log flooding or infinite loops
  });
}

export function initRemoteLogging(): void {
  if (isInitialized) return;
  isInitialized = true;

  const originalFactory = log.methodFactory;

  const levels: Record<string, number> = {
    TRACE: 0,
    DEBUG: 1,
    INFO: 2,
    WARN: 3,
    ERROR: 4,
    SILENT: 5,
  };

  log.methodFactory = function (methodName, logLevel, loggerName) {
    const rawMethod = originalFactory(methodName, logLevel, loggerName);

    return function (message, ...args) {
      rawMethod(message, ...args);

      const systemStore = useSystemStore();
      const settings = systemStore.settings;
      if (!settings?.client_log_enabled) return;

      const currentLevelName = methodName.toUpperCase();
      const currentLevel = levels[currentLevelName] ?? 2;
      const minLevel = levels[((settings.client_log_level as string) || 'INFO').toUpperCase()] ?? 2;
      if (currentLevel < minLevel) return;

      let finalMessage = message;
      if (typeof message !== 'string') {
        try {
          finalMessage = JSON.stringify(message);
        } catch {
          finalMessage = String(message);
        }
      }

      const extra: Record<string, unknown> = {};
      if (args.length > 0) {
        extra.args = args.map((arg) =>
          arg instanceof Error ? { message: arg.message, stack: arg.stack, name: arg.name } : arg
        );
      }

      enqueueLog(currentLevelName, finalMessage, extra);
    };
  };

  log.setLevel(log.getLevel());

  // Sync browser console level with user's per-account preference.
  // Watched via a simple interval rather than a reactive watcher (Pinia watch requires
  // component context or explicit setup; this avoids that complexity).
  setInterval(() => {
    const userStore = useUserStore();
    const consoleLevel = (userStore.userSettings as Record<string, unknown>)?.console_log_level as
      string | undefined;
    if (consoleLevel) log.setLevel(consoleLevel.toLowerCase() as log.LogLevelDesc, false);
  }, 5000);

  window.addEventListener('error', (event) => {
    enqueueLog('ERROR', `Unhandled Error: ${event.message}`, {
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
      stack: event.error ? event.error.stack : null,
    });
  });

  window.addEventListener('unhandledrejection', (event) => {
    enqueueLog('ERROR', `Unhandled Promise Rejection: ${event.reason}`, {});
  });

  enqueueLog('INFO', 'Remote logging initialized', {});
}
