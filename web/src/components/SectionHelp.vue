<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from '@/i18n'
import { useEscapeKey } from '@/composables/useEscapeKey'

const props = defineProps<{
  helpKey: string
}>()

const { t } = useI18n()
const open = ref(false)

const text = computed(() => {
  const raw = t(props.helpKey)
  return raw === props.helpKey ? t('help_missing') : raw
})

const title = computed(() => t('help_dialog_title'))

function toggle() {
  open.value = !open.value
}

function close() {
  open.value = false
}

useEscapeKey(() => {
  if (!open.value) return false
  close()
  return true
})
</script>

<template>
  <span class="wrap">
    <button
      type="button"
      class="q"
      :title="t('help_button_a11y')"
      :aria-label="t('help_button_a11y')"
      :aria-expanded="open"
      @click.stop="toggle"
    >
      ?
    </button>
    <Teleport to="body">
      <div v-if="open" class="mask" @click.self="close">
        <div class="dialog sf-panel" role="dialog" :aria-label="title">
          <header>
            <h3>{{ title }}</h3>
            <button type="button" class="sf-btn sf-btn-ghost" @click="close">×</button>
          </header>
          <pre class="body">{{ text }}</pre>
          <footer>
            <button type="button" class="sf-btn sf-btn-primary" @click="close">{{ t('ok') }}</button>
          </footer>
        </div>
      </div>
    </Teleport>
  </span>
</template>

<style scoped>
.wrap {
  display: inline-flex;
  vertical-align: middle;
  margin-left: 0.35rem;
}
.q {
  width: 1.25rem;
  height: 1.25rem;
  border-radius: 50%;
  border: 1px solid var(--sf-line-strong);
  background: var(--sf-surface);
  color: var(--sf-ink-muted);
  font-size: 0.72rem;
  font-weight: 700;
  line-height: 1;
  padding: 0;
  cursor: help;
  transition: color 0.15s ease, border-color 0.15s ease;
}
.q:hover {
  color: var(--sf-accent);
  border-color: var(--sf-accent);
}
.mask {
  position: fixed;
  inset: 0;
  background: rgb(26 34 32 / 45%);
  display: grid;
  place-items: center;
  z-index: 60;
  padding: 1rem;
}
.dialog {
  width: min(640px, 96vw);
  max-height: min(85vh, 720px);
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
}
header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--sf-line);
  flex-shrink: 0;
}
h3 {
  margin: 0;
  font-size: var(--sf-fs-md);
}
.body {
  margin: 0;
  padding: 1rem 1.25rem;
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: break-word;
  font-family: var(--sf-font);
  font-size: var(--sf-fs-sm);
  line-height: 1.6;
  color: var(--sf-ink);
}
footer {
  display: flex;
  justify-content: flex-end;
  padding: 0.65rem 1rem;
  border-top: 1px solid var(--sf-line);
  flex-shrink: 0;
}
</style>
