<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from '@/i18n'

const props = defineProps<{
  src: string
  roi: number[] | null
  /** Optional match-content rect on the same image (guide only). */
  contentRoi?: number[] | null
}>()
const emit = defineEmits<{ close: []; save: [number[] | null] }>()

const { t } = useI18n()
const imgRef = ref<HTMLImageElement | null>(null)
const dragging = ref(false)
const start = ref<{ x: number; y: number } | null>(null)
const draft = ref<{ x0: number; y0: number; x1: number; y1: number } | null>(null)

const y0 = ref(0)
const y1 = ref(1)
const x0 = ref(0)
const x1 = ref(1)

function applyRoi(roi: number[] | null) {
  if (roi && roi.length === 4) {
    ;[y0.value, y1.value, x0.value, x1.value] = roi
  } else {
    y0.value = 0
    y1.value = 1
    x0.value = 0
    x1.value = 1
  }
}

onMounted(() => applyRoi(props.roi))
watch(
  () => props.roi,
  (r) => applyRoi(r),
)

const boxStyle = computed(() => {
  const left = Math.min(x0.value, x1.value) * 100
  const top = Math.min(y0.value, y1.value) * 100
  const width = Math.abs(x1.value - x0.value) * 100
  const height = Math.abs(y1.value - y0.value) * 100
  return {
    left: `${left}%`,
    top: `${top}%`,
    width: `${width}%`,
    height: `${height}%`,
  }
})

const contentStyle = computed(() => {
  const r = props.contentRoi
  if (!r || r.length !== 4) return null
  const [cy0, cy1, cx0, cx1] = r
  return {
    left: `${Math.min(cx0, cx1) * 100}%`,
    top: `${Math.min(cy0, cy1) * 100}%`,
    width: `${Math.abs(cx1 - cx0) * 100}%`,
    height: `${Math.abs(cy1 - cy0) * 100}%`,
  }
})

function normFromEvent(ev: MouseEvent) {
  const el = imgRef.value
  if (!el) return null
  const r = el.getBoundingClientRect()
  if (r.width <= 0 || r.height <= 0) return null
  const x = Math.min(1, Math.max(0, (ev.clientX - r.left) / r.width))
  const y = Math.min(1, Math.max(0, (ev.clientY - r.top) / r.height))
  return { x, y }
}

function onDown(ev: MouseEvent) {
  const p = normFromEvent(ev)
  if (!p) return
  dragging.value = true
  start.value = p
  draft.value = { x0: p.x, y0: p.y, x1: p.x, y1: p.y }
  ev.preventDefault()
}

function onMove(ev: MouseEvent) {
  if (!dragging.value || !start.value) return
  const p = normFromEvent(ev)
  if (!p) return
  draft.value = { x0: start.value.x, y0: start.value.y, x1: p.x, y1: p.y }
  x0.value = Math.min(start.value.x, p.x)
  x1.value = Math.max(start.value.x, p.x)
  y0.value = Math.min(start.value.y, p.y)
  y1.value = Math.max(start.value.y, p.y)
}

function onUp() {
  dragging.value = false
  start.value = null
  draft.value = null
}

function save() {
  const roi = [
    Math.min(y0.value, y1.value),
    Math.max(y0.value, y1.value),
    Math.min(x0.value, x1.value),
    Math.max(x0.value, x1.value),
  ]
  if (roi[1] - roi[0] < 0.005 || roi[3] - roi[2] < 0.005) {
    emit('save', null)
    return
  }
  emit('save', roi)
}

function clear() {
  emit('save', null)
}
</script>

<template>
  <div class="mask" @click.self="emit('close')">
    <div class="dialog sf-panel">
      <h3 class="sf-section-title">{{ t('search_region') }}</h3>
      <p class="hint">{{ t('roi_drag_hint') }}</p>
      <div
        class="stage"
        @mousedown="onDown"
        @mousemove="onMove"
        @mouseup="onUp"
        @mouseleave="onUp"
      >
        <img ref="imgRef" :src="src" alt="asset" draggable="false" />
        <div v-if="contentStyle" class="box content" :style="contentStyle" />
        <div class="box" :style="boxStyle" />
      </div>
      <details class="adv">
        <summary>{{ t('advanced') }}</summary>
        <div class="grid">
          <label>y0 <input v-model.number="y0" class="sf-input" type="number" step="0.01" min="0" max="1" /></label>
          <label>y1 <input v-model.number="y1" class="sf-input" type="number" step="0.01" min="0" max="1" /></label>
          <label>x0 <input v-model.number="x0" class="sf-input" type="number" step="0.01" min="0" max="1" /></label>
          <label>x1 <input v-model.number="x1" class="sf-input" type="number" step="0.01" min="0" max="1" /></label>
        </div>
      </details>
      <div class="sf-dialog-foot">
        <button class="sf-btn sf-btn-ghost" type="button" @click="clear">{{ t('clear_roi') }}</button>
        <button class="sf-btn" type="button" @click="emit('close')">{{ t('cancel') }}</button>
        <button class="sf-btn sf-btn-primary" type="button" @click="save">{{ t('ok') }}</button>
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
  width: min(560px, 94vw);
  padding: var(--sf-space-4);
}
.hint {
  color: var(--sf-ink-muted);
  font-size: var(--sf-fs-sm);
  margin: 0 0 var(--sf-space-3);
}
.stage {
  position: relative;
  width: 100%;
  background: #111;
  border-radius: var(--sf-radius);
  overflow: hidden;
  cursor: crosshair;
  user-select: none;
  margin-bottom: var(--sf-space-3);
}
.stage img {
  display: block;
  width: 100%;
  max-height: 360px;
  object-fit: contain;
  pointer-events: none;
}
.box {
  position: absolute;
  border: 2px solid #3ecf8e;
  background: rgb(62 207 142 / 18%);
  pointer-events: none;
}
.box.content {
  border-color: rgb(196 120 52);
  background: rgb(196 120 52 / 18%);
}
.adv {
  margin-bottom: var(--sf-space-3);
  font-size: var(--sf-fs-sm);
}
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
  margin-top: 0.5rem;
}
</style>
