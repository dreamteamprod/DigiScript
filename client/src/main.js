import Vue from 'vue';
import Vuex from 'vuex';
import VueNativeSock from 'vue-native-websocket';
import { BootstrapVue, IconsPlugin } from 'bootstrap-vue';

import store from '@/store/store';
import App from './App.vue';
import router from './router';

// Import Bootstrap and BootstrapVue CSS files (order is important)
import 'bootstrap/dist/css/bootstrap.css';
import 'bootstrap-vue/dist/bootstrap-vue.css';

// Make BootstrapVue available throughout your project
Vue.use(BootstrapVue);
// Optionally install the BootstrapVue icon components plugin
Vue.use(IconsPlugin);

Vue.use(Vuex);

Vue.use(VueNativeSock, `ws://${window.location.hostname}:${window.location.port}/api/v1/ws`, {
  reconnection: true,
  reconnectionAttempts: 5,
  reconnectionDelay: 3000,
  format: 'json',
  store,
});

Vue.config.productionTip = false;

new Vue({
  router,
  store,
  render: (h) => h(App),
}).$mount('#app');
