<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from '@/i18n'
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
const tree = ref<StateNode[]>([...(props.modelValue || [])])
const selectedId = ref<string | null>(tree.value[0]?.id ?? null)

watch(
  () => props.modelValue,
  (v) => {
    tree.value = [...(v || [])]
    if (selectedId.value && !findNodeInTree(tree.value, selectedId.value)) {
      selectedId.value = tree.value[0]?.id ?? null
    }
  },
)

const node = computed(() =>
  selectedId.value ? findNodeInTree(tree.value, selectedId.value) : null,
)

function onTreeUpdate(v: StateNode[]) {
  tree.value = v
  emit('update:modelValue', v)
}

function done() {
  emit('update:modelValue', tree.value)
  emit('close')
}
</script>

<template>
  <Teleport to="body">
    <div class="mask" @click.self="done">
      <div class="dialog">
        <header>
          <h3>{{ title || t('edit_post_tree') }}</h3>
          <button type="button" class="sf-btn sf-btn-primary" @click="done">{{ t('ok') }}</button>
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
            @change="emit('update:modelValue', tree)"
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
