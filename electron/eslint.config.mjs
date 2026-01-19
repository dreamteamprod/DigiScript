import js from '@eslint/js';
import globals from 'globals';
import prettierConfig from 'eslint-config-prettier';
import prettierPlugin from 'eslint-plugin-prettier';

export default [
  {
    ignores: [
      '**/node_modules/**',
      '**/out/**',
      '**/dist/**',
      '*.backup',
    ],
  },
  js.configs.recommended,
  {
    files: ['**/*.js'],
    plugins: {
      prettier: prettierPlugin,
    },
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: {
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
      'no-unused-vars': 'warn',
      'no-plusplus': 'off',
    },
  },
];
