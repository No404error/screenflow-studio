import { api } from '@/api/client'
import { cropFileByRoi } from '@/utils/cropUpload'

/** Upload page canvas + cropped template, then create a match setup. */
export async function createVisualFromScreenshot(
  pageId: string,
  file: File,
  payload: {
    searchRoi: number[] | null
    contentRoi: number[]
    name: string
  },
) {
  await api.uploadPageSource(pageId, file)
  const toSend = await cropFileByRoi(file, payload.contentRoi)
  const uploaded = await api.uploadAsset(pageId, toSend, payload.name || undefined)
  await api.createVisual(pageId, {
    template: uploaded.relpath,
    label: payload.name || uploaded.name,
    search_roi: payload.searchRoi,
    content_roi: payload.contentRoi,
  })
  return uploaded
}
