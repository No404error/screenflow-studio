<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { api } from '@/api/client'
import { useI18n } from '@/i18n'
import { useUiStore } from '@/stores/ui'
import { useProjectStore } from '@/stores/project'
import CaseTreePanel from '@/components/CaseTreePanel.vue'
import CaseDetailForm from '@/components/CaseDetailForm.vue'
import { findNodeInTree } from '@/utils/tree'

const { t } = useI18n()
const ui = useUiStore()
const project = useProjectStore()

const page = computed(() => {
  const id = ui.selection.pageId
  if (!id || !project.project) return null
  return project.project.page_docs[id] || null
})

const selectedId = ref<string | null>(ui.selection.nodeId || null)

watch(
  () => ui.selection.nodeId,
  (id) => {
    if (id) selectedId.value = id
  },
)

watch(
  page,
  (p) => {
    if (!p) return
    if (!selectedId.value || !findNodeInTree(p.state_tree || [], selectedId.value)) {
      selectedId.value = p.state_tree?.[0]?.id ?? null
    }
  },
  { immediate: true },
)

const node = computed(() => {
  if (!page.value || !selectedId.value) return null
  return findNodeInTree(page.value.state_tree || [], selectedId.value)
})

const featureKeys = computed(() => Object.keys(page.value?.features || {}).sort())
const macroIds = computed(() => (project.project?.macros || []).map((m) => m.id))

function onSelect(id: string | null) {
  selectedId.value = id
  if (page.value && id) ui.select({ kind: 'state', pageId: page.value.id, nodeId: id })
}

function onTreeUpdate(tree: NonNullable<typeof page.value>['state_tree']) {
  if (!page.value) return
  page.value.state_tree = tree
  project.markDirty()
}

async function saveTemplate() {
  if (!page.value) return
  const name = window.prompt(t('template_save'), `${page.value.id}_cases`)
  if (!name) return
  await api.saveTemplate(name.trim(), page.value.state_tree || [])
  ui.showToast(t('saved'))
}

async function loadTemplate() {
  if (!page.value) return
  const { templates } = await api.listTemplates()
  if (!templates.length) {
    ui.showToast(t('template_empty'))
    return
  }
  const name = window.prompt(`${t('template_load')}\n${templates.join(', ')}`, templates[0])
  if (!name) return
  if (!confirm(t('template_replace', { name }))) return
  const { tree } = await api.loadTemplate(name.trim())
  page.value.state_tree = tree
  selectedId.value = tree[0]?.id ?? null
  project.markDirty()
}
</script>

<template>
  <div v-if="page" class="state">
    <header class="head">
      <div>
        <p class="eyebrow">{{ page.name }}</p>
        <h2><I18nText k="edit_case" /></h2>
      </div>
      <div class="tpl">
        <button class="sf-btn" type="button" @click="saveTemplate"><I18nText k="template_save" /></button>
        <button class="sf-btn" type="button" @click="loadTemplate"><I18nText k="template_load" /></button>
      </div>
    </header>

    <div class="split">
      <CaseTreePanel
        :model-value="page.state_tree || []"
        :selected-id="selectedId"
        :feature-key-hint="featureKeys[0] || null"
        @update:model-value="onTreeUpdate"
        @update:selected-id="onSelect"
      />
      <CaseDetailForm
        v-if="node"
        :node="node"
        :feature-keys="featureKeys"
        :macro-ids="macroIds"
        :page-id="page.id"
        :allow-post="true"
      />
      <p v-else class="sf-empty"><I18nText k="no_selection" /></p>
    </div>
  </div>
</template>

<style scoped>
.head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: var(--sf-space-3);
  margin-bottom: var(--sf-space-4);
  padding-bottom: var(--sf-space-3);
  border-bottom: 1px solid var(--sf-line);
}
.eyebrow {
  margin: 0 0 0.15rem;
  font-size: var(--sf-fs-xs);
  color: var(--sf-ink-faint);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
h2 {
  margin: 0;
  font-size: var(--sf-fs-xl);
  letter-spacing: -0.02em;
}
.tpl {
  display: flex;
  gap: 0.4rem;
  flex-wrap: wrap;
}
.split {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: var(--sf-space-5);
  min-height: 360px;
}
@media (max-width: 800px) {
  .split {
    grid-template-columns: 1fr;
  }
}
</style>
