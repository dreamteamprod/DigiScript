import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

export interface WebSocketMessage {
  OP?: string;
  ACTION?: string;
  DATA?: unknown;
  namespace?: string;
}

export interface WebSocketState {
  isConnected: boolean;
  message: WebSocketMessage | null;
  reconnectError: boolean;
  internalUUID: string | null;
  errorCount: number;
  error: boolean;
  authenticated: boolean;
  authenticationInProgress: boolean;
  pendingAuthentication: boolean;
  newConnection: boolean;
  authSucceeded: boolean;
}

export const useWebSocketStore = defineStore('websocket', () => {
  // State
  const isConnected = ref<boolean>(false);
  const message = ref<WebSocketMessage | null>(null);
  const reconnectError = ref<boolean>(false);
  const internalUUID = ref<string | null>(null);
  const errorCount = ref<number>(0);
  const error = ref<boolean>(false);
  const authenticated = ref<boolean>(false);
  const authenticationInProgress = ref<boolean>(false);
  const pendingAuthentication = ref<boolean>(false);
  const newConnection = ref<boolean>(false);
  const authSucceeded = ref<boolean>(false);

  // Getters
  const websocketHealthy = computed(() => !error.value
    && isConnected.value
    && !reconnectError.value
    && errorCount.value === 0);

  const websocketHasPendingOperations = computed(() => pendingAuthentication.value
    || newConnection.value
    || authSucceeded.value);

  // Actions
  function setConnected(connected: boolean) {
    isConnected.value = connected;
  }

  function setMessage(msg: WebSocketMessage | null) {
    message.value = msg;
  }

  function setReconnectError(hasError: boolean) {
    reconnectError.value = hasError;
  }

  function setInternalUUID(uuid: string | null) {
    internalUUID.value = uuid;
  }

  function setErrorCount(count: number) {
    errorCount.value = count;
  }

  function setError(hasError: boolean) {
    error.value = hasError;
  }

  function setAuthenticated(auth: boolean) {
    authenticated.value = auth;
  }

  function setAuthenticationInProgress(inProgress: boolean) {
    authenticationInProgress.value = inProgress;
  }

  function setPendingAuthentication(pending: boolean) {
    pendingAuthentication.value = pending;
  }

  function setNewConnection(isNew: boolean) {
    newConnection.value = isNew;
  }

  function setAuthSucceeded(succeeded: boolean) {
    authSucceeded.value = succeeded;
  }

  function clearWsAuthentication() {
    authenticated.value = false;
    authSucceeded.value = false;
    pendingAuthentication.value = true;
  }

  function clearPendingAuthentication() {
    pendingAuthentication.value = false;
  }

  function clearNewConnection() {
    newConnection.value = false;
  }

  function clearAuthSucceeded() {
    authSucceeded.value = false;
  }

  // WebSocket connection event handlers
  function handleSocketOpen() {
    isConnected.value = true;
    error.value = false;
    reconnectError.value = false;

    if (errorCount.value !== 0) {
      // TODO: Show success toast - will be implemented when we add toast functionality
      console.log(`WebSocket reconnected after ${errorCount.value} attempts`);
      errorCount.value = 0;

      // TODO: Handle page reload if not on home route - needs router integration
      // if (currentRoute !== '/') {
      //   window.location.reload();
      // }
    }
  }

  function handleSocketClose() {
    isConnected.value = false;
    authenticated.value = false;
  }

  function handleSocketError() {
    error.value = true;
  }

  function handleSocketReconnect(count: number) {
    if (errorCount.value === 0) {
      // TODO: Show error toast
      console.error('WebSocket connection lost');
    }
    errorCount.value = count;
    authenticated.value = false;
  }

  function handleSocketReconnectError() {
    reconnectError.value = true;
  }

  return {
    // State
    isConnected,
    message,
    reconnectError,
    internalUUID,
    errorCount,
    error,
    authenticated,
    authenticationInProgress,
    pendingAuthentication,
    newConnection,
    authSucceeded,

    // Getters
    websocketHealthy,
    websocketHasPendingOperations,

    // Actions
    setConnected,
    setMessage,
    setReconnectError,
    setInternalUUID,
    setErrorCount,
    setError,
    setAuthenticated,
    setAuthenticationInProgress,
    setPendingAuthentication,
    setNewConnection,
    setAuthSucceeded,
    clearWsAuthentication,
    clearPendingAuthentication,
    clearNewConnection,
    clearAuthSucceeded,
    handleSocketOpen,
    handleSocketClose,
    handleSocketError,
    handleSocketReconnect,
    handleSocketReconnectError,
  };
});
