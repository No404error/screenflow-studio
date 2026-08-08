<script setup lang="ts">
import { useI18n } from '@/i18n'
import { useProjectStore } from '@/stores/project'
import { useUiStore } from '@/stores/ui'

const { t } = useI18n()
const project = useProjectStore()
const ui = useUiStore()
</script>

<template>
  <div>
    <h2>{{ t('macros') }}</h2>
    <ul class="list">
      <li v-for="m in project.project?.macros || []" :key="m.id">
        <button class="item" type="button" @click="ui.select({ kind: 'macro', macroId: m.id })">
          <strong>{{ m.name || m.id }}</strong>
          <span class="sf-mono">{{ m.steps?.length || 0 }} steps</span>
        </button>
      </li>
    </ul>
    <p v-if="!(project.project?.macros || []).length" class="sf-empty">{{ t('add_macro') }}</p>
  </div>
</template>

<style scoped>
h2 {
  margin: 0 0 var(--sf-space-4);
}
.list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: var(--sf-space-2);
}
.item {
  width: 100%;
  text-align: left;
  border: 1px solid var(--sf-line);
  background: var(--sf-surface);
  border-radius: var(--sf-radius);
  padding: var(--sf-space-3) var(--sf-space-4);
  display: flex;
  justify-content: space-between;
}
.item:hover {
  border-color: var(--sf-accent);
  background: var(--sf-accent-soft);
}
</style>
