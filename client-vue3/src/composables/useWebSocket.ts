import {
  ref, onMounted, onUnmounted, watch,
} from 'vue';
import { useWebSocketStore, type WebSocketMessage } from '../stores/websocket';
import { useAuthStore } from '../stores/auth';

export interface WebSocketOptions {
  reconnection?: boolean;
  reconnectionAttempts?: number;
  reconnectionDelay?: number;
  maxReconnectionDelay?: number;
  reconnectionDelayGrowFactor?: number;
}

export function useWebSocket(url?: string, options: WebSocketOptions = {}) {
  const websocketStore = useWebSocketStore();
  const authStore = useAuthStore();

  const socket = ref<WebSocket | null>(null);
  const reconnectAttempts = ref(0);
  const reconnectTimer = ref<number | null>(null);
  const isReconnecting = ref(false);

  const defaultOptions: WebSocketOptions = {
    reconnection: true,
    reconnectionAttempts: 5,
    reconnectionDelay: 1000,
    maxReconnectionDelay: 5000,
    reconnectionDelayGrowFactor: 1.3,
  };

  const config = { ...defaultOptions, ...options };

  // Create WebSocket URL - matches Vue 2 pattern exactly
  const getWebSocketUrl = (): string => {
    if (url) return url;

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const { hostname } = window.location;
    const { port } = window.location;
    return `${protocol}://${hostname}:${port}/api/v1/ws`;
  };

  // Send message to WebSocket
  const sendMessage = (message: WebSocketMessage) => {
    if (socket.value && socket.value.readyState === WebSocket.OPEN) {
      socket.value.send(JSON.stringify(message));
    } else {
      console.error('WebSocket is not connected');
    }
  };

  // Send object message (matches Vue 2 sendObj method)
  const sendObj = (obj: WebSocketMessage) => {
    sendMessage(obj);
  };

  // Handle specific OP codes - matches Vue 2 websocket.js switch statement
  const handleSpecificOpCodes = (message: WebSocketMessage) => {
    switch (message.OP) {
      case 'SET_UUID':
        if (websocketStore.internalUUID != null) {
          console.log('Reconnecting to WebSocket with existing UUID:', websocketStore.internalUUID);
          sendObj({
            OP: 'REFRESH_CLIENT',
            DATA: websocketStore.internalUUID,
          });
        } else {
          console.log('Connecting to WebSocket as new client, with UUID:', message.DATA);
          websocketStore.setInternalUUID(message.DATA as string);
          websocketStore.setNewConnection(true);
        }
        if (!websocketStore.authenticated && !websocketStore.authenticationInProgress) {
          websocketStore.setPendingAuthentication(true);
        }
        break;

      case 'WS_AUTH_SUCCESS':
        websocketStore.setAuthenticated(true);
        websocketStore.setAuthenticationInProgress(false);
        websocketStore.setPendingAuthentication(false);
        websocketStore.setAuthSucceeded(true);
        console.log('WebSocket authenticated successfully');
        break;

      case 'WS_AUTH_ERROR':
        websocketStore.setAuthenticated(false);
        websocketStore.setAuthenticationInProgress(false);
        websocketStore.setPendingAuthentication(false);
        console.error(`WebSocket authentication error: ${message.DATA}`);
        break;

      case 'WS_TOKEN_REFRESH_SUCCESS':
        console.log('WebSocket token refreshed successfully');
        break;

      case 'START_SHOW':
        // TODO: Navigate to /live when router is integrated
        console.log('Show started - should navigate to /live');
        break;

      case 'STOP_SHOW':
        // TODO: Navigate to / when router is integrated
        console.log('Show stopped - should navigate to /');
        break;

      case 'RELOAD_CLIENT':
        window.location.reload();
        break;

      case 'NOOP':
        // Do nothing for NOOP operations
        break;

      default:
        console.error(`Unknown OP received from WebSocket: ${message.OP}`);
    }
  };

  // Handle incoming WebSocket messages - CRITICAL: matches Vue 2 logic exactly
  const handleMessage = (event: MessageEvent) => {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);

      // Store the message in the WebSocket store
      websocketStore.setMessage(message);

      // Handle messages with OP key - this is the core logic from Vue 2
      if (message.OP) {
        // Handle specific OP codes that have special behavior
        handleSpecificOpCodes(message);

        // If the message contains an ACTION key, dispatch it
        if (message.ACTION && message.ACTION !== 'NOOP') {
          // TODO: Implement action dispatching to appropriate stores
          // This will need to be implemented when we have all stores migrated
          console.log('Action to dispatch:', message.ACTION, message);

          // For now, handle some critical actions manually
          if (message.ACTION === 'WS_SETTINGS_CHANGED') {
            // TODO: Update settings - will be implemented when settings store is ready
            console.log('Settings changed:', message.DATA);
          }
        }
      }
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
    }
  };

  // Reconnection logic - declare first
  const attemptReconnect = () => {
    if (reconnectAttempts.value >= (config.reconnectionAttempts || 5)) {
      websocketStore.handleSocketReconnectError();
      return;
    }

    isReconnecting.value = true;
    reconnectAttempts.value += 1;

    websocketStore.handleSocketReconnect(reconnectAttempts.value);

    const delay = Math.min(
      (config.reconnectionDelay || 1000)
      * (config.reconnectionDelayGrowFactor || 1.3) ** (reconnectAttempts.value - 1),
      config.maxReconnectionDelay || 5000,
    );

    reconnectTimer.value = window.setTimeout(() => {
      // eslint-disable-next-line @typescript-eslint/no-use-before-define
      connect();
    }, delay);
  };

  // WebSocket connection handlers
  const handleOpen = () => {
    console.log('WebSocket connected');
    websocketStore.handleSocketOpen();
    reconnectAttempts.value = 0;
    isReconnecting.value = false;

    // Add socket reference for sendObj compatibility
    if (socket.value) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (socket.value as any).sendObj = sendObj;
    }
  };

  const handleClose = () => {
    console.log('WebSocket disconnected');
    websocketStore.handleSocketClose();

    if (config.reconnection && !isReconnecting.value) {
      attemptReconnect();
    }
  };

  const handleError = (event: Event) => {
    console.error('WebSocket error:', event);
    websocketStore.handleSocketError();
  };

  // Declare connect function
  const connect = () => {
    try {
      socket.value = new WebSocket(getWebSocketUrl());

      socket.value.addEventListener('open', handleOpen);
      socket.value.addEventListener('close', handleClose);
      socket.value.addEventListener('error', handleError);
      socket.value.addEventListener('message', handleMessage);

      // Add sendObj method for compatibility
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (socket.value as any).sendObj = sendObj;
    } catch (error) {
      console.error('Error creating WebSocket connection:', error);
    }
  };

  // Disconnect from WebSocket
  const disconnect = () => {
    if (reconnectTimer.value) {
      window.clearTimeout(reconnectTimer.value);
      reconnectTimer.value = null;
    }

    if (socket.value) {
      socket.value.removeEventListener('open', handleOpen);
      socket.value.removeEventListener('close', handleClose);
      socket.value.removeEventListener('error', handleError);
      socket.value.removeEventListener('message', handleMessage);
      socket.value.close();
      socket.value = null;
    }

    websocketStore.setConnected(false);
    isReconnecting.value = false;
    reconnectAttempts.value = 0;
  };

  // Handle WebSocket authentication success
  const handleWsAuthSuccess = async () => {
    // After successful authentication, register as a new client if this is a new connection
    if (websocketStore.newConnection) {
      if (socket.value && socket.value.readyState === WebSocket.OPEN) {
        sendObj({
          OP: 'NEW_CLIENT',
          DATA: {},
        });
        websocketStore.clearNewConnection();
      }
    }
  };

  // WebSocket authentication
  const authenticateWebSocket = async () => {
    if (!authStore.authToken || !socket.value || socket.value.readyState !== WebSocket.OPEN) {
      return;
    }

    websocketStore.setAuthenticationInProgress(true);
    websocketStore.clearPendingAuthentication();

    sendObj({
      OP: 'AUTHENTICATE',
      DATA: {
        token: authStore.authToken,
      },
    });

    console.log('Sent WebSocket authentication request');
  };

  // Check WebSocket state and handle pending operations
  const checkWebSocketState = async () => {
    if (websocketStore.pendingAuthentication && authStore.authToken) {
      await authenticateWebSocket();
    }

    if (websocketStore.authSucceeded) {
      await handleWsAuthSuccess();
      websocketStore.clearAuthSucceeded();
    }

    if (websocketStore.newConnection
        && !websocketStore.pendingAuthentication
        && !websocketStore.authenticationInProgress
        && !websocketStore.authSucceeded) {
      if (socket.value && socket.value.readyState === WebSocket.OPEN) {
        sendObj({
          OP: 'NEW_CLIENT',
          DATA: {},
        });
        websocketStore.clearNewConnection();
      }
    }
  };

  const refreshWebSocketToken = async () => {
    if (!authStore.authToken || !socket.value || socket.value.readyState !== WebSocket.OPEN) {
      return;
    }

    sendObj({
      OP: 'REFRESH_TOKEN',
      DATA: {
        token: authStore.authToken,
      },
    });

    console.log('Sent WebSocket token refresh');
  };

  // Watch for auth token changes to trigger WebSocket authentication
  watch(() => authStore.authToken, (newToken) => {
    if (newToken && websocketStore.isConnected && !websocketStore.authenticated) {
      authenticateWebSocket();
    }
  });

  // Periodic check for WebSocket state
  let stateCheckInterval: number | null = null;

  onMounted(() => {
    connect();

    // Set up periodic state checking (matches Vue 2 behavior)
    stateCheckInterval = window.setInterval(checkWebSocketState, 1000);
  });

  onUnmounted(() => {
    if (stateCheckInterval) {
      window.clearInterval(stateCheckInterval);
    }
    disconnect();
  });

  return {
    socket,
    isConnected: websocketStore.isConnected,
    isAuthenticated: websocketStore.authenticated,
    sendMessage,
    sendObj,
    connect,
    disconnect,
    authenticateWebSocket,
    refreshWebSocketToken,
  };
}
