<script setup lang="ts">
import { computed, ref } from 'vue'
import { api } from '@/api/client'
import { useI18n } from '@/i18n'
import { useProjectStore } from '@/stores/project'
import { useUiStore } from '@/stores/ui'
import SectionTitle from '@/components/SectionTitle.vue'
import ImageLightbox from '@/components/ImageLightbox.vue'
import PrivacyRedactDialog from '@/components/PrivacyRedactDialog.vue'
import type { PageOriginal } from '@/types/project'

const props = defineProps<{
  pageId: string
}>()

const { t } = useI18n()
const project = useProjectStore()
const ui = useUiStore()
const fileInput = ref<HTMLInputElement | null>(null)
const preview = ref<PageOriginal | null>(null)
const busy = ref(false)
const err = ref('')
const redactPending = ref<{ file: File; url: string; name: string } | null>(null)

const page = computed(() => project.project?.page_docs[props.pageId])
const sources = computed(() => {
  const map = page.value?.sources || {}
  return Object.values(map).sort(
    (a, b) => a.label.localeCompare(b.label) || a.id.localeCompare(b.id),
  )
})

function usersOf(sourceId: string): string[] {
  const visuals = page.value?.visuals || {}
  return Object.values(visuals)
    .filter((v) => v.source_id === sourceId)
    .map((v) => v.label || v.id)
}

function pickFile() {
  fileInput.value?.click()
}

function onFiles(ev: Event) {
  const input = ev.target as HTMLInputElement
  const files = input.files
  if (!files?.length) return
  const file = files[0]
  input.value = ''
  err.value = ''
  cancelRedact()
  redactPending.value = {
    file,
    url: URL.createObjectURL(file),
    name: file.name.replace(/\.[^.]+$/, '') || 'original',
  }
}

function cancelRedact() {
  if (redactPending.value) URL.revokeObjectURL(redactPending.value.url)
  redactPending.value = null
}

async function onRedactDone(file: File) {
  const held = redactPending.value
  if (!held) return
  const label = held.name
  cancelRedact()
  busy.value = true
  err.value = ''
  try {
    project.applyServerSnapshot(await api.uploadPageSource(props.pageId, file, label))
  } catch (e) {
    err.value = String(e)
  } finally {
    busy.value = false
  }
}

async function rename(s: PageOriginal) {
  const next = await ui.askPrompt({
    title: t('original_label_prompt'),
    initial: s.label || s.id,
  })
  if (next == null) return
  project.applyServerSnapshot(
    await api.patchPageSource(props.pageId, s.id, { label: next.trim() || s.id }),
  )
}

async function remove(s: PageOriginal) {
  const used = usersOf(s.id)
  const name = s.label || s.id
  if (
    !(await ui.askConfirm({
      title: used.length
        ? t('confirm_delete_original_used', { name, setups: used.join(', ') })
        : t('confirm_delete_named', { name }),
      danger: true,
      confirmLabel: t('delete'),
    }))
  ) {
    return
  }
  busy.value = true
  err.value = ''
  try {
    project.applyServerSnapshot(await api.deletePageSource(props.pageId, s.id))
    if (preview.value?.id === s.id) preview.value = null
  } catch (e) {
    err.value = String(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="sf-panel zone">
    <div class="head">
      <SectionTitle title-key="sec_page_originals" help-key="help_page_originals" />
      <div class="sf-btn-bar">
        <button type="button" class="sf-btn sf-btn-primary" :disabled="busy" @click="pickFile">
          <I18nText k="upload_page_original" />
        </button>
        <input ref="fileInput" type="file" accept="image/*" hidden @change="onFiles" />
      </div>
    </div>
    <p class="intro"><I18nText k="page_originals_intro" /></p>
    <p v-if="err" class="err">{{ err }}</p>

    <div v-if="!sources.length" class="empty"><I18nText k="empty_page_originals" /></div>
    <div v-else class="grid">
      <figure v-for="s in sources" :key="s.id" class="card">
        <button
          type="button"
          class="thumb"
          @click="preview = preview?.id === s.id ? null : s"
        >
          <img :src="api.fileUrl(s.path)" :alt="s.label || s.id" />
        </button>
        <figcaption>
          <span class="fname">{{ s.label || s.id }}</span>
          <span v-if="usersOf(s.id).length" class="sf-badge">
            <I18nText k="original_used_by" :vars="{ names: usersOf(s.id).join(', ') }" />
          </span>
          <span v-else class="sf-badge warn"><I18nText k="original_unused" /></span>
        </figcaption>
        <div class="sf-btn-bar card-actions">
          <button type="button" class="sf-btn sf-btn-ghost" @click="rename(s)">
            <I18nText k="rename" />
          </button>
          <button type="button" class="sf-btn sf-btn-ghost danger" :disabled="busy" @click="remove(s)">
            <I18nText k="delete" />
          </button>
        </div>
      </figure>
    </div>

    <ImageLightbox
      v-if="preview"
      :src="api.fileUrl(preview.path)"
      :title="preview.label || preview.id"
      :meta="preview.path"
      @close="preview = null"
    />

    <PrivacyRedactDialog
      v-if="redactPending"
      :src="redactPending.url"
      :file="redactPending.file"
      @close="cancelRedact"
      @done="onRedactDone"
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
.head :deep(.row) {
  margin-bottom: 0;
}
.intro {
  margin: 0 0 var(--sf-space-3);
  color: var(--sf-ink-faint);
  font-size: var(--sf-fs-sm);
}
.empty,
.err {
  font-size: var(--sf-fs-sm);
  margin: 0 0 var(--sf-space-3);
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
  background: var(--sf-warn-soft);
  color: var(--sf-warn);
}
.card-actions {
  flex-wrap: wrap;
}
</style>
