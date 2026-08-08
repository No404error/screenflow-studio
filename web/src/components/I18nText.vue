<script setup lang="ts">
import { computed } from 'vue'
import { useI18n, tLang } from '@/i18n'

const props = withDefaults(
  defineProps<{
    k: string
    vars?: Record<string, string | number>
    /** Center text within the reserved box (buttons). */
    center?: boolean
  }>(),
  { center: false },
)

const { t } = useI18n()
const current = computed(() => t(props.k, props.vars))
const en = computed(() => tLang('en', props.k, props.vars))
const zh = computed(() => tLang('zh', props.k, props.vars))
</script>

<template>
  <span class="sf-i18n" :class="{ 'sf-i18n-center': center }">
    <span class="sf-i18n-cur">{{ current }}</span>
    <span class="sf-i18n-ghost" aria-hidden="true">{{ en }}</span>
    <span class="sf-i18n-ghost" aria-hidden="true">{{ zh }}</span>
  </span>
</template>
