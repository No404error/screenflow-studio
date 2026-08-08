import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { ApiError, api, connectWs } from '@/api/client'
import type { EngineStatus, Issue, JsonValue } from '@/types/project'
import { usePrefsStore } from './prefs'
import { useProjectStore } from './project'

export const useRunStore = defineStore('run', () => {
  const status = ref<EngineStatus>({ mode: 'idle' })
  const logs = ref<string[]>([])
  const connected = ref(false)
  /** Win default is elevate; synced from API settings / WS hello. */
  const runnerMode = ref('elevate')
  const pendingWarnings = ref<Issue[] | null>(null)
  let ws: WebSocket | null = null

  const mode = computed(() => status.value.mode || 'idle')
  const liveVars = computed(() => status.value.vars || {})
  const isRunning = computed(() => mode.value === 'running')
  const isPaused = computed(() => mode.value === 'paused')
  const isWaitingAdmin = computed(() => mode.value === 'waiting_admin')
  const isActive = computed(
    () => isRunning.value || isPaused.value || isWaitingAdmin.value,
  )

  function connect() {
    if (ws) return
    ws = connectWs((ev) => {
      const e = ev as {
        type?: string
        payload?: EngineStatus
        message?: string
        snapshot?: { status: EngineStatus; logs: string[]; runner_mode?: string }
      }
      if (e.type === 'hello' && e.snapshot) {
        status.value = e.snapshot.status || { mode: 'idle' }
        logs.value = e.snapshot.logs || []
        if (e.snapshot.runner_mode) runnerMode.value = e.snapshot.runner_mode
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

  async function start(opts?: { allowWarnings?: boolean }) {
    const proj = useProjectStore()
    const prefs = usePrefsStore()
    if (proj.dirty) await proj.save()
    const r = await proj.validate()
    if (!r.ok) {
      prefs.drawerOpen = true
      prefs.drawerTab = 'controls'
      throw new Error('validation_failed')
    }
    try {
      const snap = await api.engineStart({
        mode: runnerMode.value,
        allow_warnings: !!opts?.allowWarnings,
      })
      status.value = snap.status
      logs.value = snap.logs || []
      if (snap.runner_mode) runnerMode.value = snap.runner_mode
      pendingWarnings.value = null
      prefs.drawerOpen = true
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        const d = e.detail as { issues?: Issue[]; warnings_only?: boolean }
        pendingWarnings.value = (d.issues || []).filter((i) => i.level === 'warning')
        prefs.drawerOpen = true
        prefs.drawerTab = 'controls'
        return
      }
      throw e
    }
  }

  async function confirmWarnings() {
    await start({ allowWarnings: true })
  }

  function dismissWarnings() {
    pendingWarnings.value = null
  }

  async function setRunnerMode(mode: string) {
    runnerMode.value = mode
    await api.patchSettings({ runner_mode: mode })
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
    runnerMode,
    pendingWarnings,
    mode,
    liveVars,
    isRunning,
    isPaused,
    isWaitingAdmin,
    isActive,
    connect,
    start,
    confirmWarnings,
    dismissWarnings,
    setRunnerMode,
    pause,
    resume,
    stop,
    applyRuntime,
    varEntries,
  }
})
