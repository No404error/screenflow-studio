<script setup lang="ts">
import { computed, ref } from 'vue'
import { api } from '@/api/client'
import { useI18n } from '@/i18n'
import { useProjectStore } from '@/stores/project'
import SectionTitle from '@/components/SectionTitle.vue'
import AssetUploadWizard from '@/components/AssetUploadWizard.vue'
import RoiCropDialog from '@/components/RoiCropDialog.vue'
import FeatureOverlayPreview from '@/components/FeatureOverlayPreview.vue'
import { createVisualFromScreenshot } from '@/utils/createVisualFromScreenshot'
import type { MatchSetup, PageAsset } from '@/types/project'

const props = defineProps<{
  pageId: string
}>()

const { t } = useI18n()
const project = useProjectStore()
const page = computed(() => project.project?.page_docs[props.pageId])
const visuals = computed(() => {
  const map = page.value?.visuals || {}
  return Object.values(map).sort((a, b) => a.label.localeCompare(b.label) || a.id.localeCompare(b.id))
})
const assets = computed(() => page.value?.assets || [])
const pageSource = computed(() => page.value?.source || null)

const pending = ref<{ file: File; url: string; name: string } | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const cropTarget = ref<MatchSetup | null>(null)
const preview = ref<MatchSetup | null>(null)
const busy = ref(false)
const err = ref('')

function usersOf(vid: string): string[] {
  const feats = page.value?.features || {}
  return Object.values(feats)
    .filter((f) => f.visual_id === vid)
    .map((f) => f.label || f.id)
}

async function addFromScreenshot() {
  fileInput.value?.click()
}

function onFiles(ev: Event) {
  const input = ev.target as HTMLInputElement
  const files = input.files
  if (!files?.length) return
  const f = files[0]
  pending.value = {
    file: f,
    url: URL.createObjectURL(f),
    name: f.name.replace(/\.[^.]+$/, '') || 'setup',
  }
  input.value = ''
}

function cancelPending() {
  if (pending.value) URL.revokeObjectURL(pending.value.url)
  pending.value = null
}

async function finishWizard(payload: {
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
    await createVisualFromScreenshot(props.pageId, file, payload)
    await project.refreshFromServer()
  } catch (e) {
    err.value = String(e)
  } finally {
    busy.value = false
  }
}

async function addFromTemplate(a: PageAsset) {
  busy.value = true
  err.value = ''
  try {
    await api.createVisual(props.pageId, {
      template: a.relpath,
      label: a.name,
      search_roi: null,
    })
    await project.refreshFromServer()
  } catch (e) {
    err.value = String(e)
  } finally {
    busy.value = false
  }
}

async function rename(v: MatchSetup) {
  const next = prompt(t('setup_label_prompt'), v.label || v.id)
  if (next == null) return
  await api.patchVisual(props.pageId, v.id, { label: next.trim() || v.id })
  await project.refreshFromServer()
}

async function onRoi(roi: number[] | null) {
  if (!cropTarget.value) return
  await api.patchVisual(props.pageId, cropTarget.value.id, {
    search_roi: roi,
    clear_search_roi: roi == null,
  })
  cropTarget.value = null
  await project.refreshFromServer()
}

async function remove(v: MatchSetup) {
  const used = usersOf(v.id)
  const msg = used.length
    ? t('confirm_delete_setup_used', { name: v.label || v.id, features: used.join(', ') })
    : t('confirm_delete_named', { name: v.label || v.id })
  if (!confirm(msg)) return
  await api.deleteVisual(props.pageId, v.id)
  await project.refreshFromServer()
}
</script>

<template>
  <div>
    <div class="head">
      <SectionTitle title-key="sec_page_setups" help-key="help_page_setups" />
      <div class="sf-btn-bar">
        <button type="button" class="sf-btn sf-btn-primary" :disabled="busy" @click="addFromScreenshot">
          <I18nText k="add_setup_screenshot" />
        </button>
        <input ref="fileInput" type="file" accept="image/*" hidden @change="onFiles" />
      </div>
    </div>
    <p class="intro"><I18nText k="setups_intro" /></p>
    <p v-if="err" class="err">{{ err }}</p>

    <div v-if="!visuals.length" class="empty"><I18nText k="empty_setups" /></div>
    <div v-else class="grid">
      <figure v-for="v in visuals" :key="v.id" class="card">
        <button type="button" class="thumb" @click="preview = v">
          <img v-if="v.asset" :src="api.fileUrl(v.asset)" :alt="v.label" />
        </button>
        <figcaption>
          <span class="fname">{{ v.label || v.id }}</span>
          <span class="sf-badge">
            {{ v.search_roi ? t('search_custom') : t('search_full') }}
          </span>
          <span v-if="usersOf(v.id).length" class="sf-badge">
            <I18nText k="setup_used_n" :vars="{ n: usersOf(v.id).length }" />
          </span>
          <span v-else class="sf-badge warn"><I18nText k="setup_idle" /></span>
        </figcaption>
        <div class="sf-btn-bar card-actions">
          <button type="button" class="sf-btn sf-btn-ghost" @click="rename(v)">
            <I18nText k="rename" />
          </button>
          <button
            type="button"
            class="sf-btn sf-btn-ghost"
            :disabled="!pageSource"
            :title="pageSource ? t('edit_matching_search') : t('no_source_for_overlay')"
            @click="cropTarget = v"
          >
            <I18nText k="edit_matching_search" />
          </button>
          <button type="button" class="sf-btn sf-btn-ghost danger" @click="remove(v)">
            <I18nText k="delete" />
          </button>
        </div>
      </figure>
    </div>

    <details v-if="assets.length" class="from-lib">
      <summary><I18nText k="add_setup_from_template" /></summary>
      <div class="lib-grid">
        <button
          v-for="a in assets"
          :key="a.relpath"
          type="button"
          class="tile"
          :disabled="busy"
          @click="addFromTemplate(a)"
        >
          <img :src="api.fileUrl(a.relpath)" :alt="a.name" />
          <span class="sf-mono">{{ a.name }}</span>
        </button>
      </div>
    </details>

    <AssetUploadWizard
      v-if="pending"
      :src="pending.url"
      :preferred-name="pending.name"
      mode="full"
      @close="cancelPending"
      @done="finishWizard"
    />
    <RoiCropDialog
      v-if="cropTarget && pageSource"
      :src="api.fileUrl(pageSource)"
      :roi="cropTarget.search_roi || null"
      :content-roi="cropTarget.content_roi || null"
      @close="cropTarget = null"
      @save="onRoi"
    />
    <FeatureOverlayPreview
      v-if="preview"
      :src="pageSource ? api.fileUrl(pageSource) : api.fileUrl(preview.asset)"
      :title="preview.label || preview.id"
      :meta="pageSource || preview.asset"
      :on-source="!!pageSource"
      :search-roi="preview.search_roi || null"
      :content-roi="preview.content_roi || null"
      @close="preview = null"
    />
  </div>
</template>

<style scoped>
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sf-space-3);
  flex-wrap: wrap;
  margin-bottom: var(--sf-space-2);
}
.intro {
  margin: 0 0 var(--sf-space-3);
  color: var(--sf-ink-faint);
  font-size: var(--sf-fs-sm);
}
.empty,
.err {
  font-size: var(--sf-fs-sm);
  margin-bottom: var(--sf-space-3);
}
.err {
  color: var(--sf-danger);
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: var(--sf-space-3);
}
.card {
  margin: 0;
  border: 1px solid var(--sf-line);
  border-radius: var(--sf-radius);
  padding: 0.5rem;
  background: var(--sf-surface);
}
.thumb {
  display: block;
  width: 100%;
  padding: 0;
  border: none;
  background: #111;
  border-radius: 4px;
  overflow: hidden;
  aspect-ratio: 16 / 10;
  cursor: zoom-in;
}
.thumb img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
figcaption {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  align-items: center;
  margin: 0.45rem 0.1rem;
  font-size: var(--sf-fs-xs);
}
.fname {
  font-weight: 600;
  color: var(--sf-ink);
}
.warn {
  background: color-mix(in srgb, #c45c26 18%, transparent);
  color: #a34a1a;
}
.card-actions {
  flex-wrap: wrap;
}
.from-lib {
  margin-top: var(--sf-space-4);
  border-top: 1px solid var(--sf-line);
  padding-top: var(--sf-space-3);
}
.from-lib summary {
  cursor: pointer;
  font-size: var(--sf-fs-xs);
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--sf-ink-faint);
  margin-bottom: var(--sf-space-2);
}
.lib-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: var(--sf-space-2);
}
.tile {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.3rem;
  border: 1px solid var(--sf-line);
  border-radius: var(--sf-radius);
  background: var(--sf-surface);
  cursor: pointer;
  text-align: left;
}
.tile img {
  width: 100%;
  aspect-ratio: 16 / 10;
  object-fit: contain;
  background: #111;
  border-radius: 3px;
}
.tile span {
  font-size: var(--sf-fs-xs);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
