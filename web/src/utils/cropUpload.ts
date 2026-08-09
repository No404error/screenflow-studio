/** Solid fill used for privacy redaction (matches --sf-ink). */
export const REDACT_FILL = '#1a2220'

/** Crop an image File by normalized ROI [y0,y1,x0,x1] and return a PNG File. */

export async function cropFileByRoi(file: File, roi: number[]): Promise<File> {
  const [y0, y1, x0, x1] = roi
  const url = URL.createObjectURL(file)
  try {
    const img = await loadImage(url)
    const sx = Math.round(Math.min(x0, x1) * img.naturalWidth)
    const sy = Math.round(Math.min(y0, y1) * img.naturalHeight)
    const sw = Math.max(1, Math.round(Math.abs(x1 - x0) * img.naturalWidth))
    const sh = Math.max(1, Math.round(Math.abs(y1 - y0) * img.naturalHeight))
    const canvas = document.createElement('canvas')
    canvas.width = sw
    canvas.height = sh
    const ctx = canvas.getContext('2d')
    if (!ctx) throw new Error('canvas')
    ctx.drawImage(img, sx, sy, sw, sh, 0, 0, sw, sh)
    const blob = await new Promise<Blob>((resolve, reject) => {
      canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('toBlob'))), 'image/png')
    })
    const base = file.name.replace(/\.[^.]+$/, '') || 'crop'
    return new File([blob], `${base}_crop.png`, { type: 'image/png' })
  } finally {
    URL.revokeObjectURL(url)
  }
}

/**
 * Fill normalized ROIs [y0,y1,x0,x1] with solid ink; return a full-size PNG File.
 * Empty `rois` returns the original file unchanged.
 */
export async function redactFileByRois(file: File, rois: number[][]): Promise<File> {
  if (!rois.length) return file
  const url = URL.createObjectURL(file)
  try {
    const img = await loadImage(url)
    const canvas = document.createElement('canvas')
    canvas.width = img.naturalWidth
    canvas.height = img.naturalHeight
    const ctx = canvas.getContext('2d')
    if (!ctx) throw new Error('canvas')
    ctx.drawImage(img, 0, 0)
    ctx.fillStyle = REDACT_FILL
    for (const roi of rois) {
      if (!roi || roi.length !== 4) continue
      const [y0, y1, x0, x1] = roi
      const sx = Math.round(Math.min(x0, x1) * img.naturalWidth)
      const sy = Math.round(Math.min(y0, y1) * img.naturalHeight)
      const sw = Math.max(1, Math.round(Math.abs(x1 - x0) * img.naturalWidth))
      const sh = Math.max(1, Math.round(Math.abs(y1 - y0) * img.naturalHeight))
      ctx.fillRect(sx, sy, sw, sh)
    }
    const blob = await new Promise<Blob>((resolve, reject) => {
      canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('toBlob'))), 'image/png')
    })
    const base = file.name.replace(/\.[^.]+$/, '') || 'original'
    return new File([blob], `${base}.png`, { type: 'image/png' })
  } finally {
    URL.revokeObjectURL(url)
  }
}

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = () => reject(new Error('image load failed'))
    img.src = src
  })
}
