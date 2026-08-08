<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from '@/i18n'

const props = defineProps<{
  src: string
  roi: number[] | null
}>()
const emit = defineEmits<{ close: []; save: [number[] | null] }>()

const { t } = useI18n()
const y0 = ref(0)
const y1 = ref(1)
const x0 = ref(0)
const x1 = ref(1)

onMounted(() => {
  if (props.roi && props.roi.length === 4) {
    ;[y0.value, y1.value, x0.value, x1.value] = props.roi
  }
})

function save() {
  const roi = [
    Math.min(y0.value, y1.value),
    Math.max(y0.value, y1.value),
    Math.min(x0.value, x1.value),
    Math.max(x0.value, x1.value),
  ]
  emit('save', roi)
}

function clear() {
  emit('save', null)
}
</script>

<template>
  <div class="mask" @click.self="emit('close')">
    <div class="dialog sf-panel">
      <h3 class="sf-section-title">{{ t('roi') }}</h3>
      <p class="hint">Normalized [y0, y1, x0, x1] in 0–1 of screen.</p>
      <img :src="src" alt="asset" />
      <div class="grid">
        <label>y0 <input v-model.number="y0" class="sf-input" type="number" step="0.01" min="0" max="1" /></label>
        <label>y1 <input v-model.number="y1" class="sf-input" type="number" step="0.01" min="0" max="1" /></label>
        <label>x0 <input v-model.number="x0" class="sf-input" type="number" step="0.01" min="0" max="1" /></label>
        <label>x1 <input v-model.number="x1" class="sf-input" type="number" step="0.01" min="0" max="1" /></label>
      </div>
      <div class="actions">
        <button class="sf-btn" type="button" @click="clear">{{ t('clear_roi') }}</button>
        <button class="sf-btn" type="button" @click="emit('close')">Cancel</button>
        <button class="sf-btn sf-btn-primary" type="button" @click="save">OK</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.mask {
  position: fixed;
  inset: 0;
  background: rgb(26 34 32 / 45%);
  display: grid;
  place-items: center;
  z-index: 40;
}
.dialog {
  width: min(420px, 92vw);
  padding: var(--sf-space-4);
}
img {
  width: 100%;
  max-height: 180px;
  object-fit: contain;
  background: #111;
  border-radius: var(--sf-radius);
  margin-bottom: var(--sf-space-3);
}
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--sf-space-2);
  margin-bottom: var(--sf-space-3);
}
.hint {
  font-size: var(--sf-fs-sm);
  color: var(--sf-ink-muted);
}
.actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--sf-space-2);
}
</style>
