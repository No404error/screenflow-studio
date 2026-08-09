<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api/client'
import { useI18n } from '@/i18n'
import { useQuitApp } from '@/composables/useQuitApp'
import { useUiStore } from '@/stores/ui'
import { useProjectStore } from '@/stores/project'

const { t } = useI18n()
const ui = useUiStore()
const project = useProjectStore()
const router = useRouter()
const { quitApp } = useQuitApp()
const error = ref('')
const busy = ref(false)

async function openPath() {
  busy.value = true
  error.value = ''
  try {
    const { path } = await api.pickFolder(undefined, t('open'))
    if (!path) return
    await project.open(path)
    await router.push('/studio')
  } catch (e) {
    error.value = String(e)
  } finally {
    busy.value = false
  }
}

async function newProject() {
  busy.value = true
  error.value = ''
  try {
    const { path: parent } = await api.pickFolder(undefined, t('parent_prompt'))
    if (!parent) return
    const name = await ui.askPrompt({
      title: t('project_name'),
      initial: t('untitled_project'),
    })
    if (!name) return
    await project.create(parent, name.trim())
    await router.push('/studio')
  } catch (e) {
    error.value = String(e)
  } finally {
    busy.value = false
  }
}

async function openRecent(path: string) {
  busy.value = true
  error.value = ''
  try {
    await project.open(path)
    await router.push('/studio')
  } catch (e) {
    error.value = String(e)
  } finally {
    busy.value = false
  }
}

async function onClearRecent() {
  await ui.clearRecent()
}

async function onRemoveRecent(path: string, ev: Event) {
  ev.stopPropagation()
  ev.preventDefault()
  try {
    await ui.removeRecent(path)
  } catch (e) {
    error.value = String(e)
  }
}

async function onReopenToggle(ev: Event) {
  const on = (ev.target as HTMLInputElement).checked
  ui.reopenLast = on
  await api.patchSettings({ reopen_last_project: on })
}
</script>

<template>
  <div class="welcome">
    <div class="hero">
      <p class="brand"><I18nText k="app_name" /></p>
      <h1><I18nText k="tagline" /></h1>
      <p class="sub"><I18nText k="welcome_sub" /></p>
      <div class="sf-btn-cluster actions">
        <button class="sf-btn sf-btn-primary" :disabled="busy" @click="openPath"><I18nText k="open" /></button>
        <button class="sf-btn" :disabled="busy" @click="newProject"><I18nText k="new_project" /></button>
      </div>
      <p v-if="error" class="err">{{ error }}</p>
    </div>
    <aside class="recent">
      <div class="recent-head">
        <h2><I18nText k="recent" /></h2>
        <button v-if="ui.recent.length" class="sf-btn sf-btn-ghost" type="button" @click="onClearRecent">
          <I18nText k="clear_recent" />
        </button>
      </div>
      <ul v-if="ui.recent.length">
        <li v-for="r in ui.recent" :key="r.path" class="recent-row">
          <button type="button" class="recent-item" :disabled="busy" @click="openRecent(r.path)">
            <span class="name">{{ r.name }}</span>
            <span class="path sf-mono">{{ r.path }}</span>
          </button>
          <button
            type="button"
            class="sf-btn sf-btn-ghost recent-remove"
            :disabled="busy"
            :title="t('remove_recent_a11y')"
            :aria-label="t('remove_recent_a11y')"
            @click="onRemoveRecent(r.path, $event)"
          >
            ×
          </button>
        </li>
      </ul>
      <p v-else class="empty"><I18nText k="empty_project" /></p>
      <label class="reopen">
        <input type="checkbox" :checked="ui.reopenLast" @change="onReopenToggle" />
        <I18nText k="reopen_last" />
      </label>
      <div class="lang">
        <label class="sf-label"><I18nText k="lang" /></label>
        <select class="sf-select" :value="ui.lang" @change="ui.setLang(($event.target as HTMLSelectElement).value)">
          <option value="en">English</option>
          <option value="zh">中文</option>
        </select>
      </div>
      <button type="button" class="sf-btn sf-btn-ghost quit" :disabled="busy" @click="quitApp">
        <I18nText k="quit" />
      </button>
    </aside>
  </div>
</template>

<style scoped>
.welcome {
  min-height: 100%;
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  gap: clamp(2rem, 5vw, 4rem);
  padding: clamp(2.5rem, 7vw, 5rem);
  background:
    radial-gradient(1000px 520px at 8% -8%, #cfe8e6 0%, transparent 55%),
    linear-gradient(165deg, #f7faf8 0%, var(--sf-paper) 50%, #e8efec 100%);
}
.hero {
  display: flex;
  flex-direction: column;
  justify-content: center;
  max-width: 34rem;
}
.brand {
  font-size: var(--sf-fs-hero);
  font-weight: 700;
  letter-spacing: -0.04em;
  margin: 0 0 var(--sf-space-2);
  color: var(--sf-ink);
}
h1 {
  font-size: var(--sf-fs-xl);
  margin: 0 0 var(--sf-space-3);
  font-weight: 600;
}
.sub {
  color: var(--sf-ink-muted);
  margin: 0 0 var(--sf-space-5);
  line-height: 1.5;
}
.actions {
  gap: 0.75rem;
}
.err {
  color: var(--sf-danger);
  margin-top: var(--sf-space-3);
}
.recent {
  align-self: center;
  background: var(--sf-surface);
  border: 1px solid var(--sf-line);
  border-radius: calc(var(--sf-radius) + 4px);
  padding: var(--sf-space-4);
}
.quit {
  margin-top: var(--sf-space-4);
  width: 100%;
}
.recent-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: var(--sf-space-3);
}
.recent h2 {
  margin: 0;
  font-size: var(--sf-fs-md);
}
.recent ul {
  list-style: none;
  margin: 0;
  padding: 0;
}
.recent-row {
  display: flex;
  align-items: stretch;
  gap: 0.15rem;
  border-radius: var(--sf-radius);
}
.recent-row:hover {
  background: var(--sf-accent-soft);
}
.recent-item {
  flex: 1;
  min-width: 0;
  text-align: left;
  border: none;
  background: transparent;
  padding: 0.55rem 0.35rem;
  border-radius: var(--sf-radius);
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  cursor: pointer;
}
.recent-remove {
  flex-shrink: 0;
  align-self: center;
  min-width: 2rem;
  opacity: 0.55;
}
.recent-row:hover .recent-remove,
.recent-remove:focus-visible {
  opacity: 1;
}
.name {
  font-weight: 600;
}
.path {
  font-size: var(--sf-fs-xs);
  color: var(--sf-ink-faint);
  word-break: break-all;
}
.empty {
  color: var(--sf-ink-muted);
}
.reopen {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  margin: var(--sf-space-3) 0;
  font-size: var(--sf-fs-sm);
  color: var(--sf-ink-muted);
}
.lang {
  margin-top: var(--sf-space-2);
}
@media (max-width: 800px) {
  .welcome {
    grid-template-columns: 1fr;
  }
}
</style>
