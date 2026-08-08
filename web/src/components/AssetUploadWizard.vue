<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from '@/i18n'

const props = withDefaults(
  defineProps<{
    src: string
    preferredName: string
    /** full = search area + match picture; content = artwork crop only */
    mode?: 'full' | 'content'
  }>(),
  { mode: 'full' },
)

const emit = defineEmits<{
  close: []
  done: [payload: { searchRoi: number[] | null; contentRoi: number[]; name: string }]
}>()

const { t } = useI18n()
const contentOnly = computed(() => props.mode === 'content')
const step = ref<1 | 2>(contentOnly.value ? 2 : 1)
const name = ref(props.preferredName)
const searchRoi = ref<number[] | null>(null)
const zoom = ref(1)
const stepTotal = computed(() => (contentOnly.value ? 1 : 2))
const stepDisplay = computed(() => (contentOnly.value ? 1 : step.value))

const imgRef = ref<HTMLImageElement | null>(null)
const dragging = ref(false)
const start = ref<{ x: number; y: number } | null>(null)
/** Step 1 defaults to the full image. */
const y0 = ref(0)
const y1 = ref(1)
const x0 = ref(0)
const x1 = ref(1)
const err = ref('')

const title = computed(() => {
  if (contentOnly.value) return t('upload_artwork_title')
  return step.value === 1 ? t('upload_step_search_title') : t('upload_step_content_title')
})
const hint = computed(() => {
  if (contentOnly.value) return t('upload_artwork_hint')
  return step.value === 1 ? t('upload_step_search_hint') : t('upload_step_content_hint')
})
const zoomLabel = computed(() => `${Math.round(zoom.value * 100)}%`)

const boxStyle = computed(() => pctBox(x0.value, y0.value, x1.value, y1.value))
const searchGuideStyle = computed(() => {
  const r = searchRoi.value
  if (!r) return null
  return pctBox(r[2], r[0], r[3], r[1])
})

function pctBox(xa: number, ya: number, xb: number, yb: number) {
  const left = Math.min(xa, xb) * 100
  const top = Math.min(ya, yb) * 100
  const width = Math.abs(xb - xa) * 100
  const height = Math.abs(yb - ya) * 100
  return { left: `${left}%`, top: `${top}%`, width: `${width}%`, height: `${height}%` }
}

function setFullBox() {
  x0.value = 0
  y0.value = 0
  x1.value = 1
  y1.value = 1
}

function currentRoi(): number[] {
  return [
    Math.min(y0.value, y1.value),
    Math.max(y0.value, y1.value),
    Math.min(x0.value, x1.value),
    Math.max(x0.value, x1.value),
  ]
}

function isTiny(roi: number[]) {
  return roi[1] - roi[0] < 0.005 || roi[3] - roi[2] < 0.005
}

function isFullFrame(roi: number[]) {
  return roi[0] <= 0.001 && roi[1] >= 0.999 && roi[2] <= 0.001 && roi[3] >= 0.999
}

function clampToSearch(nx: number, ny: number) {
  const r = searchRoi.value
  if (!r || step.value !== 2) return { x: nx, y: ny }
  const [sy0, sy1, sx0, sx1] = r
  return {
    x: Math.min(sx1, Math.max(sx0, nx)),
    y: Math.min(sy1, Math.max(sy0, ny)),
  }
}

function normFromEvent(ev: MouseEvent) {
  const el = imgRef.value
  if (!el) return null
  const r = el.getBoundingClientRect()
  if (r.width <= 0 || r.height <= 0) return null
  const x = Math.min(1, Math.max(0, (ev.clientX - r.left) / r.width))
  const y = Math.min(1, Math.max(0, (ev.clientY - r.top) / r.height))
  return clampToSearch(x, y)
}

function onDown(ev: MouseEvent) {
  const p = normFromEvent(ev)
  if (!p) return
  dragging.value = true
  start.value = p
  x0.value = p.x
  x1.value = p.x
  y0.value = p.y
  y1.value = p.y
  err.value = ''
  ev.preventDefault()
}

function onMove(ev: MouseEvent) {
  if (!dragging.value || !start.value) return
  const p = normFromEvent(ev)
  if (!p) return
  x0.value = Math.min(start.value.x, p.x)
  x1.value = Math.max(start.value.x, p.x)
  y0.value = Math.min(start.value.y, p.y)
  y1.value = Math.max(start.value.y, p.y)
}

function onUp() {
  dragging.value = false
  start.value = null
}

function setZoom(next: number) {
  zoom.value = Math.min(4, Math.max(0.5, Math.round(next * 100) / 100))
}

function zoomIn() {
  setZoom(zoom.value + 0.25)
}

function zoomOut() {
  setZoom(zoom.value - 0.25)
}

function zoomReset() {
  setZoom(1)
}

function onWheel(ev: WheelEvent) {
  if (!ev.ctrlKey && !ev.metaKey) return
  ev.preventDefault()
  const delta = ev.deltaY > 0 ? -0.15 : 0.15
  setZoom(zoom.value + delta)
}

function seedContentInsideSearch() {
  const r = searchRoi.value
  if (!r) {
    x0.value = 0.3
    x1.value = 0.7
    y0.value = 0.3
    y1.value = 0.7
    return
  }
  const [sy0, sy1, sx0, sx1] = r
  const mx = (sx0 + sx1) / 2
  const my = (sy0 + sy1) / 2
  const hw = (sx1 - sx0) * 0.35
  const hh = (sy1 - sy0) * 0.35
  x0.value = Math.max(sx0, mx - hw)
  x1.value = Math.min(sx1, mx + hw)
  y0.value = Math.max(sy0, my - hh)
  y1.value = Math.min(sy1, my + hh)
}

function goSearchNext() {
  const roi = currentRoi()
  if (isTiny(roi)) {
    err.value = t('upload_need_selection')
    return
  }
  // Full-frame selection ≡ full-screen search (no stored ROI)
  searchRoi.value = isFullFrame(roi) ? null : roi
  step.value = 2
  seedContentInsideSearch()
  err.value = ''
}

function goSearchFull() {
  setFullBox()
  searchRoi.value = null
  step.value = 2
  seedContentInsideSearch()
  err.value = ''
}

function goBack() {
  step.value = 1
  if (searchRoi.value) {
    ;[y0.value, y1.value, x0.value, x1.value] = searchRoi.value
  } else {
    setFullBox()
  }
  err.value = ''
}

function useSearchAsContent() {
  if (!searchRoi.value) {
    err.value = t('upload_need_search_first')
    return
  }
  ;[y0.value, y1.value, x0.value, x1.value] = searchRoi.value
  err.value = ''
}

function finish() {
  const content = currentRoi()
  if (isTiny(content)) {
    err.value = t('upload_need_selection')
    return
  }
  const search = searchRoi.value
  if (search) {
    const [sy0, sy1, sx0, sx1] = search
    if (content[0] < sy0 - 1e-6 || content[1] > sy1 + 1e-6 || content[2] < sx0 - 1e-6 || content[3] > sx1 + 1e-6) {
      err.value = t('upload_content_outside_search')
      return
    }
  }
  const trimmed = name.value.trim()
  if (!trimmed) {
    err.value = t('name_required')
    return
  }
  emit('done', { searchRoi: search, contentRoi: content, name: trimmed })
}
</script>

<template>
  <div class="mask" @click.self="emit('close')">
    <div class="dialog sf-panel">
      <header>
        <h3>{{ title }}</h3>
        <span class="steps">
          <I18nText k="upload_step_n" :vars="{ n: stepDisplay, total: stepTotal }" />
        </span>
      </header>
      <p class="hint">{{ hint }}</p>
      <div class="toolbar">
        <label class="sf-field name">
          <span class="sf-label"><I18nText k="preferred_name" /></span>
          <input v-model="name" class="sf-input" />
        </label>
        <div class="zoom" role="group" :aria-label="t('upload_zoom')">
          <button type="button" class="sf-btn sf-btn-ghost" :disabled="zoom <= 0.5" @click="zoomOut">−</button>
          <button type="button" class="sf-btn sf-btn-ghost zoom-lbl" @click="zoomReset">{{ zoomLabel }}</button>
          <button type="button" class="sf-btn sf-btn-ghost" :disabled="zoom >= 4" @click="zoomIn">+</button>
        </div>
      </div>
      <div class="viewport" @wheel="onWheel">
        <div
          class="frame"
          :style="{ width: `${zoom * 100}%` }"
          @mousedown="onDown"
          @mousemove="onMove"
          @mouseup="onUp"
          @mouseleave="onUp"
        >
          <img ref="imgRef" :src="src" alt="" draggable="false" />
          <div v-if="step === 2 && searchGuideStyle" class="guide" :style="searchGuideStyle" />
          <div class="box" :class="{ content: step === 2 }" :style="boxStyle" />
        </div>
      </div>
      <p class="zoom-tip"><I18nText k="upload_zoom_hint" /></p>
      <p v-if="err" class="err">{{ err }}</p>
      <div class="sf-dialog-foot wizard-foot">
        <button type="button" class="sf-btn sf-btn-ghost" @click="emit('close')">
          <I18nText k="cancel" />
        </button>
        <div class="sf-btn-cluster">
          <template v-if="step === 1 && !contentOnly">
            <button type="button" class="sf-btn" @click="goSearchFull">
              <I18nText k="upload_search_full" />
            </button>
            <button type="button" class="sf-btn sf-btn-primary" @click="goSearchNext">
              <I18nText k="wizard_next" />
            </button>
          </template>
          <template v-else>
            <button v-if="!contentOnly" type="button" class="sf-btn" @click="goBack">
              <I18nText k="wizard_back" />
            </button>
            <button
              v-if="searchRoi && !contentOnly"
              type="button"
              class="sf-btn"
              @click="useSearchAsContent"
            >
              <I18nText k="upload_content_same_as_search" />
            </button>
            <button type="button" class="sf-btn sf-btn-primary" @click="finish">
              <I18nText k="wizard_finish" />
            </button>
          </template>
        </div>
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
  z-index: 45;
  padding: 0.75rem;
}
.dialog {
  width: min(1100px, 98vw);
  max-height: min(96vh, 960px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: var(--sf-space-4);
}
header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.35rem;
  flex-shrink: 0;
}
h3 {
  margin: 0;
  font-size: var(--sf-fs-lg);
}
.steps {
  font-size: var(--sf-fs-xs);
  color: var(--sf-ink-faint);
  flex-shrink: 0;
}
.hint {
  margin: 0 0 var(--sf-space-3);
  color: var(--sf-ink-muted);
  font-size: var(--sf-fs-sm);
  line-height: 1.45;
  flex-shrink: 0;
}
.toolbar {
  display: flex;
  align-items: flex-end;
  gap: var(--sf-space-3);
  margin-bottom: var(--sf-space-3);
  flex-shrink: 0;
}
.name {
  flex: 1;
  margin-bottom: 0;
  min-width: 0;
}
.zoom {
  display: inline-flex;
  align-items: center;
  gap: 0.15rem;
  flex-shrink: 0;
  padding-bottom: 0.1rem;
}
.zoom .sf-btn {
  padding: 0.25rem 0.55rem;
  min-width: 2rem;
}
.zoom-lbl {
  min-width: 3.5rem;
  font-variant-numeric: tabular-nums;
}
.viewport {
  flex: 1 1 auto;
  min-height: 280px;
  max-height: min(68vh, 640px);
  overflow: auto;
  background: #111;
  border-radius: var(--sf-radius);
  border: 1px solid var(--sf-line);
  margin-bottom: 0.35rem;
  cursor: crosshair;
  user-select: none;
}
.frame {
  position: relative;
  min-width: 100%;
}
.frame img {
  display: block;
  width: 100%;
  height: auto;
  pointer-events: none;
  vertical-align: top;
}
.guide {
  position: absolute;
  border: 2px dashed #f0b429;
  background: rgb(240 180 41 / 10%);
  pointer-events: none;
}
.box {
  position: absolute;
  border: 2px solid #3ecf8e;
  background: rgb(62 207 142 / 18%);
  pointer-events: none;
  box-sizing: border-box;
}
.box.content {
  border-color: #5b9fd4;
  background: rgb(91 159 212 / 22%);
}
.zoom-tip {
  margin: 0 0 var(--sf-space-2);
  font-size: var(--sf-fs-xs);
  color: var(--sf-ink-faint);
  flex-shrink: 0;
}
.err {
  margin: 0 0 var(--sf-space-2);
  color: var(--sf-danger);
  font-size: var(--sf-fs-sm);
  flex-shrink: 0;
}
.wizard-foot {
  flex-shrink: 0;
  justify-content: space-between;
  margin-top: 0;
}
</style>
