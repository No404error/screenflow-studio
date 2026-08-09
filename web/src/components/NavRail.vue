<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from '@/i18n'
import { useUiStore } from '@/stores/ui'
import { usePrefsStore } from '@/stores/prefs'
import { useProjectStore } from '@/stores/project'
import { flattenTree, isElse as nodeIsElse } from '@/utils/tree'
import type { StateNode } from '@/types/project'

const { t } = useI18n()
const ui = useUiStore()
const prefs = usePrefsStore()
const project = useProjectStore()

const macrosOpen = ref(true)
const pagesOpen = ref(true)
/** pageId → whether case children are expanded */
const caseOpen = ref<Record<string, boolean>>({})

const pages = computed(() =>
  Object.entries(project.project?.page_docs || {}).map(([id, doc]) => ({
    id,
    name: doc.name || id,
    state_tree: doc.state_tree || [],
  })),
)
const macros = computed(() => project.project?.macros || [])

watch(
  () => ui.selection,
  (sel) => {
    if (sel.kind === 'state' && sel.pageId) {
      caseOpen.value = { ...caseOpen.value, [sel.pageId]: true }
      pagesOpen.value = true
    }
    if (sel.kind === 'page' && sel.pageId) {
      pagesOpen.value = true
    }
    if (sel.kind === 'macro' || sel.kind === 'macros') {
      macrosOpen.value = true
    }
  },
  { deep: true },
)

function isElse(n: StateNode) {
  return nodeIsElse(n)
}

function caseRows(tree: StateNode[]) {
  return flattenTree(tree || [])
}

function toggleCases(pageId: string) {
  caseOpen.value = { ...caseOpen.value, [pageId]: !caseOpen.value[pageId] }
}

function selectVariables() {
  ui.select({ kind: 'variables' })
}
function selectMacros() {
  if (ui.selection.kind === 'macros' || ui.selection.kind === 'macro') {
    macrosOpen.value = !macrosOpen.value
    if (ui.selection.kind === 'macros') return
  }
  macrosOpen.value = true
  ui.select({ kind: 'macros' })
}
function selectMacro(id: string) {
  macrosOpen.value = true
  ui.select({ kind: 'macro', macroId: id })
}
function selectPages() {
  if (ui.selection.kind === 'pages' || ui.selection.kind === 'page' || ui.selection.kind === 'state' || ui.selection.kind === 'pairs') {
    // Already in pages area: toggle fold when clicking the section label again
    if (ui.selection.kind === 'pages') {
      pagesOpen.value = !pagesOpen.value
      return
    }
  }
  pagesOpen.value = true
  ui.select({ kind: 'pages' })
}
function selectPairs() {
  pagesOpen.value = true
  ui.select({ kind: 'pairs' })
}
function selectPage(id: string) {
  pagesOpen.value = true
  ui.select({ kind: 'page', pageId: id })
}
function selectNode(pageId: string, nodeId: string) {
  caseOpen.value = { ...caseOpen.value, [pageId]: true }
  ui.select({ kind: 'state', pageId, nodeId })
}

function onAddPage() {
  ui.pageWizardOpen = true
}

function pageHasError(pageId: string) {
  return project.issues.some(
    (i) => i.level === 'error' && (i.text.includes(pageId) || i.text.includes(`pages/${pageId}`)),
  )
}
async function onAddMacro() {
  const name = await ui.askPrompt({
    title: t('add_macro'),
    initial: t('default_macro_name'),
  })
  if (name) await project.addMacro(name.trim())
}
</script>

<template>
  <aside class="nav" :class="{ collapsed: prefs.navCollapsed }">
    <div class="nav-top">
      <button class="sf-btn sf-btn-ghost icon" :title="t('toggle_nav')" @click="prefs.toggleNav">☰</button>
      <span v-if="!prefs.navCollapsed" class="title">{{ project.project?.name }}</span>
    </div>

    <nav v-if="!prefs.navCollapsed" class="tree">
      <button
        class="node top"
        :class="{ active: ui.selection.kind === 'variables' }"
        @click="selectVariables"
      >
        <I18nText k="variables" />
        <span v-if="project.undeclared.length" class="sf-badge sf-badge-warn">!</span>
      </button>

      <div class="group">
        <div class="group-head">
          <button
            type="button"
            class="twist"
            :aria-expanded="macrosOpen"
            @click="macrosOpen = !macrosOpen"
          >
            {{ macrosOpen ? '▾' : '▸' }}
          </button>
          <button
            class="node top grow"
            :class="{ active: ui.selection.kind === 'macros' }"
            @click="selectMacros"
          >
            <I18nText k="macros" />
            <span class="count">{{ macros.length }}</span>
          </button>
        </div>
        <div v-show="macrosOpen" class="group-body">
          <button
            v-for="m in macros"
            :key="m.id"
            class="node child"
            :class="{ active: ui.selection.kind === 'macro' && ui.selection.macroId === m.id }"
            @click="selectMacro(m.id)"
          >
            {{ m.name || m.id }}
          </button>
        </div>
      </div>

      <div class="group">
        <div class="group-head">
          <button
            type="button"
            class="twist"
            :aria-expanded="pagesOpen"
            @click="pagesOpen = !pagesOpen"
          >
            {{ pagesOpen ? '▾' : '▸' }}
          </button>
          <button
            class="node top grow"
            :class="{ active: ui.selection.kind === 'pages' }"
            @click="selectPages"
          >
            <I18nText k="pages" />
            <span class="count">{{ pages.length }}</span>
          </button>
        </div>
        <div v-show="pagesOpen" class="group-body">
          <button
            class="node child"
            :class="{ active: ui.selection.kind === 'pairs' }"
            @click="selectPairs"
          >
            <I18nText k="page_pairs" />
          </button>

          <div v-for="p in pages" :key="p.id" class="page-block">
            <div class="page-row">
              <button
                v-if="p.state_tree.length"
                type="button"
                class="twist sm"
                :aria-expanded="!!caseOpen[p.id]"
                :title="t('expand_cases')"
                @click="toggleCases(p.id)"
              >
                {{ caseOpen[p.id] ? '▾' : '▸' }}
              </button>
              <span v-else class="twist-spacer" />
              <button
                class="node child page grow"
                :class="{ active: ui.selection.kind === 'page' && ui.selection.pageId === p.id }"
                @click="selectPage(p.id)"
              >
                <span>{{ p.name }}</span>
                <span v-if="pageHasError(p.id)" class="err-dot" :title="t('err_has_errors')" />
              </button>
            </div>
            <div v-show="caseOpen[p.id]" class="cases">
              <button
                v-for="{ node: n, depth } in caseRows(p.state_tree)"
                :key="`${p.id}/${n.id}`"
                class="node grandchild"
                :style="{ paddingLeft: `${1.55 + depth * 0.75}rem` }"
                :class="{
                  active:
                    ui.selection.kind === 'state' &&
                    ui.selection.pageId === p.id &&
                    ui.selection.nodeId === n.id,
                }"
                @click="selectNode(p.id, n.id)"
              >
                <span class="case-name">{{ n.name || n.id }}</span>
                <span v-if="isElse(n)" class="mark else" :title="t('else')"><I18nText k="else" /></span>
                <span v-else-if="n.when_var" class="mark when" :title="t('when')"><I18nText k="when_short" /></span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </nav>

    <div v-if="!prefs.navCollapsed" class="nav-actions">
      <button class="sf-btn" @click="onAddPage"><I18nText k="add_page" /></button>
      <button class="sf-btn" @click="onAddMacro"><I18nText k="add_macro" /></button>
    </div>
  </aside>
</template>

<style scoped>
.nav {
  width: var(--sf-nav-width);
  background: var(--sf-surface);
  border-right: 1px solid var(--sf-line);
  display: flex;
  flex-direction: column;
  transition: width 0.2s ease;
  min-height: 0;
}
.nav.collapsed {
  width: var(--sf-nav-collapsed);
}
.nav-top {
  display: flex;
  align-items: center;
  gap: var(--sf-space-2);
  padding: var(--sf-space-3);
  border-bottom: 1px solid var(--sf-line);
}
.title {
  font-weight: 600;
  font-size: var(--sf-fs-sm);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.icon {
  padding: 0.35rem 0.5rem;
}
.tree {
  flex: 1;
  overflow: auto;
  padding: var(--sf-space-2) var(--sf-space-2) var(--sf-space-3);
}
.group {
  margin-top: 0.35rem;
}
.group-head,
.page-row {
  display: flex;
  align-items: center;
  gap: 0.1rem;
}
.twist {
  border: none;
  background: transparent;
  width: 1.25rem;
  height: 1.25rem;
  padding: 0;
  color: var(--sf-ink-faint);
  font-size: 0.7rem;
  flex-shrink: 0;
  border-radius: 4px;
}
.twist:hover {
  background: var(--sf-surface-2);
  color: var(--sf-ink);
}
.twist.sm {
  width: 1.1rem;
}
.twist-spacer {
  width: 1.1rem;
  flex-shrink: 0;
}
.grow {
  flex: 1;
  min-width: 0;
}
.node {
  width: 100%;
  text-align: left;
  border: none;
  background: transparent;
  padding: 0.38rem 0.5rem;
  border-radius: var(--sf-radius);
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: var(--sf-fs-sm);
}
.node.top {
  font-weight: 600;
  color: var(--sf-ink);
}
.node:hover {
  background: var(--sf-surface-2);
}
.node.active {
  background: var(--sf-accent-soft);
  color: var(--sf-accent);
}
.count {
  margin-left: auto;
  font-size: var(--sf-fs-xs);
  font-weight: 500;
  color: var(--sf-ink-faint);
  font-variant-numeric: tabular-nums;
}
.child {
  padding-left: 0.35rem;
  font-weight: 400;
  color: var(--sf-ink-muted);
}
.child.page {
  font-weight: 500;
  color: var(--sf-ink);
}
.grandchild {
  padding-left: 1.55rem;
  color: var(--sf-ink-muted);
  font-size: var(--sf-fs-xs);
}
.case-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.mark {
  margin-left: auto;
  font-size: 0.65rem;
  font-weight: 600;
  padding: 0.05rem 0.3rem;
  border-radius: 3px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  max-width: 4.5rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.mark.else {
  background: var(--sf-surface-2);
  color: var(--sf-ink-muted);
}
.mark.when {
  background: var(--sf-accent-soft);
  color: var(--sf-accent);
}
.err-dot {
  width: 0.4rem;
  height: 0.4rem;
  border-radius: 50%;
  background: var(--sf-danger);
  margin-left: auto;
  flex-shrink: 0;
}
.nav-actions {
  display: flex;
  flex-direction: column;
  gap: var(--sf-space-2);
  padding: var(--sf-space-3);
  border-top: 1px solid var(--sf-line);
}
.nav-actions .sf-btn {
  justify-content: center;
}
</style>
