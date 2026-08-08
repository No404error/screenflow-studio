import type { StateNode } from '@/types/project'

export function isElse(n: StateNode): boolean {
  return !!(n.else || n.is_else)
}

export function newCaseId(prefix = 'case'): string {
  return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`
}

export function makeCase(
  name: string,
  opts?: { isElse?: boolean; featureKey?: string | null },
): StateNode {
  const id = newCaseId(opts?.isElse ? 'else' : 'case')
  if (opts?.isElse) {
    return { id, name: name || 'Other', else: true, actions: [], children: [] }
  }
  return {
    id,
    name,
    priority: 0,
    score: { kind: 'template', key: opts?.featureKey ?? null },
    actions: [],
    children: [],
  }
}

/** Find node and its sibling list + index. Does not search post trees. */
export function locateNode(
  roots: StateNode[],
  id: string,
): { parent: StateNode | null; siblings: StateNode[]; index: number; node: StateNode } | null {
  const walk = (
    siblings: StateNode[],
    parent: StateNode | null,
  ): ReturnType<typeof locateNode> => {
    for (let i = 0; i < siblings.length; i++) {
      const n = siblings[i]
      if (n.id === id) return { parent, siblings, index: i, node: n }
      const hit = walk(n.children || [], n)
      if (hit) return hit
    }
    return null
  }
  return walk(roots, null)
}

export function findNodeInTree(roots: StateNode[], id: string): StateNode | null {
  return locateNode(roots, id)?.node ?? null
}

export function removeNodeFromTree(roots: StateNode[], id: string): StateNode[] {
  const loc = locateNode(roots, id)
  if (!loc) return roots
  loc.siblings.splice(loc.index, 1)
  return roots
}

export function moveNodeInTree(roots: StateNode[], id: string, dir: -1 | 1): boolean {
  const loc = locateNode(roots, id)
  if (!loc) return false
  const j = loc.index + dir
  if (j < 0 || j >= loc.siblings.length) return false
  const a = loc.siblings[loc.index]
  loc.siblings[loc.index] = loc.siblings[j]
  loc.siblings[j] = a
  pinElseLast(loc.siblings)
  return true
}

/** Keep default-case (ELSE) pinned at the end of a sibling list. */
export function pinElseLast(siblings: StateNode[]): void {
  const elseNodes = siblings.filter(isElse)
  if (!elseNodes.length) return
  const others = siblings.filter((n) => !isElse(n))
  siblings.splice(0, siblings.length, ...others, ...elseNodes)
}

/**
 * Reorder among the same sibling list: move `dragId` to the index of `targetId`.
 * Cross-parent drops are ignored. ELSE is re-pinned last afterward.
 */
export function moveNodeAmongSiblings(
  roots: StateNode[],
  dragId: string,
  targetId: string,
): boolean {
  if (dragId === targetId) return false
  const from = locateNode(roots, dragId)
  const to = locateNode(roots, targetId)
  if (!from || !to || from.siblings !== to.siblings) return false
  const sibs = from.siblings
  const fromIdx = from.index
  let toIdx = to.index
  const [node] = sibs.splice(fromIdx, 1)
  if (toIdx > fromIdx) toIdx -= 1
  sibs.splice(toIdx, 0, node)
  pinElseLast(sibs)
  return true
}

export function addSibling(
  roots: StateNode[],
  selectedId: string | null,
  node: StateNode,
): StateNode[] {
  if (!selectedId) {
    roots.push(node)
    return roots
  }
  const loc = locateNode(roots, selectedId)
  if (!loc) {
    roots.push(node)
    return roots
  }
  loc.siblings.splice(loc.index + 1, 0, node)
  return roots
}

export function addChild(roots: StateNode[], parentId: string, node: StateNode): boolean {
  const parent = findNodeInTree(roots, parentId)
  if (!parent) return false
  if (isElse(parent)) return false
  parent.children = parent.children || []
  // Promoting leaf→branch: clear actions/post per engine rules
  if (!parent.children.length) {
    parent.actions = []
    parent.post = null
  }
  parent.children.push(node)
  return true
}

export function flattenTree(
  roots: StateNode[],
  depth = 0,
): { node: StateNode; depth: number }[] {
  const out: { node: StateNode; depth: number }[] = []
  for (const n of roots) {
    out.push({ node: n, depth })
    if (n.children?.length) out.push(...flattenTree(n.children, depth + 1))
  }
  return out
}

export function hasElseAmong(siblings: StateNode[]): boolean {
  return siblings.some(isElse)
}
