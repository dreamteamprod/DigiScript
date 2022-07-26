const { defineConfig } = require('@vue/cli-service');
const path = require('path');
const webpack = require('webpack');

module.exports = defineConfig({
  transpileDependencies: true,
  outputDir: '../server/static/',
  assetsDir: './assets',
  indexPath: '../public/index.html',
  configureWebpack: {
    resolve: {
      extensions: ['', '.js'],
      alias: {
        utils: path.resolve(__dirname, './src/utils'),
      },
    },
    plugins: [
      new webpack.ProvidePlugin({
        utils: 'utils',
      }),
    ],
  },
});
