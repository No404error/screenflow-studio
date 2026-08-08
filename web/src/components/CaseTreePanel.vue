<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from '@/i18n'
import {
  addChild,
  addSibling,
  flattenTree,
  hasElseAmong,
  isElse,
  locateNode,
  makeCase,
  moveNodeAmongSiblings,
  removeNodeFromTree,
} from '@/utils/tree'
import type { StateNode } from '@/types/project'

const props = defineProps<{
  modelValue: StateNode[]
  selectedId: string | null
  featureKeyHint?: string | null
  /** When true, hide add-child (flat post trees still allow nested if false) */
  allowNested?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [StateNode[]]
  'update:selectedId': [string | null]
  change: []
}>()

const { t } = useI18n()
const allowNested = computed(() => props.allowNested !== false)

const rows = computed(() => flattenTree(props.modelValue || []))
const dragId = ref<string | null>(null)
const dropId = ref<string | null>(null)

function roots(): StateNode[] {
  return props.modelValue || []
}

function touch(next: StateNode[]) {
  emit('update:modelValue', next)
  emit('change')
}

function select(id: string) {
  emit('update:selectedId', id)
}

function onAddCase() {
  const n = makeCase(t('default_case_name', { n: (props.modelValue?.length || 0) + 1 }), {
    featureKey: props.featureKeyHint,
  })
  const next = [...roots()]
  addSibling(next, props.selectedId, n)
  touch(next)
  select(n.id)
}

function onAddElse() {
  const next = [...roots()]
  // ELSE only among root siblings of selected node's list, or roots
  let siblings = next
  if (props.selectedId) {
    const loc = locateNode(next, props.selectedId)
    if (loc) siblings = loc.siblings
  }
  if (hasElseAmong(siblings)) {
    alert(t('else_exists'))
    return
  }
  const n = makeCase(t('else'), { isElse: true })
  addSibling(next, props.selectedId, n)
  touch(next)
  select(n.id)
}

function onAddChild() {
  if (!props.selectedId || !allowNested.value) return
  const n = makeCase(t('default_child_name'), { featureKey: props.featureKeyHint })
  const next = [...roots()]
  if (!addChild(next, props.selectedId, n)) {
    alert(t('cannot_nest_else'))
    return
  }
  touch(next)
  select(n.id)
}

function onDeleteRow(id: string) {
  const next = [...roots()]
  removeNodeFromTree(next, id)
  touch(next)
  if (props.selectedId === id) {
    emit('update:selectedId', next[0]?.id ?? null)
  }
}

function canDropOn(targetId: string): boolean {
  if (!dragId.value || dragId.value === targetId) return false
  const from = locateNode(roots(), dragId.value)
  const to = locateNode(roots(), targetId)
  return !!(from && to && from.siblings === to.siblings)
}

function onDragStart(id: string, ev: DragEvent) {
  dragId.value = id
  dropId.value = id
  select(id)
  ev.dataTransfer?.setData('text/plain', id)
  if (ev.dataTransfer) ev.dataTransfer.effectAllowed = 'move'
}

function onDragOver(id: string, ev: DragEvent) {
  if (!canDropOn(id)) {
    if (dropId.value === id) dropId.value = null
    return
  }
  ev.preventDefault()
  if (ev.dataTransfer) ev.dataTransfer.dropEffect = 'move'
  dropId.value = id
}

function onDrop(id: string, ev: DragEvent) {
  ev.preventDefault()
  const from = dragId.value
  if (!from || !canDropOn(id)) {
    dragId.value = null
    dropId.value = null
    return
  }
  const next = [...roots()]
  if (moveNodeAmongSiblings(next, from, id)) touch(next)
  dragId.value = null
  dropId.value = null
}

function onDragEnd() {
  dragId.value = null
  dropId.value = null
}
</script>

<template>
  <aside class="panel">
    <div class="sf-btn-cluster toolbar">
      <button type="button" class="sf-btn sf-btn-primary" @click="onAddCase">
        <I18nText k="add_case" />
      </button>
      <button type="button" class="sf-btn" @click="onAddElse"><I18nText k="else" /></button>
      <button
        v-if="allowNested"
        type="button"
        class="sf-btn sf-btn-ghost"
        :disabled="!selectedId"
        @click="onAddChild"
      >
        <I18nText k="add_child" />
      </button>
    </div>
    <div class="list">
      <div
        v-for="{ node, depth } in rows"
        :key="node.id"
        class="row"
        :class="{
          active: node.id === selectedId,
          dragging: dragId === node.id,
          'drop-target': dropId === node.id && dragId && dragId !== node.id && canDropOn(node.id),
        }"
        :style="{ paddingLeft: `${0.35 + depth * 0.85}rem` }"
        @click="select(node.id)"
        @dragover="onDragOver(node.id, $event)"
        @drop="onDrop(node.id, $event)"
      >
        <span
          class="grip"
          draggable="true"
          role="button"
          tabindex="0"
          :title="t('drag_reorder')"
          :aria-label="t('drag_reorder')"
          @click.stop
          @dragstart="onDragStart(node.id, $event)"
          @dragend="onDragEnd"
        >
          ⋮⋮
        </span>
        <span class="name">{{ node.name || node.id }}</span>
        <span v-if="isElse(node)" class="mark"><I18nText k="else" /></span>
        <span v-else-if="node.when_var" class="mark if"><I18nText k="when_short" /></span>
        <span v-if="node.children?.length" class="nest">{{ node.children.length }}</span>
        <button
          type="button"
          class="row-del"
          :title="t('delete')"
          :aria-label="t('delete')"
          @click.stop="onDeleteRow(node.id)"
        >
          ×
        </button>
      </div>
      <p v-if="!rows.length" class="sf-empty"><I18nText k="empty_cases" /></p>
    </div>
  </aside>
</template>

<style scoped>
.panel {
  background: var(--sf-surface-2);
  border-radius: var(--sf-radius-lg);
  padding: var(--sf-space-2);
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  min-height: 280px;
}
.toolbar {
  gap: var(--sf-btn-gap);
}
.toolbar .sf-btn {
  min-height: 1.75rem;
  font-size: var(--sf-fs-xs);
  padding: 0 0.55rem;
}
.list {
  flex: 1;
  overflow: auto;
  margin-top: 0.25rem;
}
.row {
  width: 100%;
  text-align: left;
  border: 1px solid transparent;
  background: transparent;
  padding: 0.35rem 0.35rem;
  border-radius: var(--sf-radius);
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: var(--sf-fs-sm);
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease, opacity 0.15s ease;
}
.row:hover {
  background: var(--sf-surface);
}
.row.active {
  background: var(--sf-accent-soft);
  color: var(--sf-accent);
  font-weight: 600;
}
.row.dragging {
  opacity: 0.45;
}
.row.drop-target {
  border-color: var(--sf-accent);
  box-shadow: inset 0 2px 0 0 var(--sf-accent);
}
.grip {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.2rem;
  border: none;
  background: transparent;
  color: var(--sf-ink-faint);
  cursor: grab;
  padding: 0.2rem 0;
  line-height: 1;
  letter-spacing: -0.12em;
  font-size: 0.8rem;
  border-radius: 3px;
  user-select: none;
}
.grip:hover {
  color: var(--sf-ink-muted);
  background: var(--sf-surface);
}
.grip:active {
  cursor: grabbing;
}
.name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
  flex: 1;
}
.mark {
  font-size: 0.65rem;
  font-weight: 600;
  padding: 0.05rem 0.3rem;
  border-radius: 3px;
  background: var(--sf-surface);
  color: var(--sf-ink-muted);
  flex-shrink: 0;
}
.mark.if {
  background: var(--sf-accent-soft);
  color: var(--sf-accent);
}
.nest {
  font-size: 0.65rem;
  color: var(--sf-ink-faint);
  font-variant-numeric: tabular-nums;
}
.row-del {
  flex-shrink: 0;
  margin-left: 0.15rem;
  width: 1.35rem;
  height: 1.35rem;
  border: none;
  border-radius: var(--sf-radius);
  background: transparent;
  color: var(--sf-ink-faint);
  font-size: 1rem;
  line-height: 1;
  padding: 0;
  opacity: 0;
  cursor: pointer;
  transition: opacity 0.12s ease, color 0.12s ease, background 0.12s ease;
}
.row:hover .row-del,
.row.active .row-del,
.row-del:focus-visible {
  opacity: 1;
}
.row-del:hover {
  color: var(--sf-danger);
  background: var(--sf-danger-soft);
}
</style>
