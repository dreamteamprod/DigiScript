import Vue from 'vue';
import Vuex from 'vuex';
import VueNativeSock from 'vue-native-websocket';
import { BootstrapVue, IconsPlugin } from 'bootstrap-vue';
import Vuelidate from 'vuelidate';
import ToastPlugin from 'vue-toast-notification';

import store from '@/store/store';
import App from './App.vue';
import router from './router';

import 'bootstrap/dist/css/bootstrap.css';
import 'bootstrap-vue/dist/bootstrap-vue.css';
import 'vue-toast-notification/dist/theme-sugar.css';

Vue.use(BootstrapVue);
Vue.use(IconsPlugin);

Vue.use(Vuex);
Vue.use(Vuelidate);
Vue.use(ToastPlugin, {
  position: 'top-right',
});

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
