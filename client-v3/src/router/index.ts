import { createRouter, createWebHistory } from 'vue-router';
import { isElectron } from '@/js/platform';
import HomeView from '@/views/HomeView.vue';
import NotFoundView from '@/views/NotFoundView.vue';
import PlaceholderView from '@/views/PlaceholderView.vue';

const router = createRouter({
  history: createWebHistory('/ui-new/'),
  routes: [
    {
      path: '/electron/server-selector',
      name: 'electron-server-selector',
      component: () => import('@/views/electron/ServerSelector.vue'),
      meta: { requiresAuth: false, isElectronOnly: true },
    },
    {
      path: '/',
      name: 'home',
      component: HomeView,
      meta: { requiresAuth: false },
    },
    {
      path: '/about',
      name: 'about',
      component: () => import('@/views/AboutView.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/user/LoginView.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/config',
      name: 'config',
      component: () => import('@/views/config/ConfigView.vue'),
      meta: { requiresAuth: true, requiresAdmin: true },
    },
    {
      path: '/show-config',
      component: () => import('@/views/show/ShowConfigView.vue'),
      meta: { requiresAuth: true, requiresShowAccess: true },
      children: [
        {
          name: 'show-config',
          path: '',
          component: () => import('@/views/show/config/ConfigShow.vue'),
          meta: { requiresAuth: true, requiresShowAccess: true },
        },
        {
          name: 'show-config-cast',
          path: 'cast',
          component: () => import('@/views/show/config/ConfigCast.vue'),
          meta: { requiresAuth: true, requiresShowAccess: true },
        },
        {
          name: 'show-config-stage',
          path: 'stage',
          component: PlaceholderView,
          meta: { requiresAuth: true, requiresShowAccess: true },
        },
        {
          name: 'show-config-characters',
          path: 'characters',
          component: () => import('@/views/show/config/ConfigCharacters.vue'),
          meta: { requiresAuth: true, requiresShowAccess: true },
        },
        {
          name: 'show-config-acts-scenes',
          path: 'acts',
          component: () => import('@/views/show/config/ConfigActsAndScenes.vue'),
          meta: { requiresAuth: true, requiresShowAccess: true },
        },
        {
          name: 'show-config-cues',
          path: 'cues',
          component: () => import('@/views/show/config/ConfigCues.vue'),
          meta: { requiresAuth: true, requiresShowAccess: true },
        },
        {
          name: 'show-config-mics',
          path: 'mics',
          component: () => import('@/views/show/config/ConfigMics.vue'),
          meta: { requiresAuth: true, requiresShowAccess: true },
        },
        {
          name: 'show-config-script',
          path: 'script',
          component: PlaceholderView,
          meta: { requiresAuth: true, requiresShowAccess: true },
        },
        {
          name: 'show-config-script-revisions',
          path: 'script-revisions',
          component: PlaceholderView,
          meta: { requiresAuth: true, requiresShowAccess: true },
        },
        {
          name: 'show-sessions',
          path: 'sessions',
          component: () => import('@/views/show/config/ConfigSessions.vue'),
          meta: { requiresAuth: true, requiresShowAccess: true },
        },
      ],
    },
    {
      path: '/live',
      name: 'live',
      component: PlaceholderView,
      meta: { requiresAuth: false },
    },
    {
      path: '/me',
      name: 'user-settings',
      component: () => import('@/views/user/SettingsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/force-password-change',
      name: 'force-password-change',
      component: () => import('@/views/user/ForcePasswordChangeView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/help',
      component: () => import('@/views/HelpView.vue'),
      meta: { requiresAuth: false },
      children: [
        { path: '', redirect: '/help/getting-started' },
        {
          name: 'help-doc',
          path: ':slug(.*)',
          component: () => import('@/views/help/HelpDocView.vue'),
          meta: { requiresAuth: false },
        },
      ],
    },
    {
      path: '/404',
      name: '404',
      component: NotFoundView,
      meta: { requiresAuth: false },
    },
    {
      path: '/:pathMatch(.*)*',
      component: NotFoundView,
    },
  ],
});

router.beforeEach(async (to) => {
  const { useSystemStore } = await import('@/stores/system');
  const { useUserStore } = await import('@/stores/user');
  const { toast } = await import('@/js/toast');

  const systemStore = useSystemStore();
  const userStore = useUserStore();

  // Electron: require active connection before any page except server-selector
  if (isElectron() && to.path !== '/electron/server-selector') {
    try {
      const activeConnection = await window.electronAPI?.getActiveConnection?.();
      if (!activeConnection) {
        toast.warning('Please select a server to connect to');
        return '/electron/server-selector';
      }
    } catch {
      return '/electron/server-selector';
    }
  }

  // Electron-only pages are inaccessible in the browser
  if (to.matched.some((r) => r.meta.isElectronOnly) && !isElectron()) {
    toast.error('This page is only available in the desktop app');
    return '/';
  }

  if (to.path === '/electron/server-selector') return undefined;

  // Load RBAC roles on first navigation if not already loaded
  if (systemStore.rbacRoles.length === 0) {
    await systemStore.getRbacRoles();
    await systemStore.getSettings();
    await userStore.getCurrentUser();
    if (userStore.currentUser) {
      await userStore.getCurrentRbac();
    }
  }

  const requiresAuth = to.matched.some((r) => r.meta.requiresAuth);
  const requiresAdmin = to.matched.some((r) => r.meta.requiresAdmin);
  const requiresShowAccess = to.matched.some((r) => r.meta.requiresShowAccess);

  // If no admin user yet, send everyone to home (which shows the create-admin UI)
  if (
    systemStore.settings &&
    (systemStore.settings as Record<string, unknown>).has_admin_user === false
  ) {
    if (to.path !== '/') {
      toast.error('Please create an admin user before continuing');
      return '/';
    }
    return undefined;
  }

  const currentUser = userStore.currentUser;
  const isAuthenticated = currentUser !== null;

  // Already logged in — don't show login page
  if (to.path === '/login' && isAuthenticated) {
    toast.info('You are already logged in');
    return '/';
  }

  // Require auth
  if (requiresAuth && !isAuthenticated) {
    toast.error('Please log in to access this page');
    return '/login';
  }

  // Force password change
  const requiresPasswordChange = currentUser?.requires_password_change === true;
  const isPasswordChangePage = to.path === '/force-password-change';

  if (isAuthenticated && requiresPasswordChange && !isPasswordChangePage) {
    toast.warning('You must change your password before continuing');
    return '/force-password-change';
  }

  if (isPasswordChangePage && !requiresPasswordChange) {
    return '/';
  }

  // Admin-only pages
  if (requiresAdmin && !systemStore.isAdminUser) {
    toast.error('Admin access required');
    return '/';
  }

  // Show access
  if (requiresShowAccess) {
    if (!systemStore.currentShow) {
      toast.error('No show is currently selected');
      return '/';
    }
    if (!systemStore.hasShowAccess) {
      toast.error('You do not have permission to access show configuration');
      return '/';
    }
  }

  // Live page requires an active show session
  if (to.path === '/live') {
    // Show session check added in Phase 6 when show store is available
    // For now, allow navigation (the live page itself will handle the guard)
  }

  return undefined;
});

export default router;
