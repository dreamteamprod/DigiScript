import js from '@eslint/js';
import pluginVue from 'eslint-plugin-vue';
import globals from 'globals';
import babelParser from '@babel/eslint-parser';
import prettierConfig from 'eslint-config-prettier';
import prettierPlugin from 'eslint-plugin-prettier';

export default [
  {
    ignores: [
      '**/node_modules/**',
      '**/dist/**',
      '../server/static/**',
      'junit/**',
      '*.backup',
      'src/docs/**',
    ],
  },
  js.configs.recommended,
  ...pluginVue.configs['flat/vue2-recommended'],
  {
    files: ['**/*.{js,vue}'],
    plugins: {
      prettier: prettierPlugin,
    },
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      parser: pluginVue.processors['.vue'].parser,
      parserOptions: {
        parser: babelParser,
        requireConfigFile: false,
        ecmaVersion: 13,
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
      // Prettier integration - runs Prettier as an ESLint rule
      'prettier/prettier': 'error',

      // Disable formatting rules that conflict with Prettier
      ...prettierConfig.rules,

      // Let Prettier handle line length (via printWidth config)
      'max-len': 'off',

      // Custom linting rules (non-formatting)
      'no-unused-vars': 'off',
      'vue/no-unused-vars': 'off',
      'no-plusplus': 'off',
      'no-param-reassign': [
        'error',
        {
          props: true,
          ignorePropertyModificationsFor: ['state', 'acc', 'e'],
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