import js from '@eslint/js';
import vuePlugin from 'eslint-plugin-vue';
import importPlugin from 'eslint-plugin-import';
import accessibilityPlugin from 'eslint-plugin-vuejs-accessibility';
import stylisticPlugin from '@stylistic/eslint-plugin';
import globals from 'globals';

export default [
  js.configs.recommended,
  
  {
    rules: {
      'semi': ['error', 'always'], // Enforce semicolons
      '@stylistic/semi': ['error', 'always'], // Enforce semicolons (stylistic plugin)
      'space-before-function-paren': ['error', {
        anonymous: 'always',
        named: 'never',
        asyncArrow: 'always',
      }], // Preserve original function spacing
      '@stylistic/space-before-function-paren': ['error', {
        anonymous: 'always',
        named: 'never',
        asyncArrow: 'always',
      }], // Preserve original function spacing (stylistic plugin)
      'comma-dangle': ['error', 'always-multiline'], // Keep trailing commas
      '@stylistic/comma-dangle': ['error', 'always-multiline'], // Keep trailing commas (stylistic plugin)
      'quotes': ['error', 'single', { avoidEscape: true }], // Keep single quotes
      '@stylistic/quotes': ['error', 'single', { avoidEscape: true }], // Keep single quotes (stylistic plugin)
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
  
  ...vuePlugin.configs['flat/vue2-recommended'],
  
  {
    languageOptions: {
      ecmaVersion: 2021,
      sourceType: 'module',
      globals: {
        ...globals.browser,
        fetch: 'readonly',
        URLSearchParams: 'readonly',
      },
    },
  },
  
  {
    plugins: {
      vue: vuePlugin,
      import: importPlugin,
      'vuejs-accessibility': accessibilityPlugin,
      '@stylistic': stylisticPlugin,
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
