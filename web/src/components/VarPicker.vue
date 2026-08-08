<script setup lang="ts">
import { computed } from 'vue'
import { useProjectStore } from '@/stores/project'

const props = defineProps<{
  modelValue: string
  allowEmpty?: boolean
}>()
const emit = defineEmits<{ 'update:modelValue': [string] }>()

const project = useProjectStore()
const names = computed(() => Object.keys(project.project?.vars || {}).sort())
const undeclared = computed(() => !props.modelValue || names.value.includes(props.modelValue))
</script>

<template>
  <select
    class="sf-select"
    :class="{ warn: modelValue && !undeclared }"
    :value="modelValue"
    @change="emit('update:modelValue', ($event.target as HTMLSelectElement).value)"
  >
    <option v-if="allowEmpty" value="">—</option>
    <option v-for="n in names" :key="n" :value="n">{{ n }}</option>
    <option v-if="modelValue && !names.includes(modelValue)" :value="modelValue">
      {{ modelValue }} (undeclared)
    </option>
  </select>
</template>

<style scoped>
.warn {
  border-color: var(--sf-warn);
  background: var(--sf-warn-soft);
}
</style>
