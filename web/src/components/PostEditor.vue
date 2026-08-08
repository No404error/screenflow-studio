<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from '@/i18n'
import { useProjectStore } from '@/stores/project'
import type { PostListen } from '@/types/project'

const props = defineProps<{
  modelValue: PostListen | null | undefined
}>()
const emit = defineEmits<{ 'update:modelValue': [PostListen | null] }>()

const { t } = useI18n()
const project = useProjectStore()

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
</script>

<template>
  <details class="post" :open="!!modelValue">
    <summary>
      {{ t('post') }}
      <label class="tog" @click.stop>
        <input v-model="enabled" type="checkbox" />
      </label>
    </summary>
    <div v-if="modelValue" class="body">
      <label class="sf-field">
        <span class="sf-label">mode</span>
        <select
          class="sf-select"
          :value="modelValue.mode"
          @change="patch({ mode: ($event.target as HTMLSelectElement).value })"
        >
          <option value="once">once</option>
          <option value="until_page">until_page</option>
          <option value="until_case">until_case</option>
          <option value="frames">frames</option>
        </select>
      </label>
      <label v-if="modelValue.mode === 'frames'" class="sf-field">
        <span class="sf-label">frames</span>
        <input
          class="sf-input"
          type="number"
          :value="modelValue.frames ?? 1"
          @input="patch({ frames: Number(($event.target as HTMLInputElement).value) })"
        />
      </label>
      <label class="sf-field">
        <span class="sf-label">settle (s)</span>
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
        end on unknown
      </label>
    </div>
  </details>
</template>

<style scoped>
.post {
  border: 1px solid var(--sf-line);
  border-radius: var(--sf-radius);
  padding: var(--sf-space-3);
  margin-top: var(--sf-space-4);
}
summary {
  cursor: pointer;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.body {
  margin-top: var(--sf-space-3);
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: var(--sf-space-3);
}
.check {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-top: 1.2rem;
}
</style>
