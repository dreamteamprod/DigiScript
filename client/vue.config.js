const { defineConfig } = require('@vue/cli-service');

module.exports = defineConfig({
  transpileDependencies: true,
  outputDir: '../server/static/',
  assetsDir: './assets',
  indexPath: '../public/index.html'
});
