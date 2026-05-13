import js from '@eslint/js';
import globals from 'globals';
import prettierConfig from 'eslint-config-prettier';
import prettierPlugin from 'eslint-plugin-prettier';
import tsPlugin from '@typescript-eslint/eslint-plugin';
import tsParser from '@typescript-eslint/parser';

const sharedRules = {
  'prettier/prettier': 'error',
  ...prettierConfig.rules,
  'max-len': 'off',
  'no-plusplus': 'off',
};

const tsRules = {
  ...sharedRules,
  '@typescript-eslint/no-explicit-any': 'off',
  '@typescript-eslint/no-unused-vars': 'warn',
  // TypeScript handles undefined-variable checks; no-undef causes false positives
  // on TS-specific constructs (namespaces, declare global, etc.)
  'no-undef': 'off',
};

export default [
  {
    ignores: ['**/node_modules/**', '**/out/**', '**/dist/**', '*.backup'],
  },
  js.configs.recommended,
  // ESM TypeScript files (main process + services)
  {
    files: ['**/*.ts'],
    plugins: {
      prettier: prettierPlugin,
      '@typescript-eslint': tsPlugin,
    },
    languageOptions: {
      parser: tsParser,
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: {
        ...globals.node,
        ...globals.es2021,
      },
    },
    rules: tsRules,
  },
  // CommonJS TypeScript files (preload must be CJS when sandbox is enabled)
  {
    files: ['**/*.cts'],
    plugins: {
      prettier: prettierPlugin,
      '@typescript-eslint': tsPlugin,
    },
    languageOptions: {
      parser: tsParser,
      ecmaVersion: 2022,
      sourceType: 'commonjs',
      globals: {
        ...globals.node,
        ...globals.es2021,
      },
    },
    rules: tsRules,
  },
];
