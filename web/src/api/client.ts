import type { EngineStatus, Issue, ProjectDTO } from '@/types/project'

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
    const msg =
      typeof detail === 'object' && detail && 'detail' in detail
        ? JSON.stringify((detail as { detail: unknown }).detail)
        : String(detail)
    throw new Error(msg || res.statusText)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export const api = {
  health: () => request<{ status: string }>('/api/health'),
  settings: () =>
    request<{
      lang: string
      recent: { path: string; name: string }[]
      runner_mode: string
    }>('/api/settings'),
  setLang: (lang: string) =>
    request<{ lang: string }>('/api/settings/lang', {
      method: 'POST',
      body: JSON.stringify({ lang }),
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
    return res.json() as Promise<{ name: string; relpath: string; roi?: number[] | null }>
  },
  deleteAsset: (pageId: string, name: string) =>
    request<ProjectDTO>(
      `/api/project/pages/${encodeURIComponent(pageId)}/assets/${encodeURIComponent(name)}`,
      { method: 'DELETE' },
    ),
  setAssetRoi: (pageId: string, name: string, roi: number[] | null) =>
    request<ProjectDTO>(
      `/api/project/pages/${encodeURIComponent(pageId)}/assets/${encodeURIComponent(name)}/roi`,
      { method: 'PUT', body: JSON.stringify({ roi }) },
    ),
  fileUrl: (relpath: string) => `/api/file?relpath=${encodeURIComponent(relpath)}`,
  validate: () => request<{ issues: Issue[]; ok: boolean }>('/api/validate', { method: 'POST' }),
  engineStart: () => request<{ status: EngineStatus; logs: string[] }>('/api/engine/start', { method: 'POST' }),
  enginePause: () => request('/api/engine/pause', { method: 'POST' }),
  engineResume: () => request('/api/engine/resume', { method: 'POST' }),
  engineStop: () => request('/api/engine/stop', { method: 'POST' }),
  engineStatus: () =>
    request<{ status: EngineStatus; logs: string[]; running: boolean }>('/api/engine/status'),
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
