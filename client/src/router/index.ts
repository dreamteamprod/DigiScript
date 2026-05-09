import Vue from 'vue';
import VueRouter from 'vue-router';
import type { RouteConfig } from 'vue-router';
import { isElectron } from '@/js/platform';

Vue.use(VueRouter);

const VueToast = Vue as typeof Vue & {
  $toast: {
    success: (m: string) => void;
    error: (m: string) => void;
    info: (m: string) => void;
    warning: (m: string) => void;
  };
};

const routes: RouteConfig[] = [
  {
    path: '/electron/server-selector',
    name: 'electron-server-selector',
    component: () => import('../views/electron/ServerSelector.vue'),
    meta: { requiresAuth: false, isElectronOnly: true },
  },
  {
    path: '/',
    name: 'home',
    component: () => import('../views/HomeView.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/about',
    name: 'about',
    component: () => import('../views/AboutView.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/config',
    name: 'config',
    component: () => import('../views/config/ConfigView.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
  {
    path: '/show-config',
    component: () => import('../views/show/ShowConfigView.vue'),
    meta: { requiresAuth: true, requiresShowAccess: true },
    children: [
      {
        name: 'show-config',
        path: '',
        component: () => import('../views/show/config/ConfigShow.vue'),
        meta: { requiresAuth: true, requiresShowAccess: true },
      },
      {
        name: 'show-config-cast',
        path: 'cast',
        component: () => import('../views/show/config/ConfigCast.vue'),
        meta: { requiresAuth: true, requiresShowAccess: true },
      },
      {
        name: 'show-config-stage',
        path: 'stage',
        component: () => import('../views/show/config/ConfigStage.vue'),
        meta: { requiresAuth: true, requiresShowAccess: true },
      },
      {
        name: 'show-config-characters',
        path: 'characters',
        component: () => import('../views/show/config/ConfigCharacters.vue'),
        meta: { requiresAuth: true, requiresShowAccess: true },
      },
      {
        name: 'show-config-acts-scenes',
        path: 'acts',
        component: () => import('../views/show/config/ConfigActsAndScenes.vue'),
        meta: { requiresAuth: true, requiresShowAccess: true },
      },
      {
        name: 'show-config-cues',
        path: 'cues',
        component: () => import('../views/show/config/ConfigCues.vue'),
        meta: { requiresAuth: true, requiresShowAccess: true },
      },
      {
        name: 'show-config-mics',
        path: 'mics',
        component: () => import('../views/show/config/ConfigMics.vue'),
        meta: { requiresAuth: true, requiresShowAccess: true },
      },
      {
        name: 'show-config-script',
        path: 'script',
        component: () => import('../views/show/config/ConfigScript.vue'),
        meta: { requiresAuth: true, requiresShowAccess: true },
      },
      {
        name: 'show-config-script-revisions',
        path: 'script-revisions',
        component: () => import('../views/show/config/ConfigScriptRevisions.vue'),
        meta: { requiresAuth: true, requiresShowAccess: true },
      },
      {
        name: 'show-sessions',
        path: 'sessions',
        component: () => import('../views/show/config/ConfigSessions.vue'),
        meta: { requiresAuth: true, requiresShowAccess: true },
      },
    ],
  },
  {
    path: '/live',
    name: 'live',
    component: () => import('../views/show/ShowLiveView.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/user/LoginView.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/me',
    name: 'user_settings',
    component: () => import('../views/user/Settings.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/force-password-change',
    name: 'force_password_change',
    component: () => import('../views/user/ForcePasswordChangeView.vue'),
    meta: { requiresAuth: true, requiresPasswordChange: true },
  },
  {
    path: '/help',
    component: () => import('../views/HelpView.vue'),
    meta: { requiresAuth: false },
    children: [
      {
        path: '',
        redirect: 'getting-started',
      },
      {
        name: 'help-doc',
        path: ':slug(.*)',
        component: () => import('../views/help/HelpDocView.vue'),
        meta: { requiresAuth: false },
      },
    ],
  },
  {
    path: '*',
    name: '404',
    component: () => import('../views/404View.vue'),
    meta: { requiresAuth: false },
  },
];

const router = new VueRouter({
  mode: window.location.protocol === 'file:' ? 'hash' : 'history',
  base: import.meta.env.BASE_URL,
  routes,
});

router.beforeEach(async (to, from, next) => {
  // router.app is typed as Vue but lacks $store/$toast augmentations at the router level
  const app = router.app as any;

  let requiresSettingsFetch = false;
  if (app.$store === undefined) {
    await app.$nextTick();
    requiresSettingsFetch = true;
  } else {
    const rbacRoles = app.$store.getters.RBAC_ROLES;
    if (!rbacRoles || rbacRoles.length === 0) {
      requiresSettingsFetch = true;
    }
  }

  if (isElectron() && to.path !== '/electron/server-selector') {
    try {
      const activeConnection = await window.electronAPI?.getActiveConnection?.();
      if (!activeConnection) {
        if (app.$toast) {
          app.$toast.warning('Please select a server to connect to');
        }
        return next('/electron/server-selector');
      }
    } catch (error) {
      console.error('Error checking active connection:', error);
      return next('/electron/server-selector');
    }
  }

  const isElectronOnly = to.matched.some((record) => record.meta.isElectronOnly);
  if (isElectronOnly && !isElectron()) {
    if (app.$toast) {
      app.$toast.error('This page is only available in the desktop app');
    }
    return next('/');
  }

  if (to.path === '/electron/server-selector') {
    return next();
  }

  if (requiresSettingsFetch) {
    await app.$store.dispatch('GET_RBAC_ROLES');
    await app.$store.dispatch('GET_SETTINGS');
    await app.$store.dispatch('GET_CURRENT_USER');
    if (app.$store.getters.CURRENT_USER) {
      await app.$store.dispatch('GET_CURRENT_RBAC');
    }
  }

  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth);
  const requiresAdmin = to.matched.some((record) => record.meta.requiresAdmin);
  const requiresShowAccess = to.matched.some((record) => record.meta.requiresShowAccess);

  if (app.$store.getters.SETTINGS && !app.$store.getters.SETTINGS.has_admin_user) {
    if (to.path !== '/') {
      VueToast.$toast.error('Please create an admin user before continuing');
      return next('/');
    }
    return next();
  }

  const currentUser = app.$store.getters.CURRENT_USER;
  const isAuthenticated = currentUser !== null;
  const isAdmin = currentUser?.is_admin === true;

  const hasShowAccess = (): boolean => {
    if (!app.$store.getters.CURRENT_SHOW) return false;
    if (isAdmin) return true;

    const rbacRoles = app.$store.getters.RBAC_ROLES;
    const userRbac = app.$store.getters.CURRENT_USER_RBAC;

    if (
      !rbacRoles.length ||
      !userRbac ||
      (!Object.keys(userRbac).includes('shows') &&
        !Object.keys(userRbac).includes('script') &&
        !Object.keys(userRbac).includes('cuetypes'))
    ) {
      return false;
    }

    const writeMask: number = rbacRoles.find((x: { key: string }) => x.key === 'WRITE')?.value ?? 0;
    const readMask: number = rbacRoles.find((x: { key: string }) => x.key === 'READ')?.value ?? 0;
    const executeMask: number =
      rbacRoles.find((x: { key: string }) => x.key === 'EXECUTE')?.value ?? 0;

    const showAllowed =
      userRbac.shows?.[0] && (userRbac.shows[0][1] & (writeMask | executeMask | readMask)) !== 0;
    const scriptAllowed =
      userRbac.script?.[0] && (userRbac.script[0][1] & (writeMask | readMask)) !== 0;
    const cueTypesAllowed =
      userRbac.cuetypes &&
      userRbac.cuetypes.filter((x: [number, number]) => (x[1] & (writeMask | readMask)) !== 0)
        .length > 0;

    return !!(showAllowed || scriptAllowed || cueTypesAllowed);
  };

  if (to.path === '/login' && isAuthenticated) {
    VueToast.$toast.info('You are already logged in');
    return next(from.fullPath);
  }

  if (requiresAuth && !isAuthenticated) {
    VueToast.$toast.error('Please log in to access this page');
    return next('/login');
  }

  const requiresPasswordChange = currentUser?.requires_password_change === true;
  const isPasswordChangePage = to.path === '/force-password-change';

  if (isAuthenticated && requiresPasswordChange && !isPasswordChangePage) {
    VueToast.$toast.warning('You must change your password before continuing');
    return next('/force-password-change');
  }

  if (isPasswordChangePage && !requiresPasswordChange) {
    return next('/');
  }

  if (requiresAdmin && !isAdmin) {
    VueToast.$toast.error('Admin access required');
    return next('/');
  }

  if (requiresShowAccess) {
    if (!app.$store.getters.CURRENT_SHOW) {
      VueToast.$toast.error('No show is currently selected');
      return next('/');
    }
    if (!hasShowAccess()) {
      VueToast.$toast.error('You do not have permission to access show configuration');
      return next('/');
    }
  }

  if (to.path === '/live') {
    await app.$store.dispatch('GET_SHOW_SESSION_DATA');
    const showSession = app.$store.getters.CURRENT_SHOW_SESSION;
    const websocketHealthy = app.$store.getters.WEBSOCKET_HEALTHY;

    if (!showSession || !websocketHealthy) {
      VueToast.$toast.error('No active show session or connection issue');
      return next('/');
    }
  }
  return next();
});

export default router;
