import log from 'loglevel';
import { debounce } from 'lodash';
import { getActivePinia } from 'pinia';
import { toast } from '@/js/toast';
import { useWebSocketStore } from '@/stores/websocket';
import { useSystemStore } from '@/stores/system';
import { useUserStore } from '@/stores/user';
import { getWebSocketURL } from '@/js/platform';
import type { WsMessage } from '@/types/api/websocket';

const INITIAL_RECONNECT_DELAY_MS = 1000;
const MAX_RECONNECT_DELAY_MS = 30000;

let ws: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let errorCount = 0;

function getReconnectDelay(): number {
  return Math.min(INITIAL_RECONNECT_DELAY_MS * 2 ** errorCount, MAX_RECONNECT_DELAY_MS);
}

function sendObj(data: object): void {
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(data));
  } else {
    log.warn('Attempted to send WS message but socket is not open');
  }
}

const settingsChangedToast = debounce(() => toast.info('Settings synced from server'), 1000, {
  leading: true,
  trailing: false,
});

async function handleMessage(msg: WsMessage): Promise<void> {
  const wsStore = useWebSocketStore();
  const systemStore = useSystemStore();
  const userStore = useUserStore();
  const { default: router } = await import('@/router');

  switch (msg.OP) {
    case 'SET_UUID': {
      const newUUID = msg.DATA as unknown as string;
      if (wsStore.internalUUID != null) {
        log.debug('Reconnecting with existing UUID:', wsStore.internalUUID);
        sendObj({ OP: 'REFRESH_CLIENT', DATA: wsStore.internalUUID });
      } else {
        log.debug('New connection, received UUID:', newUUID);
        wsStore.$patch({ internalUUID: newUUID });
      }
      wsStore.$patch({ pendingAuthentication: true });
      // Authenticate immediately if we have a token
      const token = userStore.authToken;
      if (token) {
        sendObj({ OP: 'AUTHENTICATE', DATA: { token } });
      }
      break;
    }
    case 'WS_AUTH_SUCCESS':
      wsStore.$patch({ authenticated: true, authSucceeded: true, pendingAuthentication: false });
      errorCount = 0;
      log.info('WebSocket authenticated successfully');
      // Announce as new client if applicable
      sendObj({ OP: 'NEW_CLIENT', DATA: {} });
      break;
    case 'WS_AUTH_ERROR':
      wsStore.$patch({ authenticated: false, pendingAuthentication: false });
      log.error('WebSocket authentication error:', msg.DATA);
      break;
    case 'WS_TOKEN_REFRESH_SUCCESS':
      log.info('WebSocket token refreshed successfully');
      break;
    case 'SETTINGS_CHANGED':
      await systemStore.updateSettings(
        msg.DATA as Parameters<typeof systemStore.updateSettings>[0]
      );
      settingsChangedToast();
      break;
    case 'START_SHOW':
      if (router.currentRoute.value.path !== '/live') {
        router.push('/live');
      }
      break;
    case 'STOP_SHOW':
      if (router.currentRoute.value.path !== '/') {
        router.push('/');
      }
      break;
    case 'RELOAD_CLIENT':
      window.location.reload();
      break;
    default:
      log.warn(`Unknown OP received from WebSocket: ${msg.OP}`);
  }

  // Dispatch named Pinia action if ACTION key is present
  if (msg.ACTION) {
    await dispatchAction(msg.ACTION, msg.DATA);
  }
}

// Converts SCREAMING_SNAKE_CASE WS action names to camelCase Pinia action names.
// e.g. GET_CUE_TYPES → getCueTypes, ELECTED_LEADER → electedLeader
function screamingToCamel(s: string): string {
  return s.toLowerCase().replace(/_([a-z])/g, (_, c: string) => c.toUpperCase());
}

async function dispatchAction(action: string, data: Record<string, unknown>): Promise<void> {
  // Actions that can't be auto-routed by naming convention
  if (action === 'TOKEN_REFRESH') {
    const payload = data as { DATA: { access_token: string } };
    await useUserStore().tokenRefreshFromServer(payload.DATA.access_token);
    return;
  }
  if (action === 'SHOW_CHANGED') {
    const userStore = useUserStore();
    if (userStore.currentUser != null) {
      await userStore.getCurrentUser();
      await userStore.getCurrentRbac();
    }
    window.location.reload();
    return;
  }
  if (action === 'USER_LOGOUT') {
    await useUserStore().logout();
    return;
  }
  if (action === 'WS_SETTINGS_CHANGED') {
    await useSystemStore().settingsChanged();
    settingsChangedToast();
    return;
  }

  // Convention-based dispatch: searches all instantiated Pinia stores for a method whose
  // camelCase name matches the WS action. Adding a store action is sufficient to handle
  // the corresponding WS event — no registration required.
  const camelAction = screamingToCamel(action);
  const pinia = getActivePinia();
  if (pinia) {
    const storeMap = (pinia as unknown as { _s: Map<string, Record<string, unknown>> })._s;
    for (const store of storeMap.values()) {
      if (Object.hasOwn(store, camelAction) && typeof store[camelAction] === 'function') {
        await (store[camelAction] as (d: Record<string, unknown>) => Promise<void>)(data);
        return;
      }
    }
  }

  log.debug(`No handler for WS action: ${action}`);
}

function connect(): void {
  const wsStore = useWebSocketStore();

  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    return;
  }

  let wsURL: string;
  try {
    wsURL = getWebSocketURL();
  } catch (e) {
    log.error('Cannot determine WebSocket URL:', e);
    return;
  }

  log.debug('Connecting to WebSocket:', wsURL);
  ws = new WebSocket(wsURL);

  ws.onopen = async () => {
    const wasErrored = errorCount > 0;
    wsStore.$patch({ isConnected: true });
    if (wasErrored) {
      toast.success(
        `WebSocket reconnected after ${errorCount} attempt${errorCount > 1 ? 's' : ''}`
      );
    }
    log.info('WebSocket connected');
    if (wasErrored) {
      const { useShowStore } = await import('@/stores/show');
      const showStore = useShowStore();
      if (showStore.currentSession != null) {
        await showStore.getShowSessionData();
      }
    }
  };

  ws.onmessage = (event: MessageEvent) => {
    try {
      const msg: WsMessage = JSON.parse(event.data as string);
      handleMessage(msg).catch((err) => log.error('Error handling WS message:', err));
    } catch (e) {
      log.error('Failed to parse WS message:', e);
    }
  };

  ws.onclose = () => {
    wsStore.$patch({ isConnected: false, authenticated: false });
    log.info('WebSocket closed, scheduling reconnect');
    scheduleReconnect();
  };

  ws.onerror = () => {
    log.error('WebSocket error');
    errorCount++;
    if (errorCount === 1) {
      toast.error('WebSocket connection lost');
    }
  };
}

function scheduleReconnect(): void {
  if (reconnectTimer) return;
  const delay = getReconnectDelay();
  log.debug(`Reconnecting WebSocket in ${delay}ms`);
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    connect();
  }, delay);
}

export function useWebSocket() {
  const wsStore = useWebSocketStore();

  // Register the send function in the store so other stores can call it
  wsStore.registerSend(sendObj);

  return { sendObj, connect };
}
