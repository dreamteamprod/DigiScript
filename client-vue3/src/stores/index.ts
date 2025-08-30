import { createPinia } from 'pinia';

// Create and export the Pinia store instance
const pinia = createPinia();

// Export store types for future use
export type RootState = {
  // Future store state types will be added here during Phase 2
  // This will include user state, websocket state, show state, etc.
}

// Future stores will be imported and exported here in Phase 2:
// export { useUserStore } from './user'
// export { useWebSocketStore } from './websocket'
// export { useShowStore } from './show'
// export { useScriptStore } from './script'

export { pinia };
export default pinia;
