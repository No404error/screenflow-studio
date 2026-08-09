import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

const STORAGE_KEY = 'screenflow.studio.prefs'

export type DrawerTab = 'controls' | 'vars' | 'logs'

type PrefsSnapshot = {
  showFeatureIds?: boolean
  navCollapsed?: boolean
  drawerOpen?: boolean
  drawerTab?: DrawerTab
}

function readStored(): PrefsSnapshot {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return {}
    const data = JSON.parse(raw) as PrefsSnapshot
    return data && typeof data === 'object' ? data : {}
  } catch {
    return {}
  }
}

function writeStored(data: PrefsSnapshot) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
  } catch {
    /* quota / private mode */
  }
}

/**
 * Browser-local Studio preferences (not project data, not ~/.screenflow/ui.json).
 * Persists across reloads via localStorage.
 */
export const usePrefsStore = defineStore('prefs', () => {
  const stored = readStored()

  const showFeatureIds = ref(!!stored.showFeatureIds)
  const navCollapsed = ref(!!stored.navCollapsed)
  const drawerOpen = ref(!!stored.drawerOpen)
  const drawerTab = ref<DrawerTab>(
    stored.drawerTab === 'vars' || stored.drawerTab === 'logs' || stored.drawerTab === 'controls'
      ? stored.drawerTab
      : 'controls',
  )

  function persist() {
    writeStored({
      showFeatureIds: showFeatureIds.value,
      navCollapsed: navCollapsed.value,
      drawerOpen: drawerOpen.value,
      drawerTab: drawerTab.value,
    })
  }

  watch([showFeatureIds, navCollapsed, drawerOpen, drawerTab], persist)

  function toggleNav() {
    navCollapsed.value = !navCollapsed.value
  }

  function toggleDrawer() {
    drawerOpen.value = !drawerOpen.value
  }

  return {
    showFeatureIds,
    navCollapsed,
    drawerOpen,
    drawerTab,
    toggleNav,
    toggleDrawer,
  }
})
