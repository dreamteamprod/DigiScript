import { defineConfig } from 'vitest/config';
import vue from '@vitejs/plugin-vue';
import path from 'path';

export default defineConfig({
  plugins: [vue()],
  test: {
    globals: true,
    environment: 'jsdom',
    passWithNoTests: true,
    reporters: ['default', 'junit'],
    outputFile: {
      junit: './junit/test-results.xml',
    },
    isolate: true,
    pool: 'threads',
    css: false,
    clearMocks: true,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
