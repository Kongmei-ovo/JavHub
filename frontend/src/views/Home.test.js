import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const vueSource = readFileSync(new URL('./Home.vue', import.meta.url), 'utf8')
const externalStyle = readFileSync(new URL('../features/home/home.css', import.meta.url), 'utf8')
// Wave P1-3: 下载候选 tab 已彻底剥离;候选行为由 Candidates.vue/useDownloadCandidates 覆盖。
// 这里只针对 Home 留下的真实任务 + 下载源 两条线断言,候选样式断言读 home.css 即可。
const source = `${vueSource}\n${externalStyle}`

function cssBlocks(content, selector) {
  const searchable = content.replace(/\/\*[\s\S]*?\*\//g, '')
  const blocks = [...searchable.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
    .filter(([, selectors]) => selectors
      .split(',')
      .map(part => part.trim())
      .includes(selector))
    .map(([, , block]) => block)
  assert.ok(blocks.length, `${selector} block should exist`)
  return blocks
}

function cssBlock(content, selector) {
  return cssBlocks(content, selector).join('\n')
}

function backgroundIncludes(token) {
  return new RegExp(`background:[\\s\\S]*var\\(--${token}\\)`)
}

function layeredSemanticBackground(token) {
  return new RegExp(`background:\\s*var\\(--surface-specular-edge\\),\\s*var\\(--surface-noise\\),\\s*var\\(--${token}\\)`)
}

function assertGlassControl(block, label) {
  assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/, `${label} should use the shared glass border`)
  assert.match(block, backgroundIncludes('material-glass-control'), `${label} should use the shared glass control material`)
  assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/, `${label} should use the shared control shadow`)
  assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/, `${label} should use shared control blur`)
}

function assertGlassControlHover(block, label) {
  assert.match(block, backgroundIncludes('material-glass-control-hover'), `${label} should use the shared hover material`)
  assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/, `${label} should use the shared hover border`)
  assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\)/, `${label} should use the shared hover shadow`)
}

function assertGlassSubtle(block, label) {
  assert.match(block, backgroundIncludes('material-glass-subtle'), `${label} should use the shared subtle material`)
  assert.match(block, /var\(--surface-specular-edge/, `${label} should include a specular edge layer`)
  assert.match(block, /var\(--surface-noise\)/, `${label} should include the shared noise layer`)
}

function singleLayerGlassBackgrounds(css) {
  return css
    .split('\n')
    .map((line, index) => ({ line: index + 1, text: line.trim() }))
    .filter(({ text }) => /^background:\s*var\(--(?:material-glass-subtle|material-glass-control|material-glass-control-hover|material-glass-sheet|glass-active-material)\);$/.test(text))
}

test('home lazy-loads downloader management outside the base downloads chunk', () => {
  assert.match(source, /import \{[^}]*\bdefineAsyncComponent\b[^}]*\} from 'vue'/)
  assert.match(source, /const DownloaderManagementPanel = defineAsyncComponent\(\(\) => import\('\.\.\/features\/downloaders\/DownloaderManagementPanel\.vue'\)\)/)
  assert.match(source, /components:\s*\{[^}]*DownloadStatsBar[^}]*TaskList[^}]*DownloaderManagementPanel[^}]*\}/)
  assert.match(source, /<DownloaderManagementPanel[\s\S]*v-if="activeTab === 'downloaders'"/)
  assert.doesNotMatch(source, /<div\s+v-else-if="activeTab === 'downloaders'"\s+class="downloaders-panel apple-reveal"/)
})

test('home delegates task empty state actions through the task list component', () => {
  assert.match(vueSource, /import TaskList from '\.\.\/features\/home\/TaskList\.vue'/)
  assert.match(vueSource, /<TaskList[\s\S]*v-else-if="activeTab === 'tasks'"/)
  assert.match(vueSource, /:task-empty-primary-label="taskEmptyPrimaryLabel"/)
  assert.match(vueSource, /@empty-action="handleTaskEmptyAction"/)
  assert.match(vueSource, /@parse="\$router\.push\('\/parse'\)"/)
  assert.match(vueSource, /taskEmptyPrimaryLabel\(\)/)
  assert.match(vueSource, /handleTaskEmptyAction\(\)[\s\S]*this\.clearTaskStatus\(\)[\s\S]*this\.openCandidatePreset\(\{ status: 'candidate', source: '' \}\)[\s\S]*this\.\$router\.push\('\/search'\)/)
})

test('home is collapsed to download tasks plus downloader sources', () => {
  // P1-3: 候选 tab + DownloadCandidatePanel + useDownloadCandidates 接线全部下线。
  assert.doesNotMatch(vueSource, /DownloadCandidatePanel/)
  assert.doesNotMatch(vueSource, /useDownloadCandidates/)
  assert.doesNotMatch(vueSource, /activeTab === 'candidates'/)
  assert.doesNotMatch(vueSource, /openCandidateTab/)
  assert.doesNotMatch(vueSource, /<h1>下载管理<\/h1>/)
  assert.match(vueSource, /<h1>下载任务<\/h1>/)
  assert.match(vueSource, /openTaskTab/)
  assert.match(vueSource, /openDownloaderTab/)
})

test('home reroutes legacy /downloads?tab=candidates deep links to /candidates', () => {
  assert.match(vueSource, /if \(this\.\$route\.query\.tab === 'candidates'\)/)
  assert.match(vueSource, /this\.\$router\.replace\(\{ path: '\/candidates', query: this\.candidateRedirectQuery/)
  assert.match(vueSource, /candidateRedirectQuery\(query = \{\}\)/)
})

test('home composes the download dashboard from focused home feature components', () => {
  assert.match(vueSource, /import DownloadStatsBar from '\.\.\/features\/home\/DownloadStatsBar\.vue'/)
  assert.match(vueSource, /import TaskList from '\.\.\/features\/home\/TaskList\.vue'/)
  assert.match(vueSource, /components:\s*\{[^}]*DownloadStatsBar[^}]*TaskList[^}]*DownloaderManagementPanel[^}]*\}/)
  assert.match(vueSource, /<DownloadStatsBar[\s\S]*:stats="stats"[\s\S]*:candidate-stats="candidateStats"[\s\S]*@select-status="setTaskStatus"[\s\S]*@open-preset="openCandidatePreset"/)
  assert.match(vueSource, /<TaskList[\s\S]*v-else-if="activeTab === 'tasks'"[\s\S]*:tasks="filteredTasks"[\s\S]*@retry="retry"[\s\S]*@remove="remove"/)
  assert.doesNotMatch(vueSource, /class="stats-bar"/)
  assert.doesNotMatch(vueSource, /class="candidate-overview"/)
  assert.doesNotMatch(vueSource, /v-for="task in filteredTasks"/)
})

test('home stat strip openCandidatePreset routes to /candidates with filter passthrough', () => {
  assert.match(vueSource, /openCandidatePreset\(preset = \{\}\)/)
  assert.match(vueSource, /this\.\$router\.push\(\{ path: '\/candidates', query: cleanObject\(query\) \}\)/)
  assert.match(vueSource, /if \(preset\.needs_magnet === true\) query\.needs_magnet = '1'/)
  assert.match(vueSource, /else if \(preset\.needs_magnet === false\) query\.needs_magnet = '0'/)
})

test('home page keeps heavyweight styles in external scoped stylesheets', () => {
  assert.match(vueSource, /<style scoped src="\.\.\/features\/home\/home\.css"><\/style>/)
  assert.ok(externalStyle.length > 8000, 'external home stylesheet should carry the base workspace CSS')
  assert.ok(vueSource.split('\n').length < 400, 'Home.vue should stay small enough to review and parse quickly')
})

test('home tab controls use shared Apple glass tokens', () => {
  const downloadTabs = cssBlock(source, '.download-tabs')
  const tabButton = cssBlock(source, '.tab-btn')
  const tabHover = cssBlock(source, '.tab-btn:hover')
  const tabActive = cssBlock(source, '.tab-btn.active')
  const tabBadge = cssBlock(source, '.tab-badge')
  const tabBadgeSubtle = cssBlock(source, '.tab-badge.subtle')

  assert.match(downloadTabs, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(downloadTabs, backgroundIncludes('material-glass-sheet'))
  assert.match(downloadTabs, /box-shadow:\s*var\(--glass-inner-shadow\)/)

  for (const block of [tabButton]) {
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/)
    assert.match(block, backgroundIncludes('material-glass-control'))
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
    assert.doesNotMatch(block, /border:\s*(?:0|none|1px solid transparent)/)
    assert.doesNotMatch(block, /background:\s*(?:transparent|none)/)
  }

  for (const block of [tabHover]) {
    assert.match(block, backgroundIncludes('material-glass-control-hover'))
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  }

  for (const block of [tabActive]) {
    assert.match(block, backgroundIncludes('glass-active-material'))
    assert.match(block, /border-color:\s*var\(--glass-active-border\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-active-shadow\)/)
  }

  assert.match(tabBadge, layeredSemanticBackground('badge-error-bg'))
  assert.match(tabBadge, /color:\s*var\(--badge-error-text\)/)
  assert.match(tabBadge, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(tabBadge, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(tabBadgeSubtle, layeredSemanticBackground('badge-success-bg'))
  assert.match(tabBadgeSubtle, /color:\s*var\(--badge-success-text\)/)

  for (const block of [
    downloadTabs,
    tabButton,
    tabActive,
    tabBadge,
    tabBadgeSubtle,
  ]) {
    assert.doesNotMatch(block, /rgba\(255,\s*255,\s*255|rgba\(255,255,255|#fff|#ffffff/i)
  }
})

test('home tab controls mirror hover glass treatment for keyboard focus', () => {
  const tabFocus = cssBlock(source, '.tab-btn:focus-visible')

  assert.match(tabFocus, /outline:\s*none/, 'download tab focus should replace the default outline')
  assert.match(tabFocus, backgroundIncludes('material-glass-control-hover'))
  assert.match(tabFocus, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(tabFocus, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/)

  assert.match(tabFocus, /color:\s*var\(--text-primary\)/)
})

test('home dashboard and task surfaces use shared Apple glass materials', () => {
  // P1-3 后 Home 只剩 stat 卡 / 任务列表 / 下载源面板,候选金属面 (.action-chip / .candidate-metric)
  // 与 .candidate-filter-ledger 由 Candidates.vue 接走,这里只校验仍属于 Home 的玻璃表面 token。
  const statCard = cssBlock(source, '.stat-card')
  const statCardHover = cssBlock(source, '.stat-card:hover')
  const filterBar = cssBlock(source, '.filter-bar')
  const filterBarHover = cssBlock(source, '.filter-bar:hover')
  const statIcon = cssBlock(source, '.stat-icon')
  const taskCover = cssBlock(source, '.task-cover')
  const coverPlaceholder = cssBlock(source, '.cover-placeholder')
  const coverOverlay = cssBlock(source, '.cover-overlay')
  const coverCode = cssBlock(source, '.cover-code')
  const taskActions = cssBlock(source, '.task-actions')
  const taskError = cssBlock(source, '.task-error')

  for (const [block, label] of [
    [statCard, 'stat cards'],
    [filterBar, 'filter bar'],
    [taskCover, 'task covers'],
    [coverPlaceholder, 'cover placeholders'],
  ]) {
    assertGlassControl(block, label)
    assert.doesNotMatch(block, /var\(--surface-control\)|var\(--bg-card\)|var\(--bg-secondary\)|var\(--border-light\)|rgba\(255,\s*255,\s*255|#fff|#ffffff/i)
  }

  for (const [block, label] of [
    [statCardHover, 'stat card hover'],
    [filterBarHover, 'filter bar hover'],
  ]) {
    assertGlassControlHover(block, label)
    assert.doesNotMatch(block, /var\(--surface-control-hover\)|var\(--border-light\)/)
  }

  assertGlassSubtle(statIcon, 'stat icon')
  assert.match(statIcon, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(statIcon, /box-shadow:\s*var\(--glass-control-shadow\)/)

  assert.match(coverOverlay, /--home-cover-scrim-clear:\s*var\(--media-caption-scrim-clear\)/)
  assert.match(coverOverlay, /--home-cover-scrim-strong:\s*var\(--media-caption-scrim-strong\)/)
  assert.match(coverOverlay, /background:\s*linear-gradient\(180deg,\s*var\(--home-cover-scrim-clear\),\s*var\(--home-cover-scrim-strong\)\)/)
  assert.doesNotMatch(coverOverlay, /rgba\(0,\s*0,\s*0|rgba\(0,0,0|#000|#000000/i)
  assert.match(coverCode, /color:\s*var\(--media-caption-text\)/)
  assert.doesNotMatch(coverCode, /color:\s*white|#fff|#ffffff/i)

  assert.match(taskActions, /border-top:\s*1px solid var\(--glass-control-border\)/)
  assert.doesNotMatch(taskActions, /var\(--border\)/)

  assert.match(taskError, /color:\s*var\(--badge-error-text\)/)
  assert.doesNotMatch(`${taskError}`, /#ef5350|#EF5350/)
})

test('home glass backgrounds are layered with specular and noise surfaces', () => {
  assert.deepEqual(singleLayerGlassBackgrounds(externalStyle), [])
})
