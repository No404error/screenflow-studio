import { createRouter, createWebHistory } from 'vue-router'
import WelcomeView from '@/views/WelcomeView.vue'
import StudioShell from '@/layouts/StudioShell.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'welcome', component: WelcomeView },
    {
      path: '/studio',
      name: 'studio',
      component: StudioShell,
    },
  ],
})

export default router
