import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { THEMES, THEME_KEYS, applyTheme, resolveThemeKey } from '../assets/themes.js'

const subscription = readFileSync(new URL('./Subscription.vue', import.meta.url), 'utf8')
const normalize = readFileSync(new URL('./Normalize.vue', import.meta.url), 'utf8')
const inventory = readFileSync(new URL('./Inventory.vue', import.meta.url), 'utf8')
const inventoryActor = readFileSync(new URL('./InventoryActor.vue', import.meta.url), 'utf8')
const home = readFileSync(new URL('./Home.vue', import.meta.url), 'utf8')
const operations = readFileSync(new URL('./Operations.vue', import.meta.url), 'utf8')
const config = readFileSync(new URL('./Config.vue', import.meta.url), 'utf8')
const genres = readFileSync(new URL('./Genres.vue', import.meta.url), 'utf8')
const search = readFileSync(new URL('./Search.vue', import.meta.url), 'utf8')
const magnetParse = readFileSync(new URL('./MagnetParse.vue', import.meta.url), 'utf8')
const apiSource = readFileSync(new URL('../api/index.js', import.meta.url), 'utf8')
const app = readFileSync(new URL('../App.vue', import.meta.url), 'utf8')

test('navigation and actor page use actor mapping language', () => {
  assert.match(app, /演员映射/)
  assert.doesNotMatch(app, /演员合并/)
  assert.match(normalize, /演员映射/)
  assert.match(normalize, /listUnmappedActors/)
  assert.match(normalize, /confirmActorMapping/)
  assert.match(normalize, /ignoreActorMapping/)
  assert.match(normalize, /getActorMappingSummary/)
  assert.match(normalize, /mappingActor/)
  assert.match(normalize, /置信/)
})

test('subscription routes missing movies into download candidates', () => {
  assert.match(subscription, /createDownloadCandidate/)
  assert.match(subscription, /查看候选/)
  assert.match(subscription, /candidate_count/)
  assert.match(subscription, /待补磁力/)
  assert.match(subscription, /新增/)
  assert.match(subscription, /existing/)
  assert.match(subscription, /include_supplement: '1'/)
  assert.doesNotMatch(subscription, /api\.createDownload\(\{ code:/)
})

test('inventory page shows mapping coverage and candidate handoff', () => {
  assert.match(inventory, /映射覆盖率/)
  assert.match(inventory, /处理未映射演员/)
  assert.match(inventory, /映射建议/)
  assert.match(inventory, /source: 'inventory'/)
  assert.match(inventory, /getActorMappingSummary/)
  assert.match(inventory, /job\.result\.unmapped/)
  assert.match(inventory, /候选/)
  assert.match(inventoryActor, /转为候选/)
  assert.match(inventoryActor, /createDownloadCandidate/)
  assert.match(inventoryActor, /查看库存下载候选/)
  assert.match(inventoryActor, /已映射到 JavInfo/)
  assert.match(inventoryActor, /未映射到 JavInfo/)
})

test('default theme controls avoid white-on-white primary buttons', () => {
  assert.doesNotMatch(inventory, /\.btn-primary\s*\{[^}]*color:\s*#fff/s)
  assert.doesNotMatch(normalize, /\.btn-primary\s*\{[^}]*color:\s*#fff/s)
  assert.doesNotMatch(search, /\.btn-primary\s*\{/)
  assert.match(inventory, /class="btn btn-primary"/)
  assert.match(normalize, /class="btn btn-primary"/)
  assert.match(inventory, /var\(--badge-warning-bg\)/)
  assert.match(inventory, /var\(--badge-success-bg\)/)
})

test('mobile navigation and settings tabs stay compact', () => {
  const bottomNavStart = app.indexOf('const bottomNavItems')
  const bottomNavEnd = app.indexOf('])', bottomNavStart)
  const bottomNavBlock = app.slice(bottomNavStart, bottomNavEnd)
  assert.equal((bottomNavBlock.match(/\{ path:/g) || []).length, 4)
  assert.doesNotMatch(bottomNavBlock, /label: '订阅'/)
  assert.doesNotMatch(bottomNavBlock, /label: '库存'/)
  assert.match(app, /const mobileMoreItems/)
  assert.match(app, /label: '磁链解析'/)
  assert.match(app, /label: '补全管理'/)
  assert.match(app, /bottom-nav-more/)
  assert.match(config, /scroll-snap-type: x proximity/)
  assert.match(config, /settings-footer[\s\S]*left: var\(--sidebar-width\)/)
  assert.match(config, /footer-content \.btn[\s\S]*width: 100%/)
})

test('external data failures render page-level retry states', () => {
  assert.match(genres, /AppleErrorState/)
  assert.match(genres, /categoryError/)
  assert.match(genres, /reloadGenreData/)
  assert.match(apiSource, /silentError: true/)
  assert.match(app, /label: '设置'/)
})

test('inline style cleanup keeps only dynamic previews in settings and genres', () => {
  assert.doesNotMatch(magnetParse, /(^|[\s<])style="/)
  assert.doesNotMatch(home, /(^|[\s<])style="/)
  assert.doesNotMatch(config, /(^|[\s<])style="/)
  assert.match(config, /theme-card-preview theme-swatch[\s\S]*:style="themeSwatchStyle\(theme\)"/)
  assert.match(config, /preview-bubble[\s\S]*:style="previewBubbleStyle\(index\)"/)
  assert.match(config, /legendary-dot" :style/)
  assert.match(genres, /:style="cloudStyle"/)
  assert.match(genres, /:style="bubbleStyle\(tag\)"/)
})

test('appearance controls keep compact state and robust custom material parsing', () => {
  assert.match(config, /class="theme-option"[\s\S]*:aria-pressed="currentTheme === key"/)
  assert.match(config, /class="segmented-mini"[\s\S]*:aria-pressed="config\.javinfo\.page_size === size"/)
  assert.match(config, /function parseGradientList/)
  assert.match(config, /char === ',' && depth === 0/)
  assert.match(config, /this\.bubbleCfg\.customGradients = parseGradientList\(this\.bubbleCfg\.customGradientsText\)/)
  assert.doesNotMatch(config, /customGradientsText[\s\S]{0,120}\.split\(',/)
})

test('theme presets stay curated and complete', () => {
  assert.deepEqual(THEME_KEYS, ['midnight', 'studio-silver', 'oled', 'deep-space', 'graphite-gold'])

  const baselineTokens = Object.keys(THEMES.midnight.vars).sort()
  for (const [key, theme] of Object.entries(THEMES)) {
    assert.deepEqual(Object.keys(theme.vars).sort(), baselineTokens, `${key} token coverage should match midnight`)
    assert.match(theme.vars['--font-body'], /Inter/)
    assert.match(theme.vars['--font-body'], /-apple-system/)
    assert.doesNotMatch(theme.vars['--font-body'], /Cormorant|Noto|Space Grotesk|Nunito/i)
    assert.doesNotMatch(theme.vars['--font-body'], /(^|,\s*)'?serif'?($|,)/i)
  }

  for (const removed of ['forest', 'tokyo', 'aurora', 'rose']) {
    assert.equal(THEMES[removed], undefined)
  }
})

test('legacy saved theme values resolve to curated themes', () => {
  assert.equal(resolveThemeKey('forest'), 'midnight')
  assert.equal(resolveThemeKey('tokyo'), 'deep-space')
  assert.equal(resolveThemeKey('aurora'), 'deep-space')
  assert.equal(resolveThemeKey('rose'), 'graphite-gold')
  assert.equal(resolveThemeKey('missing-theme'), 'midnight')

  const writes = []
  const originalDocument = globalThis.document
  const originalLocalStorage = globalThis.localStorage
  globalThis.document = {
    documentElement: {
      style: {
        setProperty: () => {},
      },
    },
  }
  globalThis.localStorage = {
    setItem: (key, value) => writes.push([key, value]),
  }

  try {
    assert.equal(applyTheme('tokyo'), 'deep-space')
    assert.deepEqual(writes.at(-1), ['javhub_theme', 'deep-space'])
  } finally {
    if (originalDocument === undefined) {
      delete globalThis.document
    } else {
      globalThis.document = originalDocument
    }
    if (originalLocalStorage === undefined) {
      delete globalThis.localStorage
    } else {
      globalThis.localStorage = originalLocalStorage
    }
  }
})

test('magnet parser regex is stateless across multiple lines', () => {
  assert.match(magnetParse, /const magnetRE = .*\/i/)
  assert.doesNotMatch(magnetParse, /const magnetRE = .*\/g[i]?/)
  assert.match(magnetParse, /magnet:\\\?xt=urn:btih:\(\[A-Fa-f0-9\]\+\)/)
})

test('download page exposes candidate approval workflow', () => {
  assert.match(home, /下载候选/)
  assert.match(home, /待补磁力/)
  assert.match(home, /approveDownloadCandidate/)
  assert.match(home, /rejectDownloadCandidate/)
  assert.match(home, /updateDownloadCandidateMagnet/)
  assert.match(home, /bulkRejectDownloadCandidates/)
  assert.match(home, /批量恢复/)
  assert.match(home, /搜索番号、标题、演员/)
  assert.match(home, /syncCandidateRoute/)
  assert.match(home, /by_source/)
  assert.match(home, /全部来源/)
  assert.match(home, /candidateFilter\.source === 'supplement'/)
  assert.match(home, /candidateSourceLabel/)
  assert.match(home, /补全/)
  assert.match(home, /candidate-overview/)
  assert.match(home, /待确认候选/)
  assert.match(home, /订阅发现/)
  assert.match(home, /库存发现/)
  assert.match(home, /补全发现/)
  assert.match(home, /candidate_by_source/)
  assert.match(home, /readyCandidateCount/)
  assert.match(home, /openCandidatePreset/)
  assert.match(home, /goCandidateActor/)
  assert.match(home, /goCandidateSupplement/)
  assert.match(home, /最近动作/)
  assert.match(home, /最近处理/)
  assert.match(home, /loadCandidateRuns/)
  assert.match(home, /applyCandidateRunFilters/)
  assert.match(home, /retryFailedCandidateRun/)
  assert.match(home, /retryDownloadCandidateRunFailed/)
  assert.match(home, /listDownloadCandidateRuns/)
  assert.match(home, /失败队列/)
  assert.match(home, /重试失败/)
  assert.match(home, /dry_run: true/)
  assert.match(home, /processPreviewMessage/)
  assert.match(home, /processPreviewDetails/)
  assert.match(home, /预演中/)
  assert.match(home, /error_msg/)
  assert.match(home, /已关联任务/)
  assert.match(home, /重试/)
})

test('operations overview exposes candidate automation controls', () => {
  assert.match(operations, /立即运行/)
  assert.match(operations, /runCandidateProcessingNow/)
  assert.match(operations, /candidateSchedule/)
  assert.match(operations, /scheduleStatusLabel/)
  assert.match(operations, /下一次/)
  assert.match(operations, /候选处理正在运行/)
})

test('settings page blocks saving until remote config has loaded', () => {
  assert.match(config, /configLoading: true/)
  assert.match(config, /configLoaded: false/)
  assert.match(config, /configLoadError: ''/)
  assert.match(config, /async loadConfig\(\)/)
  assert.match(config, /canSaveConfig\(\)/)
  assert.match(config, /v-else-if="configLoadError"/)
  assert.match(config, /v-if="canSaveConfig" class="settings-footer"/)
  assert.match(config, /保存已暂停以避免覆盖现有设置/)
  assert.match(config, /if \(!this\.canSaveConfig\)[\s\S]*已阻止保存/)
  assert.match(config, /:disabled="testingTelegram \|\| !canSaveConfig \|\| !config\.telegram\.bot_token"/)
  assert.match(config, /@retry="loadConfig"/)
  assert.match(config, /max_auto_downloads_per_run/)
  assert.match(config, /max_auto_downloads_per_24h/)
})

test('interactive filters avoid stale actions and stale pagination', () => {
  assert.match(search, /this\.clearSort\(\{ search: false \}\)/)
  assert.match(search, /clearSort\(\{ search = true \} = \{\}\)/)
  assert.match(genres, /this\.categoryError = ''[\s\S]*this\.displayedTags = this\.shuffledTags/)
  assert.match(genres, /if \(!this\.categories\.length && !this\.loading\) this\.categoryError = 'stats_failed'/)
})

test('download mutations are guarded by in-flight state', () => {
  assert.match(home, /bulkCandidateLoading: false/)
  assert.match(home, /candidateMutations: \{\}/)
  assert.match(home, /retryingTasks: \{\}/)
  assert.match(home, /isCandidateMutating\(id\)/)
  assert.match(home, /this\.setCandidateMutation\(candidate\.id, 'approve'\)/)
  assert.match(home, /this\.clearCandidateMutation\(candidate\.id\)/)
  assert.match(home, /if \(this\.selectedCandidateIds\.length === 0 \|\| this\.bulkCandidateLoading\) return/)
  assert.match(home, /async retry\(task\)/)
  assert.match(home, /await api\.createDownload/)
  assert.match(home, /await this\.loadTasks\(\)/)
})
