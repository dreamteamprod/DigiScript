# Vue.js 3 Migration Plan — Issue #1033

## Context

Vue 2.7.14 reached End of Life on 31 December 2023. DigiScript's frontend currently runs on
it. The strangler-fig approach — a parallel `client-v3/` directory served at `/ui-new/` — lets
pages migrate incrementally without disrupting the live Vue 2 app.

**Out of scope**: The `feature/collaborative-editing` branch (Yjs/CRDT). It will be integrated
into the Vue 3 frontend as a separate future issue.

---

## Technology Stack

| Library | Vue 2 (client/) | Vue 3 (client-v3/) |
|---|---|---|
| Vue | 2.7.14 | ^3.5.0 |
| Vue Router | 3.6.5 | ^5.0.7 |
| State | Vuex 3.6.2 | Pinia ^3.0.0 |
| State persistence | vuex-persistedstate 3.2.1 | pinia-plugin-persistedstate ^4.7.1 |
| UI | bootstrap-vue 2.23.1 + Bootstrap 4.6.2 | bootstrap-vue-next ^0.45.3 + Bootstrap 5.3.x |
| Validation | vuelidate 0.7.7 | @vuelidate/core ^2.0.3 + @vuelidate/validators ^2.0.4 |
| WebSocket | vue-native-websocket 2.0.15 | custom `useWebSocket()` composable |
| Toast | vue-toast-notification 0.6.3 | vue-toast-notification ^3.1.3 |
| Multiselect | vue-multiselect 2.1.9 | vue-multiselect ^3.5.0 |
| Splitpanes | splitpanes ^2.4.1 | splitpanes ^4.0.4 |
| Theming | bootswatch 4.6.2 | bootswatch ^5.3.8 |
| Vite plugin | @vitejs/plugin-vue2 | @vitejs/plugin-vue ^6.0.6 |
| Vite | 7.3.3 | ^8.0.12 |
| ESLint | 9.x | 10.x |
| jQuery | 3.7.1 | **dropped** (Bootstrap 5 doesn't need it) |

Framework-agnostic packages are copied unchanged: `d3-*`, `lodash`, `loglevel`, `deep-object-diff`,
`contrast-color`, `dompurify`, `fuse.js`, `core-js`. Note: `marked` jumps from 11.2.0 → ^18.0.3
(API changes to handle when migrating the help view in Phase 2).

## Persistence Strategy (corrected from original draft)

Auth token storage: **NOT** via pinia-plugin-persistedstate. The `user.ts` module stores it
directly in `localStorage` under key `digiscript_auth_token`, same as Vue 2.

pinia-plugin-persistedstate persists only:
- `websocket.internalUUID`
- `show.stageManagerMode`

## WebSocket OP routing in Vue 3

In Vue 2, `passToStoreHandler` calls `this.store.commit(eventName.toUpperCase(), msg)` which
routes to the `SOCKET_ONMESSAGE` mutation's switch block. In Vue 3, the `useWebSocket()`
composable handles the switch directly, calling Pinia store actions:

```
OP: SET_UUID        → wsStore.$patch({ internalUUID, pendingAuthentication: true })
OP: WS_AUTH_SUCCESS → wsStore.$patch({ authenticated: true, authSucceeded: true })
OP: WS_AUTH_ERROR   → wsStore.$patch({ authenticated: false })
OP: SETTINGS_CHANGED → systemStore.updateSettings(msg.DATA)
OP: START_SHOW      → router.push('/ui-new/live')
OP: STOP_SHOW       → router.push('/ui-new/')
OP: RELOAD_CLIENT   → window.location.reload()
```

Messages with `msg.ACTION` also call the corresponding Pinia store action by name.

---

## Repository Structure

```
/
├── client/            (Vue 2 — untouched until Phase 14)
├── client-v3/         (Vue 3 — created in Phase 0)
│   ├── src/
│   │   ├── main.ts
│   │   ├── App.vue
│   │   ├── shims-vue.d.ts
│   │   ├── router/index.ts
│   │   ├── stores/
│   │   ├── composables/
│   │   │   └── useWebSocket.ts  (Phase 1)
│   │   ├── views/
│   │   ├── components/
│   │   ├── types/api/
│   │   ├── constants/
│   │   └── js/
│   │       ├── http-interceptor.ts
│   │       └── platform/  (browser.ts, electron.ts, index.ts)
│   ├── package.json
│   ├── vite.config.ts   (base: '/ui-new/', outDir: '../server/static/ui-new/')
│   ├── tsconfig.json    (strict: true, useDefineForClassFields: true)
│   └── eslint.config.ts (ESLint 10, flat/recommended Vue 3)
└── server/
    └── static/
        ├── index.html         (Vue 2, served at /)
        └── ui-new/            (Vue 3, served at /ui-new/)
            ├── index.html
            └── assets/
```

---

## Phase Status

### ✅ Phase 0: Skeleton & Dual-Serving Infrastructure
- `client-v3/` created with full toolchain (Vite 8, Vue 3.5, Pinia 3, BVN 0.45)
- `server/controllers/controllers.py`: `RootControllerV3` added
- `server/digi_server/app_server.py`: `/ui-new/assets/` and `/ui-new/` handlers added
- CI: `nodelint.yml` + `client-v3` lint/typecheck jobs; `client-test.yml` + client-v3 test job
- Build: ✓  Typecheck: ✓  Lint: ✓  Tests: ✓

---

### ✅ Phase 1: Core Infrastructure
- Pinia stores: `user.ts`, `system.ts`, `websocket.ts` (persists `internalUUID` only)
- Composable: `useWebSocket.ts` — WS lifecycle + OP routing (replaces vue-native-websocket)
- `js/http-interceptor.ts` — port with Pinia stores called inside fetch override (not module scope)
- `js/platform/` directory copied verbatim (browser.ts, electron.ts, index.ts)
- `js/utils.ts`, `js/logger.ts`, `js/customValidators.ts` ported
- `types/api/` + `types/index.ts` + `constants/` — verbatim copies from `client/src/`
- `router/index.ts` — full route list + `beforeEach` guard (Vue Router 5 syntax)
- `App.vue` — full BVN navbar port (`<script setup>`, `storeToRefs`, `useVuelidate`)
- Stub views: `NotFoundView.vue`, `LoginView.vue`, `PlaceholderView.vue`
- Build: ✓  Typecheck: ✓  Lint: ✓  Tests: ✓

Key notes:
- Auth token: `localStorage.getItem('digiscript_auth_token')` direct (not persistedstate)
- `wsStore._sendFn` registered by composable so stores can send WS messages without circular imports
- Cross-store RBAC getters in `system.ts` use module-level `getUserRbac()` helper (lazy user store ref)

### ✅ Phase 2: Simple Read-Only Pages
- `stores/help.ts` — Pinia port of Vuex help module (manifest, document cache, Fuse.js search)
- `components/MarkdownRenderer.vue` — `marked` v18 async API via `watch` + `ref`; `:deep()` CSS; `import.meta.env.BASE_URL` for portable links
- `views/HomeView.vue` — reads `systemStore.currentShow` / `settings` + `userStore.currentUser`; `currentShowSession` stubbed null (Phase 6)
- `views/AboutView.vue` — static content, `<script setup>`
- `views/HelpView.vue` — BVN port with Fuse.js search, debounced input, sticky sidebar
- `views/help/HelpDocView.vue` — watch `route.params.slug`, cache-first doc loading
- `router/index.ts` — `/about` and `/help` routes wired to real components
- Build: ✓  Typecheck: ✓  Lint: ✓  Tests: ✓

### ✅ Phase 3: Authentication Pages
- `composables/useFormValidation.ts` — `$v`-field-state helper; port of `formValidationMixin`
- `composables/usePasswordValidation.ts` — `passwordRules` + `confirmPasswordRules` factory; `sameAs` takes value not field name in v2
- `views/user/LoginView.vue` — `useVuelidate()` composable pattern; `@submit.prevent`; `isLoginRequest` exclusion in HTTP interceptor
- `views/user/ForcePasswordChangeView.vue` — computed rules for reactive `sameAs`; `BAlert :model-value`; `BSpinner small`
- `stores/user.ts` — `changePassword()` action; reactive `authToken` state; `_setToken`/`_clearToken`; toast singleton
- `router/index.ts` — `/force-password-change` wired to real component
- Build: ✓  Typecheck: ✓  Lint: ✓  Tests: ✓

### ✅ Phase 4: User Settings
- `views/user/SettingsView.vue` — 6-tab pill-vertical shell
- `components/user/settings/AboutUser.vue` — `titleCase` + sorted `BTableSimple`
- `components/user/settings/UserSettingsConfig.vue` — 7-field settings form, PATCH `/api/v1/user/settings`, vuelidate
- `components/user/settings/ChangePassword.vue` — 3-field form; `usePasswordValidation`; sends `old_password`
- `components/user/settings/ApiToken.vue` — generate/regenerate/revoke with BModal confirmations; `#append` slot
- `components/user/settings/CueColourPreferences.vue` — cue types fetched locally; `BModal` ref pattern for all modals; `contrastColor`
- `components/user/settings/StageDirectionStyles.vue` — stage direction styles fetched locally; `v-model:pressed`; inline `.toUpperCase()`/`.toLowerCase()` (no Vue 3 filters)
- `js/customValidators.ts` — `notNull`, `notNullAndGreaterThanZero`
- `stores/user.ts` — 8 CRUD actions for overrides; `changePassword` accepts `oldPassword`; `logout` clears `cueColourOverrides`
- `router/index.ts` — `/me` wired to `SettingsView`
- Build: ✓  Typecheck: ✓  Lint: ✓  Tests: ✓

### ✅ Phase 4: User Settings
- `stores/user.ts` — `logout` clears `cueColourOverrides`; `changePassword` accepts `oldPassword`; 8 CRUD actions for stage direction style + cue colour overrides
- `js/customValidators.ts` — `notNull`, `notNullAndGreaterThanZero`
- `views/user/SettingsView.vue` — 6-tab pill-vertical shell; `content-class="flex-fill"` required on `<BTabs vertical>` (BVN behaviour differs from BV2)
- `components/user/settings/AboutUser.vue` — sorted `BTableSimple class="w-100"`, `titleCase` utility
- `components/user/settings/UserSettingsConfig.vue` — 7-field settings form, Vuelidate, PATCH `/api/v1/user/settings`
- `components/user/settings/ChangePassword.vue` — `usePasswordValidation` composable; sends `old_password`
- `components/user/settings/ApiToken.vue` — `v-model` BModal pattern; `<template #append>` for copy button
- `components/user/settings/CueColourPreferences.vue` — local cue type fetch; `ref<InstanceType<typeof BModal>>` for all 4 modals; dual Vuelidate instances
- `components/user/settings/StageDirectionStyles.vue` — local style fetch; `v-model:pressed`; inline `.toUpperCase()`/`.toLowerCase()` (no Vue 3 filters)
- `router/index.ts` — `/me` wired to `SettingsView`
- Build: ✓  Typecheck: ✓  Lint: ✓  Tests: ✓  Visual: ✓

---

### Phase 5: System Configuration
Config* views, modal pattern migration: `this.$bvModal.hide()` → `ref<BModal>.value?.hide()`.

### Phase 6: Show Configuration — Foundation
ShowConfigView.vue tab shell; stores/show.ts; RBAC bitmask utility.

### Phase 7: Show Configuration — Basic Tabs
ConfigShow, ConfigActsAndScenes, ConfigCast, ConfigCharacters.
`statsTableMixin` → `useStatsTable()` composable.

### Phase 8: Show Configuration — Cues & Sessions
`cueDisplayMixin` → `useCueDisplay()` composable.

### Phase 9: Show Configuration — Microphones
D3 timeline: `timelineMixin` → `useTimeline()` composable.
CRITICAL: D3 datasets stored as `ref<T[]>`, NOT `reactive()`. D3 owns SVG internals.

### Phase 10: Show Configuration — Stage
`stores/stage.ts` (port from store/modules/stage.ts).
Reuse `useTimeline()` from Phase 9.

### Phase 11: Show Configuration — Script & Revisions
Most complex section. Note: migrates dev/main branch script editor only; collaborative
editing (Yjs) is a separate follow-up.
`Vue.set()` → direct assignment (Pinia/Proxy handles reactivity).

### Phase 12: Show Live View
WebSocket-driven real-time view. Cue triggering via `sendObj()` from `useWebSocket()`.

### Phase 13: Electron Support (Optional / Future)

### Phase 14: Cutover — Vue 3 becomes default at /
- Vue 3 base: `/`; Vue 2 moves to `/ui-legacy/`

### Phase 15: Vue 2 Sunset
Remove `client/` directory and all associated routes/CI steps.

---

## Vue 2 → Vue 3 Migration Reference

### Lifecycle hooks
| Vue 2 | Vue 3 Composition |
|---|---|
| created() | setup() |
| mounted() | onMounted() |
| beforeDestroy() | onBeforeUnmount() |
| destroyed() | onUnmounted() |

### Reactivity
| Vue 2 | Vue 3 |
|---|---|
| Vue.set(obj, key, val) | obj[key] = val |
| Vue.delete(obj, key) | delete obj[key] |
| Vue.filter() | utility function / computed |
| Vue.prototype.$x | app.config.globalProperties.$x |

### Vuex → Pinia
| Vuex | Pinia |
|---|---|
| mutations | removed — set state directly in actions |
| namespaced: true | each store is its own module |
| mapGetters() | storeToRefs() |
| store.dispatch('mod/ACTION') | myStore.action() |
| store.commit('MOD/MUT', val) | myStore.field = val |

### Bootstrap 4 → 5 CSS differences
- `ml-*` / `mr-*` → `ms-*` / `me-*`
- `text-left` / `text-right` → `text-start` / `text-end`
- `pl-*` / `pr-*` → `ps-*` / `pe-*`

### bootstrap-vue → bootstrap-vue-next modal pattern
```vue
<!-- Vue 2 (programmatic) -->
this.$bvModal.hide('my-modal')
this.$bvModal.msgBoxConfirm('Are you sure?')

<!-- Vue 3 (ref-based) -->
<BModal ref="myModal" ...>
const myModal = ref<InstanceType<typeof BModal>>()
myModal.value?.hide()
```

### BTabs vertical — content pane width (CRITICAL)

BV2's `<b-tabs vertical>` automatically made the tab content pane fill
remaining horizontal space. BVN does **not** do this — the pane shrinks
to its content width, breaking horizontal layouts inside it.

**Always add `content-class="flex-fill"` to every `<BTabs vertical>`:**

```vue
<!-- Wrong — content pane shrinks to fit -->
<BTabs pills vertical>

<!-- Correct — content pane fills remaining space -->
<BTabs pills vertical content-class="flex-fill">
```

### BTableSimple — explicit width required

BVN's `<BTableSimple>` does not default to `width: 100%`. Always add
`class="w-100"` to match BV2's full-width table behaviour:

```vue
<BTableSimple class="w-100">
```
