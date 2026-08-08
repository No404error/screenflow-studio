<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from '@/i18n'
import { useUiStore } from '@/stores/ui'
import { useProjectStore } from '@/stores/project'

const { t } = useI18n()
const ui = useUiStore()
const project = useProjectStore()
const router = useRouter()
const error = ref('')
const busy = ref(false)

async function openPath() {
  const path = window.prompt(t('path_prompt'))
  if (!path) return
  busy.value = true
  error.value = ''
  try {
    await project.open(path.trim())
    await router.push('/studio')
  } catch (e) {
    error.value = String(e)
  } finally {
    busy.value = false
  }
}

async function newProject() {
  const parent = window.prompt(t('parent_prompt'))
  if (!parent) return
  const name = window.prompt(t('project_name'), 'Untitled Project')
  if (!name) return
  busy.value = true
  error.value = ''
  try {
    await project.create(parent.trim(), name.trim())
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
</script>

<template>
  <div class="welcome">
    <div class="hero">
      <p class="brand">{{ t('app_name') }}</p>
      <h1>{{ t('tagline') }}</h1>
      <p class="sub">Editor-first Web Studio · variables & bindings first-class</p>
      <div class="actions">
        <button class="sf-btn sf-btn-primary" :disabled="busy" @click="openPath">{{ t('open') }}</button>
        <button class="sf-btn" :disabled="busy" @click="newProject">{{ t('new_project') }}</button>
      </div>
      <p v-if="error" class="err">{{ error }}</p>
    </div>
    <aside class="recent sf-panel">
      <h2 class="sf-section-title">{{ t('recent') }}</h2>
      <ul v-if="ui.recent.length">
        <li v-for="r in ui.recent" :key="r.path">
          <button class="recent-item" @click="openRecent(r.path)">
            <span class="name">{{ r.name }}</span>
            <span class="path sf-mono">{{ r.path }}</span>
          </button>
        </li>
      </ul>
      <p v-else class="sf-empty">{{ t('empty_project') }}</p>
      <div class="lang">
        <label class="sf-label">{{ t('lang') }}</label>
        <select class="sf-select" :value="ui.lang" @change="ui.setLang(($event.target as HTMLSelectElement).value)">
          <option value="en">English</option>
          <option value="zh">中文</option>
        </select>
      </div>
    </aside>
  </div>
</template>

<style scoped>
.welcome {
  min-height: 100%;
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: var(--sf-space-6);
  padding: clamp(2rem, 6vw, 4rem);
  background:
    radial-gradient(1200px 600px at 10% -10%, #cfe8e6 0%, transparent 55%),
    linear-gradient(165deg, #f7faf8 0%, var(--sf-paper) 45%, #e8efec 100%);
}
.hero {
  display: flex;
  flex-direction: column;
  justify-content: center;
  max-width: 36rem;
}
.brand {
  font-size: var(--sf-fs-hero);
  font-weight: 700;
  letter-spacing: -0.03em;
  margin: 0 0 var(--sf-space-2);
  color: var(--sf-ink);
}
h1 {
  font-size: var(--sf-fs-xl);
  font-weight: 500;
  margin: 0 0 var(--sf-space-3);
  color: var(--sf-ink-muted);
}
.sub {
  color: var(--sf-ink-faint);
  margin: 0 0 var(--sf-space-5);
}
.actions {
  display: flex;
  gap: var(--sf-space-3);
}
.err {
  color: var(--sf-danger);
  margin-top: var(--sf-space-3);
}
.recent {
  align-self: center;
  padding: var(--sf-space-5);
}
.recent ul {
  list-style: none;
  margin: 0;
  padding: 0;
}
.recent-item {
  width: 100%;
  text-align: left;
  border: none;
  background: transparent;
  padding: var(--sf-space-3);
  border-radius: var(--sf-radius);
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.recent-item:hover {
  background: var(--sf-accent-soft);
}
.name {
  font-weight: 600;
}
.path {
  color: var(--sf-ink-faint);
  font-size: var(--sf-fs-xs);
  word-break: break-all;
}
.lang {
  margin-top: var(--sf-space-5);
}
@media (max-width: 800px) {
  .welcome {
    grid-template-columns: 1fr;
  }
}
</style>
