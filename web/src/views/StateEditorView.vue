<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from '@/i18n'
import { useUiStore } from '@/stores/ui'
import { useProjectStore } from '@/stores/project'
import BindingsStrip from '@/components/BindingsStrip.vue'
import StepsEditor from '@/components/StepsEditor.vue'
import VarPicker from '@/components/VarPicker.vue'
import PostEditor from '@/components/PostEditor.vue'
import { findNode, formatWhenVar, parseWhenVar } from '@/utils/vars'
import type { StateNode } from '@/types/project'

const { t } = useI18n()
const ui = useUiStore()
const project = useProjectStore()

const page = computed(() => {
  const id = ui.selection.pageId
  if (!id || !project.project) return null
  return project.project.page_docs[id] || null
})

const selectedId = ref(ui.selection.nodeId || '')

watch(
  () => ui.selection.nodeId,
  (id) => {
    if (id) selectedId.value = id
  },
)

const node = computed(() => {
  if (!page.value || !selectedId.value) return null
  return findNode(page.value.state_tree || [], selectedId.value)
})

const featureKeys = computed(() => Object.keys(page.value?.features || {}).sort())
const macroIds = computed(() => (project.project?.macros || []).map((m) => m.id))

const whenName = computed({
  get: () => parseWhenVar(node.value?.when_var)?.name || '',
  set: (name: string) => {
    if (!node.value) return
    const cur = parseWhenVar(node.value.when_var)
    node.value.when_var = formatWhenVar(name, cur?.value) || null
    project.markDirty()
  },
})

const whenValue = computed({
  get: () => parseWhenVar(node.value?.when_var)?.value ?? '',
  set: (value: string) => {
    if (!node.value) return
    const cur = parseWhenVar(node.value.when_var)
    node.value.when_var = formatWhenVar(cur?.name || whenName.value, value) || null
    project.markDirty()
  },
})

function mark() {
  project.markDirty()
}

function isElse(n: StateNode) {
  return !!(n.else || n.is_else)
}

function selectNode(id: string) {
  selectedId.value = id
  if (page.value) ui.select({ kind: 'state', pageId: page.value.id, nodeId: id })
}

function addCase() {
  if (!page.value) return
  const id = `case_${Date.now().toString(36)}`
  page.value.state_tree = page.value.state_tree || []
  page.value.state_tree.push({
    id,
    name: `Case ${page.value.state_tree.length + 1}`,
    priority: 0,
    score: { kind: 'template', key: featureKeys.value[0] || null },
    actions: [],
    children: [],
  })
  project.markDirty()
  selectNode(id)
}

function addElse() {
  if (!page.value) return
  if ((page.value.state_tree || []).some(isElse)) {
    alert('ELSE already exists')
    return
  }
  const id = `else_${Date.now().toString(36)}`
  page.value.state_tree = page.value.state_tree || []
  page.value.state_tree.push({
    id,
    name: 'ELSE',
    else: true,
    actions: [],
    children: [],
  })
  project.markDirty()
  selectNode(id)
}

function removeNode() {
  if (!page.value || !node.value) return
  page.value.state_tree = (page.value.state_tree || []).filter((n) => n.id !== node.value!.id)
  project.markDirty()
  selectedId.value = page.value.state_tree[0]?.id || ''
}

function setScoreKind(kind: string) {
  if (!node.value) return
  if (!node.value.score) node.value.score = { kind: 'template' }
  node.value.score.kind = kind as 'template' | 'constant' | 'invert'
  mark()
}
</script>

<template>
  <div v-if="page" class="state">
    <header class="head">
      <h2>{{ page.name }} — {{ t('actions') }}</h2>
      <div class="row">
        <button class="sf-btn" type="button" @click="addCase">{{ t('add_case') }}</button>
        <button class="sf-btn" type="button" @click="addElse">+ {{ t('else') }}</button>
      </div>
    </header>

    <div class="split">
      <aside class="tree sf-panel">
        <button
          v-for="n in page.state_tree || []"
          :key="n.id"
          class="tn"
          :class="{ active: n.id === selectedId }"
          @click="selectNode(n.id)"
        >
          <span>{{ n.name || n.id }}</span>
          <span v-if="isElse(n)" class="sf-badge sf-badge-else">{{ t('else') }}</span>
          <span v-if="n.when_var" class="sf-badge sf-badge-when">if</span>
        </button>
        <p v-if="!(page.state_tree || []).length" class="sf-empty">{{ t('add_case') }}</p>
      </aside>

      <section v-if="node" class="detail">
        <BindingsStrip :node="node" />
        <label class="sf-field">
          <span class="sf-label">{{ t('name') }}</span>
          <input v-model="node.name" class="sf-input" @input="mark" />
        </label>

        <div class="grid">
          <label class="sf-field">
            <span class="sf-label">priority</span>
            <input v-model.number="node.priority" class="sf-input" type="number" @input="mark" />
          </label>
          <label class="sf-field check">
            <input
              type="checkbox"
              :checked="isElse(node)"
              @change="
                node.else = ($event.target as HTMLInputElement).checked;
                mark()
              "
            />
            {{ t('else') }}
          </label>
        </div>

        <div v-if="!isElse(node)" class="block">
          <h3 class="sf-section-title">{{ t('score') }}</h3>
          <div class="grid">
            <select
              class="sf-select"
              :value="node.score?.kind || 'template'"
              @change="setScoreKind(($event.target as HTMLSelectElement).value)"
            >
              <option value="template">template</option>
              <option value="invert">invert</option>
              <option value="constant">constant</option>
            </select>
            <select
              v-if="(node.score?.kind || 'template') !== 'constant'"
              class="sf-select"
              :value="node.score?.key || ''"
              @change="
                if (!node.score) node.score = { kind: 'template' };
                node.score.key = ($event.target as HTMLSelectElement).value;
                mark()
              "
            >
              <option value="">—</option>
              <option v-for="k in featureKeys" :key="k" :value="k">{{ k }}</option>
            </select>
            <input
              v-else
              class="sf-input"
              type="number"
              step="0.01"
              :value="node.score?.constant ?? 0"
              @input="
                if (!node.score) node.score = { kind: 'constant' };
                node.score.constant = Number(($event.target as HTMLInputElement).value);
                mark()
              "
            />
          </div>
        </div>

        <div class="block">
          <h3 class="sf-section-title">{{ t('when') }}</h3>
          <div class="grid">
            <VarPicker v-model="whenName" allow-empty />
            <input v-model="whenValue" class="sf-input" placeholder="value (optional)" />
          </div>
        </div>

        <StepsEditor
          :model-value="node.actions || []"
          :feature-keys="featureKeys"
          :macro-ids="macroIds"
          @update:model-value="
            node.actions = $event;
            mark()
          "
        />
        <PostEditor v-model="node.post" />

        <button class="sf-btn sf-btn-danger" type="button" style="margin-top: 1rem" @click="removeNode">
          {{ t('delete') }}
        </button>
      </section>
      <p v-else class="sf-empty">{{ t('no_selection') }}</p>
    </div>
  </div>
</template>

<style scoped>
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--sf-space-4);
}
h2 {
  margin: 0;
  font-size: var(--sf-fs-lg);
}
.row {
  display: flex;
  gap: 0.4rem;
}
.split {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: var(--sf-space-4);
  min-height: 420px;
}
.tree {
  padding: var(--sf-space-2);
  align-self: start;
}
.tn {
  width: 100%;
  text-align: left;
  border: none;
  background: transparent;
  padding: 0.45rem 0.55rem;
  border-radius: var(--sf-radius);
  display: flex;
  gap: 0.3rem;
  align-items: center;
  font-size: var(--sf-fs-sm);
}
.tn:hover {
  background: var(--sf-surface-2);
}
.tn.active {
  background: var(--sf-accent-soft);
  color: var(--sf-accent);
  font-weight: 600;
}
.detail {
  min-width: 0;
}
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--sf-space-3);
}
.block {
  margin: var(--sf-space-4) 0;
}
.check {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-top: 1.4rem;
}
@media (max-width: 800px) {
  .split {
    grid-template-columns: 1fr;
  }
}
</style>
