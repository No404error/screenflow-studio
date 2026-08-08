<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from '@/i18n'
import { useUiStore } from '@/stores/ui'
import { useProjectStore } from '@/stores/project'
import type { StateNode } from '@/types/project'

const { t } = useI18n()
const ui = useUiStore()
const project = useProjectStore()

const pages = computed(() => Object.values(project.project?.page_docs || {}))
const macros = computed(() => project.project?.macros || [])

function isElse(n: StateNode) {
  return !!(n.else || n.is_else)
}

function selectVariables() {
  ui.select({ kind: 'variables' })
}
function selectMacros() {
  ui.select({ kind: 'macros' })
}
function selectMacro(id: string) {
  ui.select({ kind: 'macro', macroId: id })
}
function selectPages() {
  ui.select({ kind: 'pages' })
}
function selectPairs() {
  ui.select({ kind: 'pairs' })
}
function selectPage(id: string) {
  ui.select({ kind: 'page', pageId: id })
}
function selectNode(pageId: string, nodeId: string) {
  ui.select({ kind: 'state', pageId, nodeId })
}

async function onAddPage() {
  const name = window.prompt(t('wizard_page'), 'Page')
  if (name) await project.addPage(name)
}
async function onAddMacro() {
  const name = window.prompt(t('add_macro'), 'macro')
  if (name) await project.addMacro(name)
}
</script>

<template>
  <aside class="nav" :class="{ collapsed: ui.navCollapsed }">
    <div class="nav-top">
      <button class="sf-btn sf-btn-ghost icon" title="Toggle (Ctrl+B)" @click="ui.toggleNav">☰</button>
      <span v-if="!ui.navCollapsed" class="title">{{ project.project?.name }}</span>
    </div>
    <nav v-if="!ui.navCollapsed" class="tree">
      <button
        class="node"
        :class="{ active: ui.selection.kind === 'variables' }"
        @click="selectVariables"
      >
        {{ t('variables') }}
        <span v-if="project.undeclared.length" class="sf-badge sf-badge-warn">!</span>
      </button>

      <div class="group">
        <button class="node" :class="{ active: ui.selection.kind === 'macros' }" @click="selectMacros">
          {{ t('macros') }}
        </button>
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

      <div class="group">
        <button class="node" :class="{ active: ui.selection.kind === 'pages' }" @click="selectPages">
          {{ t('pages') }}
        </button>
        <button
          class="node child"
          :class="{ active: ui.selection.kind === 'pairs' }"
          @click="selectPairs"
        >
          {{ t('page_pairs') }}
        </button>
        <div v-for="p in pages" :key="p.id" class="page-block">
          <button
            class="node child"
            :class="{ active: ui.selection.kind === 'page' && ui.selection.pageId === p.id }"
            @click="selectPage(p.id)"
          >
            {{ p.name || p.id }}
          </button>
          <button
            v-for="n in p.state_tree || []"
            :key="`${p.id}/${n.id}`"
            class="node grandchild"
            :class="{
              active:
                ui.selection.kind === 'state' &&
                ui.selection.pageId === p.id &&
                ui.selection.nodeId === n.id,
            }"
            @click="selectNode(p.id, n.id)"
          >
            <span>{{ n.name || n.id }}</span>
            <span v-if="isElse(n)" class="sf-badge sf-badge-else">{{ t('else') }}</span>
            <span v-if="n.when_var" class="sf-badge sf-badge-when">if</span>
            <span
              v-if="(n.actions || []).some((s) => s.op === 'set_var' || s.op === 'clear_var')"
              class="sf-badge sf-badge-set"
              >var</span
            >
          </button>
        </div>
      </div>
    </nav>
    <div v-if="!ui.navCollapsed" class="nav-actions">
      <button class="sf-btn" @click="onAddPage">{{ t('add_page') }}</button>
      <button class="sf-btn" @click="onAddMacro">{{ t('add_macro') }}</button>
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
  padding: var(--sf-space-2);
}
.node {
  width: 100%;
  text-align: left;
  border: none;
  background: transparent;
  padding: 0.4rem 0.55rem;
  border-radius: var(--sf-radius);
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: var(--sf-fs-sm);
}
.node:hover {
  background: var(--sf-surface-2);
}
.node.active {
  background: var(--sf-accent-soft);
  color: var(--sf-accent);
  font-weight: 600;
}
.child {
  padding-left: 1.1rem;
}
.grandchild {
  padding-left: 1.8rem;
  color: var(--sf-ink-muted);
}
.nav-actions {
  display: flex;
  flex-direction: column;
  gap: var(--sf-space-2);
  padding: var(--sf-space-3);
  border-top: 1px solid var(--sf-line);
}
</style>
