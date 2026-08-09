<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { api } from '@/api/client'
import { useProjectStore } from '@/stores/project'
import type { MatchSetup } from '@/types/project'

const props = defineProps<{
  pageId: string
  featureId: string
  featureLabel: string
}>()

const emit = defineEmits<{
  close: []
  selected: []
}>()

const project = useProjectStore()
const busy = ref(false)
const err = ref('')

const visuals = computed(() => {
  const map = project.project?.page_docs[props.pageId]?.visuals || {}
  return Object.values(map).sort((a, b) => a.label.localeCompare(b.label) || a.id.localeCompare(b.id))
})

async function pick(v: MatchSetup) {
  busy.value = true
  err.value = ''
  try {
    project.applyServerSnapshot(
      await api.selectFeatureVisual(props.pageId, props.featureId, v.id),
    )
    emit('selected')
    emit('close')
  } catch (e) {
    err.value = String(e)
  } finally {
    busy.value = false
  }
}

function onKey(ev: KeyboardEvent) {
  if (ev.key === 'Escape') emit('close')
}

onMounted(() => document.addEventListener('keydown', onKey))
onUnmounted(() => document.removeEventListener('keydown', onKey))
</script>

<template>
  <Teleport to="body">
    <div class="mask" @click.self="emit('close')">
      <div
        class="dialog sf-panel"
        role="dialog"
        aria-modal="true"
        :aria-label="featureLabel"
      >
        <header>
          <h3><I18nText k="select_setup_title" /></h3>
          <button type="button" class="sf-btn sf-btn-ghost" @click="emit('close')">×</button>
        </header>
        <p class="hint">
          <I18nText k="select_setup_hint" :vars="{ name: featureLabel }" />
        </p>
        <p v-if="!visuals.length" class="empty"><I18nText k="empty_setups_pick" /></p>
        <div v-else class="grid">
          <button
            v-for="v in visuals"
            :key="v.id"
            type="button"
            class="tile"
            :disabled="busy"
            @click="pick(v)"
          >
            <img v-if="v.asset" :src="api.fileUrl(v.asset)" :alt="v.label" />
            <span>{{ v.label || v.id }}</span>
            <span class="sf-mono dim">{{ v.id }}</span>
          </button>
        </div>
        <p v-if="err" class="err">{{ err }}</p>
        <div class="sf-dialog-foot">
          <button type="button" class="sf-btn" :disabled="busy" @click="emit('close')">
            <I18nText k="cancel" />
          </button>
        </div>
      </div>
    </div>
  </Teleport>
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
  width: min(520px, 100%);
  max-height: min(80vh, 560px);
  display: flex;
  flex-direction: column;
  padding: var(--sf-space-4);
}
header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
header h3 {
  margin: 0;
  font-size: var(--sf-fs-lg);
}
.hint {
  margin: 0.35rem 0 var(--sf-space-3);
  color: var(--sf-ink-muted);
  font-size: var(--sf-fs-sm);
}
.empty {
  color: var(--sf-ink-faint);
  font-size: var(--sf-fs-sm);
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: var(--sf-space-2);
  overflow: auto;
  min-height: 0;
  flex: 1;
}
.tile {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.35rem;
  border: 1px solid var(--sf-line);
  border-radius: var(--sf-radius);
  background: var(--sf-surface);
  cursor: pointer;
  text-align: left;
}
.tile:hover:not(:disabled) {
  border-color: var(--sf-accent);
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
}
.dim {
  opacity: 0.65;
}
.err {
  color: var(--sf-danger);
  font-size: var(--sf-fs-sm);
}
</style>
