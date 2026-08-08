import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import I18nText from './components/I18nText.vue'
import './styles/global.css'

const app = createApp(App)
app.component('I18nText', I18nText)
app.use(createPinia())
app.use(router)
app.mount('#app')
