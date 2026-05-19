import path from 'path';
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import Components from 'unplugin-vue-components/vite';
import { BootstrapVueNextResolver } from 'bootstrap-vue-next';
import Icons from 'unplugin-icons/vite';
import IconsResolve from 'unplugin-icons/resolver';

export default defineConfig({
  plugins: [
    vue(),
    Components({
      resolvers: [BootstrapVueNextResolver(), IconsResolve()],
      dts: true,
    }),
    Icons({
      compiler: 'vue3',
      autoInstall: false,
    }),
  ],
  base: process.env.BUILD_TARGET === 'electron' ? './' : '/ui-new/',
  build: {
    outDir:
      process.env.BUILD_TARGET === 'electron' ? './dist-electron' : '../server/static/ui-new/',
    assetsDir: './assets',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules') && !id.includes('?commonjs-entry')) {
            if (id.includes('bootstrap-vue-next') || id.includes('/bootstrap/')) {
              return 'bootstrap-vendor';
            }
            if (
              id.includes('/vue/') ||
              id.includes('vue-router') ||
              id.includes('/pinia/') ||
              id.includes('pinia-plugin-persistedstate')
            ) {
              return 'vue-vendor';
            }
            if (
              id.includes('/lodash/') ||
              id.includes('loglevel') ||
              id.includes('deep-object-diff') ||
              id.includes('contrast-color')
            ) {
              return 'utils-vendor';
            }
            if (id.includes('marked') || id.includes('dompurify') || id.includes('fuse.js')) {
              return 'docs-vendor';
            }
            return 'vendor';
          }
        },
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]',
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
    extensions: ['.ts', '.js', '.vue', '.json'],
  },
  css: {
    preprocessorOptions: {
      scss: {
        api: 'modern-compiler',
        loadPaths: [path.resolve(__dirname, 'node_modules')],
        // Bootstrap 5 and Bootswatch still use legacy Sass @import syntax;
        // suppress those third-party deprecation warnings.
        quietDeps: true,
        silenceDeprecations: ['import', 'global-builtin', 'color-functions'],
      },
    },
    devSourcemap: true,
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
      '/api/v1/ws': {
        target: 'ws://localhost:8080',
        ws: true,
      },
    },
  },
});
