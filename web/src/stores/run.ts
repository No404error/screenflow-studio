import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api, connectWs } from '@/api/client'
import type { EngineStatus, JsonValue } from '@/types/project'
import { useProjectStore } from './project'
import { useUiStore } from './ui'

export const useRunStore = defineStore('run', () => {
  const status = ref<EngineStatus>({ mode: 'idle' })
  const logs = ref<string[]>([])
  const connected = ref(false)
  let ws: WebSocket | null = null

  const mode = computed(() => status.value.mode || 'idle')
  const liveVars = computed(() => status.value.vars || {})
  const isRunning = computed(() => mode.value === 'running')
  const isPaused = computed(() => mode.value === 'paused')
  const isActive = computed(() => isRunning.value || isPaused.value)

  function connect() {
    if (ws) return
    ws = connectWs((ev) => {
      const e = ev as { type?: string; payload?: EngineStatus; message?: string; snapshot?: { status: EngineStatus; logs: string[] } }
      if (e.type === 'hello' && e.snapshot) {
        status.value = e.snapshot.status || { mode: 'idle' }
        logs.value = e.snapshot.logs || []
        connected.value = true
      } else if (e.type === 'status' && e.payload) {
        status.value = e.payload
      } else if (e.type === 'log' && e.message) {
        logs.value = [...logs.value.slice(-400), e.message]
      }
    })
    ws.onclose = () => {
      connected.value = false
      ws = null
      setTimeout(connect, 1500)
    }
  }

  async function start() {
    const proj = useProjectStore()
    if (proj.dirty) await proj.save()
    const r = await proj.validate()
    if (!r.ok) {
      useUiStore().drawerOpen = true
      useUiStore().drawerTab = 'controls'
      throw new Error('Validation failed')
    }
    const snap = await api.engineStart()
    status.value = snap.status
    logs.value = snap.logs || []
    useUiStore().drawerOpen = true
  }

  async function pause() {
    await api.enginePause()
  }

  async function resume() {
    await api.engineResume()
  }

  async function stop() {
    await api.engineStop()
    status.value = { mode: 'idle', vars: {} }
  }

  async function applyRuntime() {
    const p = useProjectStore().project
    if (!p) return
    await api.patchRuntime(p.runtime as unknown as Record<string, unknown>)
  }

  function varEntries(): [string, JsonValue][] {
    return Object.entries(liveVars.value)
  }

  return {
    status,
    logs,
    connected,
    mode,
    liveVars,
    isRunning,
    isPaused,
    isActive,
    connect,
    start,
    pause,
    resume,
    stop,
    applyRuntime,
    varEntries,
  }
})
