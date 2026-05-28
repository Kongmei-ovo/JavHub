import assert from 'node:assert/strict'
import test from 'node:test'

import {
  candidateKey,
  candidateName,
  confidenceText,
  initials,
} from './inventoryPresentation.js'

test('candidateName keeps actor mapping presentation fallback order', () => {
  assert.equal(candidateName({ javinfo_actress_name: '三上悠亜', name_kanji: 'ignored' }), '三上悠亜')
  assert.equal(candidateName({ name_kanji: '桃乃木かな', name: 'ignored' }), '桃乃木かな')
  assert.equal(candidateName({ name_romaji: 'Momonogi Kana' }), 'Momonogi Kana')
  assert.equal(candidateName({ name_ja: '架乃ゆら', name: 'ignored' }), '架乃ゆら')
  assert.equal(candidateName({ name_en: 'Yura Kano' }), 'Yura Kano')
  assert.equal(candidateName({ name: 'Local Name' }), 'Local Name')
  assert.equal(candidateName({ id: 123 }), '123')
  assert.equal(candidateName({}), '')
})

test('candidateKey keeps local ids before JavInfo ids and names', () => {
  assert.equal(candidateKey({ id: 1, javinfo_actress_id: 2, javinfo_actress_name: 'Name' }), '1')
  assert.equal(candidateKey({ javinfo_actress_id: 2, javinfo_actress_name: 'Name' }), '2')
  assert.equal(candidateKey({ javinfo_actress_name: 'Name' }), 'Name')
  assert.equal(candidateKey({ name_kanji: '名前' }), '名前')
  assert.equal(candidateKey({}), '')
})

test('confidenceText formats confidence as rounded whole percentages', () => {
  assert.equal(confidenceText(0.912), '91%')
  assert.equal(confidenceText('0.755'), '76%')
  assert.equal(confidenceText(null), '0%')
  assert.equal(confidenceText('invalid'), '0%')
})

test('initials returns the uppercased first character or a question mark', () => {
  assert.equal(initials('alice'), 'A')
  assert.equal(initials('三上悠亜'), '三')
  assert.equal(initials(''), '?')
  assert.equal(initials(null), '?')
})
