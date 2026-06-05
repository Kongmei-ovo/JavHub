import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./App.vue', import.meta.url), 'utf8')
const routerSource = readFileSync(new URL('./router/index.js', import.meta.url), 'utf8')

function sourceBlock(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = source.match(new RegExp(`${escaped}\\s*\\{([\\s\\S]*?)\\n\\}`))
  assert.ok(match, `${selector} should exist`)
  return match[1]
}

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

test('favorite toast subscription is cleaned up when app unmounts', () => {
  assert.match(source, /const unsubscribeFavoriteState = favoriteState\.subscribe/)
  assert.match(source, /onUnmounted\(\(\) => \{[\s\S]*unsubscribeFavoriteState\(\)[\s\S]*window\.removeEventListener\(MESSAGE_EVENT, handleAppMessage\)/)
})

test('app chrome separates floating liquid navigation from calm content material', () => {
  assert.match(source, /\.app-layout::before\s*\{[\s\S]*background:\s*var\(--app-backdrop-texture\)/)
  assert.match(source, /\.sidebar\s*\{[\s\S]*margin:\s*var\(--app-chrome-inset\) 0 var\(--app-chrome-inset\) var\(--app-chrome-inset\)[\s\S]*border-radius:\s*var\(--radius-sheet\)[\s\S]*box-shadow:\s*var\(--chrome-floating-shadow\)/)
  assert.match(source, /\.sidebar\s*\{[\s\S]*position:\s*relative[\s\S]*isolation:\s*isolate/)
  assert.match(source, /\.sidebar::after\s*\{[\s\S]*background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\)[\s\S]*opacity:\s*var\(--surface-overlay-opacity\)[\s\S]*pointer-events:\s*none/)
  assert.match(source, /\.sidebar-header\s*\{[\s\S]*z-index:\s*1/)
  assert.match(source, /\.sidebar-nav\s*\{[\s\S]*z-index:\s*1/)
  assert.match(source, /\.main-content\s*\{[\s\S]*margin:\s*var\(--app-chrome-inset\)[\s\S]*background:\s*var\(--content-material\)[\s\S]*border:\s*1px solid var\(--content-material-border\)/)
  assert.match(source, /\.bottom-nav\s*\{[\s\S]*left:\s*max\(12px,\s*env\(safe-area-inset-left,\s*0px\)\)[\s\S]*right:\s*max\(12px,\s*env\(safe-area-inset-right,\s*0px\)\)[\s\S]*border-radius:\s*var\(--radius-sheet\)[\s\S]*box-shadow:\s*var\(--chrome-floating-shadow\)/)
  assert.match(source, /\.bottom-nav\s*\{[\s\S]*overflow:\s*hidden[\s\S]*isolation:\s*isolate/)
  assert.match(source, /\.bottom-nav::after\s*\{[\s\S]*background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\)[\s\S]*opacity:\s*var\(--surface-overlay-opacity\)[\s\S]*pointer-events:\s*none/)
  assert.match(source, /\.bottom-nav-item\s*\{[\s\S]*position:\s*relative[\s\S]*z-index:\s*1/)
  assert.match(source, /\.bottom-nav-item\.active\s*\{[\s\S]*background:[\s\S]*var\(--glass-active-material\)[\s\S]*box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.match(source, /\.mobile-more-sheet\s*\{[\s\S]*position:\s*relative[\s\S]*isolation:\s*isolate[\s\S]*overflow:\s*hidden/)
  assert.match(source, /\.mobile-more-sheet::after\s*\{[\s\S]*background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\)[\s\S]*opacity:\s*var\(--surface-overlay-opacity\)[\s\S]*pointer-events:\s*none/)
  assert.match(source, /\.mobile-more-sheet > \*\s*\{[\s\S]*z-index:\s*1/)
})

test('app navigation controls use layered liquid glass materials', () => {
  const layeredControl = /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-control\)/
  const layeredControlHover = /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--material-glass-control-hover\)/
  const layeredActive = /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--glass-active-material\)/
  const layeredSheet = /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--material-glass-sheet\)/

  assert.match(sourceBlock('.theme-toggle'), layeredControl)
  assert.match(sourceBlock('.theme-toggle:hover'), layeredControlHover)
  assert.match(sourceBlock('.theme-toggle__orb'), layeredActive)
  assert.match(sourceBlock('.nav-item:hover'), layeredControlHover)
  assert.match(sourceBlock('.nav-item.active'), layeredActive)
  assert.match(sourceBlock('.nav-badge'), layeredControl)
  assert.match(sourceBlock('.bottom-nav-item.active'), layeredActive)
  assert.match(sourceBlock('.mobile-more-sheet'), layeredSheet)
  assert.match(sourceBlock('.mobile-more-close'), layeredControl)
  assert.match(sourceBlock('.mobile-theme-toggle'), layeredControl)
  assert.match(sourceBlock('.mobile-more-item'), layeredControl)
  assert.match(sourceBlock('.mobile-more-item.active'), layeredActive)
  assert.match(source, /\.collapse-btn:hover\s*\{[\s\S]*background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--material-glass-control-hover\)[\s\S]*box-shadow:\s*var\(--glass-control-shadow\)/)
})
