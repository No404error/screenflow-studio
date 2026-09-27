import assert from 'node:assert/strict'
import { afterEach, test } from 'node:test'
import { api, ApiError } from '../src/api/client.ts'

const originalFetch = globalThis.fetch

afterEach(() => {
  globalThis.fetch = originalFetch
})

test('openProject preserves a plain-text API error', async () => {
  globalThis.fetch = async () => new Response('project.json not found', { status: 400 })

  await assert.rejects(api.openProject('missing'), (error) => {
    assert.ok(error instanceof ApiError)
    assert.equal(error.status, 400)
    assert.equal(error.message, 'project.json not found')
    return true
  })
})

test('openProject extracts the detail from a JSON API error', async () => {
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ detail: 'Invalid project' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    })

  await assert.rejects(api.openProject('invalid'), (error) => {
    assert.ok(error instanceof ApiError)
    assert.equal(error.status, 400)
    assert.equal(error.message, 'Invalid project')
    return true
  })
})
