import assert from 'node:assert/strict'
import test from 'node:test'

import {
  PROVIDER_KEYS,
  PROVIDER_META,
  firstNetworkProvider,
  normalizeProvider,
  providerLabel,
  providerOrderLabel,
} from './translationProviders.js'

test('translation provider metadata exposes configured network providers', () => {
  assert.deepEqual(PROVIDER_KEYS, ['google_free', 'baidu', 'deepl', 'microsoft', 'ai'])
  assert.equal(PROVIDER_META.google_free.label, 'Google 免费接口')
  assert.equal(PROVIDER_META.ai.label, '智能兜底')
})

test('providerLabel names known pipeline and network providers', () => {
  assert.equal(providerLabel('cache'), '缓存')
  assert.equal(providerLabel('mapping'), '映射')
  assert.equal(providerLabel('google_free'), 'Google 免费接口')
  assert.equal(providerLabel('openai_compatible'), '智能兜底')
  assert.equal(providerLabel('translation_service'), '批量源')
  assert.equal(providerLabel('manual'), '人工')
  assert.equal(providerLabel('custom_provider'), 'custom_provider')
  assert.equal(providerLabel(''), '')
})

test('providerOrderLabel joins known labels and falls back when empty', () => {
  assert.equal(providerOrderLabel(['cache', 'mapping', 'google_free']), '缓存 -> 映射 -> Google 免费接口')
  assert.equal(providerOrderLabel(['', null, undefined]), '未记录')
  assert.equal(providerOrderLabel(null), '未记录')
})

test('normalizeProvider maps legacy ai key and falls back safely', () => {
  assert.equal(normalizeProvider('openai_compatible'), 'ai')
  assert.equal(normalizeProvider('deepl'), 'deepl')
  assert.equal(normalizeProvider('manual'), 'google_free')
  assert.equal(normalizeProvider(''), 'google_free')
})

test('firstNetworkProvider skips cache and mapping providers', () => {
  assert.equal(firstNetworkProvider(['cache', 'mapping', 'baidu']), 'baidu')
  assert.equal(firstNetworkProvider(['cache', 'openai_compatible']), 'ai')
  assert.equal(firstNetworkProvider(['cache', 'mapping']), '')
  assert.equal(firstNetworkProvider('google_free'), '')
})
