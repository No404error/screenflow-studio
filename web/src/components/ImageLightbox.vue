<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useI18n } from '@/i18n'

const props = defineProps<{
  src: string
  title?: string
  meta?: string
}>()
const emit = defineEmits<{ close: [] }>()

const { t } = useI18n()

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}

onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <Teleport to="body">
    <div class="mask" @click.self="emit('close')">
      <div class="box" role="dialog" :aria-label="title || t('detect')">
        <header>
          <div class="titles">
            <strong>{{ title || t('preview_image') }}</strong>
            <span v-if="meta" class="meta sf-mono">{{ meta }}</span>
          </div>
          <button type="button" class="sf-btn sf-btn-ghost" @click="emit('close')">×</button>
        </header>
        <div class="stage">
          <img :src="src" :alt="title || t('preview_image')" />
        </div>
        <footer>
          <a class="sf-btn" :href="src" target="_blank" rel="noopener">{{ t('open_full') }}</a>
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.mask {
  position: fixed;
  inset: 0;
  background: rgb(26 34 32 / 55%);
  display: grid;
  place-items: center;
  z-index: 70;
  padding: 1rem;
  animation: fade 0.15s ease;
}
@keyframes fade {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}
.box {
  width: min(920px, 96vw);
  max-height: min(88vh, 820px);
  background: var(--sf-surface);
  border: 1px solid var(--sf-line);
  border-radius: var(--sf-radius-lg);
  box-shadow: 0 12px 40px rgb(26 34 32 / 25%);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
header,
footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.65rem 0.9rem;
  border-bottom: 1px solid var(--sf-line);
  flex-shrink: 0;
}
footer {
  border-bottom: none;
  border-top: 1px solid var(--sf-line);
  justify-content: flex-start;
}
.titles {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 0;
}
.meta {
  font-size: var(--sf-fs-xs);
  color: var(--sf-ink-faint);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.stage {
  flex: 1;
  min-height: 240px;
  overflow: auto;
  display: grid;
  place-items: center;
  padding: 1rem;
  background:
    linear-gradient(45deg, #e8eeeb 25%, transparent 25%) 0 0 / 16px 16px,
    linear-gradient(-45deg, #e8eeeb 25%, transparent 25%) 0 0 / 16px 16px,
    #f3f6f4;
}
.stage img {
  max-width: 100%;
  max-height: min(64vh, 640px);
  object-fit: contain;
  image-rendering: auto;
  box-shadow: 0 2px 12px rgb(0 0 0 / 12%);
  background: #fff;
}
</style>
