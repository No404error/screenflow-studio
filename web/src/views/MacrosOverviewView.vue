<script setup lang="ts">
import { useI18n } from '@/i18n'
import { useProjectStore } from '@/stores/project'
import { useUiStore } from '@/stores/ui'

const { t } = useI18n()
const project = useProjectStore()
const ui = useUiStore()

async function add() {
  const name = window.prompt(t('add_macro'), t('default_macro_name'))
  if (name) await project.addMacro(name)
}
</script>

<template>
  <div>
    <header class="head">
      <h2><I18nText k="macros" /></h2>
      <div class="sf-btn-bar">
        <button class="sf-btn sf-btn-primary" type="button" @click="add"><I18nText k="add_macro" /></button>
      </div>
    </header>
    <ul class="list">
      <li v-for="m in project.project?.macros || []" :key="m.id">
        <button class="item" type="button" @click="ui.select({ kind: 'macro', macroId: m.id })">
          <strong>{{ m.name || m.id }}</strong>
          <span class="sf-mono"><I18nText k="steps_count" :vars="{ n: m.steps?.length || 0 }" /></span>
        </button>
      </li>
    </ul>
    <p v-if="!(project.project?.macros || []).length" class="sf-empty"><I18nText k="empty_macros" /></p>
  </div>
</template>

<style scoped>
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--sf-space-4);
  gap: var(--sf-space-3);
}
h2 {
  margin: 0;
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
