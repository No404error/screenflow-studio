<script setup lang="ts">
import SectionHelp from '@/components/SectionHelp.vue'

defineProps<{
  titleKey: string
  helpKey: string
}>()
</script>

<template>
  <div class="row">
    <h3 class="title"><I18nText :k="titleKey" /></h3>
    <SectionHelp :help-key="helpKey" />
  </div>
</template>

<style scoped>
.row {
  display: flex;
  align-items: center;
  gap: 0.15rem;
  margin: 0 0 var(--sf-space-3);
}
.title {
  margin: 0;
  font-size: var(--sf-fs-sm);
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--sf-ink-muted);
}
.title :deep(.sf-i18n-cur),
.title :deep(.sf-i18n-ghost) {
  text-transform: uppercase;
}
</style>
