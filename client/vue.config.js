/* eslint-disable no-param-reassign */

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
        utils: path.resolve(__dirname, './src/js/utils'),
      },
    },
    plugins: [
      new webpack.ProvidePlugin({
        utils: 'utils',
      }),
      new webpack.ProvidePlugin({
        $: 'jquery',
        jQuery: 'jquery',
      }),
    ],
  },
  chainWebpack: (config) => {
    config.module
      .rule('vue')
      .use('vue-loader')
      .loader('vue-loader')
      .tap((options) => {
        options.transformAssetUrls = {
          img: 'src',
          image: 'xlink:href',
          'b-avatar': 'src',
          'b-img': 'src',
          'b-img-lazy': ['src', 'blank-src'],
          'b-card': 'img-src',
          'b-card-img': 'src',
          'b-card-img-lazy': ['src', 'blank-src'],
          'b-carousel-slide': 'img-src',
          'b-embed': 'src',
        };
        return options;
      });
  },
});
