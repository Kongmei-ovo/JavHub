import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./App.vue', import.meta.url), 'utf8')
const navigationSource = readFileSync(new URL('./appNavigation.js', import.meta.url), 'utf8')
const routerSource = readFileSync(new URL('./router/index.js', import.meta.url), 'utf8')

function sourceBlock(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = source.match(new RegExp(`${escaped}\\s*\\{([\\s\\S]*?)\\n\\}`))
  assert.ok(match, `${selector} should exist`)
  return match[1]
}

function lastSourceBlock(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const matches = [...source.matchAll(new RegExp(`${escaped}\\s*\\{([\\s\\S]*?)\\n\\}`, 'g'))]
  assert.ok(matches.length, `${selector} should exist`)
  return matches.at(-1)[1]
}

function exactSourceBlock(selector) {
  const blocks = [...source.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
  const match = blocks.find(([, selectors]) => selectors
    .split(',')
    .map(part => part.trim())
    .includes(selector))
  assert.ok(match, `${selector} block should exist`)
  return match[2]
}

test('App lazy loads the global video modal only when opened', () => {
  assert.match(source, /defineAsyncComponent/)
  assert.match(source, /const VideoModal = defineAsyncComponent\(\(\) => import\('\.\/components\/VideoModal\.vue'\)\)/)
  assert.doesNotMatch(source, /import VideoModal from '\.\/components\/VideoModal\.vue'/)
})

test('primary navigation is grouped around daily workflows first', () => {
  const navStart = navigationSource.indexOf('export const navGroups')
  const navEnd = navigationSource.indexOf('export const bottomNavItems', navStart)
  const navBlock = navigationSource.slice(navStart, navEnd)
  const groupLabels = [...navBlock.matchAll(/label: '([^']+)',\s*items:/g)].map((match) => match[1])
  const labels = [...navBlock.matchAll(/\{ path: '[^']+', label: '([^']+)'/g)].map((match) => match[1])

  assert.deepEqual(groupLabels, ['日常使用', '自动化维护', '系统管理'])
  assert.deepEqual(labels, [
    '今日',
    '影库',
    '随机探索',
    '我的收藏',
    '下载任务',
    '磁链解析',
    '实体目录',
    '候选确认',
    '演员订阅',
    '翻译作业',
    '配置中心',
    '运行日志',
  ])
  assert.match(source, /id="mobile-more-title">更多功能/)
  assert.match(source, /aria-label="关闭更多面板"/)
})

test('mobile more exposes initialization and maintenance entry points', () => {
  const mobileStart = navigationSource.indexOf('export const mobileMoreItems')
  const mobileEnd = navigationSource.indexOf('export const navActivePaths', mobileStart)
  const mobileBlock = navigationSource.slice(mobileStart, mobileEnd)
  const labels = [...mobileBlock.matchAll(/\{ path: '[^']+', label: '([^']+)'/g)].map((match) => match[1])

  assert.deepEqual(labels, [
    '随机探索',
    '磁链解析',
    '实体目录',
    '订阅演员',
    '翻译作业',
    '配置中心',
    '运行日志',
  ])
  assert.match(mobileBlock, /path: '\/entities'/)
  assert.match(mobileBlock, /path: '\/logs'/)
})

test('retired maintenance routes stay out of the active router', () => {
  assert.match(routerSource, /\{\s*path:\s*'\/library',\s*redirect:\s*'\/search'\s*\}/)
  assert.doesNotMatch(routerSource, /LibraryOrganize|SupplementManagement|Operations|InventoryActor/)
  assert.doesNotMatch(routerSource, /path:\s*'\/(?:library-organize|inventory|duplicates|normalize|supplement|operations)'/)
})

test('root route mounts the Today dashboard as the primary entry page', () => {
  // Today remains the dashboard while downloads owns a focused v2 page.
  assert.match(routerSource, /\{\s*path:\s*'\/',\s*name:\s*'Today',\s*component:\s*\(\) => import\('\.\.\/views\/Today\.vue'\)\s*\}/)
  assert.match(routerSource, /\{\s*path:\s*'\/today',\s*redirect:\s*'\/'\s*\}/)
  assert.match(routerSource, /\{\s*path:\s*'\/downloads',\s*name:\s*'Downloads',\s*component:\s*\(\) => import\('\.\.\/views\/Downloads\.vue'\)\s*\}/)
  assert.doesNotMatch(routerSource, /views\/Home\.vue/)
  assert.doesNotMatch(routerSource, /\/videos\/:contentId/)
  assert.doesNotMatch(routerSource, /name:\s*'VideoDetail'/)
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
  // Content area is the opaque windowpane — glass stays on chrome only.
  // This is the load-bearing "calm content" assertion: solid canvas + hairline.
  assert.match(source, /\.main-content\s*\{[\s\S]*margin:\s*var\(--app-chrome-inset\)[\s\S]*background:\s*var\(--canvas\)[\s\S]*border:\s*1px solid var\(--hairline\)/)
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

test('app shell navigation marks current route semantically across desktop mobile and more menu', () => {
  // P2: '/library' 从 library-organize 桶移到 search 桶,让"影库"导航在 /library 时也高亮。
  assert.match(navigationSource, /export const navActivePaths = \{[\s\S]*'\/search': \['\/search', '\/library'\][\s\S]*'\/genres': \['\/genres', '\/discovery'\][\s\S]*'\/entities': \['\/entities', '\/entity', '\/actor'\]/)
  assert.doesNotMatch(navigationSource, /library-organize|supplement|operations/)
  assert.match(source, /const isNavItemActive = \(path\) => \{[\s\S]*const currentPath = normalizedRoutePath\.value[\s\S]*const activePaths = navActivePaths\[path\] \|\| \[path\][\s\S]*currentPath === activePath \|\| currentPath\.startsWith\(`\$\{activePath\}\/`\)/)
  assert.match(source, /:class="\{ active: isNavItemActive\(item\.path\) \}"/)
  assert.match(source, /:aria-current="isNavItemActive\(item\.path\) \? 'page' : undefined"/)
  assert.match(source, /const isMoreRoute = computed\(\(\) => mobileMoreItems\.some\(item => isNavItemActive\(item\.path\)\)\)/)
})

test('actor detail route belongs to entity navigation instead of search', () => {
  const navBlock = navigationSource.match(/export const navActivePaths = \{[\s\S]*?\n\}/)?.[0] || ''

  assert.match(navBlock, /'\/search':\s*\['\/search', '\/library'\]/)
  assert.match(navBlock, /'\/entities':\s*\['\/entities', '\/entity', '\/actor'\]/)
  assert.doesNotMatch(navBlock, /'\/search':\s*\[[^\]]*'\/actor'/)
})

test('app shell chrome keeps scroll layers stable and focus states glassy', () => {
  assert.match(lastSourceBlock('.sidebar-nav'), /overscroll-behavior:\s*contain/)
  assert.match(lastSourceBlock('.sidebar-nav'), /scrollbar-gutter:\s*stable/)
  assert.match(sourceBlock('.main-content'), /overscroll-behavior:\s*contain/)
  assert.match(sourceBlock('.main-content'), /scrollbar-gutter:\s*stable/)
  assert.match(exactSourceBlock('.nav-item'), /border:\s*1px solid transparent/)
  assert.match(exactSourceBlock('.bottom-nav-item'), /border:\s*1px solid transparent/)
  assert.match(sourceBlock('.nav-item:focus-visible'), /outline:\s*none/)
  assert.match(sourceBlock('.nav-item:focus-visible'), /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/)
  assert.match(sourceBlock('.nav-item.active:focus-visible'), /box-shadow:\s*var\(--glass-active-shadow\),\s*var\(--focus-ring\)/)
  assert.match(exactSourceBlock('.nav-item.active'), /padding-left:\s*22px/)
  assert.match(exactSourceBlock('.nav-item.active::after'), /content:\s*""/)
  assert.match(exactSourceBlock('.nav-item.active::after'), /left:\s*7px/)
  assert.match(exactSourceBlock('.nav-item.active::after'), /background:\s*var\(--active-indicator\)/)
  assert.match(exactSourceBlock('.nav-item.active::after'), /pointer-events:\s*none/)
  assert.match(exactSourceBlock('.nav-item.active::after'), /transition:\s*opacity var\(--motion-fast\),\s*transform var\(--motion-standard\)/)
  assert.match(exactSourceBlock('.nav-item.active:focus-visible::after'), /opacity:\s*0\.28/)
  assert.match(exactSourceBlock('.nav-item.active:focus-visible::after'), /transform:\s*scaleY\(0\.74\)/)
  assert.match(sourceBlock('.bottom-nav-item:focus-visible'), /outline:\s*none/)
  assert.match(sourceBlock('.bottom-nav-item:focus-visible'), /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/)
  assert.match(sourceBlock('.bottom-nav-item.active:focus-visible'), /background:[\s\S]*var\(--glass-active-material\)/)
  assert.match(sourceBlock('.bottom-nav-item.active:focus-visible'), /border-color:\s*var\(--active-border\)/)
  assert.match(exactSourceBlock('.bottom-nav-item.active::before'), /content:\s*""/)
  assert.match(exactSourceBlock('.bottom-nav-item.active::before'), /bottom:\s*6px/)
  assert.match(exactSourceBlock('.bottom-nav-item.active::before'), /width:\s*18px/)
  assert.match(exactSourceBlock('.bottom-nav-item.active::before'), /background:\s*var\(--active-indicator\)/)
  assert.match(exactSourceBlock('.bottom-nav-item.active::before'), /pointer-events:\s*none/)
  assert.match(exactSourceBlock('.bottom-nav-item.active::before'), /transition:\s*opacity var\(--motion-fast\),\s*transform var\(--motion-standard\)/)
})

test('app shell exposes named landmarks and isolates modal background chrome', () => {
  const skipLinkTag = source.match(/<a[^>]*class="skip-link"[^>]*>/)?.[0] || ''

  assert.match(source, /const mobileMoreActive = computed\(\(\) => mobileMoreOpen\.value \|\| mobileMoreClosing\.value\)/)
  assert.match(skipLinkTag, /:inert="mobileMoreActive \? '' : undefined"/)
  assert.match(skipLinkTag, /:aria-hidden="mobileMoreActive \? 'true' : undefined"/)
  assert.match(source, /<aside[\s\S]*class="sidebar"[\s\S]*:inert="mobileMoreActive \? '' : undefined"/)
  assert.match(source, /<aside[\s\S]*class="sidebar"[\s\S]*:aria-hidden="mobileMoreActive \? 'true' : undefined"/)
  assert.match(source, /<nav class="sidebar-nav"\s+aria-label="主导航"\s+id="primary-navigation">/)
  assert.match(source, /<nav[\s\S]*class="bottom-nav"[\s\S]*aria-label="移动端主导航"[\s\S]*:inert="mobileMoreActive \? '' : undefined"/)
  assert.match(source, /<nav[\s\S]*class="bottom-nav"[\s\S]*:aria-hidden="mobileMoreActive \? 'true' : undefined"/)
  assert.match(source, /<nav class="mobile-more-grid"\s+aria-label="更多功能导航">/)
  assert.match(source, /<main[\s\S]*id="main-content"[\s\S]*class="main-content"[\s\S]*tabindex="-1"[\s\S]*aria-label="应用内容"[\s\S]*:inert="mobileMoreActive \? '' : undefined"/)
  assert.match(source, /<main[\s\S]*id="main-content"[\s\S]*:aria-hidden="mobileMoreActive \? 'true' : undefined"/)
})

test('mobile more locks the background scroll layer while the dialog is active', () => {
  assert.match(source, /<div class="app-layout" :class="\{ 'mobile-more-active': mobileMoreActive \}">/)
  assert.match(source, /\.app-layout\.mobile-more-active\s*\{[^}]*overscroll-behavior:\s*none/)
  assert.match(sourceBlock('.app-layout.mobile-more-active .main-content'), /overflow:\s*hidden/)
  assert.match(source, /\.mobile-more-overlay\s*\{[^{}]*overscroll-behavior:\s*contain/)
  assert.match(source, /const mobileMoreClosing = ref\(false\)/)
  assert.match(source, /const finishMobileMoreClose = \(\) => \{[\s\S]*mobileMoreClosing\.value = false[\s\S]*\}/)
  assert.match(source, /<transition name="mobile-more"\s+@after-leave="finishMobileMoreClose">/)
})

test('keyboard entry points expose visible system focus surfaces', () => {
  assert.match(source, /class="theme-toggle"[\s\S]*:aria-pressed="isDarkMode"/)
  assert.match(source, /class="mobile-theme-toggle"[\s\S]*:aria-pressed="isDarkMode"/)
  assert.match(sourceBlock('.theme-toggle:focus-visible'), /outline:\s*none/)
  assert.match(sourceBlock('.theme-toggle:focus-visible'), /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/)
  assert.match(sourceBlock('.skip-link:focus-visible'), /color:\s*var\(--text-primary\)/)
  assert.match(sourceBlock('.skip-link:focus-visible'), /background:[\s\S]*var\(--glass-active-material\)/)
  assert.match(sourceBlock('.skip-link:focus-visible'), /border:\s*1px solid var\(--glass-active-border\)/)
  assert.match(sourceBlock('.skip-link:focus-visible'), /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\) saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(sourceBlock('.skip-link:focus-visible'), /box-shadow:\s*var\(--glass-active-shadow\),\s*var\(--focus-ring\)/)
  assert.match(sourceBlock('.skip-link:focus-visible'), /transform:\s*translateY\(0\)/)
  assert.match(sourceBlock('.main-content:focus-visible'), /outline:\s*none/)
  // Content windowpane is solid now (--canvas + --hairline), so focus border
  // lifts to --hairline-strong and shadow stays on --shadow-card.
  assert.match(sourceBlock('.main-content:focus-visible'), /border-color:\s*var\(--hairline-strong\)/)
  assert.match(sourceBlock('.main-content:focus-visible'), /box-shadow:\s*var\(--shadow-card\),\s*var\(--focus-ring\)/)
  assert.match(sourceBlock('.mobile-more-sheet:focus-visible'), /outline:\s*none/)
  assert.match(sourceBlock('.mobile-more-sheet:focus-visible'), /border-color:\s*var\(--glass-active-border\)/)
  assert.match(sourceBlock('.mobile-more-sheet:focus-visible'), /box-shadow:\s*var\(--shadow-sheet\),\s*var\(--focus-ring\)/)
})

test('mobile more dialog owns keyboard focus and dismisses like system chrome', () => {
  const toggleBlock = source.slice(source.indexOf('const toggleMobileMore'), source.indexOf('const focusMainContent', source.indexOf('const toggleMobileMore')))

  assert.match(source, /ref="mobileMoreButtonRef"/)
  assert.match(source, /ref="mobileMoreSheetRef"/)
  assert.match(source, /class="mobile-more-sheet"[\s\S]*tabindex="-1"[\s\S]*@keydown\.esc\.stop\.prevent="closeMobileMore\(\{ restoreFocus: true \}\)"/)
  assert.match(source, /@click\.self="closeMobileMore\(\{ restoreFocus: true \}\)"/)
  assert.match(source, /@click="closeMobileMore\(\{ restoreFocus: true \}\)">/)
  assert.match(source, /class="mobile-more-close"[\s\S]*aria-keyshortcuts="Escape"[\s\S]*aria-label="关闭更多面板"/)
  assert.match(source, /class="mobile-more-close"[\s\S]*<svg viewBox="0 0 24 24"[\s\S]*<path d="M18 6L6 18M6 6l12 12"/)
  assert.doesNotMatch(source, /class="mobile-more-close"[^>]*>×<\/button>/)
  assert.match(toggleBlock, /if \(mobileMoreOpen\.value\) \{[\s\S]*closeMobileMore\(\{ restoreFocus: true \}\)[\s\S]*return[\s\S]*\}/)
  assert.match(toggleBlock, /mobileMoreClosing\.value = false[\s\S]*mobileMoreOpen\.value = true/)
  assert.doesNotMatch(toggleBlock, /mobileMoreOpen\.value = !mobileMoreOpen\.value/)
  assert.match(source, /let mobileMoreAfterCloseFocus = null/)
  assert.match(source, /const closeMobileMore = \(\{ restoreFocus = false, focusMain = false \} = \{\}\) => \{[\s\S]*mobileMoreAfterCloseFocus = restoreFocus \? 'trigger' : focusMain \? 'main' : null[\s\S]*mobileMoreClosing\.value = true[\s\S]*mobileMoreOpen\.value = false/)
  assert.match(source, /const finishMobileMoreClose = \(\) => \{[\s\S]*mobileMoreClosing\.value = false[\s\S]*if \(mobileMoreAfterCloseFocus === 'trigger'\) nextTick\(\(\) => mobileMoreButtonRef\.value\?\.focus\(\{ preventScroll: true \}\)\)[\s\S]*if \(mobileMoreAfterCloseFocus === 'main'\) focusMainContent\(\)[\s\S]*mobileMoreAfterCloseFocus = null[\s\S]*\}/)
  assert.doesNotMatch(source, /if \(restoreFocus\) nextTick\(\(\) => mobileMoreButtonRef\.value\?\.focus\(\)\)/)
  assert.match(source, /watch\(mobileMoreOpen, async \(isOpen\) => \{[\s\S]*await nextTick\(\)[\s\S]*mobileMoreSheetRef\.value\?\.focus\(\{ preventScroll: true \}\)/)
})

test('mobile more sheet reads as a restrained system menu instead of a card grid', () => {
  assert.match(lastSourceBlock('.mobile-more-overlay'), /z-index:\s*calc\(var\(--z-nav\) \+ 1\)/)
  assert.match(sourceBlock('.mobile-more-sheet'), /max-height:\s*min\(560px,\s*calc\(100dvh - 112px - env\(safe-area-inset-bottom,\s*0px\)\)\)/)
  assert.match(sourceBlock('.mobile-more-sheet'), /overflow:\s*hidden/)
  assert.match(sourceBlock('.mobile-more-grid'), /overflow-y:\s*auto/)
  assert.match(sourceBlock('.mobile-more-grid'), /overscroll-behavior:\s*contain/)
  assert.match(sourceBlock('.mobile-more-grid'), /scrollbar-gutter:\s*stable/)
  assert.match(sourceBlock('.mobile-more-close:focus-visible'), /outline:\s*none/)
  assert.match(sourceBlock('.mobile-more-close:focus-visible'), /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/)
  assert.match(sourceBlock('.mobile-more-item:focus-visible'), /outline:\s*none/)
  assert.match(sourceBlock('.mobile-more-item:focus-visible'), /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/)
  assert.match(sourceBlock('.mobile-more-item.active:focus-visible'), /box-shadow:\s*var\(--glass-active-shadow\),\s*var\(--focus-ring\)/)
  assert.match(sourceBlock('.mobile-theme-toggle:focus-visible'), /outline:\s*none/)
})

test('mobile more sheet preserves command legibility over poster-heavy pages', () => {
  assert.match(sourceBlock('.mobile-more-sheet'), /background-color:\s*color-mix\(in srgb, var\(--bg-primary\) 88%, transparent\)/)
  assert.match(sourceBlock('.mobile-theme-toggle'), /background-color:\s*color-mix\(in srgb, var\(--bg-primary\) 70%, transparent\)/)
  assert.match(sourceBlock('.mobile-more-item'), /background-color:\s*color-mix\(in srgb, var\(--bg-primary\) 70%, transparent\)/)
})

test('mobile more dialog traps tab focus within the sheet controls', () => {
  assert.match(source, /@keydown\.tab="trapMobileMoreFocus"/)
  assert.match(source, /const mobileMoreFocusableSelector = \[/)
  assert.match(source, /'a\[href\]'/)
  assert.match(source, /'button:not\(:disabled\)'/)
  assert.match(source, /const mobileMoreFocusableElements = \(\) => \{[\s\S]*mobileMoreSheetRef\.value\?\.querySelectorAll\(mobileMoreFocusableSelector\)/)
  assert.match(source, /const trapMobileMoreFocus = \(event\) => \{[\s\S]*if \(!mobileMoreOpen\.value\) return[\s\S]*const focusable = mobileMoreFocusableElements\(\)[\s\S]*event\.shiftKey[\s\S]*event\.preventDefault\(\)[\s\S]*focusMobileMoreControl\((?:last|first|event\.shiftKey \? last : first)\)/)
  assert.match(source, /trapMobileMoreFocus,/)
})

test('mobile more trigger is explicitly bound to the dialog surface', () => {
  assert.match(source, /class="bottom-nav-item bottom-nav-more"[\s\S]*:aria-label="mobileMoreActive \? '关闭更多功能' : '打开更多功能'"/)
  assert.match(source, /class="bottom-nav-item bottom-nav-more"[\s\S]*aria-controls="mobile-more-dialog"/)
  assert.match(source, /class="bottom-nav-item bottom-nav-more"[\s\S]*aria-keyshortcuts="Escape"/)
  assert.match(source, /class="bottom-nav-item bottom-nav-more"[\s\S]*:aria-expanded="mobileMoreActive"/)
  assert.match(source, /:class="\{ active: isMoreRoute, open: mobileMoreActive \}"/)
  assert.doesNotMatch(source, /:class="\{ active: mobileMoreOpen \|\| isMoreRoute \}"/)
  assert.match(sourceBlock('.bottom-nav-more.open:not(.active)'), /background:[\s\S]*var\(--material-glass-control-hover\)/)
  assert.match(source, /class="mobile-more-sheet"[\s\S]*id="mobile-more-dialog"[\s\S]*role="dialog"/)
})

test('mobile more trigger separates menu-open state from current-page state', () => {
  assert.match(sourceBlock('.bottom-nav-more::after'), /content:\s*""/)
  assert.match(sourceBlock('.bottom-nav-more::after'), /opacity:\s*0/)
  assert.match(sourceBlock('.bottom-nav-more::after'), /transition:\s*transform var\(--motion-standard\)/)
  assert.doesNotMatch(sourceBlock('.bottom-nav-more::after'), /opacity var\(--motion-fast\)/)
  assert.match(sourceBlock('.bottom-nav-more.open::after'), /opacity:\s*0\.92/)
  assert.match(sourceBlock('.bottom-nav-more.open::after'), /background:\s*var\(--glass-active-border\)/)
  assert.match(sourceBlock('.bottom-nav-more.active::after'), /opacity:\s*0/)
  assert.match(sourceBlock('.bottom-nav-more.open:not(.active)'), /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(sourceBlock('.bottom-nav-more.open:not(.active)'), /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.doesNotMatch(sourceBlock('.bottom-nav-more.open:not(.active)'), /var\(--glass-active-material\)/)
  assert.match(sourceBlock('.bottom-nav-more.open:not(.active):focus-visible'), /background:[\s\S]*var\(--material-glass-control-hover\)/)
  assert.match(sourceBlock('.bottom-nav-more.open:not(.active):focus-visible'), /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/)
})

test('route changes dismiss mobile more through the shared close handler', () => {
  const watchStart = source.indexOf('watch(() => route.fullPath')
  const watchEnd = source.indexOf('const isNavItemActive', watchStart)
  const routeWatchBlock = source.slice(watchStart, watchEnd)

  assert.match(routeWatchBlock, /if \(mobileMoreOpen\.value\) closeMobileMore\(\{ focusMain: true \}\)/)
  assert.doesNotMatch(routeWatchBlock, /mobileMoreOpen\.value\s*=\s*false/)
})

test('mobile more route selection returns keyboard focus to app content', () => {
  assert.match(source, /class="mobile-more-item"[\s\S]*@click="closeMobileMore\(\{ focusMain: true \}\)"/)
  assert.match(source, /const closeMobileMore = \(\{ restoreFocus = false, focusMain = false \} = \{\}\) => \{[\s\S]*mobileMoreAfterCloseFocus = restoreFocus \? 'trigger' : focusMain \? 'main' : null/)
  assert.match(source, /const finishMobileMoreClose = \(\) => \{[\s\S]*if \(mobileMoreAfterCloseFocus === 'main'\) focusMainContent\(\)/)
})

test('mobile more dismisses when the shell leaves the mobile breakpoint', () => {
  assert.match(source, /window\.matchMedia\?\.\('\(max-width: 768px\)'\)/)
  assert.match(source, /const closeMobileMoreOutsideMobile = \(\{ matches \}\) => \{[\s\S]*if \(!matches\) closeMobileMore\(\{ focusMain: true \}\)[\s\S]*\}/)
  assert.match(source, /mobileShellBreakpoint\?\.addEventListener\?\.\('change', closeMobileMoreOutsideMobile\)/)
  assert.match(source, /mobileShellBreakpoint\?\.removeEventListener\?\.\('change', closeMobileMoreOutsideMobile\)/)
})

test('primary shell route links return keyboard focus to app content', () => {
  const focusBlock = source.slice(source.indexOf('const focusMainContent'), source.indexOf('const closeMobileMore', source.indexOf('const focusMainContent')))

  assert.match(source, /class="skip-link"[\s\S]*@click\.prevent="focusMainContent"/)
  assert.match(source, /class="nav-item"[\s\S]*@click="focusMainContentFromNavigation"/)
  assert.match(source, /class="bottom-nav-item"[\s\S]*@click="focusMainContentFromNavigation"/)
  assert.match(focusBlock, /const focusMainContent = \(\{ resetScroll = false \} = \{\}\)/)
  assert.match(focusBlock, /document\.getElementById\('main-content'\)/)
  assert.match(focusBlock, /if \(resetScroll\) main\?\.scrollTo\?\.\(\{ top: 0, left: 0 \}\)/)
  assert.match(focusBlock, /main\?\.focus\(\{ preventScroll: true \}\)/)
  assert.match(focusBlock, /const focusMainContentFromNavigation = \(event\) => \{[\s\S]*if \(event\.detail !== 0\) return[\s\S]*focusMainContent\(\{ resetScroll: true \}\)[\s\S]*\}/)
  assert.match(source, /focusMainContentFromNavigation,/)
})

test('mobile more tab trap loops focus when starting outside actionable controls', () => {
  const trapBlock = source.slice(source.indexOf('const trapMobileMoreFocus'), source.indexOf('watch(mobileMoreOpen', source.indexOf('const trapMobileMoreFocus')))
  assert.match(trapBlock, /const activeIndex = focusable\.indexOf\(document\.activeElement\)/)
  assert.match(trapBlock, /if \(!focusable\.length\) \{[\s\S]*event\.preventDefault\(\)[\s\S]*mobileMoreSheetRef\.value\?\.focus\(\{ preventScroll: true \}\)[\s\S]*return/)
  assert.match(trapBlock, /if \(activeIndex === -1\) \{[\s\S]*event\.preventDefault\(\)[\s\S]*focusMobileMoreControl\(event\.shiftKey \? last : first\)[\s\S]*return/)
  assert.match(trapBlock, /event\.shiftKey && activeIndex === 0/)
  assert.match(trapBlock, /!event\.shiftKey && activeIndex === focusable\.length - 1/)
})

test('mobile more tab loop keeps wrapped focus targets inside the masked scroll area', () => {
  const trapStart = source.indexOf('const trapMobileMoreFocus')
  const trapEnd = source.indexOf('watch(mobileMoreOpen', trapStart)
  const trapBlock = source.slice(trapStart, trapEnd)

  assert.match(source, /const focusMobileMoreControl = \(element\) => \{[\s\S]*element\?\.focus\?\.\(\{ preventScroll: true \}\)[\s\S]*element\?\.scrollIntoView\?\.\(\{ block: 'nearest', inline: 'nearest' \}\)[\s\S]*\}/)
  assert.match(trapBlock, /focusMobileMoreControl\(event\.shiftKey \? last : first\)/)
  assert.match(trapBlock, /focusMobileMoreControl\(last\)/)
  assert.match(trapBlock, /focusMobileMoreControl\(first\)/)
  assert.doesNotMatch(trapBlock, /\b(?:first|last)\.focus\(\)/)
})

test('active navigation chrome tracks route changes inside masked scrollports', () => {
  const mountedBlock = source.slice(source.indexOf('onMounted(() => {'), source.indexOf('onUnmounted', source.indexOf('onMounted(() => {')))

  assert.match(source, /const syncActiveNavigationIntoView = \(\) => nextTick\(\(\) => requestAnimationFrame\(\(\) => document\.querySelectorAll\('\.sidebar-nav \.nav-item\.active, \.mobile-more-grid \.mobile-more-item\.active'\)\.forEach\(element => element\.scrollIntoView\?\.\(\{ block: 'nearest', inline: 'nearest' \}\)\)\)\)/)
  assert.match(mountedBlock, /syncActiveNavigationIntoView\(\)/)
  assert.match(source, /watch\(\(\) => route\.fullPath, \(newPath\) => \{[\s\S]*syncActiveNavigationIntoView\(\)[\s\S]*\}\)/)
  assert.match(source, /watch\(mobileMoreOpen, async \(isOpen\) => \{[\s\S]*mobileMoreSheetRef\.value\?\.focus\(\{ preventScroll: true \}\)[\s\S]*syncActiveNavigationIntoView\(\)[\s\S]*\}\)/)
})

test('collapsed sidebar keeps icon rail navigation named and visually centered', () => {
  assert.match(source, /:aria-label="sidebarCollapsed \? item\.label : undefined"/)
  assert.match(source, /:title="sidebarCollapsed \? item\.label : undefined"/)
  assert.match(source, /<nav class="sidebar-nav"\s+aria-label="主导航"\s+id="primary-navigation">/)
  assert.match(source, /aria-controls="primary-navigation"/)
  assert.match(source, /aria-keyshortcuts="Meta\+B Control\+B"/)
  assert.match(source, /:aria-expanded="!sidebarCollapsed"/)
  assert.match(source, /window\.addEventListener\(('keydown'|"keydown"), toggleSidebarFromKeyboard\)/)
  assert.match(source, /window\.removeEventListener\(('keydown'|"keydown"), toggleSidebarFromKeyboard\)/)
  assert.match(source, /const toggleSidebarFromKeyboard = \(event\) => \{[\s\S]*event\.key\.toLowerCase\(\) !== 'b'[\s\S]*!\(event\.metaKey \|\| event\.ctrlKey\)[\s\S]*event\.target\?\.closest\?\.\('input, textarea, select, \[contenteditable="true"\]'\)[\s\S]*event\.preventDefault\(\)[\s\S]*sidebarCollapsed\.value = !sidebarCollapsed\.value/)
  assert.match(source, /const toggleSidebarFromKeyboard = \(event\) => \{[\s\S]*mobileMoreActive\.value[\s\S]*sidebarCollapsed\.value = !sidebarCollapsed\.value/)
  assert.match(source, /const toggleSidebarFromKeyboard = \(event\) => \{[\s\S]*event\.repeat \|\| event\.altKey \|\| event\.shiftKey[\s\S]*sidebarCollapsed\.value = !sidebarCollapsed\.value/)
  assert.match(source, /:aria-label="sidebarCollapsed \? '展开侧边栏' : '收起侧边栏'"/)
  assert.match(source, /:title="sidebarCollapsed \? '展开侧边栏' : '收起侧边栏'"/)
  assert.match(source, /\.sidebar\.collapsed :is\(\.logo, \.theme-toggle\)\s*\{ display:\s*none; \}/)
  assert.match(sourceBlock('.sidebar.collapsed .sidebar-header'), /justify-content:\s*center/)
  assert.match(sourceBlock('.sidebar.collapsed :is(.sidebar-header-actions, .collapse-btn)'), /justify-content:\s*center/)
  assert.doesNotMatch(sourceBlock('.sidebar.collapsed :is(.sidebar-header-actions, .collapse-btn)'), /display:\s*none/)
  assert.match(sourceBlock('.sidebar.collapsed .collapse-btn'), /width:\s*38px[\s\S]*height:\s*38px/)
  assert.match(sourceBlock('.sidebar.collapsed .sidebar-nav'), /padding:\s*12px 8px/)
  assert.match(sourceBlock('.sidebar.collapsed .nav-item'), /justify-content:\s*center/)
  assert.match(sourceBlock('.sidebar.collapsed .nav-item'), /padding:\s*11px 0/)
  assert.match(sourceBlock('.sidebar.collapsed .nav-item.active::after'), /content:\s*""/)
  assert.match(sourceBlock('.sidebar.collapsed .nav-item.active::after'), /left:\s*auto/)
  assert.match(sourceBlock('.sidebar.collapsed .nav-item.active::after'), /background:\s*var\(--active-indicator\)/)
  assert.match(exactSourceBlock('.sidebar.collapsed .nav-item.active:focus-visible::after'), /opacity:\s*0\.34/)
  assert.match(exactSourceBlock('.sidebar.collapsed .nav-item.active:focus-visible::after'), /transform:\s*scaleY\(0\.74\)/)
  assert.match(exactSourceBlock('.sidebar.collapsed .nav-item.active:focus-visible'), /box-shadow:\s*var\(--glass-active-shadow\),\s*var\(--focus-ring\)/)
})

test('app scroll containers expose subtle edge depth without extra markup', () => {
  assert.match(sourceBlock('.sidebar::before'), /background:\s*linear-gradient\(to bottom, var\(--bg-primary\), transparent\)/)
  assert.match(sourceBlock('.sidebar::before'), /opacity:\s*0\.16/)
  assert.match(lastSourceBlock('.sidebar-nav'), /mask-image:\s*linear-gradient\(to bottom, transparent, currentColor 12px, currentColor calc\(100% - 16px\), transparent\)/)
  assert.match(sourceBlock('.sidebar.collapsed .sidebar-nav'), /mask-image:\s*linear-gradient\(to bottom, transparent, currentColor 10px, currentColor calc\(100% - 14px\), transparent\)/)
  assert.match(sourceBlock('.main-content::before'), /background:\s*linear-gradient\(to bottom, var\(--bg-primary\), transparent\)/)
  assert.match(sourceBlock('.main-content::before'), /opacity:\s*0\.10/)
  assert.match(sourceBlock('.main-content::after'), /background:\s*linear-gradient\(to top, var\(--bg-primary\), transparent\)/)
  assert.match(sourceBlock('.main-content::after'), /position:\s*sticky/)
  assert.match(sourceBlock('.main-content::after'), /bottom:\s*0/)
  assert.match(sourceBlock('.mobile-more-sheet::before'), /background:\s*linear-gradient\(to bottom, var\(--bg-primary\), transparent\)/)
  assert.match(sourceBlock('.mobile-more-sheet::before'), /opacity:\s*0\.14/)
  assert.match(sourceBlock('.sidebar::before'), /pointer-events:\s*none/)
  assert.match(sourceBlock('.main-content::before'), /pointer-events:\s*none/)
  assert.match(sourceBlock('.main-content::after'), /pointer-events:\s*none/)
  assert.match(sourceBlock('.mobile-more-sheet::before'), /pointer-events:\s*none/)
  assert.match(sourceBlock('.mobile-more-grid'), /mask-image:\s*linear-gradient\(to bottom, transparent, currentColor 12px, currentColor calc\(100% - 14px\), transparent\)/)
})

test('app shell route families keep system navigation active on related pages', () => {
  const navStart = navigationSource.indexOf('export const navActivePaths')
  const navBlock = navigationSource.slice(navStart)

  // P2: '/library' 已被并入"影库" (= /search) 桶,让深链落到浏览而不是维护台。
  assert.match(navBlock, /'\/search':\s*\['\/search', '\/library'\]/)
  assert.match(navBlock, /'\/entities':\s*\['\/entities', '\/entity', '\/actor'\]/)
  assert.match(navBlock, /'\/downloads':\s*\['\/downloads', '\/tasks'\]/)
  assert.match(navBlock, /'\/subscription':\s*\['\/subscription', '\/subscriptions'\]/)
  assert.match(navBlock, /'\/settings':\s*\['\/settings', '\/config'\]/)
  assert.match(navBlock, /'\/logs':\s*\['\/logs', '\/log'\]/)
  assert.doesNotMatch(navBlock, /library-organize|supplement|operations/)
  assert.match(source, /const normalizedRoutePath = computed\(\(\) => route\.path\.replace\(\/\\\/\+\$\/, ''\) \|\| '\/'\)/)
  assert.match(source, /const currentPath = normalizedRoutePath\.value/)
})

test('app shell navigation exposes calm pressed states across desktop and mobile chrome', () => {
  assert.match(sourceBlock('.theme-toggle:active'), /transform:\s*translateY\(0\) scale\(0\.98\)/)
  assert.match(sourceBlock('.collapse-btn:active'), /transform:\s*scale\(0\.96\)/)
  assert.match(sourceBlock('.nav-item:active'), /transform:\s*translateY\(0\) scale\(0\.985\)/)
  assert.match(sourceBlock('.nav-item.active:active'), /box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.match(sourceBlock('.bottom-nav-item:active'), /transform:\s*scale\(0\.97\)/)
  assert.match(sourceBlock('.bottom-nav-item.active:active'), /box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.match(sourceBlock('.mobile-more-close:active'), /transform:\s*translateY\(0\) scale\(0\.96\)/)
  assert.match(sourceBlock('.mobile-theme-toggle:active'), /transform:\s*translateY\(0\) scale\(0\.985\)/)
  assert.match(sourceBlock('.mobile-more-item:active'), /transform:\s*translateY\(0\) scale\(0\.985\)/)
  assert.match(sourceBlock('.mobile-more-item.active:active'), /box-shadow:\s*var\(--glass-active-shadow\)/)
})

test('app shell respects reduced motion without removing focus or active affordances', () => {
  assert.match(source, /@media \(prefers-reduced-motion: reduce\)\s*\{[\s\S]*\.sidebar,[\s\S]*\.theme-toggle,[\s\S]*\.theme-toggle__orb,[\s\S]*\.collapse-btn,[\s\S]*\.nav-item,[\s\S]*\.nav-item svg,[\s\S]*\.bottom-nav-item,[\s\S]*\.bottom-nav-item svg,[\s\S]*\.mobile-more-overlay,[\s\S]*\.mobile-more-sheet,[\s\S]*\.mobile-more-close,[\s\S]*\.mobile-theme-toggle,[\s\S]*\.mobile-more-item,[\s\S]*\.mobile-more-enter-active,[\s\S]*\.mobile-more-leave-active,[\s\S]*\.mobile-more-enter-active \.mobile-more-sheet,[\s\S]*\.mobile-more-leave-active \.mobile-more-sheet[\s\S]*transition-duration:\s*1ms\s*!important/)
  assert.match(source, /@media \(prefers-reduced-motion: reduce\)\s*\{[\s\S]*\.bottom-nav-more::after,[\s\S]*transition-duration:\s*1ms\s*!important/)
  assert.match(source, /@media \(prefers-reduced-motion: reduce\)\s*\{[\s\S]*\.bottom-nav-item\.active::before,[\s\S]*transition-duration:\s*1ms\s*!important/)
  assert.match(source, /@media \(prefers-reduced-motion: reduce\)\s*\{[\s\S]*\.nav-item\.active::after,[\s\S]*transition-duration:\s*1ms\s*!important/)
  assert.match(source, /@media \(prefers-reduced-motion: reduce\)\s*\{[\s\S]*\.theme-toggle:hover,[\s\S]*\.nav-item:focus-visible,[\s\S]*\.nav-item\.active:focus-visible::after,[\s\S]*\.bottom-nav-item:hover svg,[\s\S]*\.bottom-nav-item\.active::before,[\s\S]*\.mobile-more-close:hover,[\s\S]*\.mobile-theme-toggle:hover,[\s\S]*\.mobile-more-item:hover,[\s\S]*\.mobile-more-enter-from \.mobile-more-sheet,[\s\S]*\.mobile-more-leave-to \.mobile-more-sheet[\s\S]*transform:\s*none\s*!important/)
})

test('mobile app shell reserves viewport space from a single bottom chrome contract', () => {
  assert.match(sourceBlock('.app-layout'), /--mobile-bottom-nav-height:\s*70px/)
  // WAVE-3 C2: Liquid Glass floating tab bar — minimum offset 20px floor and
  // stacks 12px on top of the env-driven safe area when the device reports one.
  assert.match(sourceBlock('.app-layout'), /--mobile-bottom-nav-offset:\s*max\(20px,\s*calc\(env\(safe-area-inset-bottom,\s*0px\)\s*\+\s*12px\)\)/)
  assert.match(sourceBlock('.app-layout'), /--mobile-bottom-nav-reserve:\s*calc\(var\(--mobile-bottom-nav-height\) \+ var\(--mobile-bottom-nav-offset\) \+ 12px\)/)
  assert.match(sourceBlock('.bottom-nav'), /min-height:\s*var\(--mobile-bottom-nav-height\)/)
  assert.match(sourceBlock('.bottom-nav'), /bottom:\s*var\(--mobile-bottom-nav-offset\)/)
  assert.match(sourceBlock('.bottom-nav'), /contain:\s*layout paint/)
  assert.match(lastSourceBlock('.main-content'), /padding-bottom:\s*var\(--mobile-bottom-nav-reserve\)/)
  assert.match(lastSourceBlock('.mobile-more-overlay'), /padding:\s*0 12px var\(--mobile-bottom-nav-reserve\)/)
})

test('app shell scroll and touch chrome behave like native app surfaces', () => {
  assert.match(lastSourceBlock('.sidebar-nav'), /-webkit-overflow-scrolling:\s*touch/)
  assert.match(lastSourceBlock('.sidebar-nav'), /scroll-padding-block:\s*12px 16px/)
  assert.match(exactSourceBlock('.nav-item'), /scroll-margin-block:\s*12px 16px/)
  assert.match(sourceBlock('.main-content'), /-webkit-overflow-scrolling:\s*touch/)
  assert.match(sourceBlock('.main-content'), /scroll-padding-block:\s*30px var\(--app-chrome-inset\)/)
  assert.match(lastSourceBlock('.main-content'), /scroll-padding-bottom:\s*var\(--mobile-bottom-nav-reserve\)/)
  assert.match(sourceBlock('.mobile-more-grid'), /-webkit-overflow-scrolling:\s*touch/)
  assert.match(sourceBlock('.mobile-more-grid'), /scroll-padding-block:\s*1px 10px/)
  assert.match(sourceBlock('.mobile-more-item'), /scroll-margin-block:\s*12px/)
  assert.match(source, /\.theme-toggle,\s*\.collapse-btn,\s*\.nav-item,\s*\.bottom-nav-item,\s*\.mobile-more-close,\s*\.mobile-theme-toggle,\s*\.mobile-more-item\s*\{[\s\S]*touch-action:\s*manipulation[\s\S]*-webkit-tap-highlight-color:\s*transparent/)
})

test('app shell transitions stay on composited visual properties', () => {
  const appStyle = source.slice(source.indexOf('<style scoped>'), source.indexOf('</style>'))
  const transitionLines = appStyle
    .split('\n')
    .map(line => line.trim())
    .filter(line => line.startsWith('transition:'))

  assert.ok(transitionLines.length >= 8)
  assert.equal(transitionLines.some(line => /width|height|padding|margin|left|right|top|bottom|min-width|min-height|max-height/.test(line)), false)
  assert.match(exactSourceBlock('.collapse-btn'), /transition:\s*transform var\(--motion-standard\),\s*opacity var\(--motion-fast\)/)
  assert.doesNotMatch(exactSourceBlock('.collapse-btn'), /transition:\s*var\(--transition\)/)
})

test('app shell lets the CSS build emit compatible backdrop filters', () => {
  const appStyle = source.slice(source.indexOf('<style scoped>'), source.indexOf('</style>'))

  assert.match(appStyle, /backdrop-filter:\s*blur\(var\(--glass-blur-/)
  assert.doesNotMatch(appStyle, /-webkit-backdrop-filter:/)
})
