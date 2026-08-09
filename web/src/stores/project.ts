import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '@/api/client'
import { t } from '@/i18n'
import type { Issue, ProjectDTO, StateNode } from '@/types/project'
import { mergeDirtyPageDocs } from '@/utils/mergeProject'
import { collectVarRefs, undeclaredRefs } from '@/utils/vars'
import { useUiStore } from './ui'
import { useRunStore } from './run'

function emptyRuntime(): ProjectDTO['runtime'] {
  return {
    match_threshold: 0.72,
    poll_interval: 0.5,
    action_delay: 0.45,
    action_cooldown: 0.35,
    state_conf_margin: 0.03,
    state_near: 0.03,
    page_pair_margin: 0.03,
    page_detect_near: 0.35,
    ref_width: 1920,
    ref_height: 1080,
    verbose_log: false,
    allow_redecide_during_action: false,
    log_language: 'en',
    hotkeys: { start: 'f9', pause: 'f10', stop: 'f11' },
  }
}

export const useProjectStore = defineStore('project', () => {
  const project = ref<ProjectDTO | null>(null)
  const dirty = ref(false)
  const issues = ref<Issue[]>([])
  const saving = ref(false)

  const hasProject = computed(() => !!project.value)
  const varRefs = computed(() => (project.value ? collectVarRefs(project.value) : []))
  const undeclared = computed(() => (project.value ? undeclaredRefs(project.value) : []))

  function markDirty() {
    dirty.value = true
  }

  function setProject(p: ProjectDTO) {
    if (!p.page_docs) p.page_docs = {}
    if (!p.vars) p.vars = {}
    if (!p.var_schema) p.var_schema = {}
    if (!p.macros) p.macros = []
    if (!p.page_pairs) p.page_pairs = []
    if (!p.runtime) p.runtime = emptyRuntime()
    project.value = p
    dirty.value = false
  }

  async function open(path: string) {
    const p = await api.openProject(path)
    setProject(p)
    const ui = useUiStore()
    await ui.loadSettings()
    ui.select({ kind: 'variables' })
  }

  async function create(parent: string, name: string) {
    const p = await api.newProject(parent, name)
    setProject(p)
    const ui = useUiStore()
    await ui.loadSettings()
    ui.select({ kind: 'variables' })
  }

  async function save() {
    if (!project.value) return
    saving.value = true
    try {
      // Sync pages id list from page_docs
      project.value.pages = Object.keys(project.value.page_docs)
      const pairs: string[][] = []
      const seen = new Set<string>()
      for (const page of Object.values(project.value.page_docs)) {
        if (!page.pair_with) continue
        const key = [page.id, page.pair_with].sort().join('|')
        if (seen.has(key)) continue
        seen.add(key)
        pairs.push([page.id, page.pair_with])
      }
      project.value.page_pairs = pairs
      const saved = await api.saveProject(project.value)
      setProject(saved)
      const ui = useUiStore()
      ui.showToast(useRunStore().isActive ? t('save_reload_hint') : t('saved'))
    } finally {
      saving.value = false
    }
  }

  async function close() {
    await api.closeProject()
    project.value = null
    dirty.value = false
    issues.value = []
    useUiStore().select({ kind: 'welcome' })
  }

  async function confirmLeaveIfDirty(): Promise<boolean> {
    if (!dirty.value) return true
    const ui = useUiStore()
    const choice = await ui.askUnsaved()
    if (choice === 'cancel') return false
    if (choice === 'save') await save()
    return true
  }

  async function addPage(name: string) {
    await saveIfDirty()
    const p = await api.addPage(name)
    setProject(p)
    useUiStore().select({ kind: 'page', pageId: Object.keys(p.page_docs).at(-1) })
  }

  async function removePage(pageId: string) {
    const p = await api.deletePage(pageId)
    setProject(p)
    useUiStore().select({ kind: 'pages' })
  }

  async function addMacro(name: string) {
    await saveIfDirty()
    const p = await api.addMacro(name)
    setProject(p)
  }

  async function removeMacro(macroId: string) {
    const p = await api.deleteMacro(macroId)
    setProject(p)
    useUiStore().select({ kind: 'macros' })
  }

  async function saveIfDirty() {
    if (dirty.value) await save()
  }

  /**
   * Apply a server project DTO. If local edits are dirty, keep unsaved page/editor
   * fields and leave dirty=true.
   */
  function applyServerSnapshot(p: ProjectDTO) {
    if (!p.page_docs) p.page_docs = {}
    if (!p.vars) p.vars = {}
    if (!p.var_schema) p.var_schema = {}
    if (!p.macros) p.macros = []
    if (!p.page_pairs) p.page_pairs = []
    if (!p.runtime) p.runtime = emptyRuntime()
    if (dirty.value && project.value) {
      project.value = mergeDirtyPageDocs(project.value, p)
      dirty.value = true
      return
    }
    project.value = p
    dirty.value = false
  }

  async function refreshFromServer() {
    const p = await api.getProject()
    applyServerSnapshot(p)
  }

  async function validate() {
    if (dirty.value) await save()
    const r = await api.validate()
    issues.value = r.issues
    return r
  }

  function ensureNodeIds(nodes: StateNode[], prefix: string) {
    nodes.forEach((n, i) => {
      if (!n.id) n.id = `${prefix}_${i}`
      if (n.children) ensureNodeIds(n.children, n.id)
      if (n.post?.tree) ensureNodeIds(n.post.tree, `${n.id}_post`)
    })
  }

  return {
    project,
    dirty,
    issues,
    saving,
    hasProject,
    varRefs,
    undeclared,
    markDirty,
    setProject,
    applyServerSnapshot,
    open,
    create,
    save,
    close,
    confirmLeaveIfDirty,
    addPage,
    removePage,
    addMacro,
    removeMacro,
    refreshFromServer,
    validate,
    ensureNodeIds,
  }
})
