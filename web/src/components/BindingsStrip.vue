<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from '@/i18n'
import { useProjectStore } from '@/stores/project'
import { useUiStore } from '@/stores/ui'
import { parseWhenVar, parseSetVar } from '@/utils/vars'
import type { ActionStep, StateNode } from '@/types/project'

const props = defineProps<{
  node?: StateNode | null
  steps?: ActionStep[] | null
}>()

const { t } = useI18n()
const project = useProjectStore()
const ui = useUiStore()

const items = computed(() => {
  const out: { name: string; kind: string }[] = []
  if (props.node?.when_var) {
    const w = parseWhenVar(props.node.when_var)
    if (w) out.push({ name: w.name, kind: 'when' })
  }
  for (const s of props.steps || props.node?.actions || []) {
    if (s.op === 'set_var') {
      const p = parseSetVar(s.target)
      if (p.name) out.push({ name: p.name, kind: 'set' })
    }
    if (s.op === 'clear_var' && s.target) {
      out.push({ name: String(s.target), kind: 'clear' })
    }
  }
  return out
})

const declared = computed(() => new Set(Object.keys(project.project?.vars || {})))

function goVars() {
  ui.select({ kind: 'variables' })
}
</script>

<template>
  <div v-if="items.length" class="strip">
    <span class="label">{{ t('bindings') }}</span>
    <button
      v-for="(it, i) in items"
      :key="i"
      class="chip"
      :class="{ warn: !declared.has(it.name) }"
      @click="goVars"
    >
      <span class="kind">{{
        it.kind === 'when' ? t('bind_when') : it.kind === 'set' ? t('bind_set') : t('bind_clear')
      }}</span>
      {{ it.name }}
    </button>
  </div>
</template>

<style scoped>
.strip {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem;
  padding: 0.5rem 0.75rem;
  background: var(--sf-surface-2);
  border: 1px solid var(--sf-line);
  border-radius: var(--sf-radius);
  margin-bottom: var(--sf-space-4);
}
.label {
  font-size: var(--sf-fs-xs);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--sf-ink-muted);
  margin-right: 0.25rem;
}
.chip {
  border: 1px solid var(--sf-line);
  background: var(--sf-surface);
  border-radius: 999px;
  padding: 0.15rem 0.55rem;
  font-size: var(--sf-fs-xs);
  font-family: var(--sf-mono);
}
.chip.warn {
  background: var(--sf-warn-soft);
  border-color: color-mix(in srgb, var(--sf-warn) 40%, var(--sf-line));
}
.kind {
  color: var(--sf-ink-faint);
  margin-right: 0.25rem;
}
</style>
