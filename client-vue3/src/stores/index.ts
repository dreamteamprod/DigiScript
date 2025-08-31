import { createPinia } from 'pinia';

// Import stores
export { useWebSocketStore } from './websocket';
export { useAuthStore } from './auth';

// Export store types for future use
export type RootState = {
  // WebSocket and Auth stores are now implemented
  // Future stores will be added in subsequent phases:
  // show state, script state, etc.
}

// Create and export the Pinia store instance
const pinia = createPinia();

export { pinia };
export default pinia;
