<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from '@/i18n'
import { useProjectStore } from '@/stores/project'
import VarPicker from '@/components/VarPicker.vue'
import { formatSetVar, parseSetVar } from '@/utils/vars'
import type { ActionStep } from '@/types/project'

const props = defineProps<{
  modelValue: ActionStep[]
  featureKeys?: string[]
  macroIds?: string[]
}>()
const emit = defineEmits<{ 'update:modelValue': [ActionStep[]] }>()

const { t } = useI18n()
const project = useProjectStore()

const steps = computed({
  get: () => props.modelValue || [],
  set: (v) => {
    emit('update:modelValue', v)
    project.markDirty()
  },
})

const ops = ['click', 'key', 'wait', 'hold_key', 'macro', 'set_var', 'clear_var', 'script']

function update(i: number, patch: Partial<ActionStep>) {
  const next = steps.value.map((s, idx) => (idx === i ? { ...s, ...patch } : s))
  steps.value = next
}

function add() {
  steps.value = [...steps.value, { op: 'click', target: props.featureKeys?.[0] || '' }]
}

function remove(i: number) {
  steps.value = steps.value.filter((_, idx) => idx !== i)
}

function move(i: number, dir: -1 | 1) {
  const j = i + dir
  if (j < 0 || j >= steps.value.length) return
  const next = [...steps.value]
  ;[next[i], next[j]] = [next[j], next[i]]
  steps.value = next
}

function setVarName(i: number, name: string) {
  const cur = parseSetVar(steps.value[i].target)
  update(i, { target: formatSetVar(name, cur.value) })
}

function setVarValue(i: number, value: string) {
  const cur = parseSetVar(steps.value[i].target)
  update(i, { target: formatSetVar(cur.name, value) })
}
</script>

<template>
  <div class="steps">
    <div class="head">
      <h3 class="sf-section-title">{{ t('actions') }}</h3>
      <button class="sf-btn" type="button" @click="add">{{ t('add_step') }}</button>
    </div>
    <div v-for="(s, i) in steps" :key="i" class="step" :data-op="s.op">
      <div class="bar" />
      <select class="sf-select op" :value="s.op" @change="update(i, { op: ($event.target as HTMLSelectElement).value })">
        <option v-for="op in ops" :key="op" :value="op">{{ op }}</option>
      </select>

      <template v-if="s.op === 'click'">
        <select
          class="sf-select"
          :value="String(s.target ?? '')"
          @change="update(i, { target: ($event.target as HTMLSelectElement).value })"
        >
          <option value="">—</option>
          <option v-for="k in featureKeys || []" :key="k" :value="k">{{ k }}</option>
        </select>
      </template>
      <template v-else-if="s.op === 'key' || s.op === 'hold_key'">
        <input
          class="sf-input"
          :value="String(s.target ?? '')"
          placeholder="key"
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
          class="sf-select"
          :value="String(s.target ?? '')"
          @change="update(i, { target: ($event.target as HTMLSelectElement).value })"
        >
          <option value="">—</option>
          <option v-for="m in macroIds || []" :key="m" :value="m">{{ m }}</option>
        </select>
      </template>
      <template v-else-if="s.op === 'set_var'">
        <VarPicker :model-value="parseSetVar(s.target).name" @update:model-value="setVarName(i, $event)" />
        <input
          class="sf-input"
          :value="parseSetVar(s.target).value ?? ''"
          placeholder="value"
          @input="setVarValue(i, ($event.target as HTMLInputElement).value)"
        />
      </template>
      <template v-else-if="s.op === 'clear_var'">
        <VarPicker
          :model-value="String(s.target ?? '')"
          @update:model-value="update(i, { target: $event })"
        />
      </template>
      <template v-else>
        <input
          class="sf-input"
          :value="String(s.target ?? '')"
          placeholder="scripts/foo.py"
          @input="update(i, { target: ($event.target as HTMLInputElement).value })"
        />
      </template>

      <div class="ops">
        <button type="button" class="sf-btn sf-btn-ghost" @click="move(i, -1)">↑</button>
        <button type="button" class="sf-btn sf-btn-ghost" @click="move(i, 1)">↓</button>
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
}
.step {
  display: grid;
  grid-template-columns: 4px 7.5rem 1fr 1fr auto;
  gap: 0.4rem;
  align-items: center;
  padding: 0.45rem 0.5rem;
  margin-bottom: 0.4rem;
  background: var(--sf-surface);
  border: 1px solid var(--sf-line);
  border-radius: var(--sf-radius);
}
.bar {
  width: 4px;
  height: 100%;
  min-height: 1.6rem;
  border-radius: 2px;
  background: var(--sf-line-strong);
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
.narrow {
  max-width: 5rem;
}
.ops {
  display: flex;
  gap: 0.1rem;
}
@media (max-width: 900px) {
  .step {
    grid-template-columns: 4px 1fr;
  }
}
</style>
