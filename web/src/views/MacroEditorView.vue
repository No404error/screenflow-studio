<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from '@/i18n'
import { useUiStore } from '@/stores/ui'
import { useProjectStore } from '@/stores/project'
import StepsEditor from '@/components/StepsEditor.vue'
import BindingsStrip from '@/components/BindingsStrip.vue'

const { t } = useI18n()
const ui = useUiStore()
const project = useProjectStore()

const macro = computed(() => {
  const id = ui.selection.macroId
  if (!id || !project.project) return null
  return project.project.macros.find((m) => m.id === id) || null
})

const featureKeys = computed(() => {
  const keys = new Set<string>()
  for (const p of Object.values(project.project?.page_docs || {})) {
    Object.keys(p.features || {}).forEach((k) => keys.add(k))
  }
  return [...keys].sort()
})

const macroIds = computed(() =>
  (project.project?.macros || []).map((m) => m.id).filter((id) => id !== macro.value?.id),
)

function mark() {
  project.markDirty()
}

async function remove() {
  if (!macro.value) return
  if (!confirm(`Delete macro ${macro.value.name}?`)) return
  await project.removeMacro(macro.value.id)
}
</script>

<template>
  <div v-if="macro" class="macro">
    <header class="head">
      <div>
        <h2>{{ macro.name || macro.id }}</h2>
        <p class="sf-mono">{{ macro.id }}</p>
      </div>
      <button class="sf-btn sf-btn-danger" type="button" @click="remove">{{ t('delete') }}</button>
    </header>
    <label class="sf-field">
      <span class="sf-label">{{ t('name') }}</span>
      <input v-model="macro.name" class="sf-input" @input="mark" />
    </label>
    <BindingsStrip :steps="macro.steps" />
    <StepsEditor v-model="macro.steps" :feature-keys="featureKeys" :macro-ids="macroIds" />
  </div>
</template>

<style scoped>
.head {
  display: flex;
  justify-content: space-between;
  margin-bottom: var(--sf-space-4);
}
h2 {
  margin: 0;
}
.sf-mono {
  color: var(--sf-ink-faint);
  margin: 0.2rem 0 0;
}
</style>
