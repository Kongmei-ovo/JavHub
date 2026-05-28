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
    favoriteState.listeners?.clear?.()
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

test('favorite state notifies listeners in order and can unsubscribe one listener', async (t) => {
  const originalToggleFavorite = api.toggleFavorite
  const events = []
  t.after(() => {
    api.toggleFavorite = originalToggleFavorite
    state.registry = new Map()
    state.items = []
    state.initialized = false
    favoriteState.listener = null
    favoriteState.listeners?.clear?.()
  })

  api.toggleFavorite = async () => ({ data: { is_favorited: true } })
  state.registry = new Map()
  state.items = []
  state.initialized = true
  favoriteState.listener = null
  favoriteState.listeners?.clear?.()

  const unsubscribeFirst = favoriteState.subscribe((event) => events.push(['first', event.type, event.id, event.is_favorited]))
  favoriteState.subscribe((event) => events.push(['second', event.type, event.id, event.is_favorited]))

  assert.equal(typeof unsubscribeFirst, 'function')

  await favoriteState.toggle('video', 'abc123')
  unsubscribeFirst()
  await favoriteState.toggle('video', 'def456')

  assert.deepEqual(events, [
    ['first', 'video', 'abc123', true],
    ['second', 'video', 'abc123', true],
    ['second', 'video', 'def456', true],
  ])
})
