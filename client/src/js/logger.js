import log from 'loglevel';
import { makeURL } from '@/js/utils';
import store from '@/store/store';

let isInitialized = false;

/**
 * Initialize remote logging.
 * This hooks into the loglevel library to send logs to the server.
 */
export function initRemoteLogging() {
  if (isInitialized) return;
  isInitialized = true;

  const originalFactory = log.methodFactory;

  log.methodFactory = function (methodName, logLevel, loggerName) {
    const rawMethod = originalFactory(methodName, logLevel, loggerName);

    return function (message, ...args) {
      // Always call the standard log method first
      rawMethod(message, ...args);

      // Get settings from store
      const settings = store.getters.SETTINGS;
      if (!settings || !settings.client_log_enabled) {
        return;
      }

      // Avoid recursion and check for specific prefixes we might want to ignore
      if (typeof message === 'string' && message.startsWith('[RemoteLog]')) {
        return;
      }

      // Check if the current message level meets the minimum required level from settings
      const minLevelStr = settings.client_log_level || 'INFO';
      const levels = {
        TRACE: 0,
        DEBUG: 1,
        INFO: 2,
        WARN: 3,
        ERROR: 4,
        SILENT: 5,
      };

      const currentLevelName = methodName.toUpperCase();
      const currentLevel = levels[currentLevelName] !== undefined ? levels[currentLevelName] : 2;
      const minLevel =
        levels[minLevelStr.toUpperCase()] !== undefined ? levels[minLevelStr.toUpperCase()] : 2;

      if (currentLevel < minLevel) {
        return;
      }

      // Prepare payload
      let finalMessage = message;
      let extra = {};

      if (typeof message !== 'string') {
        try {
          finalMessage = JSON.stringify(message);
        } catch (e) {
          finalMessage = String(message);
        }
      }

      if (args.length > 0) {
        extra.args = args.map((arg) => {
          if (arg instanceof Error) {
            return {
              message: arg.message,
              stack: arg.stack,
              name: arg.name,
            };
          }
          return arg;
        });
      }

      // Send to server
      sendRemoteLog(currentLevelName, finalMessage, extra);
    };
  };

  // Re-apply the level to trigger the factory update
  log.setLevel(log.getLevel());

  // Intercept global errors
  window.addEventListener('error', (event) => {
    log.error(`[RemoteLog] Unhandled Error: ${event.message}`, {
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
      stack: event.error ? event.error.stack : null,
    });
  });

  window.addEventListener('unhandledrejection', (event) => {
    log.error(`[RemoteLog] Unhandled Promise Rejection: ${event.reason}`);
  });

  log.info('[RemoteLog] Remote logging initialized');
}

/**
 * Send a log message to the server.
 * Uses fetch directly to avoid potential infinite loops with HTTP interceptors.
 */
async function sendRemoteLog(level, message, extra) {
  try {
    const token = store.getters.AUTH_TOKEN;
    const headers = {
      'Content-Type': 'application/json',
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const payload = {
      level,
      message,
      extra,
    };

    const url = makeURL('/api/v1/logs');

    // Fire and forget
    fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
    }).catch(() => {
      // Intentionally ignore errors to prevent log flooding or infinite loops
    });
  } catch (err) {
    // Intentionally ignore
  }
}
