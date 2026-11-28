import type { Config } from 'prettier';

const config: Config = {
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

  vueIndentScriptAndStyle: false,
  singleAttributePerLine: false,

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

export default config;
