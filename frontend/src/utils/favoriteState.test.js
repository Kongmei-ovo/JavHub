import test from 'node:test'
import assert from 'node:assert/strict'

import api from '../api/index.js'
import { favoriteState, state } from './favoriteState.js'

test('favorite registry stores server-provided entity types without object property writes', async (t) => {
  const originalGetFavorites = api.getFavorites
  t.after(() => {
    api.getFavorites = originalGetFavorites
    state.registry = {}
    state.items = []
    state.initialized = false
    favoriteState.listener = null
  })

  api.getFavorites = async () => ({
    data: [
      { entity_type: '__proto__', entity_id: 'polluted', metadata: {}, created_at: '2026-01-01T00:00:00Z' },
      { entity_type: 'video', entity_id: 'abc123', metadata: {}, created_at: '2026-01-01T00:00:00Z' },
    ],
  })

  state.registry = {}
  state.items = []
  state.initialized = false

  await favoriteState.init()

  assert.equal(state.registry instanceof Map, true)
  assert.equal(favoriteState.isFavorited('__proto__', 'polluted'), true)
  assert.equal(favoriteState.isFavorited('video', 'abc123'), true)
  assert.equal(Object.prototype.polluted, undefined)
})
