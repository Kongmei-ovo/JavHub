import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const searchSource = readFileSync(new URL('./Search.vue', import.meta.url), 'utf8')
const favoritesSource = readFileSync(new URL('./Favorites.vue', import.meta.url), 'utf8')
const logsSource = readFileSync(new URL('../features/operations/LogStreamPanel.vue', import.meta.url), 'utf8')

test('search page gives failed and empty searches concrete next actions', () => {
  assert.match(searchSource, /<AppleSkeleton\s+v-if="loading"[\s\S]*variant="gallery"[\s\S]*label="影片结果加载中"/)
  assert.match(searchSource, /next-step="检查 JavInfo 服务状态，或稍后重新发起检索。"/)
  assert.match(searchSource, /secondary-action-label="清除条件"/)
  assert.match(searchSource, /@secondary-action="clearFilters"/)
  assert.match(searchSource, /next-step="清除筛选后会回到随机探索，也可以保留条件继续调整关键词。"/)
  assert.match(searchSource, /secondary-action-label="随机探索"/)
  assert.match(searchSource, /@secondary-action="startRandomExplore"/)
})

test('favorites page uses shared skeleton and empty state components', () => {
  assert.match(favoritesSource, /import AppleSkeleton from '\.\.\/components\/AppleSkeleton\.vue'/)
  assert.match(favoritesSource, /import AppleEmptyState from '\.\.\/components\/AppleEmptyState\.vue'/)
  assert.match(favoritesSource, /<AppleSkeleton\s+v-if="videoLoading"[\s\S]*variant="gallery"[\s\S]*label="收藏影片加载中"/)
  assert.match(favoritesSource, /<AppleEmptyState[\s\S]*:title="emptyTitle"[\s\S]*:description="emptyDescription"/)
  assert.match(favoritesSource, /:next-step="emptyNextStep"/)
  assert.match(favoritesSource, /:secondary-action-label="emptySecondaryActionLabel"/)
  assert.match(favoritesSource, /@secondary-action="handleEmptySecondaryAction"/)
  assert.doesNotMatch(favoritesSource, /<div v-if="videoLoading" class="favorites-grid favorites-grid-loading">/)
  assert.doesNotMatch(favoritesSource, /class="curate-empty"/)
})

test('logs page replaces bare loading and empty text with shared states', () => {
  assert.match(logsSource, /import AppleSkeleton from '\.\.\/\.\.\/components\/AppleSkeleton\.vue'/)
  assert.match(logsSource, /import AppleEmptyState from '\.\.\/\.\.\/components\/AppleEmptyState\.vue'/)
  assert.match(logsSource, /import AppleErrorState from '\.\.\/\.\.\/components\/AppleErrorState\.vue'/)
  assert.match(logsSource, /<AppleSkeleton\s+v-if="loading && !logs\.length"[\s\S]*variant="list"[\s\S]*label="日志加载中"/)
  assert.match(logsSource, /<AppleErrorState[\s\S]*v-else-if="logsError"/)
  assert.match(logsSource, /next-step="检查后端日志接口或清除筛选条件后再试。"/)
  assert.match(logsSource, /<AppleEmptyState[\s\S]*v-else-if="logs.length === 0"/)
  assert.match(logsSource, /next-step="清除筛选后可以查看全部日志，也可以刷新等待新事件写入。"/)
  assert.match(logsSource, /secondary-action-label="清除筛选"/)
  assert.doesNotMatch(logsSource, /<div v-if="loading" class="loading">加载中\.\.\.<\/div>/)
  assert.doesNotMatch(logsSource, /<div v-else-if="logs\.length === 0" class="empty">暂无日志<\/div>/)
})
