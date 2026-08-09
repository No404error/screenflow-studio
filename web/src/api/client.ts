import type { EngineStatus, Issue, ProjectDTO, StateNode } from '@/types/project'

export class ApiError extends Error {
  status: number
  detail: unknown
  constructor(status: number, detail: unknown) {
    const msg =
      typeof detail === 'object' && detail && 'message' in detail
        ? String((detail as { message: string }).message)
        : typeof detail === 'object' && detail && 'detail' in detail
          ? JSON.stringify((detail as { detail: unknown }).detail)
          : String(detail)
    super(msg || `HTTP ${status}`)
    this.status = status
    this.detail = detail
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...(init?.headers || {}),
    },
  })
  if (!res.ok) {
    let detail: unknown
    try {
      detail = await res.json()
    } catch {
      detail = await res.text()
    }
    const payload =
      typeof detail === 'object' && detail && 'detail' in detail
        ? (detail as { detail: unknown }).detail
        : detail
    throw new ApiError(res.status, payload)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export type SettingsDTO = {
  lang: string
  recent: { path: string; name: string }[]
  runner_mode: string
  reopen_last_project?: boolean
  reopen_path?: string | null
}

export const api = {
  settings: () => request<SettingsDTO>('/api/settings'),
  patchSettings: (patch: { runner_mode?: string; reopen_last_project?: boolean }) =>
    request<SettingsDTO>('/api/settings', {
      method: 'PATCH',
      body: JSON.stringify(patch),
    }),
  clearRecent: () => request<SettingsDTO>('/api/settings/clear-recent', { method: 'POST' }),
  setLang: (lang: string) =>
    request<{ lang: string }>('/api/settings/lang', {
      method: 'POST',
      body: JSON.stringify({ lang }),
    }),
  pickFolder: (initial?: string, title?: string) =>
    request<{ path: string | null }>('/api/dialog/folder', {
      method: 'POST',
      body: JSON.stringify({ initial, title }),
    }),
  openProject: (path: string) =>
    request<ProjectDTO>('/api/project/open', {
      method: 'POST',
      body: JSON.stringify({ path }),
    }),
  newProject: (parent: string, name: string) =>
    request<ProjectDTO>('/api/project/new', {
      method: 'POST',
      body: JSON.stringify({ parent, name }),
    }),
  closeProject: () => request<{ status: string }>('/api/project/close', { method: 'POST' }),
  getProject: () => request<ProjectDTO>('/api/project'),
  saveProject: (project: ProjectDTO) =>
    request<ProjectDTO>('/api/project', {
      method: 'PUT',
      body: JSON.stringify({ project }),
    }),
  addPage: (name: string) =>
    request<ProjectDTO>('/api/project/add-page', {
      method: 'POST',
      body: JSON.stringify({ name }),
    }),
  deletePage: (pageId: string) =>
    request<ProjectDTO>(`/api/project/pages/${encodeURIComponent(pageId)}`, {
      method: 'DELETE',
    }),
  addMacro: (name: string, id?: string) =>
    request<ProjectDTO>('/api/project/add-macro', {
      method: 'POST',
      body: JSON.stringify({ name, id }),
    }),
  deleteMacro: (macroId: string) =>
    request<ProjectDTO>(`/api/project/macros/${encodeURIComponent(macroId)}`, {
      method: 'DELETE',
    }),
  uploadAsset: async (pageId: string, file: File, preferredName?: string) => {
    const fd = new FormData()
    fd.append('file', file)
    const q = preferredName ? `?preferred_name=${encodeURIComponent(preferredName)}` : ''
    const res = await fetch(`/api/project/pages/${encodeURIComponent(pageId)}/assets${q}`, {
      method: 'POST',
      body: fd,
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json() as Promise<{ name: string; relpath: string }>
  },
  uploadPageSource: async (pageId: string, file: File, label?: string) => {
    const fd = new FormData()
    fd.append('file', file)
    const q = label ? `?label=${encodeURIComponent(label)}` : ''
    const res = await fetch(`/api/project/pages/${encodeURIComponent(pageId)}/sources${q}`, {
      method: 'POST',
      body: fd,
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json() as Promise<ProjectDTO>
  },
  patchPageSource: (pageId: string, sourceId: string, body: { label?: string }) =>
    request<ProjectDTO>(
      `/api/project/pages/${encodeURIComponent(pageId)}/sources/${encodeURIComponent(sourceId)}`,
      { method: 'PATCH', body: JSON.stringify(body) },
    ),
  deletePageSource: (pageId: string, sourceId: string) =>
    request<ProjectDTO>(
      `/api/project/pages/${encodeURIComponent(pageId)}/sources/${encodeURIComponent(sourceId)}`,
      { method: 'DELETE' },
    ),
  deleteAsset: (pageId: string, name: string) =>
    request<ProjectDTO>(
      `/api/project/pages/${encodeURIComponent(pageId)}/assets/${encodeURIComponent(name)}`,
      { method: 'DELETE' },
    ),
  createFeature: (pageId: string, body: { label?: string; id?: string; notes?: string }) =>
    request<ProjectDTO>(`/api/project/pages/${encodeURIComponent(pageId)}/features`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  patchFeature: (
    pageId: string,
    featureId: string,
    body: { label?: string; notes?: string; recognize?: boolean; id?: string },
  ) =>
    request<ProjectDTO>(
      `/api/project/pages/${encodeURIComponent(pageId)}/features/${encodeURIComponent(featureId)}`,
      { method: 'PATCH', body: JSON.stringify(body) },
    ),
  deleteFeature: (pageId: string, featureId: string) =>
    request<ProjectDTO>(
      `/api/project/pages/${encodeURIComponent(pageId)}/features/${encodeURIComponent(featureId)}`,
      { method: 'DELETE' },
    ),
  selectFeatureVisual: (pageId: string, featureId: string, visualId: string | null) =>
    request<ProjectDTO>(
      `/api/project/pages/${encodeURIComponent(pageId)}/features/${encodeURIComponent(featureId)}/visual`,
      { method: 'PUT', body: JSON.stringify({ visual_id: visualId }) },
    ),
  unbindFeature: (pageId: string, featureId: string) =>
    request<ProjectDTO>(
      `/api/project/pages/${encodeURIComponent(pageId)}/features/${encodeURIComponent(featureId)}/bind`,
      { method: 'DELETE' },
    ),
  createVisual: (
    pageId: string,
    body: {
      template: string
      label?: string
      id?: string
      search_roi?: number[] | null
      content_roi?: number[] | null
      source_id?: string | null
    },
  ) =>
    request<ProjectDTO>(`/api/project/pages/${encodeURIComponent(pageId)}/visuals`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  patchVisual: (
    pageId: string,
    visualId: string,
    body: {
      label?: string
      template?: string
      search_roi?: number[] | null
      content_roi?: number[] | null
      clear_search_roi?: boolean
      clear_content_roi?: boolean
      source_id?: string | null
      clear_source_id?: boolean
    },
  ) =>
    request<ProjectDTO>(
      `/api/project/pages/${encodeURIComponent(pageId)}/visuals/${encodeURIComponent(visualId)}`,
      { method: 'PATCH', body: JSON.stringify(body) },
    ),
  deleteVisual: (pageId: string, visualId: string) =>
    request<ProjectDTO>(
      `/api/project/pages/${encodeURIComponent(pageId)}/visuals/${encodeURIComponent(visualId)}`,
      { method: 'DELETE' },
    ),
  listTemplates: () => request<{ templates: string[] }>('/api/templates'),
  saveTemplate: (name: string, tree: StateNode[]) =>
    request<{ ok: boolean; name: string }>('/api/templates', {
      method: 'POST',
      body: JSON.stringify({ name, tree }),
    }),
  loadTemplate: (name: string) =>
    request<{ tree: StateNode[] }>(`/api/templates/${encodeURIComponent(name)}`),
  fileUrl: (relpath: string) => `/api/file?relpath=${encodeURIComponent(relpath)}`,
  validate: () =>
    request<{
      issues: Issue[]
      errors: Issue[]
      warnings: Issue[]
      ok: boolean
      has_warnings: boolean
    }>('/api/validate', { method: 'POST' }),
  engineStart: (opts?: { mode?: string; allow_warnings?: boolean }) =>
    request<{ status: EngineStatus; logs: string[]; running?: boolean; runner_mode?: string }>(
      '/api/engine/start',
      {
        method: 'POST',
        body: JSON.stringify(opts || {}),
      },
    ),
  enginePause: () => request('/api/engine/pause', { method: 'POST' }),
  engineResume: () => request('/api/engine/resume', { method: 'POST' }),
  engineStop: () => request('/api/engine/stop', { method: 'POST' }),
  patchRuntime: (runtime: Record<string, unknown>) =>
    request('/api/engine/runtime', {
      method: 'PATCH',
      body: JSON.stringify({ runtime }),
    }),
}

export function connectWs(onEvent: (ev: unknown) => void): WebSocket {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  const ws = new WebSocket(`${proto}://${location.host}/api/ws`)
  ws.onmessage = (m) => {
    try {
      onEvent(JSON.parse(m.data))
    } catch {
      /* ignore */
    }
  }
  const ping = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) ws.send('ping')
  }, 15000)
  ws.addEventListener('close', () => clearInterval(ping))
  return ws
}
