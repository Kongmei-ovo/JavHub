import test from 'node:test'
import assert from 'node:assert/strict'

import {
  createSourceDraft,
  mergeMagnetResults,
  selectableMagnetSources,
  sourceHost,
  sourceTypeLabel,
  sourceTypeMark,
  validateSourceDraft,
} from './sourcePresentation.js'

const TORZNAB_DRAFT = {
  id: '',
  type: 'torznab',
  kind: 'prowlarr',
  name: '',
  enabled: true,
  base_url: '',
  api_key: '',
  api_key_configured: false,
  indexer: 'all',
  categories: '',
  limit: 20,
  timeout: 15,
}

test('source draft defaults to a fresh enabled Prowlarr instance', () => {
  const first = createSourceDraft('torznab')
  const second = createSourceDraft('torznab')

  assert.deepEqual(first, TORZNAB_DRAFT)
  assert.deepEqual(second, TORZNAB_DRAFT)
  assert.notEqual(first, second)

  first.name = 'changed'
  assert.equal(second.name, '')
})

test('source draft validation returns field-level required errors for a new Torznab source', () => {
  assert.deepEqual(validateSourceDraft(createSourceDraft('torznab')), {
    name: '请输入来源名称',
    base_url: '请输入有效的 HTTP(S) URL',
    api_key: '请输入 API Key',
  })
})

test('source draft validation requires HTTP(S) and bounded integer settings', () => {
  const draft = {
    ...createSourceDraft('torznab'),
    name: 'Prowlarr',
    base_url: 'ftp://indexer.example.test/api',
    api_key: 'secret',
    limit: 1.5,
    timeout: 61,
  }

  assert.deepEqual(validateSourceDraft(draft), {
    base_url: '请输入有效的 HTTP(S) URL',
    limit: '返回上限必须是 1–100 的整数',
    timeout: '超时必须是 1–60 的整数',
  })

  assert.deepEqual(validateSourceDraft({
    ...draft,
    base_url: 'https://indexer.example.test/api',
    limit: 100,
    timeout: 1,
  }), {})
})

test('source draft validation lets an edited source keep its configured API key', () => {
  const draft = {
    ...createSourceDraft('torznab'),
    id: 'source-1',
    name: 'Prowlarr',
    base_url: 'http://localhost:9696',
    api_key: '   ',
    api_key_configured: true,
  }

  assert.deepEqual(validateSourceDraft(draft), {})
  assert.deepEqual(validateSourceDraft({ ...draft, api_key_configured: false }), {
    api_key: '请输入 API Key',
  })
  assert.deepEqual(validateSourceDraft({ ...draft, id: '' }), {
    api_key: '请输入 API Key',
  })
})

test('source type presentation distinguishes built-ins, Torznab providers, and AVDB', () => {
  assert.equal(sourceTypeLabel({ type: 'm3u8' }), '在线 M3U8')
  assert.equal(sourceTypeLabel({ type: 'torznab', kind: 'prowlarr' }), 'Prowlarr')
  assert.equal(sourceTypeLabel({ type: 'torznab', kind: 'jackett' }), 'Jackett')
  assert.equal(sourceTypeLabel({ type: 'torznab', kind: 'torznab' }), '通用 Torznab')
  assert.equal(sourceTypeLabel({ type: 'avdb' }), 'AVDB 公开库')
  assert.equal(sourceTypeMark({ type: 'm3u8' }), 'HLS')
  assert.equal(sourceTypeMark({ type: 'torznab' }), 'BT')
  assert.equal(sourceTypeMark({ type: 'avdb' }), 'DB')
})

test('source host extracts a host and safely falls back for invalid input', () => {
  assert.equal(sourceHost({ base_url: 'http://localhost:9696/api/' }), 'localhost:9696')
  assert.equal(sourceHost('https://indexer.example.test/path'), 'indexer.example.test')
  assert.equal(sourceHost('not a URL'), 'not a URL')
  assert.equal(sourceHost(null), '尚未配置')
})

test('selectable magnet sources always start with auto and use only eligible saved sources', () => {
  const snapshot = {
    builtins: [
      { id: 'm3u8', type: 'm3u8', name: '在线 M3U8', enabled: true },
      { id: 'not-saved', type: 'torznab', name: '不应出现', enabled: true },
    ],
    sources: [
      { id: 'm3u8-copy', type: 'm3u8', name: '在线副本', enabled: true },
      { id: 'prowlarr', type: 'torznab', kind: 'prowlarr', name: '主索引', enabled: true },
      { id: 'disabled', type: 'torznab', name: '已停用', enabled: false },
      { id: 'avdb-unavailable', type: 'avdb', name: 'wrong label', enabled: true, available: false },
      { id: 'avdb-disabled', type: 'avdb', enabled: false, available: true },
      { id: 'avdb', type: 'avdb', name: 'wrong label', enabled: true, available: true, status: 'failed' },
      { id: 'unknown', type: 'plugin', name: '未知', enabled: true },
    ],
  }

  assert.deepEqual(selectableMagnetSources(snapshot), [
    { value: 'auto', label: '自动' },
    { value: 'prowlarr', label: '主索引' },
    { value: 'avdb', label: 'AVDB 公开库' },
  ])
  assert.deepEqual(selectableMagnetSources(), [{ value: 'auto', label: '自动' }])
})

test('magnet merge keeps existing order then adds unique searched hashes', () => {
  const existing = [{ magnet: 'magnet:?xt=urn:btih:ABC', title: 'existing' }]
  const searched = [
    { magnet: 'magnet:?xt=urn:btih:abc', title: 'duplicate' },
    { magnet: 'magnet:?xt=urn:btih:DEF', source: 'Prowlarr' },
  ]
  const existingBefore = structuredClone(existing)
  const searchedBefore = structuredClone(searched)

  const merged = mergeMagnetResults(existing, searched)

  assert.equal(merged.length, 2)
  assert.equal(merged[0], existing[0])
  assert.equal(merged[1], searched[1])
  assert.equal(merged[1].source, 'Prowlarr')
  assert.deepEqual(existing, existingBefore)
  assert.deepEqual(searched, searchedBefore)
})

test('magnet merge prefers explicit hashes then BTIH then a normalized complete URI', () => {
  const merged = mergeMagnetResults([
    { info_hash: 'AbC', magnet: 'magnet:?xt=urn:btih:OTHER', title: 'explicit' },
    { magnet: 'magnet:?dn=One+File&tr=https%3A%2F%2Ft.test', title: 'uri' },
  ], [
    { info_hash: 'abc', magnet: 'magnet:?xt=urn:btih:DIFFERENT', title: 'explicit duplicate' },
    { magnet: 'MAGNET:?tr=https%3A%2F%2Ft.test&dn=One%20File', title: 'uri duplicate' },
    { info_hash: 'different', magnet: 'magnet:?xt=urn:btih:OTHER', title: 'explicit identity wins' },
  ])

  assert.deepEqual(merged.map(item => item.title), [
    'explicit',
    'uri',
    'explicit identity wins',
  ])
})

test('magnet merge never collapses entries that have no usable identity', () => {
  const first = { title: 'first without a URI' }
  const second = { title: 'second without a URI' }

  assert.deepEqual(mergeMagnetResults([first], [second]), [first, second])
})
