<script setup lang="ts">
import { computed } from 'vue'
import { useProjectStore } from '@/stores/project'
import { useUiStore } from '@/stores/ui'
import SectionTitle from '@/components/SectionTitle.vue'

const project = useProjectStore()
const ui = useUiStore()

const pages = computed(() =>
  Object.entries(project.project?.page_docs || {}).map(([id, doc]) => ({
    id,
    name: doc.name || id,
    cases: (doc.state_tree || []).length,
    pair: doc.pair_with || null,
  })),
)

function addPage() {
  ui.pageWizardOpen = true
}
</script>

<template>
  <div>
    <header class="head">
      <SectionTitle title-key="sec_pages" help-key="help_page_images" />
      <div class="sf-btn-bar">
        <button class="sf-btn sf-btn-primary" type="button" @click="addPage"><I18nText k="add_page" /></button>
      </div>
    </header>
    <ul class="list">
      <li v-for="p in pages" :key="p.id">
        <button class="item" type="button" @click="ui.select({ kind: 'page', pageId: p.id })">
          <span>
            <strong>{{ p.name }}</strong>
            <span class="meta sf-mono">{{ p.id }} · <I18nText k="cases_count" :vars="{ n: p.cases }" /></span>
          </span>
          <span v-if="p.pair" class="sf-badge"><I18nText k="pair_with_label" :vars="{ name: p.pair }" /></span>
        </button>
      </li>
    </ul>
    <p v-if="!pages.length" class="sf-empty"><I18nText k="empty_pages" /></p>
    <button class="sf-btn linkish" type="button" @click="ui.select({ kind: 'pairs' })">
      <I18nText k="page_pairs" /> →
    </button>
  </div>
</template>

<style scoped>
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--sf-space-4);
  gap: var(--sf-space-3);
}
.head :deep(.row) {
  margin-bottom: 0;
}
.list {
  list-style: none;
  margin: 0 0 var(--sf-space-4);
  padding: 0;
  display: grid;
  gap: var(--sf-space-2);
}
.item {
  width: 100%;
  text-align: left;
  border: 1px solid var(--sf-line);
  background: var(--sf-surface);
  border-radius: var(--sf-radius);
  padding: var(--sf-space-3) var(--sf-space-4);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--sf-space-3);
}
.item:hover {
  border-color: var(--sf-accent);
  background: var(--sf-accent-soft);
}
.meta {
  display: block;
  margin-top: 0.2rem;
  color: var(--sf-ink-faint);
  font-size: var(--sf-fs-xs);
}
.linkish {
  border: none;
  background: transparent;
  color: var(--sf-accent);
  padding: 0;
}
</style>
