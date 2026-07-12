import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const listSource = readFileSync(new URL('./CatalogCollectionList.vue', import.meta.url), 'utf8')
const panelSource = readFileSync(new URL('./ActressCatalogPanel.vue', import.meta.url), 'utf8')

test('catalog separates source, metadata completeness, and 115 ownership', () => {
  assert.match(listSource, />资料来源</)
  assert.match(listSource, />资料状态</)
  assert.match(listSource, /DMM收录/)
  assert.match(listSource, /补充源独有/)
  assert.match(listSource, /已补齐/)
  assert.match(listSource, /待补齐/)
  assert.match(listSource, /\? '已有' : '未有'/)
})

test('catalog filters and hero avoid ambiguous private and ingest wording', () => {
  assert.match(panelSource, /媒体库 <small>115 已有<\/small>/)
  assert.match(panelSource, /DMM收录/)
  assert.match(panelSource, /补充源独有/)
  assert.doesNotMatch(panelSource, /label: '私拍'/)
  assert.doesNotMatch(panelSource, /label: '已入库'/)
})
