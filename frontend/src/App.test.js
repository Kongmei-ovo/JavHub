import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./App.vue', import.meta.url), 'utf8')
const routerSource = readFileSync(new URL('./router/index.js', import.meta.url), 'utf8')

test('App lazy loads the global video modal only when opened', () => {
  assert.match(source, /defineAsyncComponent/)
  assert.match(source, /const VideoModal = defineAsyncComponent\(\(\) => import\('\.\/components\/VideoModal\.vue'\)\)/)
  assert.doesNotMatch(source, /import VideoModal from '\.\/components\/VideoModal\.vue'/)
})

test('primary navigation is grouped around daily workflows first', () => {
  const navStart = source.indexOf('const navGroups')
  const navEnd = source.indexOf('const bottomNavItems', navStart)
  const navBlock = source.slice(navStart, navEnd)
  const groupLabels = [...navBlock.matchAll(/label: '([^']+)',\s*items:/g)].map((match) => match[1])
  const labels = [...navBlock.matchAll(/\{ path: '[^']+', label: '([^']+)'/g)].map((match) => match[1])

  assert.deepEqual(groupLabels, ['日常使用', '自动化维护', '系统管理'])
  assert.deepEqual(labels, [
    '影片检索',
    '随机探索',
    '我的收藏',
    '下载任务',
    '磁链解析',
    '实体目录',
    '演员订阅',
    '片库整理',
    '补全管理',
    '翻译作业',
    '运营总览',
    '配置中心',
    '运行日志',
  ])
  assert.match(source, /id="mobile-more-title">更多功能/)
  assert.match(source, /aria-label="关闭更多面板"/)
})

test('mobile more exposes initialization and maintenance entry points', () => {
  const mobileStart = source.indexOf('const mobileMoreItems')
  const mobileEnd = source.indexOf('const isMoreRoute', mobileStart)
  const mobileBlock = source.slice(mobileStart, mobileEnd)
  const labels = [...mobileBlock.matchAll(/\{ path: '[^']+', label: '([^']+)'/g)].map((match) => match[1])

  assert.deepEqual(labels, [
    '我的收藏',
    '磁链解析',
    '实体目录',
    '订阅演员',
    '片库整理',
    '翻译作业',
    '补全管理',
    '配置中心',
    '运行日志',
  ])
  assert.match(mobileBlock, /path: '\/entities'/)
  assert.match(mobileBlock, /path: '\/library-organize'/)
  assert.match(mobileBlock, /path: '\/logs'/)
})

test('maintenance routes converge on the unified library organizer', () => {
  assert.match(routerSource, /path:\s*'\/library-organize'[\s\S]*LibraryOrganize/)
  assert.match(routerSource, /path:\s*'\/inventory'[\s\S]*tab:\s*'inventory'/)
  assert.match(routerSource, /path:\s*'\/library'[\s\S]*tab:\s*'check'/)
  assert.match(routerSource, /path:\s*'\/duplicates'[\s\S]*tab:\s*'duplicates'/)
  assert.match(routerSource, /path:\s*'\/normalize'[\s\S]*tab:\s*'mapping'/)
  assert.match(routerSource, /path:\s*'\/inventory\/actors\/:id'[\s\S]*actor_id:\s*to\.params\.id/)
})

test('root route redirects to video search as the primary entry page', () => {
  assert.match(routerSource, /\{\s*path:\s*'\/',\s*redirect:\s*'\/search'\s*\}/)
  assert.doesNotMatch(routerSource, /\/videos\/:contentId/)
  assert.doesNotMatch(routerSource, /name:\s*'VideoDetail'/)
  assert.doesNotMatch(routerSource, /\{\s*path:\s*'\/',\s*component:/)
})

test('query-backed modal routes resume by fullPath and keep list pages alive', () => {
  assert.match(source, /watch\(\(\) => route\.fullPath/)
  assert.match(source, /newPath === modalState\.openedOnRoute/)
  assert.match(source, /'Subscription'/)
  assert.match(source, /'Actor'/)
  assert.doesNotMatch(source, /'Subscriptions'/)
})
