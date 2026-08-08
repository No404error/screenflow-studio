<script setup lang="ts">
import { onMounted } from 'vue'
import { useI18n } from '@/i18n'
import { useRunStore } from '@/stores/run'
import { usePrefsStore } from '@/stores/prefs'
import { useUiStore } from '@/stores/ui'
import { useProjectStore } from '@/stores/project'
import SectionHelp from '@/components/SectionHelp.vue'
import SectionTitle from '@/components/SectionTitle.vue'

const { t } = useI18n()
const run = useRunStore()
const prefs = usePrefsStore()
const ui = useUiStore()
const project = useProjectStore()

function mark() {
  project.markDirty()
}

async function onRunnerMode(ev: Event) {
  const v = (ev.target as HTMLSelectElement).value
  await run.setRunnerMode(v)
}

onMounted(async () => {
  const s = await ui.loadSettings()
  if (s?.runner_mode) run.runnerMode = s.runner_mode
})
</script>

<template>
  <div v-if="prefs.drawerOpen" class="drawer">
    <div class="tabs">
      <button
        :class="{ active: prefs.drawerTab === 'controls' }"
        @click="prefs.drawerTab = 'controls'"
      >
        <I18nText k="controls" />
      </button>
      <button :class="{ active: prefs.drawerTab === 'vars' }" @click="prefs.drawerTab = 'vars'">
        <I18nText k="live_vars" />
      </button>
      <button :class="{ active: prefs.drawerTab === 'logs' }" @click="prefs.drawerTab = 'logs'">
        <I18nText k="logs" />
      </button>
    </div>

    <div v-if="prefs.drawerTab === 'controls' && project.project" class="pane">
      <div v-if="run.pendingWarnings?.length" class="warn-box">
        <p><I18nText k="validate_warnings" /></p>
        <ul>
          <li v-for="(w, i) in run.pendingWarnings" :key="i">{{ w.text }}</li>
        </ul>
        <div class="warn-actions">
          <button class="sf-btn" type="button" @click="run.dismissWarnings()"><I18nText k="abort_run" /></button>
          <button class="sf-btn sf-btn-primary" type="button" @click="run.confirmWarnings()">
            <I18nText k="continue_run" />
          </button>
        </div>
      </div>

      <SectionTitle title-key="sec_runtime" help-key="help_runtime" />
      <div class="sf-grid-fields">
        <label class="sf-field sf-field-select">
          <span class="sf-label"><I18nText k="runner_mode" /></span>
          <select class="sf-select" :value="run.runnerMode" @change="onRunnerMode">
            <option value="elevate">{{ t('runner_elevate') }}</option>
            <option value="inline">{{ t('runner_inline') }}</option>
          </select>
        </label>
        <label class="sf-field">
          <span class="sf-label"><I18nText k="match_threshold" /></span>
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
          <span class="sf-label"><I18nText k="poll_interval" /></span>
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
          <span class="sf-label"><I18nText k="param_state_near" /></span>
          <input
            v-model.number="project.project.runtime.state_near"
            class="sf-input"
            type="number"
            step="0.01"
            min="0"
            max="1"
            @change="mark(); run.applyRuntime()"
          />
        </label>
        <label class="sf-field">
          <span class="sf-label"><I18nText k="param_state_margin" /></span>
          <input
            v-model.number="project.project.runtime.state_conf_margin"
            class="sf-input"
            type="number"
            step="0.01"
            min="0"
            max="1"
            @change="mark(); run.applyRuntime()"
          />
        </label>
      </div>
      <details class="adv">
        <summary>
          <span class="sum-left">
            <I18nText k="sec_runtime_advanced" />
            <SectionHelp help-key="help_runtime_advanced" />
          </span>
        </summary>
        <div class="sf-grid-fields">
          <label class="sf-field">
            <span class="sf-label"><I18nText k="ref_size" /></span>
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
            <small class="sf-hint"><I18nText k="ref_hint" /></small>
          </label>
          <label class="sf-field">
            <span class="sf-label"><I18nText k="action_delay" /></span>
            <input
              v-model.number="project.project.runtime.action_delay"
              class="sf-input"
              type="number"
              step="0.05"
              min="0"
              @change="mark(); run.applyRuntime()"
            />
          </label>
          <label class="sf-field">
            <span class="sf-label"><I18nText k="action_cooldown" /></span>
            <input
              v-model.number="project.project.runtime.action_cooldown"
              class="sf-input"
              type="number"
              step="0.05"
              min="0"
              @change="mark(); run.applyRuntime()"
            />
          </label>
          <label class="sf-field">
            <span class="sf-label"><I18nText k="page_pair_margin" /></span>
            <input
              v-model.number="project.project.runtime.page_pair_margin"
              class="sf-input"
              type="number"
              step="0.01"
              min="0"
              max="1"
              @change="mark(); run.applyRuntime()"
            />
          </label>
          <label class="sf-field">
            <span class="sf-label"><I18nText k="page_detect_near" /></span>
            <input
              v-model.number="project.project.runtime.page_detect_near"
              class="sf-input"
              type="number"
              step="0.01"
              min="0"
              max="1"
              @change="mark(); run.applyRuntime()"
            />
          </label>
          <label class="sf-field sf-field-select">
            <span class="sf-label"><I18nText k="log_language" /></span>
            <select
              class="sf-select"
              :value="project.project.runtime.log_language"
              @change="
                project.project!.runtime.log_language = ($event.target as HTMLSelectElement).value;
                mark();
                run.applyRuntime()
              "
            >
              <option value="en">English</option>
              <option value="zh">中文</option>
            </select>
            <small class="sf-hint"><I18nText k="log_language_hint" /></small>
          </label>
          <label class="sf-field check">
            <input
              v-model="project.project.runtime.verbose_log"
              type="checkbox"
              @change="mark(); run.applyRuntime()"
            />
            <I18nText k="verbose_log" />
          </label>
          <label class="sf-field check">
            <input
              v-model="project.project.runtime.allow_redecide_during_action"
              type="checkbox"
              @change="mark(); run.applyRuntime()"
            />
            <I18nText k="abort_on_page_change" />
          </label>
          <div class="sf-field hotkeys">
            <span class="sf-label"><I18nText k="hotkeys" /></span>
            <p class="hint">
              <I18nText k="hotkeys_line" :vars="{ start: project.project.runtime.hotkeys?.start || 'f9', pause: project.project.runtime.hotkeys?.pause || 'f10', stop: project.project.runtime.hotkeys?.stop || 'f11', }" />
            </p>
            <small class="hint"><I18nText k="hotkeys_web_hint" /></small>
          </div>
        </div>
      </details>
      <div v-if="project.issues.length" class="issues">
        <h3 class="sf-section-title"><I18nText k="issues" /></h3>
        <ul>
          <li v-for="(iss, i) in project.issues" :key="i" :class="iss.level">{{ iss.text }}</li>
        </ul>
      </div>
      <button class="sf-btn" @click="project.validate()"><I18nText k="validate" /></button>
    </div>

    <div v-else-if="prefs.drawerTab === 'vars'" class="pane">
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
.warn-box {
  background: #fff8e8;
  border: 1px solid #f0c36d;
  border-radius: var(--sf-radius);
  padding: var(--sf-space-3);
  margin-bottom: var(--sf-space-3);
}
.warn-box ul {
  margin: 0.5rem 0;
  padding-left: 1.1rem;
}
.warn-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
}
.adv {
  margin: var(--sf-space-3) 0;
  border: 1px solid var(--sf-line);
  border-radius: var(--sf-radius);
  padding: var(--sf-space-2) var(--sf-space-3);
}
.adv summary {
  cursor: pointer;
  font-weight: 600;
  font-size: var(--sf-fs-sm);
}
.sum-left {
  display: inline-flex;
  align-items: center;
}
.adv .sf-grid-fields {
  margin-top: var(--sf-space-3);
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
}
.hotkeys {
  grid-column: 1 / -1;
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
