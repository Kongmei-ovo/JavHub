import test from 'node:test'
import assert from 'node:assert/strict'
import {
  DEFAULT_SEARCH_PREFERENCES,
  SEARCH_PREFERENCES_KEY,
  loadSearchPreferences,
  normalizeSearchPreferences,
  saveSearchPreferences,
} from './searchPreferences.js'

function withLocalStorage(storage, run) {
  const original = globalThis.localStorage
  globalThis.localStorage = storage
  try {
    run()
  } finally {
    if (original === undefined) {
      delete globalThis.localStorage
    } else {
      globalThis.localStorage = original
    }
  }
}

test('search preferences normalize unknown values to safe defaults', () => {
  assert.deepEqual(
    normalizeSearchPreferences({ defaultSort: 'bad', defaultServiceCode: 'other' }),
    DEFAULT_SEARCH_PREFERENCES,
  )
  assert.deepEqual(
    normalizeSearchPreferences({ defaultSort: 'release_date_desc', defaultServiceCode: 'digital' }),
    { defaultSort: 'release_date_desc', defaultServiceCode: 'digital' },
  )
})

test('search preferences load and save localStorage values', () => {
  const writes = new Map()
  const storage = {
    getItem: key => writes.get(key) || null,
    setItem: (key, value) => writes.set(key, value),
  }

  withLocalStorage(storage, () => {
    const saved = saveSearchPreferences({ defaultSort: 'runtime_mins_asc', defaultServiceCode: 'ebook' })
    assert.deepEqual(saved, { defaultSort: 'runtime_mins_asc', defaultServiceCode: 'ebook' })
    assert.equal(writes.get(SEARCH_PREFERENCES_KEY), JSON.stringify(saved))
    assert.deepEqual(loadSearchPreferences(), saved)
  })
})

