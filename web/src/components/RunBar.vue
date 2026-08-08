<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from '@/i18n'
import { useRunStore } from '@/stores/run'
import { useUiStore } from '@/stores/ui'

const { t } = useI18n()
const run = useRunStore()
const ui = useUiStore()

const label = computed(() => {
  const s = run.status
  const parts = [s.mode || 'idle']
  if (s.page_label || s.page_id) parts.push(String(s.page_label || s.page_id))
  if (s.state) parts.push(String(s.state))
  if (s.sticky) parts.push(`post:${s.post_mode || '?'}`)
  const n = Object.keys(s.vars || {}).length
  parts.push(`vars ${n}`)
  return parts.join(' · ')
})

async function onStart() {
  try {
    await run.start()
  } catch (e) {
    ui.showToast(String(e))
  }
}
</script>

<template>
  <footer class="runbar">
    <button class="summary" @click="ui.drawerOpen = !ui.drawerOpen">
      <span class="dot" :class="run.mode" />
      <span class="sf-mono">{{ label }}</span>
    </button>
    <div class="actions">
      <button v-if="!run.isActive" class="sf-btn sf-btn-primary" @click="onStart">{{ t('start') }}</button>
      <button v-if="run.isRunning" class="sf-btn" @click="run.pause()">{{ t('pause') }}</button>
      <button v-if="run.isPaused" class="sf-btn" @click="run.resume()">{{ t('resume') }}</button>
      <button v-if="run.isActive" class="sf-btn sf-btn-danger" @click="run.stop()">{{ t('stop') }}</button>
      <button class="sf-btn sf-btn-ghost" @click="ui.drawerOpen = !ui.drawerOpen">▾</button>
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
.dot.paused {
  background: #f0b429;
}
.actions {
  display: flex;
  gap: 0.35rem;
  flex-shrink: 0;
}
.actions .sf-btn {
  padding: 0.25rem 0.65rem;
  font-size: var(--sf-fs-sm);
}
</style>
