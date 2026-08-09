import { api } from '@/api/client'
import type { ProjectDTO } from '@/types/project'
import { createVisualFromOriginal } from '@/utils/createVisualFromScreenshot'

/**
 * Upload a new page original + cropped template, create a match setup, select it.
 */
export async function bindFeatureFromScreenshot(
  pageId: string,
  featureId: string,
  file: File,
  payload: {
    searchRoi: number[] | null
    contentRoi: number[]
    name: string
  },
  opts?: { beforeSourceIds?: Set<string>; beforeVisualIds?: Set<string> },
): Promise<ProjectDTO> {
  const beforeVisuals = opts?.beforeVisualIds || new Set<string>()
  let dto = await createVisualFromOriginal(pageId, {
    file,
    searchRoi: payload.searchRoi,
    contentRoi: payload.contentRoi,
    name: payload.name,
    beforeSourceIds: opts?.beforeSourceIds || new Set(),
  })
  const visuals = dto.page_docs[pageId]?.visuals || {}
  let createdId: string | null = null
  for (const id of Object.keys(visuals)) {
    if (!beforeVisuals.has(id)) {
      createdId = id
      break
    }
  }
  if (!createdId) createdId = Object.keys(visuals).at(-1) || null
  if (!createdId) throw new Error('visual missing after create')
  dto = await api.selectFeatureVisual(pageId, featureId, createdId)
  return dto
}
