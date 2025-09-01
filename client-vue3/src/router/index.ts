import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '../stores/auth';
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
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { requiresGuest: true },
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('../views/UserSettingsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/system-admin',
      name: 'system-admin',
      component: () => import('../views/admin/SystemAdminView.vue'),
      meta: { requiresAuth: true, requiresAdmin: true },
    },
    {
      path: '/user-management',
      name: 'user-management',
      component: () => import('../views/admin/UserManagementView.vue'),
      meta: { requiresAuth: true, requiresAdmin: true },
    },
  ],
});

// Navigation guards
router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore();

  // If no current user and we have a token, try to get current user
  if (!authStore.currentUser && authStore.authToken) {
    try {
      await authStore.getCurrentUser();
    } catch (error) {
      console.error('Error getting current user:', error);
      // Clear invalid token
      authStore.clearAuthData();
    }
  }

  const isAuthenticated = authStore.isAuthenticated && authStore.currentUser;

  // Check if route requires authentication
  if (to.meta.requiresAuth && !isAuthenticated) {
    next({ name: 'login' });
    return;
  }

  // Check if route requires guest (not authenticated)
  if (to.meta.requiresGuest && isAuthenticated) {
    next({ name: 'home' });
    return;
  }

  // Check if route requires admin access
  if (to.meta.requiresAdmin && !authStore.isAdmin) {
    next({ name: 'home' });
    return;
  }

  next();
});

export default router;
