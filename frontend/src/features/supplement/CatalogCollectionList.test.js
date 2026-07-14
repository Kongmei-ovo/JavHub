import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const listSource = readFileSync(new URL('./CatalogCollectionList.vue', import.meta.url), 'utf8')
const panelSource = readFileSync(new URL('./ActressCatalogPanel.vue', import.meta.url), 'utf8')
const panelStyle = readFileSync(new URL('./actressCatalogPanel.css', import.meta.url), 'utf8')

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

test('download source status uses the shared menu control instead of nested stage navigation', () => {
  assert.match(panelSource, /v-else-if="stage === 'sources'"[\s\S]*class="source-stage-select"/)
  assert.match(panelSource, /v-model="sourceStageFilter"/)
  assert.match(panelSource, /aria-label="下载源状态筛选"/)
  assert.match(panelSource, /hint: `\$\{by\('find_source'\)\} 部`/)
  assert.doesNotMatch(panelSource, /stage-seg fp-seg fp-seg-wrap/)
})

test('stage navigation styles cannot override filter segmented controls', () => {
  assert.match(panelStyle, /\.stage-row \.stage-seg button/)
  assert.doesNotMatch(panelStyle, /^\.stage-seg(?:\s|\{|\.)/m)
  assert.match(panelStyle, /\.fp-row :deep\(\.glass-select__button\)/)
  assert.doesNotMatch(panelStyle, /\.glass-select__trigger/)
})
