<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { api } from '@/api/client'
import { useProjectStore } from '@/stores/project'
import type { FeatureDef } from '@/types/project'

const props = defineProps<{
  modelValue: string
  keys: string[]
  pageId?: string | null
}>()
const emit = defineEmits<{ 'update:modelValue': [string] }>()

const project = useProjectStore()
const open = ref(false)
const hover = ref<{ url: string; x: number; y: number; name: string } | null>(null)
const root = ref<HTMLElement | null>(null)
let timer: ReturnType<typeof setTimeout> | null = null

function featureFor(key: string): FeatureDef | null {
  if (!key || !props.pageId || !project.project) return null
  return project.project.page_docs[props.pageId]?.features?.[key] || null
}

function relpathFor(key: string): string | null {
  return featureFor(key)?.link?.asset || null
}

function labelFor(key: string): string {
  const f = featureFor(key)
  return (f?.label || key).trim() || key
}

const display = computed(() => (props.modelValue ? labelFor(props.modelValue) : '—'))

function pick(key: string) {
  emit('update:modelValue', key)
  open.value = false
  hover.value = null
}

function onEnter(key: string, ev: MouseEvent) {
  const rel = relpathFor(key)
  if (!rel) return
  if (timer) clearTimeout(timer)
  const x = ev.clientX
  const y = ev.clientY
  timer = setTimeout(() => {
    hover.value = {
      url: api.fileUrl(rel),
      name: labelFor(key),
      x: Math.min(x + 16, window.innerWidth - 280),
      y: Math.min(y + 16, window.innerHeight - 200),
    }
  }, 160)
}

function onLeaveList() {
  if (timer) clearTimeout(timer)
  timer = null
  hover.value = null
}

function onDoc(ev: MouseEvent) {
  if (!root.value?.contains(ev.target as Node)) {
    open.value = false
    onLeaveList()
  }
}

onMounted(() => document.addEventListener('mousedown', onDoc))
onUnmounted(() => document.removeEventListener('mousedown', onDoc))
</script>

<template>
  <div ref="root" class="wrap">
    <button
      type="button"
      class="sf-select trigger"
      :title="modelValue || undefined"
      @click="open = !open"
    >
      <span class="val">{{ display }}</span>
      <span class="caret" aria-hidden="true">▾</span>
    </button>
    <ul v-if="open" class="menu" @mouseleave="onLeaveList">
      <li @click="pick('')">—</li>
      <li
        v-for="k in keys"
        :key="k"
        :class="{ on: k === modelValue, unbound: !relpathFor(k) }"
        @mouseenter="onEnter(k, $event)"
        @click="pick(k)"
      >
        {{ labelFor(k) }}
        <span v-if="!relpathFor(k)" class="mark">·</span>
      </li>
    </ul>
    <Teleport to="body">
      <div v-if="hover" class="float" :style="{ left: `${hover.x}px`, top: `${hover.y}px` }">
        <img :src="hover.url" :alt="hover.name" />
        <span>{{ hover.name }}</span>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.wrap {
  position: relative;
  flex: 1 1 var(--sf-col-select);
  min-width: min(100%, var(--sf-col-select));
}
.trigger {
  width: 100%;
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  text-align: left;
  cursor: pointer;
  padding-right: 0.55rem;
}
.val {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.caret {
  flex-shrink: 0;
  width: var(--sf-select-caret);
  text-align: center;
  color: var(--sf-ink-faint);
  font-size: 0.7rem;
  line-height: 1;
}
.menu {
  position: absolute;
  z-index: 25;
  left: 0;
  right: 0;
  top: calc(100% + 2px);
  margin: 0;
  padding: 0.25rem;
  list-style: none;
  background: var(--sf-surface);
  border: 1px solid var(--sf-line);
  border-radius: var(--sf-radius);
  max-height: 12rem;
  overflow: auto;
  box-shadow: 0 8px 24px rgb(0 0 0 / 12%);
}
.menu li {
  padding: 0.35rem 0.45rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: var(--sf-fs-sm);
  overflow-wrap: anywhere;
  word-break: break-word;
  white-space: normal;
}
.menu li.unbound {
  color: var(--sf-ink-faint);
}
.menu li .mark {
  margin-left: 0.25rem;
  opacity: 0.5;
}
.menu li:hover,
.menu li.on {
  background: var(--sf-accent-soft);
  color: var(--sf-accent);
}
.float {
  position: fixed;
  z-index: 60;
  width: 240px;
  padding: 0.4rem;
  background: var(--sf-surface);
  border: 1px solid var(--sf-line);
  border-radius: var(--sf-radius);
  box-shadow: 0 12px 32px rgb(0 0 0 / 18%);
  pointer-events: none;
}
.float img {
  width: 100%;
  max-height: 160px;
  object-fit: contain;
  background: #111;
  border-radius: 4px;
  display: block;
}
.float span {
  display: block;
  margin-top: 0.25rem;
  font-size: var(--sf-fs-xs);
}
</style>
