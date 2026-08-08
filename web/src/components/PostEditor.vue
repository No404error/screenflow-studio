<script setup lang="ts">
import { computed, defineAsyncComponent, ref } from 'vue'
import { useI18n } from '@/i18n'
import { useProjectStore } from '@/stores/project'
import SectionHelp from '@/components/SectionHelp.vue'
import type { PostListen, StateNode } from '@/types/project'

const PostTreeModal = defineAsyncComponent(() => import('@/components/PostTreeModal.vue'))

const props = withDefaults(
  defineProps<{
    modelValue: PostListen | null | undefined
    featureKeys?: string[]
    macroIds?: string[]
    pageId?: string | null
    titleKey?: string
    helpKey?: string
  }>(),
  {
    titleKey: 'sec_case_post',
    helpKey: 'help_case_post',
  },
)
const emit = defineEmits<{ 'update:modelValue': [PostListen | null] }>()

const { t } = useI18n()
const project = useProjectStore()
const treeOpen = ref(false)

const enabled = computed({
  get: () => !!props.modelValue,
  set: (on: boolean) => {
    if (on) {
      emit('update:modelValue', {
        mode: 'until_page',
        settle: 0,
        end_on_unknown: false,
        tree: [],
      })
    } else {
      emit('update:modelValue', null)
    }
    project.markDirty()
  },
})

function patch(p: Partial<PostListen>) {
  if (!props.modelValue) return
  emit('update:modelValue', { ...props.modelValue, ...p })
  project.markDirty()
}

function onTree(tree: StateNode[]) {
  patch({ tree })
}

const caseCount = computed(() => props.modelValue?.tree?.length ?? 0)
</script>

<template>
  <details class="post" :open="!!modelValue">
    <summary>
      <span class="sum-left">
        {{ t(titleKey) }}
        <SectionHelp :help-key="helpKey" />
      </span>
      <label class="tog" @click.stop>
        <input v-model="enabled" type="checkbox" />
      </label>
    </summary>
    <div v-if="modelValue" class="body sf-grid-fields">
      <label class="sf-field sf-field-select">
        <span class="sf-label"><I18nText k="post_mode" /></span>
        <select
          class="sf-select"
          :value="modelValue.mode"
          @change="patch({ mode: ($event.target as HTMLSelectElement).value })"
        >
          <option value="once">{{ t('post_mode_once') }}</option>
          <option value="until_page">{{ t('post_mode_until_page') }}</option>
          <option value="until_case">{{ t('post_mode_until_case') }}</option>
          <option value="frames">{{ t('post_mode_frames') }}</option>
        </select>
      </label>
      <label v-if="modelValue.mode === 'frames'" class="sf-field">
        <span class="sf-label"><I18nText k="post_frames" /></span>
        <input
          class="sf-input"
          type="number"
          :value="modelValue.frames ?? 1"
          @input="patch({ frames: Number(($event.target as HTMLInputElement).value) })"
        />
      </label>
      <label class="sf-field">
        <span class="sf-label"><I18nText k="post_settle" /></span>
        <input
          class="sf-input"
          type="number"
          step="0.05"
          :value="modelValue.settle ?? 0"
          @input="patch({ settle: Number(($event.target as HTMLInputElement).value) })"
        />
      </label>
      <label class="sf-field check">
        <input
          type="checkbox"
          :checked="!!modelValue.end_on_unknown"
          @change="patch({ end_on_unknown: ($event.target as HTMLInputElement).checked })"
        />
        <I18nText k="post_end_unknown" />
      </label>
      <div class="tree-row">
        <button type="button" class="sf-btn sf-btn-primary" @click="treeOpen = true">
          <I18nText k="edit_post_tree" />
          <span class="count">{{ caseCount }}</span>
        </button>
      </div>
    </div>
  </details>

  <PostTreeModal
    v-if="treeOpen && modelValue"
    :model-value="modelValue.tree || []"
    :feature-keys="featureKeys || []"
    :macro-ids="macroIds || []"
    :page-id="pageId"
    @update:model-value="onTree"
    @close="treeOpen = false"
  />
</template>

<style scoped>
.post {
  border: 1px solid var(--sf-line);
  border-radius: var(--sf-radius);
  padding: var(--sf-space-3);
  margin: 0;
}
summary {
  cursor: pointer;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.sum-left {
  display: inline-flex;
  align-items: center;
}
.body {
  margin-top: var(--sf-space-3);
}
.check {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  grid-column: 1 / -1;
}
.tree-row {
  grid-column: 1 / -1;
}
.count {
  margin-left: 0.35rem;
  opacity: 0.75;
  font-variant-numeric: tabular-nums;
}
</style>
