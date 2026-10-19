# DigiScript Client (V3)

**Requirements**: Node 24.15+, pnpm 12.x (run `corepack enable` once; it uses the version pinned in `packageManager`)

## Project setup
```
pnpm install
```

### Run the development server
```
pnpm run dev
```

The dev server starts at `http://localhost:5173` and proxies API requests to `http://localhost:8080`.

### Compiles and minifies for production
```
pnpm run build
```

### Lints and formats files
```
pnpm run lint
```

### Type checking
```
pnpm run typecheck
```

### Unit tests
```
pnpm run test:run
```

### E2E tests
```
pnpm run test:e2e
```

See [e2e/README.md](./e2e/README.md) for full details on running and writing E2E tests.

## Project Structure

### Source Directory
The [src](./src) directory is where the main Vue 3 project lives.

* [assets](./src/assets): static assets such as CSS and images.
* [components](./src/components): reusable Vue components, organised by feature area.
* [composables](./src/composables): Composition API composables (shared logic, replaces Vue 2 mixins).
* [constants](./src/constants): shared constants used across components.
* [js](./src/js): plain TypeScript utilities — HTTP interceptor, validators.
* [router](./src/router): Vue Router configuration and navigation guards.
* [stores](./src/stores): Pinia stores for application state (user, show, script, websocket, etc.).
* [types](./src/types): TypeScript interfaces for API response shapes and shared types.
* [views](./src/views): page-level components mapped to router routes.
* [App.vue](./src/App.vue): root component — defines the main layout and houses the router view.
* [main.ts](./src/main.ts): application entry point, configures Vue, Pinia, and the router.
