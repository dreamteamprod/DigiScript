import Vue from 'vue';
import Vuex from 'vuex';
import VueNativeSock from 'vue-native-websocket';
import { BootstrapVue, IconsPlugin } from 'bootstrap-vue';
import Vuelidate from 'vuelidate';
import ToastPlugin from 'vue-toast-notification';
import Multiselect from 'vue-multiselect';

import store from '@/store/store';
import App from './App.vue';
import router from './router';

import './assets/styles/dark.scss';
import 'vue-toast-notification/dist/theme-sugar.css';
import 'vue-multiselect/dist/vue-multiselect.min.css';

Vue.use(BootstrapVue);
Vue.use(IconsPlugin);
Vue.component('MultiSelect', Multiselect);

Vue.use(Vuex);
Vue.use(Vuelidate);
Vue.use(ToastPlugin, {
  position: 'top-right',
});

Vue.use(VueNativeSock, `ws://${window.location.hostname}:${window.location.port}/api/v1/ws`, {
  reconnection: true,
  format: 'json',
  store,
  passToStoreHandler(eventName, event, next) {
    // Ignore anything that doesn't start with SOCKET_ as per
    // https://www.npmjs.com/package/vue-native-websocket
    if (!eventName.startsWith('SOCKET_')) {
      return;
    }
    // Custom message handling here
    if (this.format === 'json' && event.data) {
      const msg = JSON.parse(event.data);
      // If the message contains an OP key, then this is going to be something we care about
      if (msg.OP) {
        // Always call the commit function here, as we care about it
        if (msg.OP !== 'NOOP') {
          this.store.commit(eventName.toUpperCase(), msg);
        }
        if (msg.ACTION) {
          // If we have an action, then call the corresponding action too, this means a single
          // WS message can do two things (commit a mutation, AND perform an action)
          if (msg.ACTION !== 'NOOP') {
            this.store.dispatch([msg.namespace || '', msg.ACTION].filter((e) => !!e).join('/'), msg);
          }
        }
        return;
      }
    }
    next(eventName, event);
  },
});

Vue.config.productionTip = false;
Vue.config.devtools = import.meta.env.MODE === 'development';

Vue.filter('capitalize', (value) => {
  if (!value) return '';
  return value.toString().split(' ').map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
});

new Vue({
  router,
  store,
  render: (h) => h(App),
}).$mount('#app');
