<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from '@/i18n'
import { useRunStore } from '@/stores/run'
import { usePrefsStore } from '@/stores/prefs'
import { useUiStore } from '@/stores/ui'

const { t } = useI18n()
const run = useRunStore()
const prefs = usePrefsStore()
const ui = useUiStore()

const postModeLabel = computed(() => {
  const m = String(run.status.post_mode || '')
  const key = `post_mode_${m}` as const
  const mapped = t(key)
  return mapped !== key ? mapped : m || '?'
})

const label = computed(() => {
  const s = run.status
  if (run.isWaitingAdmin) return t('status_waiting_admin')
  const parts: string[] = []
  const mode = s.mode || 'idle'
  if (mode === 'running') parts.push(t('status_running'))
  else if (mode === 'paused') parts.push(t('status_paused'))
  else if (mode === 'waiting_admin') parts.push(t('status_waiting_admin'))
  else parts.push(t('status_idle'))
  if (s.page_label || s.page_id) parts.push(String(s.page_label || s.page_id))
  if (s.state) parts.push(String(s.state))
  if (s.sticky) parts.push(t('status_followup', { mode: postModeLabel.value }))
  const n = Object.keys(s.vars || {}).length
  parts.push(t('status_vars', { n }))
  return parts.join(' · ')
})

async function onStart() {
  try {
    await run.start()
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    ui.showToast(msg === 'validation_failed' || msg === 'Validation failed' ? t('validation_failed') : msg)
  }
}
</script>

<template>
  <footer class="runbar">
    <button class="summary" @click="prefs.toggleDrawer()">
      <span
        class="ws"
        :class="run.connected ? 'on' : 'off'"
        :title="run.connected ? t('connected') : t('disconnected')"
      />
      <span class="dot" :class="run.mode" />
      <span class="sf-mono text" :title="label">{{ label }}</span>
    </button>
    <div class="sf-btn-cluster actions">
      <button v-if="!run.isActive" class="sf-btn sf-btn-primary" @click="onStart"><I18nText k="start" /></button>
      <button v-if="run.isRunning" class="sf-btn" @click="run.pause()"><I18nText k="pause" /></button>
      <button v-if="run.isPaused" class="sf-btn" @click="run.resume()"><I18nText k="resume" /></button>
      <button v-if="run.isActive" class="sf-btn sf-btn-ghost danger" @click="run.stop()"><I18nText k="stop" /></button>
      <button class="sf-btn sf-btn-ghost" @click="prefs.toggleDrawer()">▾</button>
    </div>
  </footer>
</template>

<style scoped>
.runbar {
  height: var(--sf-runbar-h);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sf-space-3);
  padding: 0 var(--sf-space-3);
  background: var(--sf-ink);
  color: #e8eeeb;
  z-index: 10;
}
.summary {
  border: none;
  background: transparent;
  color: inherit;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
  overflow: hidden;
}
.text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ws {
  width: 0.4rem;
  height: 0.4rem;
  border-radius: 50%;
  flex-shrink: 0;
}
.ws.on {
  background: #6ee7b7;
}
.ws.off {
  background: #f87171;
}
.dot {
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 50%;
  background: #8a9692;
}
.dot.running {
  background: #3ecf8e;
  box-shadow: 0 0 0 3px rgb(62 207 142 / 25%);
}
.dot.paused,
.dot.waiting_admin {
  background: #f0b429;
}
.actions {
  flex-shrink: 0;
}
.actions .sf-btn {
  min-height: 1.75rem;
  padding: 0 0.65rem;
  font-size: var(--sf-fs-sm);
}
.actions .sf-btn:not(.sf-btn-primary) {
  background: rgb(255 255 255 / 8%);
  border-color: rgb(255 255 255 / 18%);
  color: #e8eeeb;
}
.actions .sf-btn-ghost {
  background: transparent;
  border-color: transparent;
}
.actions .sf-btn.danger {
  color: #ffb4a9;
}
</style>
