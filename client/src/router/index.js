import Vue from 'vue';
import VueRouter from 'vue-router';
import HomeView from '../views/HomeView.vue';

Vue.use(VueRouter);

const routes = [
  {
    path: '/',
    name: 'home',
    component: HomeView,
  },
  {
    path: '/about',
    name: 'about',
    component: () => import('../views/AboutView.vue'),
  },
  {
    path: '/config',
    name: 'config',
    component: () => import('../views/ConfigView.vue'),
  },
  {
    path: '/show-config',
    component: () => import(/* webpackChunkName: "show-config" */ '../views/show/ShowConfigView.vue'),
    children: [
      {
        name: 'show-config',
        path: '',
        component: () => import(/* webpackChunkName: "show-config" */ '../views/show/config/ConfigShow.vue'),
      },
      {
        name: 'show-config-cast',
        path: 'cast',
        component: () => import(/* webpackChunkName: "show-config" */ '../views/show/config/ConfigCast.vue'),
      },
      {
        name: 'show-config-characters',
        path: 'characters',
        component: () => import(/* webpackChunkName: "show-config" */ '../views/show/config/ConfigCharacters.vue'),
      },
      {
        name: 'show-config-character-groups',
        path: 'character-groups',
        component: () => import(/* webpackChunkName: "show-config" */ '../views/show/config/ConfigCharacterGroups.vue'),
      },
      {
        name: 'show-config-acts',
        path: 'acts',
        component: () => import(/* webpackChunkName: "show-config" */ '../views/show/config/ConfigActs.vue'),
      },
      {
        name: 'show-config-scenes',
        path: 'scenes',
        component: () => import(/* webpackChunkName: "show-config" */ '../views/show/config/ConfigScenes.vue'),
      },
      {
        name: 'show-config-cues',
        path: 'cues',
        component: () => import(/* webpackChunkName: "show-config" */ '../views/show/config/ConfigCues.vue'),
      },
      {
        name: 'show-config-script',
        path: 'script',
        component: () => import(/* webpackChunkName: "show-config" */ '../views/show/config/ConfigScript.vue'),
      },
    ],
  },
  {
    path: '*',
    name: '404',
    component: () => import('../views/404View.vue'),
  },
];

const router = new VueRouter({
  mode: 'history',
  base: process.env.BASE_URL,
  routes,
});

export default router;
