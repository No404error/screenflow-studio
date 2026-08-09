import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api, type SettingsDTO } from '@/api/client'
import { setI18nLang } from '@/i18n'
import type { NavSelection } from '@/types/project'

export type ToastSeverity = 'info' | 'danger' | 'ok'

export type DialogSelectOption = { id: string; label: string }

export type AppDialog =
  | {
      kind: 'alert'
      title: string
      message: string
      resolve: () => void
    }
  | {
      kind: 'confirm'
      title: string
      message?: string
      warn?: string
      danger?: boolean
      confirmLabel?: string
      resolve: (v: boolean) => void
    }
  | {
      kind: 'prompt'
      title: string
      message?: string
      initial?: string
      placeholder?: string
      resolve: (v: string | null) => void
    }
  | {
      kind: 'select'
      title: string
      message?: string
      options: DialogSelectOption[]
      resolve: (v: string | null) => void
    }

export type AskAlertOpts = { title: string; message: string }
export type AskConfirmOpts = {
  title: string
  message?: string
  warn?: string
  danger?: boolean
  confirmLabel?: string
}
export type AskPromptOpts = {
  title: string
  message?: string
  initial?: string
  placeholder?: string
}
export type AskSelectOpts = {
  title: string
  message?: string
  options: DialogSelectOption[]
}

export const useUiStore = defineStore('ui', () => {
  /** Session / server-backed UI (lang, recent, selection). Layout prefs → usePrefsStore. */
  const selection = ref<NavSelection>({ kind: 'welcome' })
  const recent = ref<{ path: string; name: string }[]>([])
  const lang = ref('en')
  const toast = ref('')
  const toastSeverity = ref<ToastSeverity>('info')
  const reopenLast = ref(true)
  const reopenPath = ref<string | null>(null)
  const pageWizardOpen = ref(false)
  /** Local host process has exited; show a static “you can close this tab” screen. */
  const appExited = ref(false)
  const unsavedPrompt = ref<null | { resolve: (v: 'save' | 'discard' | 'cancel') => void }>(null)
  const dialog = ref<AppDialog | null>(null)

  function select(sel: NavSelection) {
    selection.value = sel
  }

  function showToast(msg: string, severity: ToastSeverity = 'info') {
    toast.value = msg
    toastSeverity.value = severity
    setTimeout(() => {
      if (toast.value === msg) {
        toast.value = ''
        toastSeverity.value = 'info'
      }
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

  async function removeRecent(path: string) {
    const s = await api.removeRecent(path)
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

  function dismissDialog() {
    const d = dialog.value
    if (!d) return
    if (d.kind === 'alert') d.resolve()
    else if (d.kind === 'confirm') d.resolve(false)
    else d.resolve(null)
    dialog.value = null
  }

  function askAlert(opts: AskAlertOpts): Promise<void> {
    dismissDialog()
    return new Promise((resolve) => {
      dialog.value = { kind: 'alert', ...opts, resolve }
    })
  }

  function askConfirm(opts: AskConfirmOpts): Promise<boolean> {
    dismissDialog()
    return new Promise((resolve) => {
      dialog.value = { kind: 'confirm', ...opts, resolve }
    })
  }

  function askPrompt(opts: AskPromptOpts): Promise<string | null> {
    dismissDialog()
    return new Promise((resolve) => {
      dialog.value = { kind: 'prompt', ...opts, resolve }
    })
  }

  function askSelect(opts: AskSelectOpts): Promise<string | null> {
    dismissDialog()
    return new Promise((resolve) => {
      dialog.value = { kind: 'select', ...opts, resolve }
    })
  }

  function answerAlert() {
    if (dialog.value?.kind !== 'alert') return
    dialog.value.resolve()
    dialog.value = null
  }

  function answerConfirm(v: boolean) {
    if (dialog.value?.kind !== 'confirm') return
    dialog.value.resolve(v)
    dialog.value = null
  }

  function answerPrompt(v: string | null) {
    if (dialog.value?.kind !== 'prompt') return
    dialog.value.resolve(v)
    dialog.value = null
  }

  function answerSelect(v: string | null) {
    if (dialog.value?.kind !== 'select') return
    dialog.value.resolve(v)
    dialog.value = null
  }

  return {
    selection,
    recent,
    lang,
    toast,
    toastSeverity,
    reopenLast,
    reopenPath,
    pageWizardOpen,
    appExited,
    unsavedPrompt,
    dialog,
    select,
    showToast,
    loadSettings,
    setLang,
    clearRecent,
    removeRecent,
    askUnsaved,
    answerUnsaved,
    askAlert,
    askConfirm,
    askPrompt,
    askSelect,
    answerAlert,
    answerConfirm,
    answerPrompt,
    answerSelect,
    dismissDialog,
  }
})
