import vuePlugin from 'eslint-plugin-vue';
import importPlugin from 'eslint-plugin-import';
import accessibilityPlugin from 'eslint-plugin-vuejs-accessibility';
import promisePlugin from 'eslint-plugin-promise';
import nPlugin from 'eslint-plugin-n';
import js from '@eslint/js';
import globals from 'globals';

export default [
  js.configs.recommended,
  
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
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
    },
  },
  
  {
    rules: {
      'no-var': 'error',
      'prefer-const': 'error',
      'prefer-rest-params': 'error',
      'prefer-spread': 'error',
      'object-shorthand': 'error',
      'quote-props': ['error', 'as-needed'],
      'no-array-constructor': 'error',
      'array-callback-return': 'error',
      'prefer-template': 'error',
      'template-curly-spacing': 'error',
      'no-useless-escape': 'error',
      'no-loop-func': 'error',
      'prefer-arrow-callback': 'error',
      'arrow-spacing': 'error',
      'arrow-parens': ['error', 'as-needed'],
      'no-useless-constructor': 'error',
      'no-dupe-class-members': 'error',
      'no-duplicate-imports': 'error',
      'import/first': 'error',
      'import/no-duplicates': 'error',
      'import/no-mutable-exports': 'error',
      'import/newline-after-import': 'error',
      'import/no-unresolved': 'off', // Turning off due to alias resolution issues
      'promise/param-names': 'error',
      'n/no-deprecated-api': 'error',
    },
  },
  
  {
    plugins: {
      vue: vuePlugin,
      import: importPlugin,
      'vuejs-accessibility': accessibilityPlugin,
      promise: promisePlugin,
      n: nPlugin,
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
