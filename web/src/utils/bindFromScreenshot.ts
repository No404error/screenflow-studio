import { api } from '@/api/client'
import { cropFileByRoi } from '@/utils/cropUpload'

/** Upload page source + cropped artwork, then bind feature with both ROIs. */
export async function bindFeatureFromScreenshot(
  pageId: string,
  featureId: string,
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
  await api.bindFeature(pageId, featureId, {
    asset: uploaded.relpath,
    search_roi: payload.searchRoi,
    content_roi: payload.contentRoi,
  })
  return uploaded
}
