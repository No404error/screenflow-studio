import { api } from '@/api/client'
import type { ProjectDTO } from '@/types/project'
import { cropFileByRoi } from '@/utils/cropUpload'

/** Fetch a project-relative image as a File for cropping. */
export async function fileFromRelpath(relpath: string, name = 'original'): Promise<File> {
  const res = await fetch(api.fileUrl(relpath))
  if (!res.ok) throw new Error(`failed to load ${relpath}`)
  const blob = await res.blob()
  const ext = relpath.includes('.') ? relpath.slice(relpath.lastIndexOf('.')) : '.png'
  return new File([blob], `${name}${ext}`, { type: blob.type || 'image/png' })
}

export function newestSourceId(dto: ProjectDTO, pageId: string, before: Set<string>): string | null {
  const map = dto.page_docs[pageId]?.sources || {}
  for (const id of Object.keys(map)) {
    if (!before.has(id)) return id
  }
  return Object.keys(map).at(-1) || null
}

/**
 * Create a match setup from an existing page original, or upload a new original first.
 */
export async function createVisualFromOriginal(
  pageId: string,
  opts: {
    /** Existing original id; if omitted, `file` is uploaded as a new original. */
    sourceId?: string | null
    file: File
    searchRoi: number[] | null
    contentRoi: number[]
    name: string
    /** Source ids present before upload (required when sourceId is omitted). */
    beforeSourceIds?: Set<string>
  },
): Promise<ProjectDTO> {
  let sourceId = (opts.sourceId || '').trim()
  if (!sourceId) {
    const before = opts.beforeSourceIds || new Set<string>()
    const uploadedDto = await api.uploadPageSource(pageId, opts.file, opts.name || undefined)
    sourceId = newestSourceId(uploadedDto, pageId, before) || ''
    if (!sourceId) throw new Error('source missing after upload')
  }
  const toSend = await cropFileByRoi(opts.file, opts.contentRoi)
  const uploaded = await api.uploadAsset(pageId, toSend, opts.name || undefined)
  return api.createVisual(pageId, {
    template: uploaded.relpath,
    label: opts.name || uploaded.name,
    search_roi: opts.searchRoi,
    content_roi: opts.contentRoi,
    source_id: sourceId,
  })
}

/** Upload new original + create setup (no existing source_id). */
export async function createVisualFromScreenshot(
  pageId: string,
  file: File,
  payload: {
    searchRoi: number[] | null
    contentRoi: number[]
    name: string
  },
  beforeSourceIds?: Set<string>,
): Promise<ProjectDTO> {
  return createVisualFromOriginal(pageId, {
    file,
    searchRoi: payload.searchRoi,
    contentRoi: payload.contentRoi,
    name: payload.name,
    beforeSourceIds,
  })
}
