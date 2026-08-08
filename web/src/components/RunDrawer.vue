<script setup lang="ts">
import { useI18n } from '@/i18n'
import { useRunStore } from '@/stores/run'
import { useUiStore } from '@/stores/ui'
import { useProjectStore } from '@/stores/project'

const { t } = useI18n()
const run = useRunStore()
const ui = useUiStore()
const project = useProjectStore()

function mark() {
  project.markDirty()
}
</script>

<template>
  <div v-if="ui.drawerOpen" class="drawer">
    <div class="tabs">
      <button :class="{ active: ui.drawerTab === 'controls' }" @click="ui.drawerTab = 'controls'">
        {{ t('controls') }}
      </button>
      <button :class="{ active: ui.drawerTab === 'vars' }" @click="ui.drawerTab = 'vars'">
        {{ t('live_vars') }}
      </button>
      <button :class="{ active: ui.drawerTab === 'logs' }" @click="ui.drawerTab = 'logs'">
        {{ t('logs') }}
      </button>
    </div>

    <div v-if="ui.drawerTab === 'controls' && project.project" class="pane">
      <div class="grid">
        <label class="sf-field">
          <span class="sf-label">{{ t('match_threshold') }}</span>
          <input
            v-model.number="project.project.runtime.match_threshold"
            class="sf-input"
            type="number"
            step="0.01"
            min="0"
            max="1"
            @change="mark(); run.applyRuntime()"
          />
        </label>
        <label class="sf-field">
          <span class="sf-label">{{ t('poll_interval') }}</span>
          <input
            v-model.number="project.project.runtime.poll_interval"
            class="sf-input"
            type="number"
            step="0.05"
            min="0.05"
            @change="mark(); run.applyRuntime()"
          />
        </label>
        <label class="sf-field">
          <span class="sf-label">{{ t('ref_size') }}</span>
          <div class="row">
            <input
              v-model.number="project.project.runtime.ref_width"
              class="sf-input"
              type="number"
              @change="mark()"
            />
            <span>×</span>
            <input
              v-model.number="project.project.runtime.ref_height"
              class="sf-input"
              type="number"
              @change="mark()"
            />
          </div>
          <small class="hint">{{ t('ref_hint') }}</small>
        </label>
        <label class="sf-field check">
          <input v-model="project.project.runtime.verbose_log" type="checkbox" @change="mark(); run.applyRuntime()" />
          Verbose log
        </label>
      </div>
      <div v-if="project.issues.length" class="issues">
        <h3 class="sf-section-title">{{ t('issues') }}</h3>
        <ul>
          <li v-for="(iss, i) in project.issues" :key="i" :class="iss.level">{{ iss.text }}</li>
        </ul>
      </div>
      <button class="sf-btn" @click="project.validate()">{{ t('validate') }}</button>
    </div>

    <div v-else-if="ui.drawerTab === 'vars'" class="pane">
      <table v-if="Object.keys(run.liveVars).length" class="vars">
        <tbody>
          <tr v-for="[k, v] in Object.entries(run.liveVars)" :key="k">
            <td class="sf-mono">{{ k }}</td>
            <td class="sf-mono">{{ JSON.stringify(v) }}</td>
          </tr>
        </tbody>
      </table>
      <p v-else class="sf-empty">—</p>
    </div>

    <div v-else class="pane logs sf-mono">
      <div v-for="(line, i) in run.logs" :key="i">{{ line }}</div>
    </div>
  </div>
</template>

<style scoped>
.drawer {
  height: var(--sf-drawer-h);
  background: var(--sf-surface);
  border-top: 1px solid var(--sf-line);
  display: flex;
  flex-direction: column;
  animation: rise 0.2s ease;
}
@keyframes rise {
  from {
    transform: translateY(8px);
    opacity: 0.6;
  }
  to {
    transform: none;
    opacity: 1;
  }
}
.tabs {
  display: flex;
  gap: 0.25rem;
  padding: var(--sf-space-2) var(--sf-space-3);
  border-bottom: 1px solid var(--sf-line);
}
.tabs button {
  border: none;
  background: transparent;
  padding: 0.35rem 0.75rem;
  border-radius: var(--sf-radius);
  color: var(--sf-ink-muted);
}
.tabs button.active {
  background: var(--sf-accent-soft);
  color: var(--sf-accent);
  font-weight: 600;
}
.pane {
  flex: 1;
  overflow: auto;
  padding: var(--sf-space-3) var(--sf-space-4);
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: var(--sf-space-3);
}
.row {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}
.hint {
  color: var(--sf-ink-faint);
  font-size: var(--sf-fs-xs);
}
.check {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-top: 1.4rem;
}
.issues ul {
  margin: 0 0 var(--sf-space-3);
  padding-left: 1.1rem;
}
.issues .error {
  color: var(--sf-danger);
}
.issues .warning {
  color: var(--sf-warn);
}
.vars {
  width: 100%;
  border-collapse: collapse;
}
.vars td {
  padding: 0.3rem 0.5rem;
  border-bottom: 1px solid var(--sf-line);
}
.logs {
  font-size: var(--sf-fs-xs);
  white-space: pre-wrap;
}
</style>
