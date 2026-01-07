import js from '@eslint/js';
import pluginVue from 'eslint-plugin-vue';
import globals from 'globals';
import babelParser from '@babel/eslint-parser';

export default [
  {
    ignores: [
      '**/node_modules/**',
      '**/dist/**',
      '../server/static/**',
      'junit/**',
      '*.backup',
    ],
  },
  js.configs.recommended,
  ...pluginVue.configs['flat/vue2-recommended'],
  {
    files: ['**/*.{js,vue}'],
    languageOptions: {
      ecmaVersion: 2021,
      sourceType: 'module',
      parser: pluginVue.processors['.vue'].parser,
      parserOptions: {
        parser: babelParser,
        requireConfigFile: false,
        ecmaVersion: 12,
        sourceType: 'module',
        babelOptions: {
          presets: ['@babel/preset-env'],
        },
      },
      globals: {
        ...globals.browser,
        ...globals.node,
        ...globals.es2021,
      },
    },
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
      'max-len': [
        'error',
        150,
        2,
        {
          ignoreUrls: true,
          ignoreComments: false,
          ignoreRegExpLiterals: true,
          ignoreStrings: true,
          ignoreTemplateLiterals: true,
        },
      ],
    },
  },
  {
    files: ['**/*.test.js'],
    languageOptions: {
      globals: {
        describe: 'readonly',
        it: 'readonly',
        expect: 'readonly',
        vi: 'readonly',
        beforeEach: 'readonly',
        afterEach: 'readonly',
      },
    },
  },
];