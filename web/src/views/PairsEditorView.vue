<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from '@/i18n'
import { useProjectStore } from '@/stores/project'

const { t } = useI18n()
const project = useProjectStore()

const pages = computed(() => Object.values(project.project?.page_docs || {}))
const pairs = computed(() => {
  const seen = new Set<string>()
  const out: [string, string][] = []
  for (const p of pages.value) {
    if (!p.pair_with) continue
    const key = [p.id, p.pair_with].sort().join('|')
    if (seen.has(key)) continue
    seen.add(key)
    out.push([p.id, p.pair_with])
  }
  return out
})

const a = ref('')
const b = ref('')

function label(id: string) {
  return project.project?.page_docs[id]?.name || id
}

function addPair() {
  if (!project.project || !a.value || !b.value || a.value === b.value) return
  const pa = project.project.page_docs[a.value]
  const pb = project.project.page_docs[b.value]
  if (!pa || !pb) return
  // clear old partners
  for (const p of Object.values(project.project.page_docs)) {
    if (p.pair_with === a.value || p.pair_with === b.value) p.pair_with = null
  }
  pa.pair_with = b.value
  pb.pair_with = a.value
  project.markDirty()
}

function clearPair(x: string, y: string) {
  if (!project.project) return
  const pa = project.project.page_docs[x]
  const pb = project.project.page_docs[y]
  if (pa) pa.pair_with = null
  if (pb) pb.pair_with = null
  project.markDirty()
}
</script>

<template>
  <div>
    <h2>{{ t('page_pairs') }}</h2>
    <p class="hint">Look-alike pages compete with priority when scores are close.</p>
    <ul class="list">
      <li v-for="([x, y], i) in pairs" :key="i" class="row">
        <span>{{ label(x) }} ↔ {{ label(y) }}</span>
        <button class="sf-btn sf-btn-danger" type="button" @click="clearPair(x, y)">{{ t('delete') }}</button>
      </li>
    </ul>
    <div class="add">
      <select v-model="a" class="sf-select">
        <option value="">—</option>
        <option v-for="p in pages" :key="p.id" :value="p.id">{{ p.name || p.id }}</option>
      </select>
      <select v-model="b" class="sf-select">
        <option value="">—</option>
        <option v-for="p in pages" :key="p.id" :value="p.id">{{ p.name || p.id }}</option>
      </select>
      <button class="sf-btn sf-btn-primary" type="button" @click="addPair">Add</button>
    </div>
  </div>
</template>

<style scoped>
h2 {
  margin: 0 0 var(--sf-space-2);
}
.hint {
  color: var(--sf-ink-muted);
  margin: 0 0 var(--sf-space-4);
}
.list {
  list-style: none;
  margin: 0 0 var(--sf-space-4);
  padding: 0;
}
.row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.55rem 0.75rem;
  border: 1px solid var(--sf-line);
  border-radius: var(--sf-radius);
  margin-bottom: 0.4rem;
  background: var(--sf-surface);
}
.add {
  display: flex;
  gap: 0.5rem;
  max-width: 36rem;
}
</style>
