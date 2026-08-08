import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api, type SettingsDTO } from '@/api/client'
import { setI18nLang } from '@/i18n'
import type { NavSelection } from '@/types/project'

export const useUiStore = defineStore('ui', () => {
  /** Session / server-backed UI (lang, recent, selection). Layout prefs → usePrefsStore. */
  const selection = ref<NavSelection>({ kind: 'welcome' })
  const recent = ref<{ path: string; name: string }[]>([])
  const lang = ref('en')
  const toast = ref('')
  const reopenLast = ref(true)
  const reopenPath = ref<string | null>(null)
  const pageWizardOpen = ref(false)
  const unsavedPrompt = ref<null | { resolve: (v: 'save' | 'discard' | 'cancel') => void }>(null)

  function select(sel: NavSelection) {
    selection.value = sel
  }

  function showToast(msg: string) {
    toast.value = msg
    setTimeout(() => {
      if (toast.value === msg) toast.value = ''
    }, 2800)
  }

  async function loadSettings(): Promise<SettingsDTO> {
    const s = await api.settings()
    lang.value = s.lang || 'en'
    setI18nLang(lang.value)
    // Ensure API validator language matches UI (Issues panel).
    if (lang.value === 'en' || lang.value === 'zh') {
      try {
        await api.setLang(lang.value)
      } catch {
        /* ignore */
      }
    }
    recent.value = s.recent || []
    reopenLast.value = s.reopen_last_project !== false
    reopenPath.value = s.reopen_path || null
    return s
  }

  async function setLang(l: string) {
    await api.setLang(l)
    lang.value = l
    setI18nLang(l)
  }

  async function clearRecent() {
    const s = await api.clearRecent()
    recent.value = s.recent || []
  }

  function askUnsaved(): Promise<'save' | 'discard' | 'cancel'> {
    return new Promise((resolve) => {
      unsavedPrompt.value = { resolve }
    })
  }

  function answerUnsaved(v: 'save' | 'discard' | 'cancel') {
    unsavedPrompt.value?.resolve(v)
    unsavedPrompt.value = null
  }

  return {
    selection,
    recent,
    lang,
    toast,
    reopenLast,
    reopenPath,
    pageWizardOpen,
    unsavedPrompt,
    select,
    showToast,
    loadSettings,
    setLang,
    clearRecent,
    askUnsaved,
    answerUnsaved,
  }
})
