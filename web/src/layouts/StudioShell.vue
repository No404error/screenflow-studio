<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from '@/i18n'
import { useUiStore } from '@/stores/ui'
import { useProjectStore } from '@/stores/project'
import { useRunStore } from '@/stores/run'
import type { NavSelection } from '@/types/project'
import NavRail from '@/components/NavRail.vue'
import RunBar from '@/components/RunBar.vue'
import RunDrawer from '@/components/RunDrawer.vue'
import SectionHelp from '@/components/SectionHelp.vue'
import PageWizard from '@/components/PageWizard.vue'
import VariablesView from '@/views/VariablesView.vue'
import PageEditorView from '@/views/PageEditorView.vue'
import StateEditorView from '@/views/StateEditorView.vue'
import MacroEditorView from '@/views/MacroEditorView.vue'
import MacrosOverviewView from '@/views/MacrosOverviewView.vue'
import PairsEditorView from '@/views/PairsEditorView.vue'
import PagesOverviewView from '@/views/PagesOverviewView.vue'

const { t } = useI18n()
const ui = useUiStore()
const project = useProjectStore()
const run = useRunStore()
const router = useRouter()
const route = useRoute()
const aboutOpen = ref(false)
let applyingDeepLink = false

watch(
  () => project.hasProject,
  (ok) => {
    if (!ok) void router.replace('/')
  },
  { immediate: true },
)

const kind = computed(() => ui.selection.kind)

function parseSel(raw: string): NavSelection | null {
  // page:id or page:id/state:nodeId or variables|macros|pages|pairs|macro:id
  if (raw === 'variables') return { kind: 'variables' }
  if (raw === 'macros') return { kind: 'macros' }
  if (raw === 'pages') return { kind: 'pages' }
  if (raw === 'pairs') return { kind: 'pairs' }
  if (raw.startsWith('macro:')) return { kind: 'macro', macroId: raw.slice(6) }
  const m = raw.match(/^page:([^/]+)(?:\/state:(.+))?$/)
  if (!m) return null
  if (m[2]) return { kind: 'state', pageId: m[1], nodeId: m[2] }
  return { kind: 'page', pageId: m[1] }
}

function selToQuery(sel: NavSelection): string | null {
  switch (sel.kind) {
    case 'variables':
      return 'variables'
    case 'macros':
      return 'macros'
    case 'pages':
      return 'pages'
    case 'pairs':
      return 'pairs'
    case 'macro':
      return sel.macroId ? `macro:${sel.macroId}` : null
    case 'page':
      return sel.pageId ? `page:${sel.pageId}` : null
    case 'state':
      return sel.pageId
        ? `page:${sel.pageId}${sel.nodeId ? `/state:${sel.nodeId}` : ''}`
        : null
    default:
      return null
  }
}

onMounted(() => {
  const raw = typeof route.query.sel === 'string' ? route.query.sel : ''
  if (!raw) return
  const parsed = parseSel(raw)
  if (parsed) {
    applyingDeepLink = true
    ui.select(parsed)
    applyingDeepLink = false
  }
})

watch(
  () => ui.selection,
  (sel) => {
    if (applyingDeepLink) return
    const q = selToQuery(sel)
    const cur = typeof route.query.sel === 'string' ? route.query.sel : undefined
    if ((q || undefined) === cur) return
    void router.replace({ query: q ? { ...route.query, sel: q } : { ...route.query, sel: undefined } })
  },
  { deep: true },
)

async function goHome() {
  if (!(await project.confirmLeaveIfDirty())) return
  await router.push('/')
}

async function closeProject() {
  if (!(await project.confirmLeaveIfDirty())) return
  if (run.isActive) await run.stop()
  await project.close()
  await router.replace('/')
}
</script>

<template>
  <div v-if="project.project" class="shell">
    <header class="top">
      <div class="brand">
        <span class="logo"><I18nText k="app_name" /></span>
        <span class="sep">/</span>
        <span class="proj">{{ project.project.name }}</span>
        <span v-if="project.dirty" class="dirty" :title="t('unsaved')">*</span>
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
        <button type="button" class="sf-btn sf-btn-ghost" @click="aboutOpen = true">
          <I18nText k="about" />
        </button>
        <button
          class="sf-btn sf-btn-primary"
          :disabled="project.saving || !project.dirty"
          @click="project.save()"
        >
          <I18nText k="save" />
        </button>
        <button class="sf-btn sf-btn-ghost" @click="closeProject"><I18nText k="close_project" /></button>
        <button class="sf-btn sf-btn-ghost" @click="goHome"><I18nText k="home" /></button>
      </div>
    </header>

    <div class="body">
      <NavRail />
      <main class="editor">
        <div class="paper">
          <VariablesView v-if="kind === 'variables'" />
          <MacrosOverviewView v-else-if="kind === 'macros'" />
          <MacroEditorView v-else-if="kind === 'macro'" />
          <PagesOverviewView v-else-if="kind === 'pages'" />
          <PairsEditorView v-else-if="kind === 'pairs'" />
          <PageEditorView v-else-if="kind === 'page'" />
          <StateEditorView v-else-if="kind === 'state'" />
          <p v-else class="sf-empty"><I18nText k="no_selection" /></p>
        </div>
      </main>
    </div>

    <RunDrawer />
    <RunBar />

    <PageWizard v-if="ui.pageWizardOpen" @close="ui.pageWizardOpen = false" />

    <Teleport to="body">
      <div v-if="aboutOpen" class="mask" @click.self="aboutOpen = false">
        <div class="about sf-panel">
          <header>
            <h3><I18nText k="about" /></h3>
            <button type="button" class="sf-btn sf-btn-ghost" @click="aboutOpen = false">×</button>
          </header>
          <div class="about-scroll">
            <p class="about-body"><I18nText k="about_body" /></p>
            <p class="about-body tip"><I18nText k="tip" /></p>
            <p class="about-help">
              <SectionHelp help-key="help_runtime" />
              <span><I18nText k="help_button_a11y" /></span>
            </p>
          </div>
          <footer>
            <button type="button" class="sf-btn sf-btn-primary" @click="aboutOpen = false"><I18nText k="ok" /></button>
          </footer>
        </div>
      </div>
      <div v-if="ui.unsavedPrompt" class="mask">
        <div class="about sf-panel">
          <header>
            <h3><I18nText k="unsaved_title" /></h3>
          </header>
          <div class="about-scroll">
            <p class="about-body"><I18nText k="unsaved" /></p>
          </div>
          <footer class="sf-dialog-foot unsaved-actions">
            <button type="button" class="sf-btn sf-btn-ghost" @click="ui.answerUnsaved('cancel')">
              <I18nText k="unsaved_cancel" />
            </button>
            <button type="button" class="sf-btn" @click="ui.answerUnsaved('discard')">
              <I18nText k="unsaved_discard" />
            </button>
            <button type="button" class="sf-btn sf-btn-primary" @click="ui.answerUnsaved('save')">
              <I18nText k="unsaved_save" />
            </button>
          </footer>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.shell {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: var(--sf-paper);
}
.top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.65rem var(--sf-space-5);
  background: var(--sf-surface);
  border-bottom: 1px solid var(--sf-line);
  z-index: 2;
}
.brand {
  display: flex;
  align-items: baseline;
  gap: 0.4rem;
  min-width: 0;
}
.logo {
  font-size: var(--sf-fs-lg);
  font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--sf-ink);
}
.sep {
  color: var(--sf-ink-faint);
}
.proj {
  font-size: var(--sf-fs-md);
  color: var(--sf-ink-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.dirty {
  color: var(--sf-warn);
  font-weight: 700;
}
.top-actions {
  display: flex;
  gap: 0.4rem;
  align-items: center;
  flex-shrink: 0;
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
  background: var(--sf-paper);
}
.paper {
  max-width: 1100px;
  margin: 0 auto;
  min-height: calc(100% - 0.5rem);
  padding: var(--sf-space-5) var(--sf-space-6);
  background: var(--sf-surface);
  border: 1px solid var(--sf-line);
  border-radius: var(--sf-radius-lg);
  box-shadow: var(--sf-shadow-soft);
  animation: paper-in 0.22s ease;
}
@keyframes paper-in {
  from {
    opacity: 0.65;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
.mask {
  position: fixed;
  inset: 0;
  background: rgb(26 34 32 / 45%);
  display: grid;
  place-items: center;
  z-index: 60;
  padding: 1rem;
}
.about {
  width: min(560px, 96vw);
  max-height: min(85vh, 640px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.about header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--sf-line);
  flex-shrink: 0;
}
.about h3 {
  margin: 0;
}
.about-scroll {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
}
.about-body {
  margin: 0;
  padding: 1rem 1.25rem;
  font-size: var(--sf-fs-sm);
  line-height: 1.6;
  color: var(--sf-ink-muted);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: break-word;
}
.about-help {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  margin: 0;
  padding: 0 1.25rem 0.75rem;
  font-size: var(--sf-fs-xs);
  color: var(--sf-ink-faint);
}
.about footer {
  display: flex;
  justify-content: flex-end;
  flex-wrap: wrap;
  padding: 0.65rem 1rem;
  border-top: 1px solid var(--sf-line);
  flex-shrink: 0;
}
.about-body.tip {
  padding-top: 0;
  color: var(--sf-ink-faint);
}
.unsaved-actions {
  margin-top: 0;
  border-top: 1px solid var(--sf-line);
  padding: 0.65rem 1rem;
}
</style>
