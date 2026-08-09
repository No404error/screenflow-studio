<script setup lang="ts">
import { onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api/client'
import { t as translate } from '@/i18n'
import { useUiStore } from '@/stores/ui'
import { usePrefsStore } from '@/stores/prefs'
import { useRunStore } from '@/stores/run'
import { useProjectStore } from '@/stores/project'
import AppDialogHost from '@/components/AppDialogHost.vue'

const ui = useUiStore()
const prefs = usePrefsStore()
const run = useRunStore()
const project = useProjectStore()
const router = useRouter()
let didAutoReopen = false

watch(
  () => project.dirty,
  (dirty) => {
    if (ui.appExited) return
    void api.setEditorState({ dirty: Boolean(dirty) }).catch(() => {})
  },
  { immediate: true },
)

function onKey(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'b') {
    e.preventDefault()
    prefs.toggleNav()
  }
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
    e.preventDefault()
    const p = useProjectStore()
    if (p.hasProject) void p.save()
  }
}

/** Prevent accidental wheel changes on number inputs / selects (Win Studio parity). */
function onWheelCapture(e: WheelEvent) {
  const el = e.target as HTMLElement | null
  if (!el) return
  const tag = el.tagName
  if (tag === 'SELECT') {
    e.preventDefault()
    return
  }
  if (tag === 'INPUT' && (el as HTMLInputElement).type === 'number') {
    e.preventDefault()
  }
}

onMounted(async () => {
  const s = await ui.loadSettings()
  if (s.runner_mode === 'elevate' || s.runner_mode === 'inline') {
    run.runnerMode = s.runner_mode
  }
  run.connect()
  window.addEventListener('keydown', onKey)
  document.addEventListener('wheel', onWheelCapture, { capture: true, passive: false })
  if (!didAutoReopen && s.reopen_last_project !== false && s.reopen_path && !useProjectStore().hasProject) {
    didAutoReopen = true
    try {
      await useProjectStore().open(s.reopen_path)
      await router.push('/studio')
    } catch {
      /* ignore */
    }
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKey)
  document.removeEventListener('wheel', onWheelCapture, true)
})

function toastText(msg: string) {
  const mapped = translate(msg)
  return mapped !== msg ? mapped : msg
}
</script>

<template>
  <div v-if="ui.appExited" class="exited">
    <p class="exited-brand"><I18nText k="app_name" /></p>
    <h1><I18nText k="quit_done_title" /></h1>
    <p class="exited-sub"><I18nText k="quit_done_body" /></p>
  </div>
  <template v-else>
    <router-view />
    <AppDialogHost />
    <div v-if="ui.toast" class="toast" :class="ui.toastSeverity">{{ toastText(ui.toast) }}</div>
  </template>
</template>

<style scoped>
.exited {
  min-height: 100%;
  display: grid;
  place-content: center;
  gap: 0.5rem;
  padding: 2rem;
  text-align: center;
  background:
    radial-gradient(900px 480px at 12% -10%, #cfe8e6 0%, transparent 55%),
    linear-gradient(165deg, #f7faf8 0%, var(--sf-paper) 55%, #e8efec 100%);
}
.exited-brand {
  margin: 0;
  font-size: var(--sf-fs-hero);
  font-weight: 700;
  letter-spacing: -0.04em;
  color: var(--sf-ink);
}
.exited h1 {
  margin: 0;
  font-size: var(--sf-fs-xl);
  font-weight: 600;
}
.exited-sub {
  margin: 0;
  color: var(--sf-ink-muted);
  max-width: 28rem;
}
.toast {
  position: fixed;
  bottom: calc(var(--sf-runbar-h) + 16px);
  left: 50%;
  transform: translateX(-50%);
  background: var(--sf-ink);
  color: #fff;
  padding: 0.5rem 1rem;
  border-radius: var(--sf-radius);
  font-size: var(--sf-fs-sm);
  z-index: 50;
  max-width: min(90vw, 420px);
  text-align: center;
  animation: fade 0.2s ease;
  box-shadow: inset 3px 0 0 transparent;
}
.toast.danger {
  box-shadow: inset 3px 0 0 var(--sf-danger);
}
.toast.ok {
  box-shadow: inset 3px 0 0 var(--sf-ok);
}
@keyframes fade {
  from {
    opacity: 0;
    transform: translate(-50%, 6px);
  }
  to {
    opacity: 1;
    transform: translate(-50%, 0);
  }
}
</style>
