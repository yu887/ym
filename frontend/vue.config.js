const { defineConfig } = require('@vue/cli-service')
module.exports = defineConfig({
  configureWebpack: {
    devServer: {
      client: {
        overlay: false
      }
    }
  }
})