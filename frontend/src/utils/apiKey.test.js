import test from 'node:test'
import assert from 'node:assert/strict'

import { attachApiKey, getStoredApiKey, saveStoredApiKey } from './apiKey.js'

test('api key helper stores trims and clears the local key', () => {
  const originalLocalStorage = globalThis.localStorage
  const store = new Map()
  globalThis.localStorage = {
    getItem: key => store.get(key) || null,
    setItem: (key, value) => store.set(key, value),
    removeItem: key => store.delete(key),
  }

  try {
    assert.equal(saveStoredApiKey('  secret-key  '), 'secret-key')
    assert.equal(getStoredApiKey(), 'secret-key')
    assert.equal(saveStoredApiKey(''), '')
    assert.equal(getStoredApiKey(), '')
  } finally {
    if (originalLocalStorage === undefined) {
      delete globalThis.localStorage
    } else {
      globalThis.localStorage = originalLocalStorage
    }
  }
})

test('attachApiKey adds X-API-Key header when a key exists', () => {
  const originalLocalStorage = globalThis.localStorage
  globalThis.localStorage = {
    getItem: () => 'secret-key',
    setItem: () => {},
    removeItem: () => {},
  }

  try {
    const config = attachApiKey({ headers: { Accept: 'application/json' } })
    assert.equal(config.headers.Accept, 'application/json')
    assert.equal(config.headers['X-API-Key'], 'secret-key')
  } finally {
    if (originalLocalStorage === undefined) {
      delete globalThis.localStorage
    } else {
      globalThis.localStorage = originalLocalStorage
    }
  }
})
