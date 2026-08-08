<script setup lang="ts">
import { computed, ref } from 'vue'
import { api } from '@/api/client'
import { useProjectStore } from '@/stores/project'
import AssetUploadWizard from '@/components/AssetUploadWizard.vue'
import { bindFeatureFromScreenshot } from '@/utils/bindFromScreenshot'
import type { PageAsset } from '@/types/project'

const props = defineProps<{
  pageId: string
  featureId: string
  featureLabel: string
}>()

const emit = defineEmits<{
  close: []
  bound: []
}>()

const project = useProjectStore()
const fileInput = ref<HTMLInputElement | null>(null)
const pending = ref<{ file: File; url: string; name: string } | null>(null)
const busy = ref(false)
const err = ref('')

const assets = computed(() => project.project?.page_docs[props.pageId]?.assets || [])

async function bindExisting(a: PageAsset) {
  busy.value = true
  err.value = ''
  try {
    await api.bindFeature(props.pageId, props.featureId, {
      asset: a.relpath,
      search_roi: null,
    })
    await project.refreshFromServer()
    emit('bound')
    emit('close')
  } catch (e) {
    err.value = String(e)
  } finally {
    busy.value = false
  }
}

function onFiles(ev: Event) {
  const input = ev.target as HTMLInputElement
  const files = input.files
  if (!files?.length) return
  const f = files[0]
  pending.value = {
    file: f,
    url: URL.createObjectURL(f),
    name: f.name.replace(/\.[^.]+$/, '') || 'artwork',
  }
  input.value = ''
}

function cancelPending() {
  if (pending.value) URL.revokeObjectURL(pending.value.url)
  pending.value = null
}

async function finishUpload(payload: {
  searchRoi: number[] | null
  contentRoi: number[]
  name: string
}) {
  if (!pending.value) return
  const { file, url } = pending.value
  pending.value = null
  URL.revokeObjectURL(url)
  busy.value = true
  err.value = ''
  try {
    await bindFeatureFromScreenshot(props.pageId, props.featureId, file, payload)
    await project.refreshFromServer()
    emit('bound')
    emit('close')
  } catch (e) {
    err.value = String(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="mask" @click.self="emit('close')">
    <div class="dialog sf-panel">
      <header>
        <h3><I18nText k="bind_artwork_title" /></h3>
        <button type="button" class="sf-btn sf-btn-ghost" @click="emit('close')">×</button>
      </header>
      <p class="hint">
        <I18nText k="bind_artwork_hint" :vars="{ name: featureLabel }" />
      </p>
      <ol class="steps">
        <li><I18nText k="bind_step_search" /></li>
        <li><I18nText k="bind_step_content" /></li>
        <li><I18nText k="bind_step_select" /></li>
      </ol>
      <div class="toolbar">
        <button type="button" class="sf-btn sf-btn-primary" :disabled="busy" @click="fileInput?.click()">
          <I18nText k="upload_new_artwork" />
        </button>
        <input ref="fileInput" type="file" accept="image/*" hidden @change="onFiles" />
      </div>
      <p class="lib-label"><I18nText k="pick_template" /></p>
      <p v-if="!assets.length" class="empty"><I18nText k="empty_artwork_pick" /></p>
      <div v-else class="grid">
        <button
          v-for="a in assets"
          :key="a.relpath"
          type="button"
          class="tile"
          :disabled="busy"
          @click="bindExisting(a)"
        >
          <img :src="api.fileUrl(a.relpath)" :alt="a.name" />
          <span class="sf-mono">{{ a.name }}</span>
        </button>
      </div>
      <p v-if="err" class="err">{{ err }}</p>
      <div class="sf-dialog-foot">
        <button type="button" class="sf-btn" :disabled="busy" @click="emit('close')">
          <I18nText k="cancel" />
        </button>
      </div>
    </div>

    <AssetUploadWizard
      v-if="pending"
      :src="pending.url"
      :preferred-name="pending.name"
      mode="full"
      @close="cancelPending"
      @done="finishUpload"
    />
  </div>
</template>

<style scoped>
.mask {
  position: fixed;
  inset: 0;
  z-index: 40;
  background: rgb(26 34 32 / 45%);
  display: grid;
  place-items: center;
  padding: var(--sf-space-4);
}
.dialog {
  width: min(560px, 100%);
  max-height: min(80vh, 640px);
  display: flex;
  flex-direction: column;
  padding: var(--sf-space-4);
}
header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sf-space-2);
}
header h3 {
  margin: 0;
  font-size: var(--sf-fs-lg);
}
.hint {
  margin: 0.35rem 0 var(--sf-space-2);
  color: var(--sf-ink-muted);
  font-size: var(--sf-fs-sm);
}
.steps {
  margin: 0 0 var(--sf-space-3);
  padding-left: 1.2rem;
  color: var(--sf-ink-faint);
  font-size: var(--sf-fs-xs);
  line-height: 1.45;
}
.toolbar {
  margin-bottom: var(--sf-space-3);
}
.lib-label {
  margin: 0 0 var(--sf-space-2);
  font-size: var(--sf-fs-xs);
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--sf-ink-faint);
}
.empty {
  color: var(--sf-ink-faint);
  font-size: var(--sf-fs-sm);
  margin: 0 0 var(--sf-space-3);
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
  gap: var(--sf-space-2);
  overflow: auto;
  min-height: 0;
  flex: 1;
}
.tile {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  margin: 0;
  padding: 0.35rem;
  border: 1px solid var(--sf-line);
  border-radius: var(--sf-radius);
  background: var(--sf-surface);
  cursor: pointer;
  text-align: left;
}
.tile:hover:not(:disabled) {
  border-color: var(--sf-accent);
  box-shadow: 0 0 0 2px var(--sf-accent-soft);
}
.tile img {
  width: 100%;
  aspect-ratio: 16 / 10;
  object-fit: contain;
  background: #111;
  border-radius: 4px;
}
.tile span {
  font-size: var(--sf-fs-xs);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.err {
  color: var(--sf-danger);
  font-size: var(--sf-fs-sm);
  margin: var(--sf-space-2) 0 0;
}
</style>
