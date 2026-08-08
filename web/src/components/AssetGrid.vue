<script setup lang="ts">
import { computed, ref } from 'vue'
import { api } from '@/api/client'
import { useI18n } from '@/i18n'
import { usePrefsStore } from '@/stores/prefs'
import { useProjectStore } from '@/stores/project'
import SectionTitle from '@/components/SectionTitle.vue'
import SelectVisualDialog from '@/components/SelectVisualDialog.vue'
import type { FeatureDef } from '@/types/project'

const props = defineProps<{
  pageId: string
}>()

const emit = defineEmits<{
  select: [featureId: string | null]
}>()

const { t } = useI18n()
const prefs = usePrefsStore()
const project = useProjectStore()
const selected = ref<FeatureDef | null>(null)
const pickTarget = ref<FeatureDef | null>(null)

const page = computed(() => project.project?.page_docs[props.pageId])
const features = computed(() => {
  const map = page.value?.features || {}
  return Object.values(map).sort((a, b) => a.label.localeCompare(b.label) || a.id.localeCompare(b.id))
})

const selectedLive = computed(() => {
  if (!selected.value) return null
  return page.value?.features?.[selected.value.id] || null
})

function setupOf(f: FeatureDef) {
  if (!f.visual_id) return null
  return page.value?.visuals?.[f.visual_id] || f.visual || f.link || null
}

function setupLabel(f: FeatureDef): string {
  const s = setupOf(f)
  return s ? s.label || s.id : ''
}

function selectFeature(f: FeatureDef) {
  selected.value = f
  emit('select', f.id)
}

function clearSelection() {
  selected.value = null
  emit('select', null)
}

async function addFeature() {
  const label = prompt(t('feature_label_prompt'), t('default_feature_name'))
  if (label == null) return
  try {
    await api.createFeature(props.pageId, { label: label.trim() || t('default_feature_name') })
    await project.refreshFromServer()
  } catch (e) {
    alert(String(e))
  }
}

async function unbind(f: FeatureDef) {
  if (!confirm(t('confirm_unbind_feature', { name: f.label || f.id }))) return
  await api.unbindFeature(props.pageId, f.id)
  await project.refreshFromServer()
}

async function removeFeature(f: FeatureDef) {
  if (!confirm(t('confirm_delete_named', { name: f.label || f.id }))) return
  await api.deleteFeature(props.pageId, f.id)
  if (selected.value?.id === f.id) clearSelection()
  await project.refreshFromServer()
}

async function setRecognize(f: FeatureDef) {
  await api.patchFeature(props.pageId, f.id, { recognize: true })
  await project.refreshFromServer()
}

async function rename(f: FeatureDef) {
  const next = prompt(t('feature_label_prompt'), f.label || f.id)
  if (next == null) return
  await api.patchFeature(props.pageId, f.id, { label: next.trim() || f.id })
  await project.refreshFromServer()
}

async function renameId(f: FeatureDef) {
  const next = prompt(t('feature_id_prompt'), f.id)
  if (next == null) return
  const id = next.trim()
  if (!id || id === f.id) return
  try {
    await api.patchFeature(props.pageId, f.id, { id })
    if (selected.value?.id === f.id) selected.value = { ...f, id }
    await project.refreshFromServer()
    const live = page.value?.features?.[id]
    if (live) selected.value = live
  } catch (e) {
    alert(String(e))
  }
}
</script>

<template>
  <div>
    <div class="head">
      <SectionTitle title-key="sec_page_features" help-key="help_page_features" />
      <div class="sf-btn-bar head-actions">
        <label class="ids">
          <input v-model="prefs.showFeatureIds" type="checkbox" />
          <I18nText k="show_feature_ids" />
        </label>
        <button class="sf-btn sf-btn-primary" type="button" @click="addFeature">
          <I18nText k="add_feature" />
        </button>
      </div>
    </div>
    <p class="intro"><I18nText k="features_intro" /></p>
    <div v-if="!features.length" class="empty"><I18nText k="empty_features" /></div>
    <div class="grid">
      <figure
        v-for="f in features"
        :key="f.id"
        class="card"
        :class="{ sel: selectedLive?.id === f.id, unbound: !setupOf(f) }"
        @click="selectFeature(f)"
      >
        <figcaption class="card-main">
          <span class="fname">{{ f.label || f.id }}</span>
          <span v-if="prefs.showFeatureIds" class="sf-mono dim">{{ f.id }}</span>
          <div class="badges">
            <span v-if="page?.recognize_with === f.id" class="sf-badge sf-badge-when">
              <I18nText k="used_for_page" />
            </span>
            <span v-if="!setupOf(f)" class="sf-badge warn"><I18nText k="not_linked" /></span>
            <span v-else class="sf-badge"><I18nText k="using_setup" :vars="{ name: setupLabel(f) }" /></span>
          </div>
        </figcaption>
        <div class="preview-row">
          <span class="preview-label"><I18nText k="matching_preview" /></span>
          <img
            v-if="setupOf(f)?.asset"
            class="mini-thumb"
            :src="api.fileUrl(setupOf(f)!.asset)"
            :alt="setupLabel(f)"
          />
          <button v-else type="button" class="mini-cta" @click.stop="pickTarget = f">
            <I18nText k="select_setup" />
          </button>
        </div>
      </figure>
    </div>

    <aside v-if="selectedLive" class="detail">
      <div class="detail-head">
        <div class="detail-titles">
          <h3 class="sf-section-title">{{ selectedLive.label || selectedLive.id }}</h3>
          <p class="id-row">
            <code class="sf-mono">{{ selectedLive.id }}</code>
            <span v-if="page?.recognize_with === selectedLive.id" class="sf-badge sf-badge-when">
              <I18nText k="used_for_page" />
            </span>
          </p>
        </div>
        <button type="button" class="sf-btn sf-btn-ghost close" @click="clearSelection">×</button>
      </div>

      <section class="logic">
        <h4 class="sec-title"><I18nText k="feature_logic_section" /></h4>
        <p class="sec-hint"><I18nText k="feature_logic_hint" /></p>
        <div class="sf-actions">
          <div class="sf-actions-main">
            <button type="button" class="sf-btn" @click="rename(selectedLive)">
              <I18nText k="rename" />
            </button>
            <button type="button" class="sf-btn sf-btn-ghost" @click="renameId(selectedLive)">
              <I18nText k="change_id" />
            </button>
            <button
              v-if="page?.recognize_with !== selectedLive.id"
              type="button"
              class="sf-btn"
              @click="setRecognize(selectedLive)"
            >
              <I18nText k="mark_for_page" />
            </button>
          </div>
          <div class="sf-actions-danger">
            <button
              type="button"
              class="sf-btn sf-btn-ghost danger"
              @click="removeFeature(selectedLive)"
            >
              <I18nText k="delete_feature" />
            </button>
          </div>
        </div>
      </section>

      <section class="matching">
        <h4 class="sec-title"><I18nText k="matching_section" /></h4>
        <p class="sec-hint"><I18nText k="feature_select_setup_hint" /></p>
        <p class="match-value">
          <template v-if="setupOf(selectedLive)">
            <I18nText k="using_setup" :vars="{ name: setupLabel(selectedLive) }" />
          </template>
          <template v-else>—</template>
        </p>
        <div v-if="setupOf(selectedLive)?.asset" class="content-thumb">
          <img :src="api.fileUrl(setupOf(selectedLive)!.asset)" :alt="setupLabel(selectedLive)" />
        </div>
        <div class="sf-actions">
          <div class="sf-actions-main">
            <button
              type="button"
              class="sf-btn sf-btn-primary"
              @click="pickTarget = selectedLive"
            >
              <I18nText :k="setupOf(selectedLive) ? 'change_setup' : 'select_setup'" />
            </button>
          </div>
          <div class="sf-actions-danger">
            <button
              v-if="setupOf(selectedLive)"
              type="button"
              class="sf-btn sf-btn-ghost"
              @click="unbind(selectedLive)"
            >
              <I18nText k="unbind" />
            </button>
          </div>
        </div>
      </section>
    </aside>

    <SelectVisualDialog
      v-if="pickTarget"
      :page-id="pageId"
      :feature-id="pickTarget.id"
      :feature-label="pickTarget.label || pickTarget.id"
      @close="pickTarget = null"
      @selected="selected = pickTarget"
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
.head-actions {
  flex-shrink: 0;
}
.ids {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: var(--sf-fs-xs);
  color: var(--sf-ink-faint);
}
.intro {
  margin: 0 0 var(--sf-space-3);
  color: var(--sf-ink-faint);
  font-size: var(--sf-fs-sm);
}
.empty {
  color: var(--sf-ink-faint);
  font-size: var(--sf-fs-sm);
  margin-bottom: var(--sf-space-3);
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
  padding: 0.65rem 0.75rem;
  background: var(--sf-surface);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}
.card:hover {
  border-color: var(--sf-line-strong);
}
.card.sel {
  border-color: var(--sf-accent);
  box-shadow: 0 0 0 2px var(--sf-accent-soft);
}
.card.unbound {
  border-style: dashed;
}
.card-main {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin: 0;
}
.fname {
  font-weight: 600;
  font-size: var(--sf-fs-sm);
  color: var(--sf-ink);
}
.dim {
  opacity: 0.65;
  font-size: var(--sf-fs-xs);
}
.badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
}
.warn {
  background: color-mix(in srgb, #c45c26 18%, transparent);
  color: #a34a1a;
}
.preview-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding-top: 0.35rem;
  border-top: 1px solid var(--sf-line);
}
.preview-label {
  flex: 1;
  font-size: 0.65rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--sf-ink-faint);
}
.mini-thumb {
  width: 44px;
  height: 28px;
  object-fit: contain;
  background: #111;
  border-radius: 3px;
  border: 1px solid var(--sf-line);
}
.mini-cta {
  border: none;
  border-radius: var(--sf-radius);
  padding: 0.2rem 0.5rem;
  font-size: var(--sf-fs-xs);
  background: var(--sf-accent);
  color: #fff;
}
.detail {
  margin-top: var(--sf-space-4);
  padding: var(--sf-space-4);
  border: 1px solid var(--sf-line);
  border-radius: var(--sf-radius);
  background: var(--sf-surface-2);
  display: flex;
  flex-direction: column;
  gap: var(--sf-space-4);
}
.detail-head {
  display: flex;
  justify-content: space-between;
  gap: var(--sf-space-2);
}
.detail-head .sf-section-title {
  margin: 0 0 0.25rem;
  text-transform: none;
  letter-spacing: 0;
  font-size: var(--sf-fs-md);
  color: var(--sf-ink);
}
.id-row {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  margin: 0;
  font-size: var(--sf-fs-xs);
  color: var(--sf-ink-faint);
}
.logic,
.matching {
  display: flex;
  flex-direction: column;
  gap: var(--sf-space-2);
  padding-top: var(--sf-space-3);
  border-top: 1px solid var(--sf-line);
}
.sec-title {
  margin: 0;
  font-size: var(--sf-fs-sm);
  font-weight: 600;
  color: var(--sf-ink-muted);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.sec-hint {
  margin: 0;
  font-size: var(--sf-fs-xs);
  color: var(--sf-ink-faint);
}
.match-value {
  margin: 0;
  font-size: var(--sf-fs-sm);
}
.content-thumb {
  width: 100%;
  max-width: 220px;
  background: #111;
  border-radius: 4px;
  overflow: hidden;
  aspect-ratio: 16 / 10;
}
.content-thumb img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
</style>
