<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { t as translate } from '@/i18n'
import { useUiStore } from '@/stores/ui'
import { usePrefsStore } from '@/stores/prefs'
import { useRunStore } from '@/stores/run'
import { useProjectStore } from '@/stores/project'

const ui = useUiStore()
const prefs = usePrefsStore()
const run = useRunStore()
const router = useRouter()
let didAutoReopen = false

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
  <router-view />
  <div v-if="ui.toast" class="toast">{{ toastText(ui.toast) }}</div>
</template>

<style scoped>
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
