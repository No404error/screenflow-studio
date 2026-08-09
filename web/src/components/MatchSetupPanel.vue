<script setup lang="ts">
import { computed, ref } from 'vue'
import { api } from '@/api/client'
import { useI18n } from '@/i18n'
import { useEscapeKey } from '@/composables/useEscapeKey'
import { useProjectStore } from '@/stores/project'
import { useUiStore } from '@/stores/ui'
import SectionTitle from '@/components/SectionTitle.vue'
import AssetUploadWizard from '@/components/AssetUploadWizard.vue'
import PrivacyRedactDialog from '@/components/PrivacyRedactDialog.vue'
import RoiCropDialog from '@/components/RoiCropDialog.vue'
import FeatureOverlayPreview from '@/components/FeatureOverlayPreview.vue'
import {
  createVisualFromOriginal,
  fileFromRelpath,
} from '@/utils/createVisualFromScreenshot'
import { cropFileByRoi } from '@/utils/cropUpload'
import type { MatchSetup, PageOriginal } from '@/types/project'

const props = defineProps<{
  pageId: string
  /** Highlight the setup currently selected by this feature. */
  highlightFeatureId?: string | null
}>()

const { t } = useI18n()
const project = useProjectStore()
const ui = useUiStore()
const page = computed(() => project.project?.page_docs[props.pageId])
const visuals = computed(() => {
  const map = page.value?.visuals || {}
  return Object.values(map).sort((a, b) => a.label.localeCompare(b.label) || a.id.localeCompare(b.id))
})
const sources = computed(() => {
  const map = page.value?.sources || {}
  return Object.values(map).sort(
    (a, b) => a.label.localeCompare(b.label) || a.id.localeCompare(b.id),
  )
})
const features = computed(() => Object.values(page.value?.features || {}))

type Pending = {
  file: File
  url: string
  name: string
  sourceId: string | null
}
const pending = ref<Pending | null>(null)
/** New-file upload only: redact before AssetUploadWizard. */
const redactPending = ref<{ file: File; url: string; name: string } | null>(null)
const pickOpen = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const cropTarget = ref<MatchSetup | null>(null)
const cropKind = ref<'search' | 'content'>('search')
const preview = ref<MatchSetup | null>(null)
const busy = ref(false)
const err = ref('')

useEscapeKey(() => {
  if (redactPending.value) {
    cancelRedact()
    return true
  }
  if (pickOpen.value) {
    pickOpen.value = false
    return true
  }
  if (preview.value) {
    preview.value = null
    return true
  }
  return false
})

const highlightedVisualId = computed(() => {
  const fid = props.highlightFeatureId
  if (!fid) return null
  return page.value?.features?.[fid]?.visual_id || null
})

function sourceOf(v: MatchSetup): PageOriginal | null {
  const sid = v.source_id
  if (!sid) return null
  return page.value?.sources?.[sid] || null
}

function sourcePath(v: MatchSetup): string | null {
  return sourceOf(v)?.path || null
}

function usersOf(vid: string): string[] {
  const feats = page.value?.features || {}
  return Object.values(feats)
    .filter((f) => f.visual_id === vid)
    .map((f) => f.label || f.id)
}

async function offerSelectOnFeature(visualId: string) {
  if (!features.value.length) return
  if (
    !(await ui.askConfirm({
      title: t('use_setup_on_feature'),
      confirmLabel: t('use_setup_confirm_action'),
    }))
  ) {
    return
  }
  const pick = await ui.askSelect({
    title: t('use_setup_pick_feature'),
    options: features.value.map((f) => ({ id: f.id, label: f.label || f.id })),
  })
  if (pick == null) return
  if (!page.value?.features?.[pick]) {
    err.value = t('use_setup_pick_feature')
    return
  }
  project.applyServerSnapshot(await api.selectFeatureVisual(props.pageId, pick, visualId))
}

function newestVisualId(before: Set<string>): string | null {
  const map = page.value?.visuals || {}
  for (const id of Object.keys(map)) {
    if (!before.has(id)) return id
  }
  return Object.keys(map).at(-1) || null
}

function startAdd() {
  if (pickOpen.value) {
    pickOpen.value = false
    return
  }
  if (!sources.value.length) {
    fileInput.value?.click()
    return
  }
  pickOpen.value = true
}

function togglePreview(v: MatchSetup) {
  preview.value = preview.value?.id === v.id ? null : v
}

function uploadNewOriginal() {
  pickOpen.value = false
  fileInput.value?.click()
}

async function pickExisting(s: PageOriginal) {
  pickOpen.value = false
  busy.value = true
  err.value = ''
  try {
    const file = await fileFromRelpath(s.path, s.label || s.id)
    if (pending.value) URL.revokeObjectURL(pending.value.url)
    pending.value = {
      file,
      url: api.fileUrl(s.path),
      name: s.label || s.id,
      sourceId: s.id,
    }
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
  input.value = ''
  cancelPending()
  cancelRedact()
  redactPending.value = {
    file: f,
    url: URL.createObjectURL(f),
    name: f.name.replace(/\.[^.]+$/, '') || 'setup',
  }
}

function cancelRedact() {
  if (redactPending.value) URL.revokeObjectURL(redactPending.value.url)
  redactPending.value = null
}

function onRedactDone(file: File) {
  const held = redactPending.value
  if (!held) return
  const name = held.name
  const url = URL.createObjectURL(file)
  cancelRedact()
  if (pending.value?.url.startsWith('blob:')) URL.revokeObjectURL(pending.value.url)
  pending.value = {
    file,
    url,
    name,
    sourceId: null,
  }
}

function cancelPending() {
  if (pending.value?.url.startsWith('blob:')) URL.revokeObjectURL(pending.value.url)
  pending.value = null
}

async function finishWizard(payload: {
  searchRoi: number[] | null
  contentRoi: number[]
  name: string
}) {
  if (!pending.value) return
  const held = pending.value
  busy.value = true
  err.value = ''
  const before = new Set(Object.keys(page.value?.visuals || {}))
  const beforeSources = new Set(Object.keys(page.value?.sources || {}))
  try {
    project.applyServerSnapshot(
      await createVisualFromOriginal(props.pageId, {
        sourceId: held.sourceId,
        file: held.file,
        searchRoi: payload.searchRoi,
        contentRoi: payload.contentRoi,
        name: payload.name,
        beforeSourceIds: beforeSources,
      }),
    )
    if (held.url.startsWith('blob:')) URL.revokeObjectURL(held.url)
    pending.value = null
    const vid = newestVisualId(before)
    if (vid) await offerSelectOnFeature(vid)
  } catch (e) {
    err.value = String(e)
  } finally {
    busy.value = false
  }
}

async function rename(v: MatchSetup) {
  const next = await ui.askPrompt({
    title: t('setup_label_prompt'),
    initial: v.label || v.id,
  })
  if (next == null) return
  project.applyServerSnapshot(
    await api.patchVisual(props.pageId, v.id, { label: next.trim() || v.id }),
  )
}

async function onRoi(roi: number[] | null) {
  if (!cropTarget.value) return
  const id = cropTarget.value.id
  const src = sourceOf(cropTarget.value)
  if (cropKind.value === 'content') {
    // Re-crop derived template when content ROI changes and we have the original
    if (roi && src) {
      busy.value = true
      err.value = ''
      try {
        const file = await fileFromRelpath(src.path, cropTarget.value.label || id)
        const toSend = await cropFileByRoi(file, roi)
        const uploaded = await api.uploadAsset(props.pageId, toSend, cropTarget.value.label || id)
        project.applyServerSnapshot(
          await api.patchVisual(props.pageId, id, {
            content_roi: roi,
            template: uploaded.relpath,
          }),
        )
      } catch (e) {
        err.value = String(e)
      } finally {
        busy.value = false
        cropTarget.value = null
      }
      return
    }
    project.applyServerSnapshot(
      await api.patchVisual(props.pageId, id, {
        content_roi: roi,
        clear_content_roi: roi == null,
      }),
    )
  } else {
    project.applyServerSnapshot(
      await api.patchVisual(props.pageId, id, {
        search_roi: roi,
        clear_search_roi: roi == null,
      }),
    )
  }
  cropTarget.value = null
}

async function remove(v: MatchSetup) {
  const used = usersOf(v.id)
  const name = v.label || v.id
  if (
    !(await ui.askConfirm({
      title: used.length
        ? t('confirm_delete_setup_used', { name, features: used.join(', ') })
        : t('confirm_delete_named', { name }),
      danger: true,
      confirmLabel: t('delete'),
    }))
  ) {
    return
  }
  project.applyServerSnapshot(await api.deleteVisual(props.pageId, v.id))
}
</script>

<template>
  <div class="sf-panel zone">
    <div class="head">
      <SectionTitle title-key="sec_page_setups" help-key="help_page_setups" />
      <div class="sf-btn-bar">
        <button type="button" class="sf-btn sf-btn-primary" :disabled="busy" @click="startAdd">
          <I18nText k="add_setup_from_original" />
        </button>
        <input ref="fileInput" type="file" accept="image/*" hidden @change="onFiles" />
      </div>
    </div>
    <p class="intro"><I18nText k="setups_intro" /></p>
    <p v-if="err" class="err">{{ err }}</p>

    <div v-if="pickOpen" class="picker">
      <p class="picker-title"><I18nText k="pick_original_for_setup" /></p>
      <div class="picker-grid">
        <button
          v-for="s in sources"
          :key="s.id"
          type="button"
          class="tile"
          :disabled="busy"
          @click="pickExisting(s)"
        >
          <img :src="api.fileUrl(s.path)" :alt="s.label || s.id" />
          <span>{{ s.label || s.id }}</span>
        </button>
      </div>
      <div class="sf-btn-bar">
        <button type="button" class="sf-btn" :disabled="busy" @click="uploadNewOriginal">
          <I18nText k="upload_original_and_setup" />
        </button>
        <button type="button" class="sf-btn sf-btn-ghost" @click="pickOpen = false">
          <I18nText k="cancel" />
        </button>
      </div>
    </div>

    <div v-if="!visuals.length" class="empty"><I18nText k="empty_setups" /></div>
    <div v-else class="grid">
      <figure
        v-for="v in visuals"
        :key="v.id"
        class="card"
        :class="{ hi: highlightedVisualId === v.id }"
      >
        <button type="button" class="thumb" @click="togglePreview(v)">
          <img v-if="v.asset" :src="api.fileUrl(v.asset)" :alt="v.label" />
        </button>
        <figcaption>
          <span class="fname">{{ v.label || v.id }}</span>
          <span class="sf-badge">
            {{ v.search_roi ? t('search_custom') : t('search_full') }}
          </span>
          <span v-if="sourceOf(v)" class="sf-badge">
            <I18nText k="setup_on_original" :vars="{ name: sourceOf(v)!.label || sourceOf(v)!.id }" />
          </span>
          <span v-if="usersOf(v.id).length" class="sf-badge">
            <I18nText k="setup_used_by" :vars="{ names: usersOf(v.id).join(', ') }" />
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
            :disabled="!sourcePath(v)"
            :title="sourcePath(v) ? t('edit_matching_search') : t('no_original_for_overlay')"
            @click="cropKind = 'search'; cropTarget = v"
          >
            <I18nText k="edit_matching_search" />
          </button>
          <button
            type="button"
            class="sf-btn sf-btn-ghost"
            :disabled="!sourcePath(v)"
            :title="sourcePath(v) ? t('edit_matching_content') : t('no_original_for_overlay')"
            @click="cropKind = 'content'; cropTarget = v"
          >
            <I18nText k="edit_matching_content" />
          </button>
          <button type="button" class="sf-btn sf-btn-ghost danger" @click="remove(v)">
            <I18nText k="delete" />
          </button>
        </div>
      </figure>
    </div>

    <PrivacyRedactDialog
      v-if="redactPending"
      :src="redactPending.url"
      :file="redactPending.file"
      @close="cancelRedact"
      @done="onRedactDone"
    />
    <AssetUploadWizard
      v-if="pending"
      :src="pending.url"
      :preferred-name="pending.name"
      mode="full"
      context="setup"
      @close="cancelPending"
      @done="finishWizard"
    />
    <RoiCropDialog
      v-if="cropTarget && sourcePath(cropTarget)"
      :src="api.fileUrl(sourcePath(cropTarget)!)"
      :roi="(cropKind === 'content' ? cropTarget.content_roi : cropTarget.search_roi) || null"
      :content-roi="cropKind === 'search' ? cropTarget.content_roi || null : null"
      @close="cropTarget = null"
      @save="onRoi"
    />
    <FeatureOverlayPreview
      v-if="preview"
      :src="sourcePath(preview) ? api.fileUrl(sourcePath(preview)!) : api.fileUrl(preview.asset)"
      :title="preview.label || preview.id"
      :meta="sourcePath(preview) || preview.asset"
      :on-source="!!sourcePath(preview)"
      :search-roi="preview.search_roi || null"
      :content-roi="preview.content_roi || null"
      @close="preview = null"
    />
  </div>
</template>

<style scoped>
.zone {
  padding: var(--sf-space-4);
}
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
.picker {
  margin-bottom: var(--sf-space-4);
  padding: var(--sf-space-3);
  border: 1px solid var(--sf-line);
  border-radius: var(--sf-radius);
  background: var(--sf-surface);
}
.picker-title {
  margin: 0 0 var(--sf-space-2);
  font-size: var(--sf-fs-sm);
  font-weight: 600;
}
.picker-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: var(--sf-space-2);
  margin-bottom: var(--sf-space-3);
}
.tile {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.3rem;
  border: 1px solid var(--sf-line);
  border-radius: var(--sf-radius);
  background: var(--sf-bg);
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
.card.hi {
  border-color: var(--sf-accent);
  box-shadow: 0 0 0 2px var(--sf-accent-soft);
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
  background: var(--sf-warn-soft);
  color: var(--sf-warn);
}
.card-actions {
  flex-wrap: wrap;
}
</style>
