import js from '@eslint/js';
import pluginVue from 'eslint-plugin-vue';
import globals from 'globals';
import tsParser from '@typescript-eslint/parser';
import tsPlugin from '@typescript-eslint/eslint-plugin';
import prettierConfig from 'eslint-config-prettier';
import prettierPlugin from 'eslint-plugin-prettier';
import tseslint from 'typescript-eslint';

const sharedRules = {
  'prettier/prettier': 'error',
  ...prettierConfig.rules,
  'max-len': 'off',
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
};

const tsRules = {
  ...Object.assign({}, ...tseslint.configs.recommended.map((c) => c.rules ?? {})),
  '@typescript-eslint/no-explicit-any': 'off',
  '@typescript-eslint/no-unused-vars': 'off',
  // Vue 2 Options API patterns that are valid in this codebase
  '@typescript-eslint/no-this-alias': 'off',
  '@typescript-eslint/no-unsafe-function-type': 'off', // Function prop types are idiomatic in Vue 2
};

const sharedGlobals = {
  ...globals.browser,
  ...globals.node,
  ...globals.es2021,
};

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
  // TypeScript source files
  {
    files: ['**/*.ts'],
    plugins: {
      '@typescript-eslint': tsPlugin,
      prettier: prettierPlugin,
    },
    languageOptions: {
      parser: tsParser,
      parserOptions: { ecmaVersion: 2022, sourceType: 'module' },
      globals: sharedGlobals,
    },
    rules: { ...tsRules, ...sharedRules },
  },
  // Vue SFCs — all use <script lang="ts">
  {
    files: ['**/*.vue'],
    plugins: {
      '@typescript-eslint': tsPlugin,
      prettier: prettierPlugin,
    },
    languageOptions: {
      // eslint-plugin-vue ships vue-eslint-parser as its script block parser
      parser: (pluginVue.processors as any)['.vue'].parser,
      parserOptions: {
        parser: tsParser,
        ecmaVersion: 2022,
        sourceType: 'module',
      },
      globals: sharedGlobals,
    },
    rules: { ...tsRules, ...sharedRules },
  },
  // Test files — declare vitest globals
  {
    files: ['**/*.test.ts'],
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
