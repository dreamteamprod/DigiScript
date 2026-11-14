import { createApp } from 'vue';
import { createPinia } from 'pinia';
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate';
import App from './App.vue';
import router from './router';
import setupHttpInterceptor from './js/http-interceptor';
import { initRemoteLogging } from './js/logger';
import './assets/styles/dark.scss';
import 'bootstrap-vue-next/dist/bootstrap-vue-next.css';
import 'vue-toast-notification/dist/theme-sugar.css';

const app = createApp(App);

const pinia = createPinia();
pinia.use(piniaPluginPersistedstate);

app.use(pinia);
app.use(router);

setupHttpInterceptor();
initRemoteLogging();

app.mount('#app');
