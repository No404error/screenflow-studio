<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from '@/i18n'
import SectionHelp from '@/components/SectionHelp.vue'
import { useProjectStore } from '@/stores/project'
import { useUiStore } from '@/stores/ui'
import { coerceDefault, inferType } from '@/utils/vars'
import type { JsonValue, VarType } from '@/types/project'

const { t } = useI18n()
const project = useProjectStore()
const ui = useUiStore()

interface Row {
  name: string
  type: VarType
  defaultValue: string
  description: string
  refs: number
}

const rows = computed(() => {
  const p = project.project
  if (!p) return [] as Row[]
  const vars = p.vars || {}
  const schema = p.var_schema || {}
  const counts = new Map<string, number>()
  for (const r of project.varRefs) {
    counts.set(r.name, (counts.get(r.name) || 0) + 1)
  }
  const names = new Set([...Object.keys(vars), ...Object.keys(schema), ...counts.keys()])
  return [...names].sort().map((name) => {
    const val = vars[name]
    const meta = schema[name] || {}
    const type = (meta.type as VarType) || inferType(val)
    return {
      name,
      type,
      defaultValue: val === undefined || val === null ? '' : String(val),
      description: meta.description || '',
      refs: counts.get(name) || 0,
    }
  })
})

function ensure() {
  const p = project.project!
  if (!p.vars) p.vars = {}
  if (!p.var_schema) p.var_schema = {}
}

function addRow() {
  ensure()
  let base = 'var'
  let n = 1
  while (project.project!.vars![`${base}${n}`] !== undefined) n++
  const name = `${base}${n}`
  project.project!.vars![name] = false
  project.project!.var_schema![name] = { type: 'bool', description: '' }
  project.markDirty()
}

function rename(oldName: string, newName: string) {
  ensure()
  const p = project.project!
  newName = newName.trim()
  if (!newName || newName === oldName) return
  if (p.vars![newName] !== undefined) {
    alert('Name exists')
    return
  }
  p.vars![newName] = p.vars![oldName]
  delete p.vars![oldName]
  p.var_schema![newName] = { ...(p.var_schema![oldName] || {}) }
  delete p.var_schema![oldName]
  // Sync refs in when/set/clear strings
  const replaceName = (s: string | null | undefined) => {
    if (!s) return s
    if (s === oldName) return newName
    if (s.startsWith(oldName + '=')) return newName + s.slice(oldName.length)
    return s
  }
  for (const page of Object.values(p.page_docs)) {
    const walk = (nodes: typeof page.state_tree) => {
      for (const node of nodes || []) {
        if (node.when_var) node.when_var = replaceName(node.when_var) || null
        for (const step of node.actions || []) {
          if (step.op === 'set_var' || step.op === 'clear_var') {
            step.target = replaceName(String(step.target ?? '')) as string
          }
        }
        if (node.children) walk(node.children)
        if (node.post?.tree) walk(node.post.tree)
      }
    }
    walk(page.state_tree)
  }
  for (const m of p.macros || []) {
    for (const step of m.steps || []) {
      if (step.op === 'set_var' || step.op === 'clear_var') {
        step.target = replaceName(String(step.target ?? '')) as string
      }
    }
  }
  project.markDirty()
}

function setType(name: string, type: VarType) {
  ensure()
  const p = project.project!
  p.var_schema![name] = { ...(p.var_schema![name] || {}), type }
  const raw = String(p.vars![name] ?? '')
  p.vars![name] = coerceDefault(type, raw) as JsonValue
  project.markDirty()
}

function setDefault(name: string, raw: string, type: VarType) {
  ensure()
  project.project!.vars![name] = coerceDefault(type, raw) as JsonValue
  project.markDirty()
}

function setDesc(name: string, description: string) {
  ensure()
  project.project!.var_schema![name] = {
    ...(project.project!.var_schema![name] || {}),
    description,
  }
  project.markDirty()
}

function remove(name: string) {
  ensure()
  delete project.project!.vars![name]
  delete project.project!.var_schema![name]
  project.markDirty()
}

function jumpRef(name: string) {
  const ref = project.varRefs.find((r) => r.name === name)
  if (!ref) return
  if (ref.macroId) ui.select({ kind: 'macro', macroId: ref.macroId })
  else if (ref.pageId && ref.nodeId) ui.select({ kind: 'state', pageId: ref.pageId, nodeId: ref.nodeId })
  else if (ref.pageId) ui.select({ kind: 'page', pageId: ref.pageId })
}
</script>

<template>
  <div v-if="project.project" class="vars">
    <header class="head">
      <div>
        <h2>{{ t('variables') }}</h2>
        <p class="sub">
          {{ t('help_vars') }}
          <SectionHelp :text="t('help_vars')" />
        </p>
      </div>
      <button class="sf-btn sf-btn-primary" type="button" @click="addRow">+ {{ t('variables') }}</button>
    </header>

    <p v-if="project.undeclared.length" class="warn-banner">
      {{ t('undeclared') }}:
      <code v-for="u in [...new Set(project.undeclared.map((x) => x.name))]" :key="u">{{ u }}</code>
    </p>

    <table>
      <thead>
        <tr>
          <th>{{ t('name') }}</th>
          <th>{{ t('type') }}</th>
          <th>{{ t('default') }}</th>
          <th>{{ t('description') }}</th>
          <th>{{ t('refs') }}</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in rows" :key="r.name">
          <td>
            <input
              class="sf-input sf-mono"
              :value="r.name"
              @change="rename(r.name, ($event.target as HTMLInputElement).value)"
            />
          </td>
          <td>
            <select class="sf-select" :value="r.type" @change="setType(r.name, ($event.target as HTMLSelectElement).value as any)">
              <option value="bool">bool</option>
              <option value="number">number</option>
              <option value="string">string</option>
            </select>
          </td>
          <td>
            <input
              class="sf-input"
              :value="r.defaultValue"
              @change="setDefault(r.name, ($event.target as HTMLInputElement).value, r.type)"
            />
          </td>
          <td>
            <input
              class="sf-input"
              :value="r.description"
              @change="setDesc(r.name, ($event.target as HTMLInputElement).value)"
            />
          </td>
          <td>
            <button type="button" class="ref" @click="jumpRef(r.name)">{{ r.refs }}</button>
          </td>
          <td>
            <button type="button" class="sf-btn sf-btn-danger" @click="remove(r.name)">×</button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-if="!rows.length" class="sf-empty">{{ t('help_vars') }}</p>
  </div>
</template>

<style scoped>
.head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--sf-space-4);
}
h2 {
  margin: 0;
  font-size: var(--sf-fs-xl);
}
.sub {
  margin: 0.35rem 0 0;
  color: var(--sf-ink-muted);
  font-size: var(--sf-fs-sm);
}
.warn-banner {
  background: var(--sf-warn-soft);
  border: 1px solid color-mix(in srgb, var(--sf-warn) 35%, var(--sf-line));
  border-radius: var(--sf-radius);
  padding: 0.5rem 0.75rem;
  font-size: var(--sf-fs-sm);
}
.warn-banner code {
  margin-left: 0.35rem;
  font-family: var(--sf-mono);
}
table {
  width: 100%;
  border-collapse: collapse;
  background: var(--sf-surface);
  border: 1px solid var(--sf-line);
  border-radius: var(--sf-radius-lg);
  overflow: hidden;
}
th,
td {
  padding: 0.45rem 0.5rem;
  border-bottom: 1px solid var(--sf-line);
  text-align: left;
  vertical-align: middle;
}
th {
  font-size: var(--sf-fs-xs);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--sf-ink-muted);
  background: var(--sf-surface-2);
}
.ref {
  border: none;
  background: var(--sf-accent-soft);
  color: var(--sf-accent);
  border-radius: 999px;
  padding: 0.1rem 0.55rem;
  font-family: var(--sf-mono);
}
</style>
