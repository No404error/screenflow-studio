<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from '@/i18n'
import { useUiStore } from '@/stores/ui'
import { usePrefsStore } from '@/stores/prefs'
import { useProjectStore } from '@/stores/project'
import AssetGrid from '@/components/AssetGrid.vue'
import MatchSetupPanel from '@/components/MatchSetupPanel.vue'
import ArtworkLibrary from '@/components/ArtworkLibrary.vue'
import PostEditor from '@/components/PostEditor.vue'
import SectionHelp from '@/components/SectionHelp.vue'

const { t } = useI18n()
const ui = useUiStore()
const prefs = usePrefsStore()
const project = useProjectStore()
const selectedFeatureId = ref<string | null>(null)

const page = computed(() => {
  const id = ui.selection.pageId
  if (!id || !project.project) return null
  return project.project.page_docs[id] || null
})

watch(
  () => page.value?.id,
  () => {
    selectedFeatureId.value = null
  },
)

function mark() {
  project.markDirty()
}

async function remove() {
  if (!page.value) return
  if (!confirm(t('confirm_delete_page', { name: page.value.name }))) return
  await project.removePage(page.value.id)
}

function openCases() {
  if (!page.value) return
  const first = page.value.state_tree?.[0]
  if (first) ui.select({ kind: 'state', pageId: page.value.id, nodeId: first.id })
  else ui.select({ kind: 'page', pageId: page.value.id })
}
</script>

<template>
  <div v-if="page" class="page">
    <header class="head">
      <div class="titles">
        <label class="name-field">
          <span class="sf-label"><I18nText k="name" /></span>
          <input v-model="page.name" class="sf-input name-input" @input="mark" />
        </label>
        <p class="sf-mono path">{{ page.id }}</p>
      </div>
      <div class="sf-btn-bar head-actions">
        <button class="sf-btn" type="button" @click="openCases"><I18nText k="expand_cases" /></button>
        <button class="sf-btn sf-btn-ghost danger" type="button" @click="remove"><I18nText k="delete" /></button>
      </div>
    </header>

    <section class="block">
      <AssetGrid :page-id="page.id" @select="selectedFeatureId = $event" />
    </section>

    <section class="block">
      <MatchSetupPanel :page-id="page.id" />
    </section>

    <details
      class="block artwork lib-fold"
      :open="prefs.templateLibraryOpen"
      @toggle="prefs.templateLibraryOpen = ($event.target as HTMLDetailsElement).open"
    >
      <summary>
        <span class="sum-left">
          <I18nText k="sec_page_artwork" />
          <SectionHelp help-key="help_page_artwork" />
        </span>
      </summary>
      <ArtworkLibrary :page-id="page.id" :embedded="true" />
    </details>

    <details class="adv">
      <summary>
        <span class="sum-left">
          <I18nText k="sec_page_match" />
          <SectionHelp help-key="help_page_match" />
        </span>
      </summary>
      <div class="sf-grid-fields">
        <label class="sf-field">
          <span class="sf-label"><I18nText k="priority" /></span>
          <input v-model.number="page.detect_priority" class="sf-input" type="number" @input="mark" />
        </label>
        <label class="sf-field sf-field-select">
          <span class="sf-label"><I18nText k="pair_with" /></span>
          <select v-model="page.pair_with" class="sf-select" @change="mark">
            <option :value="null">—</option>
            <option
              v-for="pid in Object.keys(project.project!.page_docs).filter((x) => x !== page!.id)"
              :key="pid"
              :value="pid"
            >
              {{ project.project!.page_docs[pid]?.name || pid }}
            </option>
          </select>
        </label>
      </div>
    </details>

    <details class="adv">
      <summary>
        <span class="sum-left">
          <I18nText k="sec_page_default_post" />
          <SectionHelp help-key="help_page_default_post" />
        </span>
      </summary>
      <PostEditor v-if="page" v-model="page.default_post" :page-id="page.id" @change="mark" />
    </details>
  </div>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: var(--sf-space-5);
  max-width: 960px;
}
.head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--sf-space-3);
  flex-wrap: wrap;
}
.titles {
  min-width: 0;
  flex: 1;
}
.name-field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.name-input {
  font-size: var(--sf-fs-lg);
  font-weight: 600;
}
.path {
  margin: 0.25rem 0 0;
  color: var(--sf-ink-faint);
  font-size: var(--sf-fs-xs);
}
.block {
  padding: 0;
}
.lib-fold,
.adv {
  border: 1px solid var(--sf-line);
  border-radius: var(--sf-radius);
  padding: var(--sf-space-3) var(--sf-space-4);
  background: var(--sf-surface);
}
.lib-fold summary,
.adv summary {
  cursor: pointer;
  list-style: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.sum-left {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}
.sf-grid-fields {
  margin-top: var(--sf-space-3);
}
</style>
