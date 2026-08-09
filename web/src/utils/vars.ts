import type { ActionStep, ProjectDTO, StateNode, VarType } from '@/types/project'

export interface VarRef {
  name: string
  kind: 'when' | 'set' | 'clear'
  pageId?: string
  nodeId?: string
  macroId?: string
  path: string
}

export function parseWhenVar(raw: string | null | undefined): { name: string; value?: string } | null {
  if (!raw || !String(raw).trim()) return null
  const s = String(raw).trim()
  const eq = s.indexOf('=')
  if (eq < 0) return { name: s }
  return { name: s.slice(0, eq).trim(), value: s.slice(eq + 1) }
}

export function formatWhenVar(name: string, value?: string | null): string {
  if (!name) return ''
  if (value === undefined || value === null || value === '') return name
  return `${name}=${value}`
}

export function parseSetVar(target: string | number | null | undefined): { name: string; value?: string } {
  const s = String(target ?? '').trim()
  if (!s) return { name: '' }
  const eq = s.indexOf('=')
  if (eq < 0) return { name: s, value: 'true' }
  return { name: s.slice(0, eq).trim(), value: s.slice(eq + 1) }
}

export function formatSetVar(name: string, value?: string | null): string {
  if (!name) return ''
  if (value === undefined || value === null || value === '') return name
  return `${name}=${value}`
}

export function inferType(v: unknown): VarType {
  if (typeof v === 'boolean') return 'bool'
  if (typeof v === 'number') return 'number'
  return 'string'
}

export function coerceDefault(type: VarType, raw: string): string | number | boolean {
  if (type === 'bool') {
    const t = raw.trim().toLowerCase()
    return t === '1' || t === 'true' || t === 'yes'
  }
  if (type === 'number') {
    const n = Number(raw)
    return Number.isFinite(n) ? n : 0
  }
  return raw
}

function walkNodes(
  nodes: StateNode[],
  pageId: string,
  path: string,
  out: VarRef[],
): void {
  for (const n of nodes) {
    const here = path ? `${path}/${n.name || n.id}` : n.name || n.id
    const when = parseWhenVar(n.when_var)
    if (when) out.push({ name: when.name, kind: 'when', pageId, nodeId: n.id, path: here })
    for (const step of n.actions || []) {
      collectStep(step, out, { pageId, nodeId: n.id, path: here })
    }
    if (n.children?.length) walkNodes(n.children, pageId, here, out)
    if (n.post?.tree?.length) walkNodes(n.post.tree, pageId, `${here}/post`, out)
  }
}

function collectStep(
  step: ActionStep,
  out: VarRef[],
  loc: { pageId?: string; nodeId?: string; macroId?: string; path: string },
): void {
  if (step.op === 'set_var') {
    const p = parseSetVar(step.target)
    if (p.name) out.push({ name: p.name, kind: 'set', ...loc })
  } else if (step.op === 'clear_var') {
    const name = String(step.target ?? '').trim()
    if (name) out.push({ name, kind: 'clear', ...loc })
  }
}

export function collectVarRefs(project: ProjectDTO): VarRef[] {
  const out: VarRef[] = []
  for (const [pageId, page] of Object.entries(project.page_docs || {})) {
    walkNodes(page.state_tree || [], pageId, page.name || pageId, out)
  }
  for (const m of project.macros || []) {
    for (const step of m.steps || []) {
      collectStep(step, out, { macroId: m.id, path: `macro:${m.name || m.id}` })
    }
  }
  return out
}

export function declaredVarNames(project: ProjectDTO): Set<string> {
  return new Set(Object.keys(project.vars || {}))
}

export function undeclaredRefs(project: ProjectDTO): VarRef[] {
  const declared = declaredVarNames(project)
  return collectVarRefs(project).filter((r) => !declared.has(r.name))
}
