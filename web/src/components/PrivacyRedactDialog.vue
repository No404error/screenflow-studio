<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useI18n } from '@/i18n'
import { useEscapeKey } from '@/composables/useEscapeKey'
import { redactFileByRois } from '@/utils/cropUpload'

const props = defineProps<{
  src: string
  file: File
}>()

const emit = defineEmits<{
  close: []
  done: [file: File]
}>()

const { t } = useI18n()
const imgRef = ref<HTMLImageElement | null>(null)
const rois = ref<number[][]>([])
const selected = ref<number | null>(null)
const dragging = ref(false)
const start = ref<{ x: number; y: number } | null>(null)
const draft = ref<{ x0: number; y0: number; x1: number; y1: number } | null>(null)
const busy = ref(false)
const err = ref('')

useEscapeKey(() => {
  emit('close')
  return true
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

function hitTest(x: number, y: number): number | null {
  for (let i = rois.value.length - 1; i >= 0; i--) {
    const r = rois.value[i]
    if (!r || r.length !== 4) continue
    const [y0, y1, x0, x1] = r
    if (x >= Math.min(x0, x1) && x <= Math.max(x0, x1) && y >= Math.min(y0, y1) && y <= Math.max(y0, y1)) {
      return i
    }
  }
  return null
}

function onDown(ev: MouseEvent) {
  if (busy.value) return
  const p = normFromEvent(ev)
  if (!p) return
  const hit = hitTest(p.x, p.y)
  if (hit != null) {
    selected.value = hit
    return
  }
  selected.value = null
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
}

function onUp() {
  if (!dragging.value || !draft.value) {
    dragging.value = false
    start.value = null
    draft.value = null
    return
  }
  const { x0, y0, x1, y1 } = draft.value
  const roi = [
    Math.min(y0, y1),
    Math.max(y0, y1),
    Math.min(x0, x1),
    Math.max(x0, x1),
  ]
  dragging.value = false
  start.value = null
  draft.value = null
  if (roi[1] - roi[0] < 0.005 || roi[3] - roi[2] < 0.005) return
  rois.value = [...rois.value, roi]
  selected.value = rois.value.length - 1
}

function boxStyle(roi: number[]) {
  const [y0, y1, x0, x1] = roi
  return {
    left: `${Math.min(x0, x1) * 100}%`,
    top: `${Math.min(y0, y1) * 100}%`,
    width: `${Math.abs(x1 - x0) * 100}%`,
    height: `${Math.abs(y1 - y0) * 100}%`,
  }
}

const draftStyle = computed(() => {
  if (!draft.value) return null
  const { x0, y0, x1, y1 } = draft.value
  return boxStyle([Math.min(y0, y1), Math.max(y0, y1), Math.min(x0, x1), Math.max(x0, x1)])
})

function removeSelected() {
  if (selected.value == null) return
  const next = rois.value.slice()
  next.splice(selected.value, 1)
  rois.value = next
  selected.value = null
}

function clearAll() {
  rois.value = []
  selected.value = null
}

function onKey(e: KeyboardEvent) {
  if (e.key === 'Delete' || e.key === 'Backspace') {
    if (selected.value == null) return
    e.preventDefault()
    removeSelected()
  }
}

onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))

async function continueUpload() {
  busy.value = true
  err.value = ''
  try {
    const out = await redactFileByRois(props.file, rois.value)
    emit('done', out)
  } catch (e) {
    err.value = String(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <div class="mask" @click.self="emit('close')">
      <div class="dialog sf-panel" role="dialog" aria-modal="true" :aria-label="t('redact_title')">
        <header>
          <h3>{{ t('redact_title') }}</h3>
          <button type="button" class="sf-btn sf-btn-ghost" :aria-label="t('cancel')" @click="emit('close')">
            ×
          </button>
        </header>
        <p class="hint">{{ t('redact_hint') }}</p>
        <div
          class="stage"
          @mousedown="onDown"
          @mousemove="onMove"
          @mouseup="onUp"
          @mouseleave="onUp"
        >
          <img ref="imgRef" :src="src" alt="" draggable="false" />
          <div
            v-for="(roi, i) in rois"
            :key="i"
            class="box"
            :class="{ on: selected === i }"
            :style="boxStyle(roi)"
          />
          <div v-if="draftStyle" class="box draft" :style="draftStyle" />
        </div>
        <div class="tools">
          <button
            type="button"
            class="sf-btn"
            :disabled="selected == null || busy"
            @click="removeSelected"
          >
            {{ t('redact_remove_selected') }}
          </button>
          <button type="button" class="sf-btn" :disabled="!rois.length || busy" @click="clearAll">
            {{ t('redact_clear_all') }}
          </button>
          <span class="count">{{ t('redact_count', { n: rois.length }) }}</span>
        </div>
        <p v-if="err" class="err">{{ err }}</p>
        <footer class="sf-dialog-foot foot">
          <button type="button" class="sf-btn" :disabled="busy" @click="emit('close')">
            {{ t('cancel') }}
          </button>
          <button type="button" class="sf-btn sf-btn-primary" :disabled="busy" @click="continueUpload">
            {{ t('redact_continue') }}
          </button>
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
  width: min(640px, 96vw);
  max-height: min(90vh, 800px);
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
  box-shadow: 0 12px 40px rgb(26 34 32 / 22%);
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
}
.hint {
  margin: 0;
  padding: 0.75rem 1.25rem 0;
  color: var(--sf-ink-muted);
  font-size: var(--sf-fs-sm);
  line-height: var(--sf-lh);
  flex-shrink: 0;
}
.stage {
  position: relative;
  margin: 0.75rem 1.25rem;
  background: #111;
  border-radius: var(--sf-radius);
  overflow: hidden;
  cursor: crosshair;
  user-select: none;
  flex: 1 1 auto;
  min-height: 0;
}
.stage img {
  display: block;
  width: 100%;
  max-height: min(50vh, 420px);
  object-fit: contain;
  pointer-events: none;
}
.box {
  position: absolute;
  border: 2px solid rgb(26 34 32 / 70%);
  background: rgb(26 34 32 / 55%);
  pointer-events: none;
}
.box.on {
  border-color: var(--sf-accent);
  box-shadow: 0 0 0 1px var(--sf-accent-soft);
}
.box.draft {
  border-style: dashed;
  background: rgb(26 34 32 / 35%);
}
.tools {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sf-btn-gap);
  padding: 0 1.25rem 0.75rem;
  flex-shrink: 0;
}
.count {
  margin-left: auto;
  font-size: var(--sf-fs-sm);
  color: var(--sf-ink-faint);
}
.err {
  margin: 0 1.25rem 0.5rem;
  color: var(--sf-danger);
  font-size: var(--sf-fs-sm);
}
.foot {
  margin-top: 0;
  border-top: 1px solid var(--sf-line);
  padding: 0.65rem 1rem;
  flex-shrink: 0;
}
</style>
