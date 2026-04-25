import Vue from 'vue';
import Vuex from 'vuex';
import VueNativeSock from 'vue-native-websocket';
import { BootstrapVue, IconsPlugin } from 'bootstrap-vue';
import Vuelidate from 'vuelidate';
import ToastPlugin from 'vue-toast-notification';
import Multiselect from 'vue-multiselect';
import { Splitpanes, Pane } from 'splitpanes';

import store from '@/store/store';
import App from './App.vue';
import router from './router';
import setupHttpInterceptor from './js/http-interceptor';
import { getWebSocketURL, isElectron } from '@/js/platform';
import { initRemoteLogging } from '@/js/logger';
import log from 'loglevel';

import './assets/styles/dark.scss';
import 'vue-toast-notification/dist/theme-sugar.css';
import 'vue-multiselect/dist/vue-multiselect.min.css';
import 'splitpanes/dist/splitpanes.css';

setupHttpInterceptor();
initRemoteLogging();

log.info(`Running in ${import.meta.env.MODE} mode.`);

Vue.use(BootstrapVue);
Vue.use(IconsPlugin);
Vue.component('MultiSelect', Multiselect);
Vue.component('SplitPanes', Splitpanes);
Vue.component('SplitPane', Pane);

Vue.use(Vuex);
Vue.use(Vuelidate);
Vue.use(ToastPlugin, {
  position: 'top-right',
});

/**
 * Check if we should initialize WebSocket
 * In Electron, only initialize if there's an active connection
 */
async function shouldInitializeWebSocket() {
  if (!isElectron()) {
    // Browser mode: always initialize
    return true;
  }

  // Electron mode: check if there's an active connection
  try {
    const activeConnection = await window.electronAPI.getActiveConnection();
    return activeConnection !== null;
  } catch (error) {
    console.warn('Could not check active connection, skipping WebSocket initialization:', error);
    return false;
  }
}

/**
 * Initialize WebSocket connection
 * Only called if we have a server to connect to
 */
function initializeWebSocket() {
  try {
    const wsUrl = getWebSocketURL();
    Vue.use(VueNativeSock, wsUrl, {
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
                this.store.dispatch(
                  [msg.namespace || '', msg.ACTION].filter((e) => !!e).join('/'),
                  msg
                );
              }
            }
            return;
          }
        }
        next(eventName, event);
      },
    });
  } catch (error) {
    console.error('Failed to initialize WebSocket:', error);
  }
}

// Initialize WebSocket conditionally
shouldInitializeWebSocket().then((shouldInit) => {
  if (shouldInit) {
    initializeWebSocket();
  } else {
    console.log('Skipping WebSocket initialization - no server connection configured');
  }
});

Vue.config.productionTip = false;
Vue.config.devtools = import.meta.env.MODE === 'development';

Vue.filter('capitalize', (value) => {
  if (!value) return '';
  return value
    .toString()
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
});
Vue.filter('uppercase', (value) => {
  if (!value) return '';
  return value.toString().toUpperCase();
});
Vue.filter('lowercase', (value) => {
  if (!value) return '';
  return value.toString().toLowerCase();
});

new Vue({
  router,
  store,
  render: (h) => h(App),
}).$mount('#app');
