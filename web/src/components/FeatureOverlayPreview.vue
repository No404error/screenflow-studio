<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from '@/i18n'

const props = defineProps<{
  /** Prefer page source; fallback to artwork. */
  src: string
  title?: string
  meta?: string
  searchRoi?: number[] | null
  contentRoi?: number[] | null
  /** True when src is the page reference screenshot. */
  onSource?: boolean
}>()
const emit = defineEmits<{ close: [] }>()

const { t } = useI18n()

function pctBox(roi: number[]) {
  const [y0, y1, x0, x1] = roi
  return {
    left: `${Math.min(x0, x1) * 100}%`,
    top: `${Math.min(y0, y1) * 100}%`,
    width: `${Math.abs(x1 - x0) * 100}%`,
    height: `${Math.abs(y1 - y0) * 100}%`,
  }
}

const searchStyle = computed(() =>
  props.searchRoi && props.searchRoi.length === 4 ? pctBox(props.searchRoi) : null,
)
const contentStyle = computed(() =>
  props.contentRoi && props.contentRoi.length === 4 ? pctBox(props.contentRoi) : null,
)

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}

onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <Teleport to="body">
    <div class="mask" @click.self="emit('close')">
      <div class="box" role="dialog" :aria-label="title || t('preview_image')">
        <header>
          <div class="titles">
            <strong>{{ title || t('preview_image') }}</strong>
            <span v-if="meta" class="meta sf-mono">{{ meta }}</span>
          </div>
          <button type="button" class="sf-btn sf-btn-ghost" @click="emit('close')">×</button>
        </header>
        <div class="stage">
          <div class="frame">
            <img :src="src" :alt="title || t('preview_image')" />
            <div
              v-if="onSource && !searchStyle"
              class="box-full"
              :title="t('search_full')"
            />
            <div
              v-if="onSource && searchStyle"
              class="box-search"
              :style="searchStyle"
              :title="t('search_region')"
            />
            <div
              v-if="onSource && contentStyle"
              class="box-content"
              :style="contentStyle"
              :title="t('match_content')"
            />
          </div>
        </div>
        <footer>
          <div class="legend" v-if="onSource">
            <span class="leg search"><I18nText k="search_region" /></span>
            <span v-if="contentStyle" class="leg content"><I18nText k="match_content" /></span>
            <span v-if="!searchStyle" class="leg muted"><I18nText k="search_full" /></span>
          </div>
          <div class="legend" v-else>
            <span class="leg muted"><I18nText k="preview_artwork_only" /></span>
          </div>
          <a class="sf-btn" :href="src" target="_blank" rel="noopener">{{ t('open_full') }}</a>
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.mask {
  position: fixed;
  inset: 0;
  background: rgb(26 34 32 / 55%);
  display: grid;
  place-items: center;
  z-index: 70;
  padding: 1rem;
}
.box {
  width: min(960px, 96vw);
  max-height: min(88vh, 860px);
  background: var(--sf-surface);
  border: 1px solid var(--sf-line);
  border-radius: var(--sf-radius-lg);
  box-shadow: 0 12px 40px rgb(26 34 32 / 25%);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
header,
footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.65rem 0.9rem;
  border-bottom: 1px solid var(--sf-line);
  flex-shrink: 0;
}
footer {
  border-bottom: none;
  border-top: 1px solid var(--sf-line);
}
.titles {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 0;
}
.meta {
  font-size: var(--sf-fs-xs);
  color: var(--sf-ink-faint);
  overflow: hidden;
  text-overflow: ellipsis;
}
.stage {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: var(--sf-space-3);
  background: var(--sf-bg);
}
.frame {
  position: relative;
  display: inline-block;
  max-width: 100%;
  vertical-align: top;
}
.frame img {
  display: block;
  max-width: 100%;
  max-height: min(68vh, 640px);
  object-fit: contain;
  background: #111;
}
.box-search,
.box-content,
.box-full {
  position: absolute;
  pointer-events: none;
  box-sizing: border-box;
}
.box-full {
  inset: 0;
  border: 2px dashed rgb(90 140 120 / 70%);
}
.box-search {
  border: 2px solid rgb(46 125 98);
  background: rgb(46 125 98 / 12%);
}
.box-content {
  border: 2px solid rgb(196 120 52);
  background: rgb(196 120 52 / 18%);
}
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  font-size: var(--sf-fs-xs);
  color: var(--sf-ink-muted);
}
.leg::before {
  content: '';
  display: inline-block;
  width: 0.65rem;
  height: 0.65rem;
  margin-right: 0.3rem;
  vertical-align: -0.05rem;
  border: 1px solid currentColor;
}
.leg.search {
  color: rgb(46 125 98);
}
.leg.content {
  color: rgb(196 120 52);
}
.leg.muted {
  color: var(--sf-ink-faint);
}
.leg.muted::before {
  border-style: dashed;
}
</style>
