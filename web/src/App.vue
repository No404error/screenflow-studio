<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useUiStore } from '@/stores/ui'
import { useRunStore } from '@/stores/run'

const ui = useUiStore()
const run = useRunStore()

function onKey(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'b') {
    e.preventDefault()
    ui.toggleNav()
  }
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
    e.preventDefault()
    void import('@/stores/project').then(({ useProjectStore }) => {
      const p = useProjectStore()
      if (p.hasProject) void p.save()
    })
  }
}

onMounted(async () => {
  await ui.loadSettings()
  run.connect()
  window.addEventListener('keydown', onKey)
})

onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <router-view />
  <div v-if="ui.toast" class="toast">{{ ui.toast }}</div>
</template>

<style scoped>
.toast {
  position: fixed;
  bottom: calc(var(--sf-runbar-h) + 16px);
  left: 50%;
  transform: translateX(-50%);
  background: var(--sf-ink);
  color: #fff;
  padding: 0.5rem 1rem;
  border-radius: var(--sf-radius);
  font-size: var(--sf-fs-sm);
  z-index: 50;
  animation: fade 0.2s ease;
}
@keyframes fade {
  from {
    opacity: 0;
    transform: translate(-50%, 6px);
  }
  to {
    opacity: 1;
    transform: translate(-50%, 0);
  }
}
</style>
