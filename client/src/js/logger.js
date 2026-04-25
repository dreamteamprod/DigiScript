import log from 'loglevel';
import { makeURL } from '@/js/utils';
import store from '@/store/store';

let isInitialized = false;

const FLUSH_INTERVAL_MS = 1000;
const MAX_QUEUE_SIZE = 50;

let logQueue = [];
let flushTimer = null;

/**
 * Buffer a log entry and schedule a debounced flush.
 * Flushes immediately if the queue reaches MAX_QUEUE_SIZE.
 */
function enqueueLog(level, message, extra) {
  logQueue.push({ level, message, extra });
  if (logQueue.length >= MAX_QUEUE_SIZE) {
    flushQueue();
    return;
  }
  clearTimeout(flushTimer);
  flushTimer = setTimeout(flushQueue, FLUSH_INTERVAL_MS);
}

/**
 * Send all queued log entries to the server as a single batch request.
 * Uses fetch directly to avoid potential infinite loops with HTTP interceptors.
 */
function flushQueue() {
  clearTimeout(flushTimer);
  flushTimer = null;
  if (logQueue.length === 0) return;

  const batch = logQueue.splice(0);

  const token = store.getters.AUTH_TOKEN;
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  fetch(makeURL('/api/v1/logs/batch'), {
    method: 'POST',
    headers,
    body: JSON.stringify({ batch: batch }),
  }).catch(() => {
    // Intentionally ignore errors to prevent log flooding or infinite loops
  });
}

/**
 * Initialize remote logging.
 * This hooks into the loglevel library to send logs to the server.
 */
export function initRemoteLogging() {
  if (isInitialized) return;
  isInitialized = true;

  const originalFactory = log.methodFactory;

  const levels = { TRACE: 0, DEBUG: 1, INFO: 2, WARN: 3, ERROR: 4, SILENT: 5 };

  log.methodFactory = function (methodName, logLevel, loggerName) {
    const rawMethod = originalFactory(methodName, logLevel, loggerName);

    return function (message, ...args) {
      // Always call the standard log method first
      rawMethod(message, ...args);

      const settings = store.getters.SETTINGS;
      if (!settings || !settings.client_log_enabled) return;

      const currentLevelName = methodName.toUpperCase();
      const currentLevel = levels[currentLevelName] ?? 2;
      const minLevel = levels[(settings.client_log_level || 'INFO').toUpperCase()] ?? 2;
      if (currentLevel < minLevel) return;

      let finalMessage = message;
      if (typeof message !== 'string') {
        try {
          finalMessage = JSON.stringify(message);
        } catch {
          finalMessage = String(message);
        }
      }

      const extra = {};
      if (args.length > 0) {
        extra.args = args.map((arg) =>
          arg instanceof Error ? { message: arg.message, stack: arg.stack, name: arg.name } : arg
        );
      }

      enqueueLog(currentLevelName, finalMessage, extra);
    };
  };

  // Re-apply the level to trigger the factory update
  log.setLevel(log.getLevel());

  // Keep browser console level in sync with the user's per-account preference.
  // The false arg prevents loglevel from persisting this to localStorage.
  store.watch(
    (state, getters) => getters.USER_SETTINGS?.console_log_level,
    (newLevel) => {
      if (newLevel) log.setLevel(newLevel.toLowerCase(), false);
    },
    { immediate: true }
  );

  // Intercept global errors — enqueue directly instead of routing through
  // log.error() so the factory is never re-entered from here.
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
