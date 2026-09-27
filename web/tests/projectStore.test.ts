import { afterEach, expect, test, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useProjectStore } from '../src/stores/project'
import type { ProjectDTO } from '../src/types/project'

const originalFetch = globalThis.fetch

afterEach(() => {
  globalThis.fetch = originalFetch
})

test('edits made during a save survive the older server response', async () => {
  setActivePinia(createPinia())
  const store = useProjectStore()
  store.setProject({
    name: 'original',
    revision: 'revision-1',
    pages: [],
    page_docs: {},
    macros: [],
    page_pairs: [],
  } as unknown as ProjectDTO)

  let reply!: (response: Response) => void
  let submitted!: ProjectDTO
  globalThis.fetch = vi.fn((_path, init) => {
    submitted = JSON.parse(String((init as RequestInit).body)).project as ProjectDTO
    return new Promise<Response>((resolve) => { reply = resolve })
  }) as typeof fetch

  store.project!.name = 'first edit'
  store.markDirty()
  const saving = store.save()
  store.project!.name = 'later edit'
  store.markDirty()
  reply(new Response(JSON.stringify({ ...submitted, revision: 'revision-2' })))
  await saving

  expect(store.project!.name).toBe('later edit')
  expect(store.project!.revision).toBe('revision-2')
  expect(store.dirty).toBe(true)
})

test('an input value changed before its change event is not overwritten by save', async () => {
  setActivePinia(createPinia())
  const store = useProjectStore()
  store.setProject({
    name: 'original',
    revision: 'revision-1',
    pages: [],
    page_docs: {},
    macros: [],
    page_pairs: [],
  } as unknown as ProjectDTO)

  let reply!: (response: Response) => void
  let submitted!: ProjectDTO
  globalThis.fetch = vi.fn((_path, init) => {
    submitted = JSON.parse(String((init as RequestInit).body)).project as ProjectDTO
    return new Promise<Response>((resolve) => { reply = resolve })
  }) as typeof fetch

  store.project!.name = 'first edit'
  store.markDirty()
  const saving = store.save()
  store.project!.name = 'still typing'
  reply(new Response(JSON.stringify({ ...submitted, revision: 'revision-2' })))
  await saving

  expect(store.project!.name).toBe('still typing')
  expect(store.dirty).toBe(true)
})
