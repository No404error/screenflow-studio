<script setup lang="ts">
import { ref } from 'vue'
import { api } from '@/api/client'
import { useI18n } from '@/i18n'
import { useProjectStore } from '@/stores/project'
import RoiCropDialog from '@/components/RoiCropDialog.vue'
import type { PageAsset } from '@/types/project'

const props = defineProps<{
  pageId: string
  assets: PageAsset[]
  detectRelpath?: string
}>()

const { t } = useI18n()
const project = useProjectStore()
const fileInput = ref<HTMLInputElement | null>(null)
const cropTarget = ref<PageAsset | null>(null)

async function onFiles(ev: Event) {
  const input = ev.target as HTMLInputElement
  const files = input.files
  if (!files?.length) return
  for (const f of Array.from(files)) {
    await api.uploadAsset(props.pageId, f)
  }
  await project.refreshFromServer()
  input.value = ''
}

async function remove(name: string) {
  if (!confirm(`Delete ${name}?`)) return
  await api.deleteAsset(props.pageId, name)
  await project.refreshFromServer()
}

function openCrop(a: PageAsset) {
  cropTarget.value = a
}

async function onRoi(roi: number[] | null) {
  if (!cropTarget.value) return
  await api.setAssetRoi(props.pageId, cropTarget.value.name, roi)
  cropTarget.value = null
  await project.refreshFromServer()
}
</script>

<template>
  <div>
    <div class="head">
      <h3 class="sf-section-title">{{ t('features') }}</h3>
      <button class="sf-btn" type="button" @click="fileInput?.click()">{{ t('upload') }}</button>
      <input ref="fileInput" type="file" accept="image/*" multiple hidden @change="onFiles" />
    </div>
    <div class="grid">
      <figure v-for="a in assets" :key="a.relpath" class="card">
        <img :src="api.fileUrl(a.relpath)" :alt="a.name" />
        <figcaption>
          <span class="sf-mono">{{ a.name }}</span>
          <span v-if="detectRelpath === a.relpath" class="sf-badge sf-badge-when">detect</span>
          <span v-if="a.roi" class="sf-badge">ROI</span>
        </figcaption>
        <div class="row">
          <button type="button" class="sf-btn" @click="openCrop(a)">{{ t('crop_roi') }}</button>
          <button type="button" class="sf-btn sf-btn-danger" @click="remove(a.name)">{{ t('delete') }}</button>
        </div>
      </figure>
    </div>
    <RoiCropDialog
      v-if="cropTarget"
      :src="api.fileUrl(cropTarget.relpath)"
      :roi="cropTarget.roi || null"
      @close="cropTarget = null"
      @save="onRoi"
    />
  </div>
</template>

<style scoped>
.head {
  display: flex;
  align-items: center;
  gap: var(--sf-space-3);
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
  overflow: hidden;
  background: var(--sf-surface-2);
}
.card img {
  display: block;
  width: 100%;
  height: 100px;
  object-fit: contain;
  background: #111;
}
figcaption {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  padding: 0.35rem 0.5rem;
  font-size: var(--sf-fs-xs);
}
.row {
  display: flex;
  gap: 0.25rem;
  padding: 0 0.4rem 0.4rem;
}
.row .sf-btn {
  font-size: var(--sf-fs-xs);
  padding: 0.2rem 0.4rem;
}
</style>
