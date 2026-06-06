import test from 'node:test'
import assert from 'node:assert/strict'
import {
  DEFAULT_SEARCH_PREFERENCES,
  SEARCH_PREFERENCES_KEY,
  buildSearchPreferenceParams,
  loadSearchPreferences,
  normalizeSearchHistoryPreferences,
  normalizeSearchPreferences,
  recordSearchHistoryPreference,
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

test('search preferences record compact history hints for result ranking', () => {
  const writes = new Map()
  const storage = {
    getItem: key => writes.get(key) || null,
    setItem: (key, value) => writes.set(key, value),
  }

  withLocalStorage(storage, () => {
    recordSearchHistoryPreference({
      content_id: 'MIAA-101',
      actress_name: '小湊よつ葉',
      maker_name: 'MOODYZ',
      series_name: '企画',
      categories: [{ name_ja: 'コスプレ' }],
    })
    recordSearchHistoryPreference({
      content_id: 'MIAA-102',
      actress_name: '小湊よつ葉',
      maker_name: 'MOODYZ',
      categories: [{ name_ja: '制服' }],
    })

    assert.deepEqual(buildSearchPreferenceParams(), {
      preferred_actresses: '小湊よつ葉',
      preferred_makers: 'MOODYZ',
      preferred_series: '企画',
      preferred_categories: 'コスプレ,制服',
    })
  })
})

test('search history preference normalization preserves observed strength', () => {
  const normalized = normalizeSearchHistoryPreferences({
    actresses: { A: 3, B: 1 },
    makers: { M: 2 },
    series: {},
    categories: {},
  })

  assert.deepEqual(normalized.actresses, { A: 3, B: 1 })
  assert.deepEqual(buildSearchPreferenceParams(normalized), {
    preferred_actresses: 'A,B',
    preferred_makers: 'M',
  })
})
