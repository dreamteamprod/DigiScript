import path from 'path';
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue2';

export default defineConfig({
  plugins: [
    vue(),
  ],
  build: {
    outDir: '../server/static/',
    assetsDir: './assets',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks(id) {
          // Only chunk node_modules, ignore CommonJS entry points
          if (id.includes('node_modules') && !id.includes('?commonjs-entry')) {
            // Bootstrap and its dependencies
            if (id.includes('bootstrap-vue') || id.includes('/bootstrap/')) {
              return 'bootstrap-vendor';
            }
            // Core Vue ecosystem
            if (id.includes('/vue/') || id.includes('vue-router') ||
                id.includes('/vuex/') || id.includes('vuex-persistedstate')) {
              return 'vue-vendor';
            }
            // Utilities (lodash uses specific imports)
            if (id.includes('/lodash/') || id.includes('loglevel') ||
                id.includes('deep-object-diff') || id.includes('contrast-color')) {
              return 'utils-vendor';
            }
            // WebSocket
            if (id.includes('vue-native-websocket')) {
              return 'websocket-vendor';
            }
            // Everything else from node_modules goes to a general vendor chunk
            return 'vendor';
          }
        },
      },
    },
  },
  resolve: {
    alias: [
      {
        find: '@',
        replacement: path.resolve(__dirname, 'src'),
      },
    ],
  },
});
