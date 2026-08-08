<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from '@/i18n'
import { useProjectStore } from '@/stores/project'
import SectionTitle from '@/components/SectionTitle.vue'
import VarPicker from '@/components/VarPicker.vue'
import FeatureSelect from '@/components/FeatureSelect.vue'
import { formatSetVar, parseSetVar } from '@/utils/vars'
import { moveItem } from '@/utils/reorder'
import type { ActionStep, JsonValue } from '@/types/project'

const props = defineProps<{
  modelValue: ActionStep[]
  featureKeys?: string[]
  macroIds?: string[]
  pageId?: string | null
}>()
const emit = defineEmits<{ 'update:modelValue': [ActionStep[]] }>()

const { t } = useI18n()
const project = useProjectStore()
const openExtra = ref<Record<string, boolean>>({})
const stepKeys = ref<string[]>([])
let keySeq = 0

const dragFrom = ref<number | null>(null)
const dropAt = ref<number | null>(null)

const ops = [
  { value: 'click', labelKey: 'op_click' },
  { value: 'key', labelKey: 'op_key' },
  { value: 'wait', labelKey: 'op_wait' },
  { value: 'hold_key', labelKey: 'op_hold_key' },
  { value: 'macro', labelKey: 'op_macro' },
  { value: 'set_var', labelKey: 'op_set_var' },
  { value: 'clear_var', labelKey: 'op_clear_var' },
  { value: 'script', labelKey: 'op_script' },
] as const

const steps = computed({
  get: () => props.modelValue || [],
  set: (v) => {
    emit('update:modelValue', v)
    project.markDirty()
  },
})

watch(
  () => props.modelValue?.length ?? 0,
  (n) => {
    while (stepKeys.value.length < n) stepKeys.value.push(`step_${++keySeq}`)
    if (stepKeys.value.length > n) stepKeys.value = stepKeys.value.slice(0, n)
  },
  { immediate: true },
)

function update(i: number, patch: Partial<ActionStep>) {
  const next = steps.value.map((s, idx) => (idx === i ? { ...s, ...patch } : s))
  steps.value = next
}

function add() {
  stepKeys.value = [...stepKeys.value, `step_${++keySeq}`]
  steps.value = [...steps.value, { op: 'click', target: props.featureKeys?.[0] || '' }]
}

function remove(i: number) {
  const key = stepKeys.value[i]
  if (key) {
    const { [key]: _, ...rest } = openExtra.value
    openExtra.value = rest
  }
  stepKeys.value = stepKeys.value.filter((_, idx) => idx !== i)
  steps.value = steps.value.filter((_, idx) => idx !== i)
}

function reorder(from: number, to: number) {
  if (from === to) return
  stepKeys.value = moveItem(stepKeys.value, from, to)
  steps.value = moveItem(steps.value, from, to)
}

function onDragStart(i: number, ev: DragEvent) {
  dragFrom.value = i
  dropAt.value = i
  ev.dataTransfer?.setData('text/plain', String(i))
  if (ev.dataTransfer) ev.dataTransfer.effectAllowed = 'move'
}

function onDragOver(i: number, ev: DragEvent) {
  if (dragFrom.value === null) return
  ev.preventDefault()
  if (ev.dataTransfer) ev.dataTransfer.dropEffect = 'move'
  dropAt.value = i
}

function onDrop(i: number, ev: DragEvent) {
  ev.preventDefault()
  const from = dragFrom.value
  if (from === null) return
  reorder(from, i)
  dragFrom.value = null
  dropAt.value = null
}

function onDragEnd() {
  dragFrom.value = null
  dropAt.value = null
}

function setVarName(i: number, name: string) {
  const cur = parseSetVar(steps.value[i].target)
  update(i, { target: formatSetVar(name, cur.value) })
}

function setVarValue(i: number, value: string) {
  const cur = parseSetVar(steps.value[i].target)
  update(i, { target: formatSetVar(cur.name, value) })
}

function paramsText(s: ActionStep): string {
  if (!s.params) return ''
  try {
    return JSON.stringify(s.params, null, 2)
  } catch {
    return ''
  }
}

function setParams(i: number, raw: string) {
  const trimmed = raw.trim()
  if (!trimmed) {
    update(i, { params: null })
    return
  }
  try {
    const parsed = JSON.parse(trimmed) as Record<string, JsonValue>
    update(i, { params: parsed })
  } catch {
    /* keep typing */
  }
}
</script>

<template>
  <div class="steps">
    <div class="head">
      <SectionTitle title-key="sec_steps" help-key="help_steps" />
      <div class="sf-btn-bar">
        <button class="sf-btn sf-btn-primary" type="button" @click="add"><I18nText k="add_step" /></button>
      </div>
    </div>
    <div
      v-for="(s, i) in steps"
      :key="stepKeys[i] || i"
      class="step"
      :class="{
        dragging: dragFrom === i,
        'drop-target': dropAt === i && dragFrom !== null && dragFrom !== i,
      }"
      :data-op="s.op"
      @dragover="onDragOver(i, $event)"
      @drop="onDrop(i, $event)"
    >
      <span
        class="grip"
        draggable="true"
        role="button"
        tabindex="0"
        :title="t('drag_reorder')"
        :aria-label="t('drag_reorder')"
        @dragstart="onDragStart(i, $event)"
        @dragend="onDragEnd"
      >
        ⋮⋮
      </span>
      <div class="bar" />
      <div class="col">
        <div class="fields">
          <select
            class="sf-select op"
            :value="s.op"
            @change="update(i, { op: ($event.target as HTMLSelectElement).value })"
          >
            <option v-for="op in ops" :key="op.value" :value="op.value">{{ t(op.labelKey) }}</option>
          </select>

          <template v-if="s.op === 'click'">
            <FeatureSelect
              :model-value="String(s.target ?? '')"
              :keys="featureKeys || []"
              :page-id="pageId"
              @update:model-value="update(i, { target: $event })"
            />
          </template>
          <template v-else-if="s.op === 'key' || s.op === 'hold_key'">
            <input
              class="sf-input flex"
              :value="String(s.target ?? '')"
              :placeholder="t('key_placeholder')"
              @input="update(i, { target: ($event.target as HTMLInputElement).value })"
            />
            <input
              v-if="s.op === 'hold_key'"
              class="sf-input narrow"
              type="number"
              step="0.1"
              :value="s.hold ?? 0.2"
              @input="update(i, { hold: Number(($event.target as HTMLInputElement).value) })"
            />
          </template>
          <template v-else-if="s.op === 'wait'">
            <input
              class="sf-input narrow"
              type="number"
              step="0.05"
              :value="s.target ?? 0.5"
              @input="update(i, { target: Number(($event.target as HTMLInputElement).value) })"
            />
          </template>
          <template v-else-if="s.op === 'macro'">
            <select
              class="sf-select flex"
              :value="String(s.target ?? '')"
              @change="update(i, { target: ($event.target as HTMLSelectElement).value })"
            >
              <option value="">—</option>
              <option v-for="m in macroIds || []" :key="m" :value="m">{{ m }}</option>
            </select>
          </template>
          <template v-else-if="s.op === 'set_var'">
            <VarPicker
              class="flex"
              :model-value="parseSetVar(s.target).name"
              @update:model-value="setVarName(i, $event)"
            />
            <input
              class="sf-input flex"
              :value="parseSetVar(s.target).value ?? ''"
              :placeholder="t('value_placeholder')"
              @input="setVarValue(i, ($event.target as HTMLInputElement).value)"
            />
          </template>
          <template v-else-if="s.op === 'clear_var'">
            <VarPicker
              class="flex"
              :model-value="String(s.target ?? '')"
              @update:model-value="update(i, { target: $event })"
            />
          </template>
          <template v-else>
            <input
              class="sf-input flex"
              :value="String(s.target ?? '')"
              :placeholder="t('script_path_ph')"
              @input="update(i, { target: ($event.target as HTMLInputElement).value })"
            />
          </template>
        </div>
        <details class="extra" :open="openExtra[stepKeys[i]]">
          <summary @click.prevent="openExtra[stepKeys[i]] = !openExtra[stepKeys[i]]">
            {{ t('advanced') }}
          </summary>
          <label class="sf-field">
            <span class="sf-label">{{ t('step_reason') }}</span>
            <input
              class="sf-input"
              :value="s.reason || ''"
              @input="update(i, { reason: ($event.target as HTMLInputElement).value || null })"
            />
          </label>
          <label v-if="s.op === 'script'" class="sf-field">
            <span class="sf-label">{{ t('step_params') }}</span>
            <textarea
              class="sf-input mono"
              rows="3"
              :value="paramsText(s)"
              @change="setParams(i, ($event.target as HTMLTextAreaElement).value)"
            />
          </label>
        </details>
      </div>
      <div class="ops">
        <button type="button" class="sf-btn sf-btn-ghost sf-btn-danger" @click="remove(i)">×</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--sf-space-3);
  margin-bottom: var(--sf-space-3);
}
.head :deep(.row) {
  margin-bottom: 0;
}
.step {
  display: flex;
  align-items: stretch;
  gap: 0.5rem;
  padding: 0.5rem 0.55rem;
  margin-bottom: 0.45rem;
  background: var(--sf-surface-2);
  border: 1px solid transparent;
  border-radius: var(--sf-radius);
  transition: border-color 0.15s ease, background 0.15s ease, opacity 0.15s ease;
}
.step:hover {
  border-color: var(--sf-line);
  background: var(--sf-surface);
}
.step.dragging {
  opacity: 0.45;
}
.step.drop-target {
  border-color: var(--sf-accent);
  box-shadow: inset 0 2px 0 0 var(--sf-accent);
}
.grip {
  flex-shrink: 0;
  align-self: center;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.35rem;
  border: none;
  background: transparent;
  color: var(--sf-ink-faint);
  cursor: grab;
  padding: 0.35rem 0;
  line-height: 1;
  letter-spacing: -0.12em;
  font-size: 0.85rem;
  border-radius: var(--sf-radius);
  user-select: none;
}
.grip:hover {
  color: var(--sf-ink-muted);
  background: var(--sf-surface);
}
.grip:active {
  cursor: grabbing;
}
.bar {
  width: 3px;
  border-radius: 2px;
  background: var(--sf-line-strong);
  flex-shrink: 0;
  align-self: stretch;
  min-height: 2rem;
}
.step[data-op='click'] .bar {
  background: var(--sf-accent);
}
.step[data-op='set_var'] .bar,
.step[data-op='clear_var'] .bar {
  background: var(--sf-ok);
}
.step[data-op='wait'] .bar {
  background: var(--sf-warn);
}
.col {
  flex: 1;
  min-width: 0;
}
.fields {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  align-items: center;
  min-width: 0;
}
.op {
  width: var(--sf-op-select);
  flex: 0 0 auto;
}
.flex {
  flex: 1 1 8rem;
  min-width: 6rem;
}
.narrow {
  width: 5.5rem;
  flex: 0 0 auto;
}
.fields :deep(.sf-select),
.fields .sf-select,
.fields .sf-input {
  min-width: 0;
}
.extra {
  margin-top: 0.35rem;
  font-size: var(--sf-fs-sm);
}
.extra summary {
  cursor: pointer;
  color: var(--sf-ink-muted);
}
.extra .sf-field {
  margin-top: 0.4rem;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: var(--sf-fs-xs);
}
.ops {
  display: flex;
  gap: 0.05rem;
  flex-shrink: 0;
  align-items: flex-start;
}
.ops .sf-btn {
  padding: 0.2rem 0.4rem;
}
</style>
