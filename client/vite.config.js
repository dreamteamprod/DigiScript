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
    minify: 'esbuild',
    cssMinify: 'esbuild',
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
            // Documentation dependencies
            if (id.includes('marked') || id.includes('dompurify') || id.includes('fuse.js')) {
              return 'docs-vendor';
            }
            // Everything else from node_modules goes to a general vendor chunk
            return 'vendor';
          }
        },
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]',
      },
    },
  },
  optimizeDeps: {
    include: [
      'vue',
      'vue-router',
      'vuex',
      'bootstrap-vue',
      'jquery',
      'lodash',
    ],
    exclude: [
      'fuse.js',
    ],
  },
  resolve: {
    alias: [
      {
        find: '@',
        replacement: path.resolve(__dirname, 'src'),
      },
    ],
    extensions: ['.js', '.vue', '.json'],
  },
  css: {
    preprocessorOptions: {
      scss: {
        api: 'modern-compiler',
        loadPaths: [path.resolve(__dirname, 'node_modules')],
      },
    },
    devSourcemap: true,
  },
});
