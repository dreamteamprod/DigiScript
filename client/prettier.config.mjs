/**
 * Prettier configuration for DigiScript frontend
 * Based on Vue.js community recommendations
 * @see https://prettier.io/docs/en/configuration.html
 * @see https://vuejs.org/style-guide/
 */
export default {
  // Standard Prettier defaults with Vue community preferences
  printWidth: 100,
  tabWidth: 2,
  useTabs: false,
  semi: true,
  singleQuote: true,
  quoteProps: 'as-needed',
  trailingComma: 'es5',
  bracketSpacing: true,
  bracketSameLine: false,
  arrowParens: 'always',
  endOfLine: 'lf',

  // Vue-specific options
  vueIndentScriptAndStyle: false, // Don't indent <script> and <style> tags
  singleAttributePerLine: false, // Allow multiple attributes per line (Vue default)

  // File-specific overrides
  overrides: [
    {
      files: '*.vue',
      options: {
        parser: 'vue',
      },
    },
    {
      files: ['*.json', '.prettierrc'],
      options: {
        printWidth: 80,
      },
    },
  ],
};