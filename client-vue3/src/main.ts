import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import router from './router';
import setupHttpInterceptor from './utils/httpInterceptor';
import './assets/styles/main.css';

// Setup HTTP interceptor for automatic JWT token injection
setupHttpInterceptor();

const app = createApp(App);

// State management
const pinia = createPinia();
app.use(pinia);

// Router
app.use(router);

app.mount('#app');

// Initialize WebSocket connection after app is mounted
// This matches the Vue 2 pattern where WebSocket is initialized at app level
// The connection will be established when the composable is first used in a component
console.log('Vue 3 DigiScript app initialized - WebSocket will connect on first use');
