import test from 'node:test'
import assert from 'node:assert/strict'
import { normalizeSubscriptionKeyword, subscriptionMatchesKeyword } from './subscriptionFilter.js'

const subscription = { actress_id: 321, actress_name: '田中ねね' }
const metadata = {
  name_kanji_translated: '田中宁宁',
  name_romaji_translated: '田中寧寧',
  name_kanji: '田中ねね',
  name_kana: 'たなかねね',
  name_romaji: 'Tanaka Nene',
}

test('normalizes surrounding whitespace and latin case', () => {
  assert.equal(normalizeSubscriptionKeyword('  NENE  '), 'nene')
})

test('matches partial translated, Japanese, kana, romaji, subscription, and ID values', () => {
  for (const keyword of ['宁宁', '寧寧', '中ね', 'なかね', 'nAkA Ne', '田中', '21']) {
    assert.equal(subscriptionMatchesKeyword(subscription, metadata, keyword), true, keyword)
  }
})

test('treats blank keywords as unfiltered and tolerates missing metadata', () => {
  assert.equal(subscriptionMatchesKeyword(subscription, null, '   '), true)
  assert.equal(subscriptionMatchesKeyword(subscription, null, '田中'), true)
  assert.equal(subscriptionMatchesKeyword(subscription, null, '白石'), false)
})
