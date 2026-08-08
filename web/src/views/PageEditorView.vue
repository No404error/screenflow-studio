<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from '@/i18n'
import { api } from '@/api/client'
import { useUiStore } from '@/stores/ui'
import { useProjectStore } from '@/stores/project'
import AssetGrid from '@/components/AssetGrid.vue'
import PostEditor from '@/components/PostEditor.vue'

const { t } = useI18n()
const ui = useUiStore()
const project = useProjectStore()

const page = computed(() => {
  const id = ui.selection.pageId
  if (!id || !project.project) return null
  return project.project.page_docs[id] || null
})

function mark() {
  project.markDirty()
}

async function remove() {
  if (!page.value) return
  if (!confirm(`Delete page ${page.value.name}?`)) return
  await project.removePage(page.value.id)
}
</script>

<template>
  <div v-if="page" class="page">
    <header class="head">
      <div>
        <h2>{{ page.name || page.id }}</h2>
        <p class="sf-mono path">{{ page.id }}</p>
      </div>
      <button class="sf-btn sf-btn-danger" type="button" @click="remove">{{ t('delete') }}</button>
    </header>

    <section class="detect sf-panel">
      <h3 class="sf-section-title">{{ t('detect') }}</h3>
      <img
        v-if="page.detect"
        class="preview"
        :src="api.fileUrl(page.detect)"
        alt="detect"
        @error="($event.target as HTMLImageElement).style.display = 'none'"
      />
      <p v-else class="sf-empty">Upload a feature image to use as detect.</p>
      <label class="sf-field">
        <span class="sf-label">{{ t('name') }}</span>
        <input v-model="page.name" class="sf-input" @input="mark" />
      </label>
    </section>

    <AssetGrid :page-id="page.id" :assets="page.assets || []" :detect-relpath="page.detect" />

    <details class="adv">
      <summary>{{ t('advanced') }}</summary>
      <div class="grid">
        <label class="sf-field">
          <span class="sf-label">detect priority</span>
          <input v-model.number="page.detect_priority" class="sf-input" type="number" @input="mark" />
        </label>
        <label class="sf-field">
          <span class="sf-label">pair with</span>
          <select v-model="page.pair_with" class="sf-select" @change="mark">
            <option :value="null">—</option>
            <option
              v-for="pid in Object.keys(project.project!.page_docs).filter((x) => x !== page!.id)"
              :key="pid"
              :value="pid"
            >
              {{ project.project!.page_docs[pid].name || pid }}
            </option>
          </select>
        </label>
      </div>
      <PostEditor v-model="page.default_post" />
    </details>
  </div>
</template>

<style scoped>
.head {
  display: flex;
  justify-content: space-between;
  margin-bottom: var(--sf-space-4);
}
h2 {
  margin: 0;
}
.path {
  color: var(--sf-ink-faint);
  margin: 0.2rem 0 0;
  font-size: var(--sf-fs-sm);
}
.detect {
  padding: var(--sf-space-4);
  margin-bottom: var(--sf-space-5);
}
.preview {
  display: block;
  max-width: 100%;
  max-height: 220px;
  object-fit: contain;
  background: #111;
  border-radius: var(--sf-radius);
  margin-bottom: var(--sf-space-3);
}
.adv {
  margin-top: var(--sf-space-5);
  border: 1px solid var(--sf-line);
  border-radius: var(--sf-radius);
  padding: var(--sf-space-3);
}
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--sf-space-3);
  margin-top: var(--sf-space-3);
}
</style>
