import path from 'path';
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [vue()],
  
  // Base URL for production - Vue 3 will be served at /v3/
  base: '/v3/',
  
  // Build configuration
  build: {
    outDir: '../server/static-vue3/',
    assetsDir: 'assets',
    emptyOutDir: true,
    // Generate manifest for easier integration
    manifest: true,
    rollupOptions: {
      // Ensure clean build output
      output: {
        manualChunks: {
          vendor: ['vue', 'vue-router', 'pinia'],
        },
      },
    },
  },
  
  // Development server configuration
  server: {
    port: 3000,
    host: true, // Listen on all addresses
    cors: true,
    proxy: {
      // Proxy API calls to the main server during development
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        secure: false,
      },
      // Proxy WebSocket connections
      '/ws': {
        target: 'ws://localhost:8080',
        ws: true,
        changeOrigin: true,
      },
    },
  },
  
  // Path resolution
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  
  // Define global constants for development
  define: {
    __VUE_OPTIONS_API__: true,
    __VUE_PROD_DEVTOOLS__: false,
  },
});