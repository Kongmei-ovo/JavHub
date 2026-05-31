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
    state.detailsLoaded = false
    state.metadataTypesLoaded = new Set()
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

test('favorite init loads the lightweight index without keeping large metadata', async (t) => {
  const originalGetFavorites = api.getFavorites
  const calls = []
  t.after(() => {
    api.getFavorites = originalGetFavorites
    state.registry = new Map()
    state.items = []
    state.initialized = false
    state.detailsLoaded = false
    state.metadataTypesLoaded = new Set()
    favoriteState.listener = null
    favoriteState.listeners?.clear?.()
  })

  api.getFavorites = async (...args) => {
    calls.push(args)
    return {
      data: [
        {
          entity_type: 'video',
          entity_id: 'MIAA-784::mono',
          metadata: { title: 'large', blob: 'x'.repeat(20_000) },
          created_at: '2026-01-01T00:00:00Z',
        },
      ],
    }
  }
  state.registry = new Map()
  state.items = []
  state.initialized = false
  state.detailsLoaded = false

  await favoriteState.init()

  assert.deepEqual(calls[0], [undefined, { include_metadata: false }])
  assert.equal(favoriteState.isFavorited('video', 'MIAA-784::mono'), true)
  assert.equal(state.items[0].metadata, undefined)
  assert.equal(state.detailsLoaded, false)
})

test('favorite refresh can explicitly load full metadata for the favorites page', async (t) => {
  const originalGetFavorites = api.getFavorites
  const calls = []
  t.after(() => {
    api.getFavorites = originalGetFavorites
    state.registry = new Map()
    state.items = []
    state.initialized = false
    state.detailsLoaded = false
    state.metadataTypesLoaded = new Set()
    favoriteState.listener = null
    favoriteState.listeners?.clear?.()
  })

  api.getFavorites = async (...args) => {
    calls.push(args)
    return {
      data: [
        {
          entity_type: 'actress',
          entity_id: '123',
          metadata: { name_kanji: 'Actor' },
          created_at: '2026-01-01T00:00:00Z',
        },
      ],
    }
  }
  state.registry = new Map()
  state.items = []
  state.initialized = false
  state.detailsLoaded = false

  await favoriteState.refresh({ includeMetadata: true })

  assert.deepEqual(calls[0], [undefined, { include_metadata: true }])
  assert.deepEqual(state.items[0].metadata, { name_kanji: 'Actor' })
  assert.equal(state.detailsLoaded, true)
})

test('favorite metadata loader fetches only requested entity types and preserves lightweight videos', async (t) => {
  const originalGetFavorites = api.getFavorites
  const calls = []
  t.after(() => {
    api.getFavorites = originalGetFavorites
    state.registry = new Map()
    state.items = []
    state.initialized = false
    state.detailsLoaded = false
    state.metadataTypesLoaded = new Set()
    favoriteState.listener = null
    favoriteState.listeners?.clear?.()
  })

  api.getFavorites = async (...args) => {
    calls.push(args)
    return {
      data: [
        {
          entity_type: 'actress',
          entity_id: '123',
          metadata: { name_kanji: 'Actor' },
          created_at: '2026-01-01T00:00:00Z',
        },
      ],
    }
  }
  state.registry = new Map()
  state.items = [
    { entity_type: 'video', entity_id: 'MIAA-784::mono', created_at: '2026-01-02T00:00:00Z' },
    { entity_type: 'actress', entity_id: '123', created_at: '2026-01-01T00:00:00Z' },
  ]
  state.initialized = true
  state.detailsLoaded = false
  state.metadataTypesLoaded = new Set()

  await favoriteState.loadMetadataForTypes(['actress'])

  assert.deepEqual(calls, [['actress', { include_metadata: true }]])
  assert.equal(state.items.find(item => item.entity_type === 'video').metadata, undefined)
  assert.deepEqual(state.items.find(item => item.entity_type === 'actress').metadata, { name_kanji: 'Actor' })
  assert.equal(state.metadataTypesLoaded.has('actress'), true)
})

test('favorite state notifies listeners in order and can unsubscribe one listener', async (t) => {
  const originalToggleFavorite = api.toggleFavorite
  const events = []
  t.after(() => {
    api.toggleFavorite = originalToggleFavorite
    state.registry = new Map()
    state.items = []
    state.initialized = false
    state.detailsLoaded = false
    state.metadataTypesLoaded = new Set()
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
