<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from '@/i18n'
import { useUiStore } from '@/stores/ui'
import { useProjectStore } from '@/stores/project'
import NavRail from '@/components/NavRail.vue'
import RunBar from '@/components/RunBar.vue'
import RunDrawer from '@/components/RunDrawer.vue'
import VariablesView from '@/views/VariablesView.vue'
import PageEditorView from '@/views/PageEditorView.vue'
import StateEditorView from '@/views/StateEditorView.vue'
import MacroEditorView from '@/views/MacroEditorView.vue'
import MacrosOverviewView from '@/views/MacrosOverviewView.vue'
import PairsEditorView from '@/views/PairsEditorView.vue'

const { t } = useI18n()
const ui = useUiStore()
const project = useProjectStore()
const router = useRouter()

watch(
  () => project.hasProject,
  (ok) => {
    if (!ok) void router.replace('/')
  },
  { immediate: true },
)

const kind = computed(() => ui.selection.kind)
</script>

<template>
  <div v-if="project.project" class="shell">
    <header class="top">
      <div class="brand">
        <strong>{{ t('app_name') }}</strong>
        <span class="sep">/</span>
        <span>{{ project.project.name }}</span>
        <span v-if="project.dirty" class="dirty">*</span>
      </div>
      <div class="top-actions">
        <select
          class="sf-select lang"
          :value="ui.lang"
          @change="ui.setLang(($event.target as HTMLSelectElement).value)"
        >
          <option value="en">EN</option>
          <option value="zh">中文</option>
        </select>
        <button class="sf-btn" :disabled="project.saving || !project.dirty" @click="project.save()">
          {{ t('save') }}
        </button>
        <button class="sf-btn sf-btn-ghost" @click="router.push('/')">Home</button>
      </div>
    </header>
    <div class="body">
      <NavRail />
      <main class="editor">
        <VariablesView v-if="kind === 'variables'" />
        <MacrosOverviewView v-else-if="kind === 'macros'" />
        <MacroEditorView v-else-if="kind === 'macro'" />
        <PairsEditorView v-else-if="kind === 'pages' || kind === 'pairs'" />
        <PageEditorView v-else-if="kind === 'page'" />
        <StateEditorView v-else-if="kind === 'state'" />
        <p v-else class="sf-empty">{{ t('no_selection') }}</p>
      </main>
    </div>
    <RunDrawer />
    <RunBar />
  </div>
</template>

<style scoped>
.shell {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.55rem var(--sf-space-4);
  background: var(--sf-surface);
  border-bottom: 1px solid var(--sf-line);
}
.brand {
  display: flex;
  align-items: baseline;
  gap: 0.35rem;
  min-width: 0;
}
.sep {
  color: var(--sf-ink-faint);
}
.dirty {
  color: var(--sf-warn);
  font-weight: 700;
}
.top-actions {
  display: flex;
  gap: 0.4rem;
  align-items: center;
}
.lang {
  width: auto;
}
.body {
  flex: 1;
  display: flex;
  min-height: 0;
}
.editor {
  flex: 1;
  overflow: auto;
  padding: var(--sf-space-5);
  background:
    linear-gradient(180deg, #fbfcfb 0%, var(--sf-paper) 120px);
}
</style>
