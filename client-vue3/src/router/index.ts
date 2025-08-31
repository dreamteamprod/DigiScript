import { createRouter, createWebHistory } from 'vue-router';
import HomeView from '../views/HomeView.vue';

const router = createRouter({
  history: createWebHistory('/v3/'),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/about',
      name: 'about',
      // Lazy-loaded route
      component: () => import('../views/AboutView.vue'),
    },
    {
      path: '/websocket-test',
      name: 'websocket-test',
      component: () => import('../views/WebSocketTest.vue'),
    },
  ],
});

export default router;
