import vuePlugin from 'eslint-plugin-vue';
import importPlugin from 'eslint-plugin-import';
import accessibilityPlugin from 'eslint-plugin-vuejs-accessibility';
import globals from 'globals';
import neostandard from 'neostandard';

const baseConfig = neostandard({
  env: ['browser'],
  globals: {
    fetch: 'readonly',
    URLSearchParams: 'readonly',
  }
});

export default [
  ...baseConfig,
  
  ...vuePlugin.configs['flat/vue2-recommended'],
  
  {
    plugins: {
      vue: vuePlugin,
      import: importPlugin,
      'vuejs-accessibility': accessibilityPlugin,
    },
  },
  
  {
    files: ['**/*.{js,vue}'],
    rules: {
      'no-unused-vars': 'off',
      'vue/no-unused-vars': 'off',
      'no-plusplus': 'off',
      'no-param-reassign': ['error', {
        props: true,
        ignorePropertyModificationsFor: [
          'state',
          'acc',
          'e',
        ],
      }],
      'import/no-unresolved': 'off', // Turning off due to alias resolution issues
    },
  },
  
  {
    settings: {
      'import/resolver': {
        alias: {
          map: [
            ['@', './src'],
          ],
        },
      },
    },
  },
];
