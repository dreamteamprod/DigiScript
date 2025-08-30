import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import router from './router';
import './assets/styles/main.css';

const app = createApp(App);

// State management
app.use(createPinia());

// Router
app.use(router);

app.mount('#app');
