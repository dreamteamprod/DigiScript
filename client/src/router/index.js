import Vue from 'vue';
import VueRouter from 'vue-router';

Vue.use(VueRouter);

const routes = [
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
        name: 'show-config-characters',
        path: 'characters',
        component: () => import('../views/show/config/ConfigCharacters.vue'),
        meta: { requiresAuth: true, requiresShowAccess: true },
      },
      {
        name: 'show-config-character-groups',
        path: 'character-groups',
        component: () => import('../views/show/config/ConfigCharacterGroups.vue'),
        meta: { requiresAuth: true, requiresShowAccess: true },
      },
      {
        name: 'show-config-acts',
        path: 'acts',
        component: () => import('../views/show/config/ConfigActs.vue'),
        meta: { requiresAuth: true, requiresShowAccess: true },
      },
      {
        name: 'show-config-scenes',
        path: 'scenes',
        component: () => import('../views/show/config/ConfigScenes.vue'),
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
  mode: 'history',
  base: import.meta.env.BASE_URL,
  routes,
});

router.beforeEach(async (to, from, next) => {
  // Silly code needed for... reasons... this seems to correctly set the correct state
  // on the router and do the fetch needed for anything else. Shrug...
  let requiresSettingsFetch = false;
  if (router.app.$store === undefined) {
    await router.app.$nextTick();
    requiresSettingsFetch = true;
  }
  if (requiresSettingsFetch) {
    await router.app.$store.dispatch('GET_RBAC_ROLES');
    await router.app.$store.dispatch('GET_SETTINGS');
    await router.app.$store.dispatch('GET_CURRENT_USER');
    if (router.app.$store.getters.CURRENT_USER) {
      await router.app.$store.dispatch('GET_CURRENT_RBAC');
    }
  }

  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth);
  const requiresAdmin = to.matched.some((record) => record.meta.requiresAdmin);
  const requiresShowAccess = to.matched.some((record) => record.meta.requiresShowAccess);

  // Check if the system has admin user set up
  if (router.app.$store.getters.SETTINGS && !router.app.$store.getters.SETTINGS.has_admin_user) {
    if (to.path !== '/') {
      Vue.$toast.error('Please create an admin user before continuing');
      return next('/');
    }
    return next();
  }

  const currentUser = router.app.$store.getters.CURRENT_USER;
  const isAuthenticated = currentUser !== null;
  const isAdmin = currentUser?.is_admin === true;

  // Helper function to check show access
  const hasShowAccess = () => {
    if (!router.app.$store.getters.CURRENT_SHOW) return false;

    // Admin always has access
    if (isAdmin) return true;

    // Check RBAC permissions for show edit/execute
    const rbacRoles = router.app.$store.getters.RBAC_ROLES;
    const userRbac = router.app.$store.getters.CURRENT_USER_RBAC;

    if (!rbacRoles.length || !userRbac || (!Object.keys(userRbac).includes('shows') && !Object.keys(userRbac).includes('script') && !Object.keys(userRbac).includes('cuetypes'))) {
      return false;
    }

    const writeMask = rbacRoles.find((x) => x.key === 'WRITE')?.value || 0;
    const readMask = rbacRoles.find((x) => x.key === 'READ')?.value || 0;
    const executeMask = rbacRoles.find((x) => x.key === 'EXECUTE')?.value || 0;

    // Bitwise check if user has READ, WRITE or EXECUTE permission for shows
    const showAllowed = userRbac.shows && userRbac.shows[0]
      // eslint-disable-next-line no-bitwise
      && ((userRbac.shows[0][1] & (writeMask | executeMask | readMask)) !== 0);

    // Bitwise check if user has READ or WRITE permission for script
    const scriptAllowed = userRbac.script && userRbac.script[0]
      // eslint-disable-next-line no-bitwise
      && ((userRbac.script[0][1] & (writeMask | readMask)) !== 0);

    // Bitwise check if user has READ or WRITE permission for any cue types
    const cueTypesAllowed = userRbac.cuetypes
      // eslint-disable-next-line no-bitwise
      && userRbac.cuetypes.filter((x) => (x[1] & (writeMask | readMask)) !== 0).length > 0;

    return showAllowed || scriptAllowed || cueTypesAllowed;
  };

  // Check if we are navigating to the login page while already authenticated
  // If so, redirect to where the user just was
  if (to.path === '/login' && isAuthenticated) {
    Vue.$toast.info('You are already logged in');
    return next(from.fullPath);
  }

  // Check authentication requirements
  if (requiresAuth && !isAuthenticated) {
    Vue.$toast.error('Please log in to access this page');
    return next('/login');
  }

  // Check admin requirements
  if (requiresAdmin && !isAdmin) {
    Vue.$toast.error('Admin access required');
    return next('/');
  }

  // Check show access requirements
  if (requiresShowAccess) {
    // First check if there's a current show
    if (!router.app.$store.getters.CURRENT_SHOW) {
      Vue.$toast.error('No show is currently selected');
      return next('/');
    }

    // Then check permissions
    if (!hasShowAccess()) {
      Vue.$toast.error('You do not have permission to access show configuration');
      return next('/');
    }
  }

  // Handle special case for live route
  if (to.path === '/live') {
    await router.app.$store.dispatch('GET_SHOW_SESSION_DATA');
    const showSession = router.app.$store.getters.CURRENT_SHOW_SESSION;
    const websocketHealthy = router.app.$store.getters.WEBSOCKET_HEALTHY;

    if (!showSession || !websocketHealthy) {
      Vue.$toast.error('No active show session or connection issue');
      return next('/');
    }
  }
  return next();
});

export default router;
