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
  assert.match(source, /\.main-content\s*\{[\s\S]*margin:\s*var\(--app-chrome-inset\)[\s\S]*background:[\s\S]*var\(--surface-specular-edge\),[\s\S]*var\(--surface-noise\),[\s\S]*var\(--content-material\)[\s\S]*border:\s*1px solid var\(--content-material-border\)/)
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
  assert.match(source, /const navActivePaths = \{[\s\S]*'\/genres': \['\/genres', '\/discovery'\][\s\S]*'\/library-organize': \['\/library-organize', '\/inventory', '\/library', '\/duplicates', '\/normalize'\]/)
  assert.match(source, /const isNavItemActive = \(path\) => \{[\s\S]*const currentPath = normalizedRoutePath\.value[\s\S]*const activePaths = navActivePaths\[path\] \|\| \[path\][\s\S]*currentPath === activePath \|\| currentPath\.startsWith\(`\$\{activePath\}\/`\)/)
  assert.match(source, /:class="\{ active: isNavItemActive\(item\.path\) \}"/)
  assert.match(source, /:aria-current="isNavItemActive\(item\.path\) \? 'page' : undefined"/)
  assert.match(source, /const isMoreRoute = computed\(\(\) => mobileMoreItems\.value\.some\(item => isNavItemActive\(item\.path\)\)\)/)
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
  assert.match(sourceBlock('.bottom-nav-item:focus-visible'), /outline:\s*none/)
  assert.match(sourceBlock('.bottom-nav-item:focus-visible'), /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/)
})

test('app shell exposes named landmarks and isolates modal background chrome', () => {
  assert.match(source, /<aside[\s\S]*class="sidebar"[\s\S]*:inert="mobileMoreOpen \? '' : undefined"/)
  assert.match(source, /<nav class="sidebar-nav"\s+aria-label="主导航"\s+id="primary-navigation">/)
  assert.match(source, /<nav[\s\S]*class="bottom-nav"[\s\S]*aria-label="移动端主导航"[\s\S]*:inert="mobileMoreOpen \? '' : undefined"/)
  assert.match(source, /<nav class="mobile-more-grid"\s+aria-label="更多功能导航">/)
  assert.match(source, /<main[\s\S]*id="main-content"[\s\S]*class="main-content"[\s\S]*tabindex="-1"[\s\S]*aria-label="应用内容"[\s\S]*:inert="mobileMoreOpen \? '' : undefined"/)
})

test('mobile more locks the background scroll layer while the dialog is active', () => {
  assert.match(source, /<div class="app-layout" :class="\{ 'mobile-more-active': mobileMoreOpen \}">/)
  assert.match(sourceBlock('.app-layout.mobile-more-active .main-content'), /overflow:\s*hidden/)
})

test('keyboard entry points expose visible system focus surfaces', () => {
  assert.match(sourceBlock('.theme-toggle:focus-visible'), /outline:\s*none/)
  assert.match(sourceBlock('.theme-toggle:focus-visible'), /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/)
  assert.match(sourceBlock('.skip-link:focus-visible'), /color:\s*var\(--text-primary\)/)
  assert.match(sourceBlock('.skip-link:focus-visible'), /background:[\s\S]*var\(--glass-active-material\)/)
  assert.match(sourceBlock('.skip-link:focus-visible'), /border:\s*1px solid var\(--glass-active-border\)/)
  assert.match(sourceBlock('.skip-link:focus-visible'), /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\) saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(sourceBlock('.skip-link:focus-visible'), /box-shadow:\s*var\(--glass-active-shadow\),\s*var\(--focus-ring\)/)
  assert.match(sourceBlock('.skip-link:focus-visible'), /transform:\s*translateY\(0\)/)
  assert.match(sourceBlock('.main-content:focus-visible'), /outline:\s*none/)
  assert.match(sourceBlock('.main-content:focus-visible'), /box-shadow:\s*var\(--glass-surface-shadow\),\s*var\(--focus-ring\)/)
  assert.match(sourceBlock('.mobile-more-sheet:focus-visible'), /outline:\s*none/)
  assert.match(sourceBlock('.mobile-more-sheet:focus-visible'), /box-shadow:\s*var\(--shadow-sheet\),\s*var\(--focus-ring\)/)
})

test('mobile more dialog owns keyboard focus and dismisses like system chrome', () => {
  assert.match(source, /ref="mobileMoreButtonRef"/)
  assert.match(source, /ref="mobileMoreSheetRef"/)
  assert.match(source, /class="mobile-more-sheet"[\s\S]*tabindex="-1"[\s\S]*@keydown\.esc\.stop\.prevent="closeMobileMore\(\{ restoreFocus: true \}\)"/)
  assert.match(source, /@click\.self="closeMobileMore\(\{ restoreFocus: true \}\)"/)
  assert.match(source, /@click="closeMobileMore\(\{ restoreFocus: true \}\)">/)
  assert.match(source, /const toggleMobileMore = \(\) => \{[\s\S]*mobileMoreOpen\.value = !mobileMoreOpen\.value[\s\S]*\}/)
  assert.match(source, /const closeMobileMore = \(\{ restoreFocus = false, focusMain = false \} = \{\}\) => \{[\s\S]*mobileMoreOpen\.value = false[\s\S]*if \(restoreFocus\) nextTick\(\(\) => mobileMoreButtonRef\.value\?\.focus\(\)\)/)
  assert.match(source, /watch\(mobileMoreOpen, async \(isOpen\) => \{[\s\S]*await nextTick\(\)[\s\S]*mobileMoreSheetRef\.value\?\.focus\(\)/)
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
  assert.match(source, /const trapMobileMoreFocus = \(event\) => \{[\s\S]*if \(!mobileMoreOpen\.value\) return[\s\S]*const focusable = mobileMoreFocusableElements\(\)[\s\S]*event\.shiftKey[\s\S]*event\.preventDefault\(\)[\s\S]*(?:last|first)\.focus\(\)/)
  assert.match(source, /trapMobileMoreFocus,/)
})

test('mobile more trigger is explicitly bound to the dialog surface', () => {
  assert.match(source, /class="bottom-nav-item bottom-nav-more"[\s\S]*:aria-label="mobileMoreOpen \? '关闭更多功能' : '打开更多功能'"/)
  assert.match(source, /class="bottom-nav-item bottom-nav-more"[\s\S]*aria-controls="mobile-more-dialog"/)
  assert.match(source, /:class="\{ active: isMoreRoute, open: mobileMoreOpen \}"/)
  assert.doesNotMatch(source, /:class="\{ active: mobileMoreOpen \|\| isMoreRoute \}"/)
  assert.match(sourceBlock('.bottom-nav-more.open:not(.active)'), /background:[\s\S]*var\(--material-glass-control-hover\)/)
  assert.match(source, /class="mobile-more-sheet"[\s\S]*id="mobile-more-dialog"[\s\S]*role="dialog"/)
})

test('route changes dismiss mobile more through the shared close handler', () => {
  const watchStart = source.indexOf('watch(() => route.fullPath')
  const watchEnd = source.indexOf('const navGroups', watchStart)
  const routeWatchBlock = source.slice(watchStart, watchEnd)

  assert.match(routeWatchBlock, /closeMobileMore\(\{ focusMain: true \}\)/)
  assert.doesNotMatch(routeWatchBlock, /mobileMoreOpen\.value\s*=\s*false/)
})

test('mobile more route selection returns keyboard focus to app content', () => {
  assert.match(source, /class="mobile-more-item"[\s\S]*@click="closeMobileMore\(\{ focusMain: true \}\)"/)
  assert.match(source, /const closeMobileMore = \(\{ restoreFocus = false, focusMain = false \} = \{\}\) => \{[\s\S]*if \(focusMain\) focusMainContent\(\)/)
})

test('mobile more dismisses when the shell leaves the mobile breakpoint', () => {
  assert.match(source, /window\.matchMedia\?\.\('\(max-width: 768px\)'\)/)
  assert.match(source, /const closeMobileMoreOutsideMobile = \(\{ matches \}\) => \{[\s\S]*if \(!matches\) closeMobileMore\(\{ focusMain: true \}\)[\s\S]*\}/)
  assert.match(source, /mobileShellBreakpoint\?\.addEventListener\?\.\('change', closeMobileMoreOutsideMobile\)/)
  assert.match(source, /mobileShellBreakpoint\?\.removeEventListener\?\.\('change', closeMobileMoreOutsideMobile\)/)
})

test('primary shell route links return keyboard focus to app content', () => {
  assert.match(source, /class="skip-link"[\s\S]*@click\.prevent="focusMainContent"/)
  assert.match(source, /class="nav-item"[\s\S]*@click="focusMainContent"/)
  assert.match(source, /class="bottom-nav-item"[\s\S]*@click="focusMainContent"/)
  assert.match(source, /const focusMainContent = \(\) => nextTick\(\(\) => requestAnimationFrame\(\(\) => document\.getElementById\('main-content'\)\?\.focus\(\{ preventScroll: true \}\)\)\)/)
})

test('mobile more tab trap loops focus when starting outside actionable controls', () => {
  assert.match(source, /const activeIndex = focusable\.indexOf\(document\.activeElement\)/)
  assert.match(source, /if \(activeIndex === -1\) \{[\s\S]*event\.preventDefault\(\)[\s\S]*\(event\.shiftKey \? last : first\)\.focus\(\)[\s\S]*return/)
  assert.match(source, /event\.shiftKey && activeIndex === 0/)
  assert.match(source, /!event\.shiftKey && activeIndex === focusable\.length - 1/)
})

test('collapsed sidebar keeps icon rail navigation named and visually centered', () => {
  assert.match(source, /:aria-label="sidebarCollapsed \? item\.label : undefined"/)
  assert.match(source, /:title="sidebarCollapsed \? item\.label : undefined"/)
  assert.match(source, /<nav class="sidebar-nav"\s+aria-label="主导航"\s+id="primary-navigation">/)
  assert.match(source, /aria-controls="primary-navigation"/)
  assert.match(source, /:aria-expanded="!sidebarCollapsed"/)
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
  assert.match(sourceBlock('.sidebar.collapsed .nav-item.active::after'), /background:\s*var\(--active-indicator\)/)
})

test('app scroll containers expose subtle edge depth without extra markup', () => {
  assert.match(sourceBlock('.sidebar::before'), /background:\s*linear-gradient\(to bottom, var\(--bg-primary\), transparent\)/)
  assert.match(sourceBlock('.sidebar::before'), /opacity:\s*0\.16/)
  assert.match(sourceBlock('.main-content::before'), /background:\s*linear-gradient\(to bottom, var\(--bg-primary\), transparent\)/)
  assert.match(sourceBlock('.main-content::before'), /opacity:\s*0\.10/)
  assert.match(sourceBlock('.mobile-more-sheet::before'), /background:\s*linear-gradient\(to bottom, var\(--bg-primary\), transparent\)/)
  assert.match(sourceBlock('.mobile-more-sheet::before'), /opacity:\s*0\.14/)
  assert.match(sourceBlock('.sidebar::before'), /pointer-events:\s*none/)
  assert.match(sourceBlock('.main-content::before'), /pointer-events:\s*none/)
  assert.match(sourceBlock('.mobile-more-sheet::before'), /pointer-events:\s*none/)
})

test('app shell route families keep system navigation active on related pages', () => {
  const navStart = source.indexOf('const navActivePaths')
  const navEnd = source.indexOf('const isNavItemActive', navStart)
  const navBlock = source.slice(navStart, navEnd)

  assert.match(navBlock, /'\/search':\s*\['\/search', '\/actor'\]/)
  assert.match(navBlock, /'\/downloads':\s*\['\/downloads', '\/tasks'\]/)
  assert.match(navBlock, /'\/entities':\s*\['\/entities', '\/entity'\]/)
  assert.match(navBlock, /'\/subscription':\s*\['\/subscription', '\/subscriptions'\]/)
  assert.match(navBlock, /'\/supplement':\s*\['\/supplement', '\/supplement\/actor'\]/)
  assert.match(navBlock, /'\/settings':\s*\['\/settings', '\/config'\]/)
  assert.match(navBlock, /'\/logs':\s*\['\/logs', '\/log'\]/)
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
  assert.match(source, /@media \(prefers-reduced-motion: reduce\)\s*\{[\s\S]*\.theme-toggle:hover,[\s\S]*\.nav-item:focus-visible,[\s\S]*\.bottom-nav-item:hover svg,[\s\S]*\.mobile-more-close:hover,[\s\S]*\.mobile-theme-toggle:hover,[\s\S]*\.mobile-more-item:hover,[\s\S]*\.mobile-more-enter-from \.mobile-more-sheet,[\s\S]*\.mobile-more-leave-to \.mobile-more-sheet[\s\S]*transform:\s*none\s*!important/)
})

test('mobile app shell reserves viewport space from a single bottom chrome contract', () => {
  assert.match(sourceBlock('.app-layout'), /--mobile-bottom-nav-height:\s*70px/)
  assert.match(sourceBlock('.app-layout'), /--mobile-bottom-nav-offset:\s*max\(10px,\s*env\(safe-area-inset-bottom,\s*0px\)\)/)
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
  assert.match(sourceBlock('.main-content'), /-webkit-overflow-scrolling:\s*touch/)
  assert.match(sourceBlock('.main-content'), /scroll-padding-block:\s*30px var\(--app-chrome-inset\)/)
  assert.match(lastSourceBlock('.main-content'), /scroll-padding-bottom:\s*var\(--mobile-bottom-nav-reserve\)/)
  assert.match(sourceBlock('.mobile-more-grid'), /-webkit-overflow-scrolling:\s*touch/)
  assert.match(sourceBlock('.mobile-more-grid'), /scroll-padding-block:\s*1px 10px/)
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
