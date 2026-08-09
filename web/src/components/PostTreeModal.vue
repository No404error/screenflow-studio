<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from '@/i18n'
import { useEscapeKey } from '@/composables/useEscapeKey'
import CaseTreePanel from '@/components/CaseTreePanel.vue'
import CaseDetailForm from '@/components/CaseDetailForm.vue'
import { findNodeInTree } from '@/utils/tree'
import type { StateNode } from '@/types/project'

const props = defineProps<{
  modelValue: StateNode[]
  featureKeys: string[]
  macroIds: string[]
  pageId?: string | null
  title?: string
}>()
const emit = defineEmits<{
  'update:modelValue': [StateNode[]]
  close: []
}>()

const { t } = useI18n()

function cloneTree(nodes: StateNode[]): StateNode[] {
  return JSON.parse(JSON.stringify(nodes || [])) as StateNode[]
}

const tree = ref<StateNode[]>(cloneTree(props.modelValue))
const selectedId = ref<string | null>(tree.value[0]?.id ?? null)

const node = computed(() =>
  selectedId.value ? findNodeInTree(tree.value, selectedId.value) : null,
)

function onTreeUpdate(v: StateNode[]) {
  tree.value = v
  if (selectedId.value && !findNodeInTree(tree.value, selectedId.value)) {
    selectedId.value = tree.value[0]?.id ?? null
  }
}

function done() {
  emit('update:modelValue', tree.value)
  emit('close')
}

function cancel() {
  emit('close')
}

useEscapeKey(() => {
  cancel()
  return true
})
</script>

<template>
  <Teleport to="body">
    <div class="mask" @click.self="cancel">
      <div class="dialog">
        <header>
          <h3>{{ title || t('edit_post_tree') }}</h3>
          <div class="sf-btn-bar">
            <button type="button" class="sf-btn sf-btn-ghost" @click="cancel">
              {{ t('cancel') }}
            </button>
            <button type="button" class="sf-btn sf-btn-primary" @click="done">{{ t('ok') }}</button>
          </div>
        </header>
        <div class="body">
          <CaseTreePanel
            :model-value="tree"
            :selected-id="selectedId"
            :feature-key-hint="featureKeys[0] || null"
            :allow-nested="true"
            @update:model-value="onTreeUpdate"
            @update:selected-id="selectedId = $event"
          />
          <CaseDetailForm
            v-if="node"
            :node="node"
            :feature-keys="featureKeys"
            :macro-ids="macroIds"
            :page-id="pageId"
            :allow-post="false"
          />
          <p v-else class="sf-empty">{{ t('no_selection') }}</p>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.mask {
  position: fixed;
  inset: 0;
  background: rgb(26 34 32 / 45%);
  z-index: 55;
  display: grid;
  place-items: center;
  padding: 1rem;
}
.dialog {
  width: min(980px, 96vw);
  height: min(80vh, 720px);
  background: var(--sf-surface);
  border-radius: var(--sf-radius-lg);
  border: 1px solid var(--sf-line);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 12px 40px rgb(26 34 32 / 22%);
}
header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--sf-line);
}
h3 {
  margin: 0;
  font-size: var(--sf-fs-lg);
}
.body {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: var(--sf-space-4);
  padding: var(--sf-space-4);
  overflow: hidden;
}
.body > :last-child {
  overflow: auto;
}
@media (max-width: 800px) {
  .body {
    grid-template-columns: 1fr;
  }
}
</style>
