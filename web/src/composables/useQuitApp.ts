import { api } from '@/api/client'
import { useI18n } from '@/i18n'
import { useProjectStore } from '@/stores/project'
import { useRunStore } from '@/stores/run'
import { useUiStore } from '@/stores/ui'

/** Confirm, flush dirty/engine, then shut down the local ScreenFlow host. */
export function useQuitApp() {
  const { t } = useI18n()
  const ui = useUiStore()
  const project = useProjectStore()
  const run = useRunStore()

  async function quitApp(): Promise<boolean> {
    const ok = await ui.askConfirm({
      title: t('quit_title'),
      message: t('quit_body'),
      warn: t('quit_warn'),
      danger: true,
      confirmLabel: t('quit_confirm'),
    })
    if (!ok) return false

    if (project.hasProject && !(await project.confirmLeaveIfDirty())) {
      return false
    }

    try {
      if (run.isActive) await run.stop()
    } catch {
      /* still attempt shutdown */
    }

    try {
      await api.setEditorState({ dirty: false })
      await api.shutdownApp({ force: true })
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      ui.showToast(msg, 'danger')
      return false
    }

    ui.appExited = true
    return true
  }

  return { quitApp }
}
