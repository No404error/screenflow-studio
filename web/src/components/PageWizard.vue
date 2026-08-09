<script setup lang="ts">
import { ref } from 'vue'
import { api } from '@/api/client'
import { useI18n } from '@/i18n'
import { useEscapeKey } from '@/composables/useEscapeKey'
import { useProjectStore } from '@/stores/project'
import { useUiStore } from '@/stores/ui'
import AssetUploadWizard from '@/components/AssetUploadWizard.vue'
import PrivacyRedactDialog from '@/components/PrivacyRedactDialog.vue'
import { bindFeatureFromScreenshot } from '@/utils/bindFromScreenshot'

const emit = defineEmits<{ close: []; done: [pageId: string] }>()

const { t } = useI18n()
useEscapeKey(() => {
  onClose()
  return true
})
const project = useProjectStore()
const ui = useUiStore()

const step = ref(0)
const name = ref(t('default_page_name'))
const openCases = ref(true)
const busy = ref(false)
const error = ref('')

/** After redact: feeds AssetUploadWizard. */
const pendingFile = ref<{ file: File; url: string; name: string } | null>(null)
/** Before redact: new file pick. */
const redactPending = ref<{ file: File; url: string; name: string } | null>(null)
const prepared = ref<{
  file: File
  url: string
  name: string
  searchRoi: number[] | null
  contentRoi: number[]
} | null>(null)

function onFile(ev: Event) {
  const input = ev.target as HTMLInputElement
  const f = input.files?.[0]
  input.value = ''
  if (!f) return
  clearPrepared()
  cancelPending()
  cancelRedact()
  redactPending.value = {
    file: f,
    url: URL.createObjectURL(f),
    name: f.name.replace(/\.[^.]+$/, '') || 'feature',
  }
}

function clearPrepared() {
  if (prepared.value) URL.revokeObjectURL(prepared.value.url)
  prepared.value = null
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
  cancelPending()
  pendingFile.value = { file, url, name }
}

function cancelPending() {
  if (pendingFile.value) URL.revokeObjectURL(pendingFile.value.url)
  pendingFile.value = null
}

function onUploadDone(payload: {
  searchRoi: number[] | null
  contentRoi: number[]
  name: string
}) {
  if (!pendingFile.value) return
  const { file, url } = pendingFile.value
  pendingFile.value = null
  clearPrepared()
  prepared.value = {
    file,
    url,
    name: payload.name,
    searchRoi: payload.searchRoi,
    contentRoi: payload.contentRoi,
  }
}

function skipImage() {
  cancelRedact()
  cancelPending()
  clearPrepared()
}

async function finish() {
  const n = name.value.trim()
  if (!n) {
    error.value = t('name_required')
    return
  }
  busy.value = true
  error.value = ''
  try {
    await project.addPage(n)
    const pageId = Object.keys(project.project?.page_docs || {}).at(-1)
    if (!pageId) throw new Error('page missing')
    if (prepared.value) {
      const label = prepared.value.name || 'main'
      project.applyServerSnapshot(await api.createFeature(pageId, { label }))
      const feats = project.project?.page_docs[pageId]?.features || {}
      const created =
        Object.values(feats).find((x) => x.label === label && !x.visual_id) ||
        Object.values(feats).at(-1)
      if (!created) throw new Error('feature missing')
      project.applyServerSnapshot(
        await bindFeatureFromScreenshot(pageId, created.id, prepared.value.file, {
          searchRoi: prepared.value.searchRoi,
          contentRoi: prepared.value.contentRoi,
          name: label,
        }),
      )
      project.applyServerSnapshot(
        await api.patchFeature(pageId, created.id, { recognize: true }),
      )
    }
    clearPrepared()
    if (openCases.value) {
      ui.select({ kind: 'state', pageId, nodeId: undefined })
    } else {
      ui.select({ kind: 'page', pageId })
    }
    emit('done', pageId)
    emit('close')
  } catch (e) {
    error.value = String(e)
  } finally {
    busy.value = false
  }
}

function onClose() {
  cancelRedact()
  cancelPending()
  clearPrepared()
  emit('close')
}
</script>

<template>
  <div class="mask" @click.self="onClose">
    <div class="dialog sf-panel">
      <h3><I18nText k="wizard_title" /></h3>
      <p class="steps">{{ step + 1 }} / 3</p>

      <div v-if="step === 0" class="body">
        <label class="sf-field">
          <span class="sf-label"><I18nText k="name" /></span>
          <input v-model="name" class="sf-input" type="text" autofocus />
        </label>
      </div>

      <div v-else-if="step === 1" class="body">
        <label class="sf-field">
          <span class="sf-label"><I18nText k="upload" /></span>
          <input type="file" accept="image/*" @change="onFile" />
        </label>
        <p v-if="prepared" class="ready">
          <I18nText k="match_content" />: <code class="sf-mono">{{ prepared.name }}</code>
          ·
          {{
            prepared.searchRoi
              ? t('search_region')
              : t('search_full')
          }}
        </p>
        <img v-if="prepared" :src="prepared.url" class="prev" alt="" />
        <button class="sf-btn" type="button" @click="skipImage">
          <I18nText k="wizard_skip_image" />
        </button>
      </div>

      <div v-else class="body">
        <label class="sf-field check">
          <input v-model="openCases" type="checkbox" />
          <I18nText k="wizard_open_cases" />
        </label>
      </div>

      <p v-if="error" class="err">{{ error }}</p>
      <div class="sf-dialog-foot">
        <button class="sf-btn sf-btn-ghost" type="button" :disabled="busy" @click="onClose">
          <I18nText k="cancel" />
        </button>
        <button v-if="step > 0" class="sf-btn" type="button" :disabled="busy" @click="step--">
          <I18nText k="wizard_back" />
        </button>
        <button
          v-if="step < 2"
          class="sf-btn sf-btn-primary"
          type="button"
          :disabled="busy || (step === 0 && !name.trim())"
          @click="step++"
        >
          <I18nText k="wizard_next" />
        </button>
        <button
          v-else
          class="sf-btn sf-btn-primary"
          type="button"
          :disabled="busy"
          @click="finish"
        >
          <I18nText k="wizard_finish" />
        </button>
      </div>
    </div>

    <PrivacyRedactDialog
      v-if="redactPending"
      :src="redactPending.url"
      :file="redactPending.file"
      @close="cancelRedact"
      @done="onRedactDone"
    />
    <AssetUploadWizard
      v-if="pendingFile"
      :src="pendingFile.url"
      :preferred-name="pendingFile.name"
      @close="cancelPending"
      @done="onUploadDone"
    />
  </div>
</template>

<style scoped>
.mask {
  position: fixed;
  inset: 0;
  background: rgb(26 34 32 / 45%);
  display: grid;
  place-items: center;
  z-index: 45;
}
.dialog {
  width: min(520px, 96vw);
  max-height: min(90vh, 720px);
  overflow: auto;
  padding: var(--sf-space-4);
}
h3 {
  margin: 0 0 0.25rem;
}
.steps {
  color: var(--sf-ink-faint);
  font-size: var(--sf-fs-sm);
  margin: 0 0 var(--sf-space-3);
}
.body {
  display: flex;
  flex-direction: column;
  gap: var(--sf-space-3);
  min-height: 8rem;
}
.prev {
  max-width: 100%;
  max-height: 160px;
  object-fit: contain;
  background: var(--sf-media-well);
  border-radius: var(--sf-radius);
}
.ready {
  margin: 0;
  font-size: var(--sf-fs-sm);
  color: var(--sf-ink-muted);
}
.check {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.err {
  color: var(--sf-danger);
  font-size: var(--sf-fs-sm);
}
</style>
