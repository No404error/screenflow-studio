import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/api/client'
import { setI18nLang } from '@/i18n'
import type { NavSelection } from '@/types/project'

export const useUiStore = defineStore('ui', () => {
  const navCollapsed = ref(false)
  const drawerOpen = ref(false)
  const drawerTab = ref<'controls' | 'vars' | 'logs'>('controls')
  const selection = ref<NavSelection>({ kind: 'welcome' })
  const recent = ref<{ path: string; name: string }[]>([])
  const lang = ref('en')
  const toast = ref('')

  function toggleNav() {
    navCollapsed.value = !navCollapsed.value
  }

  function select(sel: NavSelection) {
    selection.value = sel
  }

  function showToast(msg: string) {
    toast.value = msg
    setTimeout(() => {
      if (toast.value === msg) toast.value = ''
    }, 2200)
  }

  async function loadSettings() {
    const s = await api.settings()
    lang.value = s.lang || 'en'
    setI18nLang(lang.value)
    recent.value = s.recent || []
  }

  async function setLang(l: string) {
    await api.setLang(l)
    lang.value = l
    setI18nLang(l)
  }

  return {
    navCollapsed,
    drawerOpen,
    drawerTab,
    selection,
    recent,
    lang,
    toast,
    toggleNav,
    select,
    showToast,
    loadSettings,
    setLang,
  }
})
