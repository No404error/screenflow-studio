<script setup lang="ts">
defineProps<{ text: string }>()
</script>

<template>
  <details class="help">
    <summary>?</summary>
    <p>{{ text }}</p>
  </details>
</template>

<style scoped>
.help {
  display: inline-block;
  margin-left: 0.35rem;
  vertical-align: middle;
}
summary {
  list-style: none;
  width: 1.1rem;
  height: 1.1rem;
  border-radius: 50%;
  border: 1px solid var(--sf-line-strong);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  color: var(--sf-ink-muted);
  cursor: pointer;
}
summary::-webkit-details-marker {
  display: none;
}
p {
  position: absolute;
  z-index: 20;
  max-width: 16rem;
  margin: 0.35rem 0 0;
  padding: 0.6rem 0.75rem;
  background: var(--sf-ink);
  color: #fff;
  border-radius: var(--sf-radius);
  font-size: var(--sf-fs-sm);
  font-weight: 400;
  text-transform: none;
  letter-spacing: 0;
}
</style>
