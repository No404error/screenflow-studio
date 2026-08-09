<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useI18n } from '@/i18n'
import { useEscapeKey } from '@/composables/useEscapeKey'
import { useUiStore } from '@/stores/ui'

const { t } = useI18n()
const ui = useUiStore()

const promptValue = ref('')
const selectedId = ref<string | null>(null)
const inputEl = ref<HTMLInputElement | null>(null)

const d = computed(() => ui.dialog)

watch(
  () => ui.dialog,
  async (dlg) => {
    if (!dlg) return
    if (dlg.kind === 'prompt') {
      promptValue.value = dlg.initial ?? ''
      await nextTick()
      inputEl.value?.focus()
      inputEl.value?.select()
    } else if (dlg.kind === 'select') {
      selectedId.value = dlg.options[0]?.id ?? null
      await nextTick()
    }
  },
)

useEscapeKey(() => {
  if (!ui.dialog) return false
  cancel()
  return true
})

function cancel() {
  const dlg = ui.dialog
  if (!dlg) return
  if (dlg.kind === 'alert') ui.answerAlert()
  else if (dlg.kind === 'confirm') ui.answerConfirm(false)
  else if (dlg.kind === 'prompt') ui.answerPrompt(null)
  else ui.answerSelect(null)
}

function confirmPrimary() {
  const dlg = ui.dialog
  if (!dlg) return
  if (dlg.kind === 'alert') {
    ui.answerAlert()
    return
  }
  if (dlg.kind === 'confirm') {
    ui.answerConfirm(true)
    return
  }
  if (dlg.kind === 'prompt') {
    if (!promptValue.value.trim()) return
    ui.answerPrompt(promptValue.value)
    return
  }
  if (dlg.kind === 'select') {
    if (!selectedId.value) return
    ui.answerSelect(selectedId.value)
  }
}

function onPromptKey(e: KeyboardEvent) {
  if (e.key === 'Enter') {
    e.preventDefault()
    confirmPrimary()
  }
}

function pickOption(id: string) {
  selectedId.value = id
}

function pickAndConfirm(id: string) {
  selectedId.value = id
  confirmPrimary()
}

function onDialogKey(e: KeyboardEvent) {
  if (e.key !== 'Enter') return
  const dlg = ui.dialog
  if (!dlg || dlg.kind === 'prompt') return
  if (dlg.kind === 'select' && !selectedId.value) return
  e.preventDefault()
  confirmPrimary()
}

const promptCanSubmit = computed(() => {
  if (d.value?.kind !== 'prompt') return false
  return promptValue.value.trim().length > 0
})

const selectCanSubmit = computed(() => {
  if (d.value?.kind !== 'select') return false
  return !!selectedId.value && d.value.options.length > 0
})
</script>

<template>
  <Teleport to="body">
    <div
      v-if="d"
      class="mask"
      @click.self="cancel"
      @keydown="onDialogKey"
    >
      <div
        class="dialog sf-panel"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="'sf-app-dialog-title'"
      >
        <header>
          <h3 id="sf-app-dialog-title">{{ d.title }}</h3>
          <button type="button" class="sf-btn sf-btn-ghost" :aria-label="t('cancel')" @click="cancel">
            ×
          </button>
        </header>

        <div
          v-if="
            d.kind === 'alert' ||
            d.kind === 'prompt' ||
            d.kind === 'select' ||
            (d.kind === 'confirm' && (d.message || d.warn))
          "
          class="body"
        >
          <p v-if="d.kind === 'alert'" class="msg">{{ d.message }}</p>
          <template v-else-if="d.kind === 'confirm'">
            <p v-if="d.message" class="msg">{{ d.message }}</p>
            <p v-if="d.warn" class="warn">{{ d.warn }}</p>
          </template>
          <template v-else-if="d.kind === 'prompt'">
            <p v-if="d.message" class="msg">{{ d.message }}</p>
            <input
              ref="inputEl"
              v-model="promptValue"
              class="sf-input"
              type="text"
              :placeholder="d.placeholder || ''"
              @keydown="onPromptKey"
            />
          </template>
          <template v-else-if="d.kind === 'select'">
            <p v-if="d.message" class="msg">{{ d.message }}</p>
            <p v-if="!d.options.length" class="empty">{{ t('dialog_empty_options') }}</p>
            <ul v-else class="opts" role="listbox">
              <li v-for="opt in d.options" :key="opt.id">
                <button
                  type="button"
                  class="opt"
                  role="option"
                  :aria-selected="selectedId === opt.id"
                  :class="{ on: selectedId === opt.id }"
                  @click="pickOption(opt.id)"
                  @dblclick="pickAndConfirm(opt.id)"
                >
                  <span>{{ opt.label }}</span>
                  <span v-if="opt.label !== opt.id" class="sf-mono dim">{{ opt.id }}</span>
                </button>
              </li>
            </ul>
          </template>
        </div>

        <footer class="sf-dialog-foot foot">
          <template v-if="d.kind === 'alert'">
            <button type="button" class="sf-btn sf-btn-primary" @click="confirmPrimary">
              {{ t('dialog_got_it') }}
            </button>
          </template>
          <template v-else-if="d.kind === 'confirm'">
            <button type="button" class="sf-btn" @click="cancel">{{ t('cancel') }}</button>
            <button
              type="button"
              class="sf-btn"
              :class="d.danger ? 'sf-btn-danger' : 'sf-btn-primary'"
              @click="confirmPrimary"
            >
              {{ d.confirmLabel || t('ok') }}
            </button>
          </template>
          <template v-else-if="d.kind === 'prompt'">
            <button type="button" class="sf-btn" @click="cancel">{{ t('cancel') }}</button>
            <button
              type="button"
              class="sf-btn sf-btn-primary"
              :disabled="!promptCanSubmit"
              @click="confirmPrimary"
            >
              {{ t('ok') }}
            </button>
          </template>
          <template v-else-if="d.kind === 'select'">
            <button type="button" class="sf-btn" @click="cancel">
              {{ d.options.length ? t('cancel') : t('dialog_got_it') }}
            </button>
            <button
              v-if="d.options.length"
              type="button"
              class="sf-btn sf-btn-primary"
              :disabled="!selectCanSubmit"
              @click="confirmPrimary"
            >
              {{ t('ok') }}
            </button>
          </template>
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.mask {
  position: fixed;
  inset: 0;
  z-index: 58;
  background: rgb(26 34 32 / 45%);
  display: grid;
  place-items: center;
  padding: 1rem;
}
.dialog {
  width: min(26rem, 96vw);
  max-height: min(85vh, 640px);
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
  box-shadow: 0 12px 40px rgb(26 34 32 / 22%);
}
.dialog:has(.opts) {
  width: min(28rem, 96vw);
}
header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--sf-line);
  flex-shrink: 0;
}
h3 {
  margin: 0;
  font-size: var(--sf-fs-lg);
  font-weight: 600;
  color: var(--sf-ink);
  line-height: 1.3;
  overflow-wrap: anywhere;
}
.body {
  padding: 1rem 1.25rem;
  overflow: auto;
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.msg {
  margin: 0;
  font-size: var(--sf-fs-sm);
  color: var(--sf-ink-muted);
  line-height: var(--sf-lh);
}
.warn {
  margin: 0;
  font-size: var(--sf-fs-sm);
  color: var(--sf-warn);
  background: var(--sf-warn-soft);
  border-radius: var(--sf-radius);
  padding: 0.55rem 0.7rem;
  line-height: var(--sf-lh);
}
.empty {
  margin: 0;
  font-size: var(--sf-fs-sm);
  color: var(--sf-ink-faint);
}
.opts {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  max-height: 16rem;
  overflow: auto;
}
.opt {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.1rem;
  text-align: left;
  border: 1px solid var(--sf-line);
  background: var(--sf-surface);
  border-radius: var(--sf-radius);
  padding: 0.5rem 0.65rem;
  cursor: pointer;
  font: inherit;
  color: var(--sf-ink);
}
.opt:hover {
  background: var(--sf-surface-2);
}
.opt.on {
  border-color: var(--sf-accent);
  background: var(--sf-accent-soft);
}
.dim {
  font-size: var(--sf-fs-xs);
  color: var(--sf-ink-faint);
}
.foot {
  margin-top: 0;
  border-top: 1px solid var(--sf-line);
  padding: 0.65rem 1rem;
  flex-shrink: 0;
}
</style>
