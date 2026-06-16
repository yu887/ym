
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

const app = createApp(App)

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(router)
app.use(ElementPlus)
app.mount('#app')

const resizeObserverErrorHandler = (e) => {
  if (e.message && e.message.includes('ResizeObserver loop')) {
    console.warn('ResizeObserver警告已自动忽略')
    e.stopPropagation && e.stopPropagation()
  }
}

if (typeof ResizeObserver !== 'undefined') {
  const OriginalResizeObserver = ResizeObserver
  window.ResizeObserver = function(callback) {
    const wrappedCallback = (entries, observer) => {
      try {
        callback(entries, observer)
      } catch (e) {
        resizeObserverErrorHandler(e)
      }
    }
    return new OriginalResizeObserver(wrappedCallback)
  }
  window.ResizeObserver.prototype = OriginalResizeObserver.prototype
}

if (typeof window.addEventListener === 'function') {
  window.addEventListener('error', resizeObserverErrorHandler, true)
  window.addEventListener('unhandledrejection', (e) => {
    if (e.reason && e.reason.message && e.reason.message.includes('ResizeObserver loop')) {
      console.warn('ResizeObserver警告已自动忽略')
      e.preventDefault()
    }
  })
}

