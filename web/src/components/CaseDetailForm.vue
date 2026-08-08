<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from '@/i18n'
import { useProjectStore } from '@/stores/project'
import BindingsStrip from '@/components/BindingsStrip.vue'
import StepsEditor from '@/components/StepsEditor.vue'
import VarPicker from '@/components/VarPicker.vue'
import PostEditor from '@/components/PostEditor.vue'
import FeatureSelect from '@/components/FeatureSelect.vue'
import SectionHelp from '@/components/SectionHelp.vue'
import SectionTitle from '@/components/SectionTitle.vue'
import { formatWhenVar, parseWhenVar } from '@/utils/vars'
import { isElse } from '@/utils/tree'
import type { StateNode } from '@/types/project'

const props = defineProps<{
  node: StateNode
  featureKeys: string[]
  macroIds: string[]
  pageId?: string | null
  /** Hide nested post editor (when editing a post tree itself) */
  allowPost?: boolean
}>()

const emit = defineEmits<{ change: [] }>()
const { t } = useI18n()
const project = useProjectStore()
const allowPost = computed(() => props.allowPost !== false)

const branch = computed(() => !!(props.node.children && props.node.children.length))

function mark() {
  project.markDirty()
  emit('change')
}

const whenName = computed({
  get: () => parseWhenVar(props.node.when_var)?.name || '',
  set: (name: string) => {
    const cur = parseWhenVar(props.node.when_var)
    props.node.when_var = formatWhenVar(name, cur?.value) || null
    mark()
  },
})

const whenValue = computed({
  get: () => parseWhenVar(props.node.when_var)?.value ?? '',
  set: (value: string) => {
    const cur = parseWhenVar(props.node.when_var)
    props.node.when_var = formatWhenVar(cur?.name || whenName.value, value) || null
    mark()
  },
})

function setScoreKind(kind: string) {
  if (!props.node.score) props.node.score = { kind: 'template' }
  props.node.score.kind = kind as 'template' | 'constant' | 'invert'
  mark()
}

function setElse(on: boolean) {
  props.node.else = on
  if (on) props.node.score = null
  mark()
}

const roiText = computed({
  get: () => (props.node.score?.roi ? props.node.score.roi.join(',') : ''),
  set: (raw: string) => {
    if (!props.node.score) props.node.score = { kind: 'template' }
    const parts = raw
      .split(/[\s,]+/)
      .map((x) => Number(x))
      .filter((n) => Number.isFinite(n))
    props.node.score.roi = parts.length === 4 ? parts : null
    mark()
  },
})
</script>

<template>
  <div class="detail">
    <BindingsStrip :node="node" />
    <SectionTitle title-key="sec_case_basic" help-key="help_case_basic" />

    <div class="sf-grid-fields">
      <label class="sf-field">
        <span class="sf-label"><I18nText k="name" /></span>
        <input v-model="node.name" class="sf-input" @input="mark" />
      </label>
      <label class="sf-field">
        <span class="sf-label"><I18nText k="priority" /></span>
        <input v-model.number="node.priority" class="sf-input" type="number" @input="mark" />
      </label>
      <label class="sf-field check">
        <input type="checkbox" :checked="isElse(node)" @change="setElse(($event.target as HTMLInputElement).checked)" />
        <I18nText k="else" />
      </label>
    </div>

    <div v-if="!isElse(node)" class="block">
      <h3 class="sf-section-title"><I18nText k="score" /></h3>
      <div class="sf-grid-fields">
        <select
          class="sf-select sf-field-select"
          :value="node.score?.kind || 'template'"
          @change="setScoreKind(($event.target as HTMLSelectElement).value)"
        >
          <option value="template">{{ t('score_template') }}</option>
          <option value="invert">{{ t('score_invert') }}</option>
          <option value="constant">{{ t('score_constant') }}</option>
        </select>
        <FeatureSelect
          v-if="(node.score?.kind || 'template') !== 'constant'"
          :model-value="node.score?.key || ''"
          :keys="featureKeys"
          :page-id="pageId"
          @update:model-value="
            if (!node.score) node.score = { kind: 'template' };
            node.score.key = $event;
            mark()
          "
        />
        <input
          v-else
          class="sf-input"
          type="number"
          step="0.01"
          :value="node.score?.constant ?? 0"
          @input="
            if (!node.score) node.score = { kind: 'constant' };
            node.score.constant = Number(($event.target as HTMLInputElement).value);
            mark()
          "
        />
      </div>
      <label v-if="(node.score?.kind || 'template') !== 'constant'" class="sf-field" style="margin-top: 0.75rem">
        <span class="sf-label"><I18nText k="score_roi" /></span>
        <input v-model="roiText" class="sf-input sf-mono" :placeholder="t('score_roi_ph')" />
      </label>
    </div>

    <div class="block">
      <h3 class="sf-section-title when-title">
        <span><I18nText k="when" /></span>
        <SectionHelp help-key="help_case_when" />
      </h3>
      <div class="sf-grid-fields">
        <VarPicker v-model="whenName" allow-empty />
        <input v-model="whenValue" class="sf-input" :placeholder="t('value_placeholder')" />
      </div>
    </div>

    <details class="adv">
      <summary>
        <I18nText k="sec_case_advanced" /> — <I18nText k="layer_params_title" />
        <SectionHelp help-key="help_case_layer" />
      </summary>
      <p class="intro"><I18nText k="layer_params_intro" /></p>
      <div class="sf-grid-fields">
        <label class="sf-field">
          <span class="sf-label"><I18nText k="internal_id" /></span>
          <input v-model="node.id" class="sf-input sf-mono" @change="mark" />
        </label>
        <label class="sf-field">
          <span class="sf-label"><I18nText k="match_threshold" /></span>
          <input
            class="sf-input"
            type="number"
            step="0.01"
            :value="node.layer_params?.threshold ?? ''"
            :placeholder="t('inherit')"
            @change="
              node.layer_params = node.layer_params || {};
              const v = ($event.target as HTMLInputElement).value;
              node.layer_params.threshold = v === '' ? null : Number(v);
              mark()
            "
          />
          <small class="sf-hint"><I18nText k="layer_threshold_hint" /></small>
        </label>
        <label class="sf-field">
          <span class="sf-label"><I18nText k="param_state_near" /></span>
          <input
            class="sf-input"
            type="number"
            step="0.01"
            :value="node.layer_params?.near ?? ''"
            :placeholder="t('inherit')"
            @change="
              node.layer_params = node.layer_params || {};
              const v = ($event.target as HTMLInputElement).value;
              node.layer_params.near = v === '' ? null : Number(v);
              mark()
            "
          />
          <small class="sf-hint"><I18nText k="layer_near_hint" /></small>
        </label>
        <label class="sf-field">
          <span class="sf-label"><I18nText k="param_state_margin" /></span>
          <input
            class="sf-input"
            type="number"
            step="0.01"
            :value="node.layer_params?.margin ?? ''"
            :placeholder="t('inherit')"
            @change="
              node.layer_params = node.layer_params || {};
              const v = ($event.target as HTMLInputElement).value;
              node.layer_params.margin = v === '' ? null : Number(v);
              mark()
            "
          />
          <small class="sf-hint"><I18nText k="layer_margin_hint" /></small>
        </label>
      </div>
    </details>

    <p v-if="branch" class="hint"><I18nText k="branch_no_actions" /></p>
    <template v-else>
      <StepsEditor
        :model-value="node.actions || []"
        :feature-keys="featureKeys"
        :macro-ids="macroIds"
        :page-id="pageId"
        @update:model-value="
          node.actions = $event;
          mark()
        "
      />
      <PostEditor
        v-if="allowPost"
        class="post-after-steps"
        v-model="node.post"
        :feature-keys="featureKeys"
        :macro-ids="macroIds"
        :page-id="pageId"
      />
    </template>
  </div>
</template>

<style scoped>
.post-after-steps {
  margin-top: var(--sf-space-4);
  display: block;
}
.block {
  margin: var(--sf-space-4) 0;
}
.when-title {
  display: inline-flex;
  align-items: center;
  text-transform: none;
  letter-spacing: 0;
}
.check {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  align-self: end;
  min-height: 2.15rem; /* ~ label + input so checkbox lines up with neighboring boxes */
}
.adv {
  border: 1px solid var(--sf-line);
  border-radius: var(--sf-radius);
  padding: var(--sf-space-3);
  margin: var(--sf-space-3) 0;
}
.adv summary {
  cursor: pointer;
  font-weight: 600;
  font-size: var(--sf-fs-sm);
  display: flex;
  align-items: center;
  gap: 0.25rem;
}
.hint {
  color: var(--sf-ink-muted);
  font-size: var(--sf-fs-sm);
}
.intro {
  margin: 0.35rem 0 var(--sf-space-4);
  color: var(--sf-ink-muted);
  font-size: var(--sf-fs-sm);
  line-height: 1.45;
}
.adv .sf-grid-fields {
  margin-bottom: 0;
}
</style>
