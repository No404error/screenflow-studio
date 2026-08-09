import { onMounted, onUnmounted } from 'vue'

/**
 * LIFO Escape handlers. Each handler should return true if it handled the key
 * (so lower handlers are not called).
 */
const stack: Array<() => boolean> = []

function onKey(e: KeyboardEvent) {
  if (e.key !== 'Escape') return
  for (let i = stack.length - 1; i >= 0; i--) {
    if (stack[i]?.()) {
      e.preventDefault()
      e.stopPropagation()
      return
    }
  }
}

let listening = false

function ensureListen() {
  if (listening) return
  window.addEventListener('keydown', onKey, true)
  listening = true
}

function maybeUnlisten() {
  if (stack.length || !listening) return
  window.removeEventListener('keydown', onKey, true)
  listening = false
}

/** Register an Escape handler for the lifetime of the calling component. */
export function useEscapeKey(handler: () => boolean) {
  onMounted(() => {
    stack.push(handler)
    ensureListen()
  })
  onUnmounted(() => {
    const i = stack.lastIndexOf(handler)
    if (i >= 0) stack.splice(i, 1)
    maybeUnlisten()
  })
}
