<script setup lang="ts">
import { computed, ref } from 'vue'
import { api } from '@/api/client'
import { useI18n } from '@/i18n'
import { useProjectStore } from '@/stores/project'
import { useUiStore } from '@/stores/ui'
import SectionTitle from '@/components/SectionTitle.vue'
import AssetUploadWizard from '@/components/AssetUploadWizard.vue'
import ImageLightbox from '@/components/ImageLightbox.vue'
import { cropFileByRoi } from '@/utils/cropUpload'
import type { PageAsset } from '@/types/project'

const props = withDefaults(
  defineProps<{
    pageId: string
    /** When true, parent owns the section title (e.g. collapsed <details>). */
    embedded?: boolean
  }>(),
  { embedded: false },
)

const { t } = useI18n()
const project = useProjectStore()
const ui = useUiStore()
const fileInput = ref<HTMLInputElement | null>(null)
const pending = ref<{ file: File; url: string; name: string } | null>(null)
const preview = ref<PageAsset | null>(null)

const page = computed(() => project.project?.page_docs[props.pageId])
const assets = computed(() => page.value?.assets || [])
const features = computed(() => page.value?.features || {})

function linkedLabels(relpath: string): string[] {
  const visuals = page.value?.visuals || {}
  const setupIds = new Set(
    Object.values(visuals)
      .filter((v) => v.asset === relpath)
      .map((v) => v.id),
  )
  const fromSetups = Object.values(visuals)
    .filter((v) => v.asset === relpath)
    .map((v) => v.label || v.id)
  const fromFeatures = Object.values(features.value)
    .filter((f) => f.visual_id && setupIds.has(f.visual_id))
    .map((f) => f.label || f.id)
  return fromFeatures.length ? fromFeatures : fromSetups
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
  const held = pending.value
  try {
    const toSend = await cropFileByRoi(held.file, payload.contentRoi)
    await api.uploadAsset(props.pageId, toSend, payload.name || undefined)
    project.applyServerSnapshot(await api.getProject())
    URL.revokeObjectURL(held.url)
    pending.value = null
  } catch (e) {
    ui.showToast(String(e), 'danger')
    // Keep pending for retry.
  }
}

async function remove(a: PageAsset) {
  const used = linkedLabels(a.relpath)
  if (
    !(await ui.askConfirm({
      title: used.length
        ? t('confirm_delete_artwork_linked', { name: a.name, features: used.join(', ') })
        : t('confirm_delete_named', { name: a.name }),
      danger: true,
      confirmLabel: t('delete'),
    }))
  ) {
    return
  }
  project.applyServerSnapshot(await api.deleteAsset(props.pageId, a.name))
  if (preview.value?.relpath === a.relpath) preview.value = null
}
</script>

<template>
  <div>
    <div class="head" :class="{ embedded }">
      <SectionTitle
        v-if="!embedded"
        title-key="sec_page_artwork"
        help-key="help_page_artwork"
      />
      <div class="sf-btn-bar">
        <button class="sf-btn sf-btn-primary" type="button" @click="fileInput?.click()">
          <I18nText k="upload_artwork" />
        </button>
      </div>
      <input ref="fileInput" type="file" accept="image/*" hidden @change="onFiles" />
    </div>
    <p class="intro"><I18nText k="artwork_intro" /></p>
    <div v-if="!assets.length" class="empty"><I18nText k="empty_artwork" /></div>
    <div v-else class="grid">
      <figure v-for="a in assets" :key="a.relpath" class="card">
        <div class="thumb-wrap">
          <button type="button" class="thumb" :title="t('click_to_inspect')" @click="preview = a">
            <img :src="api.fileUrl(a.relpath)" :alt="a.name" />
          </button>
          <button
            type="button"
            class="sf-btn sf-btn-ghost danger card-del"
            :title="t('delete')"
            @click="remove(a)"
          >
            <I18nText k="delete" />
          </button>
        </div>
        <figcaption>
          <span class="sf-mono name">{{ a.name }}</span>
          <span v-if="linkedLabels(a.relpath).length" class="sf-badge">
            <I18nText
              k="artwork_linked_n"
              :vars="{ n: linkedLabels(a.relpath).length }"
            />
          </span>
          <span v-else class="sf-badge warn"><I18nText k="artwork_unused" /></span>
        </figcaption>
      </figure>
    </div>

    <ImageLightbox
      v-if="preview"
      :src="api.fileUrl(preview.relpath)"
      :title="preview.name"
      :meta="preview.relpath"
      @close="preview = null"
    />
    <AssetUploadWizard
      v-if="pending"
      :src="pending.url"
      :preferred-name="pending.name"
      mode="content"
      context="library"
      @close="cancelPending"
      @done="finishUpload"
    />
  </div>
</template>

<style scoped>
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sf-space-3);
  margin-bottom: var(--sf-space-2);
  flex-wrap: wrap;
}
.head.embedded {
  justify-content: flex-end;
  margin-bottom: var(--sf-space-2);
}
.head :deep(.row) {
  margin-bottom: 0;
}
.intro {
  margin: 0 0 var(--sf-space-3);
  color: var(--sf-ink-faint);
  font-size: var(--sf-fs-sm);
}
.empty {
  color: var(--sf-ink-faint);
  font-size: var(--sf-fs-sm);
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: var(--sf-space-3);
}
.card {
  margin: 0;
  border: 1px solid var(--sf-line);
  border-radius: var(--sf-radius);
  padding: 0.45rem;
  background: var(--sf-surface);
}
.thumb-wrap {
  position: relative;
}
.thumb {
  display: block;
  width: 100%;
  border: none;
  padding: 0;
  background: var(--sf-media-well);
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
.card-del {
  position: absolute;
  top: 0.25rem;
  right: 0.25rem;
  min-height: 1.5rem;
  padding: 0 0.4rem;
  font-size: var(--sf-fs-xs);
  opacity: 0;
  background: rgb(255 255 255 / 92%);
  border-color: transparent;
  transition: opacity 0.12s ease;
}
.card:hover .card-del,
.card:focus-within .card-del {
  opacity: 1;
}
figcaption {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  align-items: center;
  margin: 0.45rem 0.1rem 0.1rem;
  font-size: var(--sf-fs-xs);
}
.name {
  font-weight: 500;
}
.warn {
  background: color-mix(in srgb, #c45c26 18%, transparent);
  color: #a34a1a;
}
</style>
