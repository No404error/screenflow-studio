import type { PageDoc, ProjectDTO } from '@/types/project'

/** Local page fields that may be edited without an immediate server round-trip. */
const DIRTY_PAGE_KEYS: (keyof PageDoc)[] = [
  'name',
  'detect_priority',
  'pair_with',
  'decide_params',
  'default_post',
  'state_tree',
]

/**
 * Merge a server project snapshot with unsaved local page edits.
 * Server wins for features/visuals/assets/sources; local dirty page editor fields are kept.
 */
export function mergeDirtyPageDocs(local: ProjectDTO, server: ProjectDTO): ProjectDTO {
  const out: ProjectDTO = {
    ...server,
    page_docs: { ...(server.page_docs || {}) },
  }
  const localDocs = local.page_docs || {}
  for (const [pid, localPage] of Object.entries(localDocs)) {
    const serverPage = out.page_docs[pid]
    if (!serverPage) continue
    const merged: PageDoc = { ...serverPage }
    for (const key of DIRTY_PAGE_KEYS) {
      if (key in localPage) {
        ;(merged as unknown as Record<string, unknown>)[key] = localPage[key]
      }
    }
    out.page_docs[pid] = merged
  }
  // Preserve other dirty root fields commonly edited in Studio
  if (local.runtime) out.runtime = { ...server.runtime, ...local.runtime }
  if (local.var_schema) out.var_schema = { ...local.var_schema }
  if (local.vars) out.vars = { ...local.vars }
  if (local.macros) out.macros = local.macros
  if (local.name) out.name = local.name
  return out
}
