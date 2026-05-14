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
const favorites = readFileSync(new URL('./Favorites.vue', import.meta.url), 'utf8')
const actor = readFileSync(new URL('./Actor.vue', import.meta.url), 'utf8')
const config = readFileSync(new URL('./Config.vue', import.meta.url), 'utf8')
const configDefaults = readFileSync(new URL('../features/config/configDefaults.js', import.meta.url), 'utf8')
const genres = readFileSync(new URL('./Genres.vue', import.meta.url), 'utf8')
const search = readFileSync(new URL('./Search.vue', import.meta.url), 'utf8')
const discoveryDetail = readFileSync(new URL('./DiscoveryDetail.vue', import.meta.url), 'utf8')
const supplement = readFileSync(new URL('./SupplementManagement.vue', import.meta.url), 'utf8')
const supplementActorPicker = readFileSync(new URL('../features/supplement/ActorPickerView.vue', import.meta.url), 'utf8')
const supplementSourceHealth = readFileSync(new URL('../features/supplement/SourceHealthPanel.vue', import.meta.url), 'utf8')
const candidateRunPanel = readFileSync(new URL('../features/candidates/CandidateRunPanel.vue', import.meta.url), 'utf8')
const homeFeatureSource = [home, candidateRunPanel].join('\n')
const configFeatureSource = [config, configDefaults].join('\n')
const supplementFeatureSource = [supplement, supplementActorPicker, supplementSourceHealth].join('\n')
const logs = readFileSync(new URL('./Logs.vue', import.meta.url), 'utf8')
const library = readFileSync(new URL('./Library.vue', import.meta.url), 'utf8')
const duplicates = readFileSync(new URL('./Duplicates.vue', import.meta.url), 'utf8')
const glassSelect = readFileSync(new URL('../components/GlassSelect.vue', import.meta.url), 'utf8')
const mainCss = readFileSync(new URL('../assets/main.css', import.meta.url), 'utf8')
const searchPreferences = readFileSync(new URL('../utils/searchPreferences.js', import.meta.url), 'utf8')
const magnetParse = readFileSync(new URL('./MagnetParse.vue', import.meta.url), 'utf8')
const apiSource = readFileSync(new URL('../api/index.js', import.meta.url), 'utf8')
const app = readFileSync(new URL('../App.vue', import.meta.url), 'utf8')
const router = readFileSync(new URL('../router/index.js', import.meta.url), 'utf8')
const translationJobs = readFileSync(new URL('./TranslationJobs.vue', import.meta.url), 'utf8')

test('navigation and actor page use actor mapping language', () => {
  assert.match(app, /演员映射/)
  assert.doesNotMatch(app, /演员合并/)
  assert.match(normalize, /演员映射/)
  assert.match(normalize, /listUnmappedActors/)
  assert.match(normalize, /confirmActorMapping/)
  assert.match(normalize, /ignoreActorMapping/)
  assert.match(normalize, /getActorMappingSummary/)
  assert.match(normalize, /待映射审核/)
  assert.doesNotMatch(normalize, />建议候选</)
  assert.match(normalize, /JavInfo 库/)
  assert.match(normalize, /Emby 库/)
  assert.match(normalize, /candidate-compare/)
  assert.match(normalize, /searchActorMappingCandidates/)
  assert.match(normalize, /reviewActorMappingWithAi/)
  assert.match(normalize, /candidateAvatar/)
  assert.match(normalize, /AI 判断/)
  assert.match(normalize, /AI判断/)
  assert.match(normalize, /aiDecisionLabel/)
  assert.match(normalize, /reviewFilterOptions/)
  assert.match(normalize, /置信/)
  assert.match(normalize, /autoMatchActorMappings/)
  assert.match(normalize, /自动匹配预演/)
  assert.match(normalize, /精确但歧义/)
  assert.match(normalize, /statuses = \['confirmed', 'ignored'\]/)
  assert.match(normalize, /actor\.candidates/)
  assert.match(normalize, /loadingMappings/)
})

test('favorites video cards display dvd numbers instead of internal ids', () => {
  assert.match(favorites, /:contentId="item\.metadata\?\.content_id \|\| item\.entity_id"/)
  assert.match(favorites, /:dvdId="movieDisplayCode\(item\)"/)
  assert.match(favorites, /metadata\.dvd_id \|\| metadata\.canonical_number \|\| metadata\.content_id \|\| item\?\.entity_id/)
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

test('primary pages use unified breathing rails', () => {
  assert.match(mainCss, /--page-gutter:\s*clamp\(16px, 2\.8vw, 40px\)/)
  assert.match(mainCss, /--page-max-standard:\s*1180px/)
  assert.match(mainCss, /--page-max-workspace:\s*1360px/)
  assert.match(mainCss, /--page-max-gallery:\s*1600px/)
  assert.match(mainCss, /\.page-shell\s*\{[\s\S]*width: min\(var\(--page-max\), calc\(100% - var\(--page-gutter\) - var\(--page-gutter\)\)\)/)
  assert.match(mainCss, /\.page-rail\s*\{[\s\S]*width: min\(var\(--page-max\), calc\(100% - var\(--page-gutter\) - var\(--page-gutter\)\)\)/)

  const mainContentBlock = app.match(/\.main-content\s*\{[^}]*\}/)?.[0] || ''
  assert.doesNotMatch(mainContentBlock, /padding/)
  assert.doesNotMatch(app, /\.main-content\s*\{\s*padding/)

  for (const [name, source] of Object.entries({
    home,
    operations,
    inventory,
    normalize,
    supplement,
    translationJobs,
    inventoryActor,
  })) {
    assert.match(source, /page-shell page-shell--workspace/, `${name} should use the workspace page shell`)
  }

  for (const [name, source] of Object.entries({
    config,
    magnetParse,
    logs,
    library,
    duplicates,
    subscription,
  })) {
    assert.match(source, /page-shell page-shell--standard/, `${name} should use the standard page shell`)
  }

  assert.match(favorites, /page-shell page-shell--gallery/)
  assert.match(search, /class="search-page page-bleed"/)
  assert.match(search, /page-rail page-rail--gallery/)
  assert.match(genres, /class="genres-page page-bleed"/)
  assert.match(genres, /page-rail page-rail--standard/)
  assert.match(discoveryDetail, /class="genre-detail-page page-bleed"/)
  assert.match(discoveryDetail, /page-rail page-rail--gallery/)
  assert.match(actor, /class="actor-page page-bleed"/)
  assert.match(actor, /page-rail page-rail--gallery/)

  for (const [name, source] of Object.entries({
    home,
    operations,
    inventory,
    normalize,
    supplement,
    translationJobs,
    config,
    magnetParse,
    logs,
    duplicates,
  })) {
    const topWrapper = source.match(/\.(home|operations-page|inventory-page|mapping-page|supplement-page|translation-page|settings|parse-page|logs|duplicates-page)\s*\{[^}]*\}/)?.[0] || ''
    assert.doesNotMatch(topWrapper, /max-width|margin:\s*0 auto|padding:\s*(?:\d|0)/, `${name} should not own page-level rail spacing`)
  }
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
  assert.match(configDefaults, /function parseGradientList/)
  assert.match(configDefaults, /char === ',' && depth === 0/)
  assert.match(config, /this\.bubbleCfg\.customGradients = parseGradientList\(this\.bubbleCfg\.customGradientsText\)/)
  assert.doesNotMatch(config, /customGradientsText[\s\S]{0,120}\.split\(',/)
})

test('theme presets stay curated and complete', () => {
  assert.deepEqual(THEME_KEYS, ['apple-espana', 'apple-pro-dark', 'midnight', 'studio-silver', 'oled', 'deep-space', 'graphite-gold'])

  const baselineTokens = Object.keys(THEMES['apple-espana'].vars).sort()
  for (const [key, theme] of Object.entries(THEMES)) {
    assert.deepEqual(Object.keys(theme.vars).sort(), baselineTokens, `${key} token coverage should match apple-espana`)
    assert.match(theme.vars['--font-body'], /SF Pro Text/)
    assert.match(theme.vars['--font-body'], /-apple-system/)
    assert.doesNotMatch(theme.vars['--font-body'], /Inter|Cormorant|Noto|Space Grotesk|Nunito/i)
    assert.doesNotMatch(theme.vars['--font-body'], /(^|,\s*)'?serif'?($|,)/i)
    assert.ok(theme.vars['--surface-nav'], `${key} should define semantic navigation material`)
  }

  assert.equal(THEMES['apple-espana'].vars['--bg-primary'], '#FFFFFF')
  assert.equal(THEMES['apple-pro-dark'].vars['--bg-primary'], '#000000')
  assert.match(app, /background: var\(--surface-nav\)/)
  assert.doesNotMatch(app, /background:\s*rgba\(245,\s*245,\s*247,\s*0\.86\)/)

  for (const removed of ['forest', 'tokyo', 'aurora', 'rose']) {
    assert.equal(THEMES[removed], undefined)
  }
})

test('legacy saved theme values resolve to curated themes', () => {
  assert.equal(resolveThemeKey('forest'), 'midnight')
  assert.equal(resolveThemeKey('tokyo'), 'deep-space')
  assert.equal(resolveThemeKey('aurora'), 'deep-space')
  assert.equal(resolveThemeKey('rose'), 'graphite-gold')
  assert.equal(resolveThemeKey('missing-theme'), 'apple-espana')

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
  assert.match(candidateRunPanel, /最近处理/)
  assert.match(home, /loadCandidateRuns/)
  assert.match(home, /applyCandidateRunFilters/)
  assert.match(home, /retryFailedCandidateRun/)
  assert.match(home, /retryDownloadCandidateRunFailed/)
  assert.match(home, /listDownloadCandidateRuns/)
  assert.match(candidateRunPanel, /失败队列/)
  assert.match(candidateRunPanel, /重试失败/)
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
  assert.match(operations, /采集后自动匹配/)
  assert.match(operations, /保守唯一/)
})

test('translation jobs has a standalone navigation page and settings no longer owns translation UI', () => {
  assert.match(app, /label: '翻译作业'/)
  assert.match(app, /path: '\/translations'/)
  assert.match(router, /path: '\/translations'/)
  assert.match(router, /TranslationJobs/)
  assert.doesNotMatch(config, /<h2>翻译映射<\/h2>/)
  assert.doesNotMatch(config, /<h2>翻译源<\/h2>/)
  assert.match(translationJobs, /name: 'TranslationJobs'/)
  assert.match(translationJobs, /class="segmented-control apple-surface"/)
  assert.match(translationJobs, /有效标题译文/)
  for (const label of ['总览', '创建作业', '翻译源', '映射导入', '历史记录']) {
    assert.match(translationJobs, new RegExp(`label: '${label}'`))
  }
  assert.match(translationJobs, /低成本批量源/)
  assert.match(translationJobs, /AI 实时 \/ 兜底/)
  assert.match(translationJobs, /公共 AI 参数在设置页维护/)
  assert.match(translationJobs, /批量作业默认不使用 AI/)
  assert.match(translationJobs, /job_type/)
  assert.match(translationJobs, /library_titles/)
  assert.match(translationJobs, /metadata_names/)
  for (const jobType of ['metadata_categories', 'metadata_series', 'metadata_makers', 'metadata_labels', 'metadata_actresses']) {
    assert.match(translationJobs, new RegExp(jobType))
  }
  for (const label of ['题材名称', '系列名称', '厂商名称', '厂牌名称', '演员名称', '全部元数据名称']) {
    assert.match(translationJobs, new RegExp(label))
  }
  assert.match(translationJobs, /progress_percent/)
  assert.match(translationJobs, /startTranslationJob/)
  assert.match(translationJobs, /listTranslationJobs/)
  assert.match(translationJobs, /getTranslationJob/)
  assert.match(translationJobs, /moveProvider/)
  assert.match(translationJobs, /上移/)
  assert.match(translationJobs, /下移/)
  assert.match(translationJobs, /setInterval\(\(\) => this\.refreshCurrentJob\(jobId\), 2000\)/)
  assert.match(translationJobs, /\['cache', 'mapping'\]/)
  assert.doesNotMatch(translationJobs, /openai_compatible[\s\S]{0,120}selectedProviderOrder/)
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
  assert.match(configFeatureSource, /max_auto_downloads_per_run/)
  assert.match(configFeatureSource, /max_auto_downloads_per_24h/)
  assert.match(configFeatureSource, /actor_mapping/)
  assert.match(configFeatureSource, /auto_match_after_collect/)
  assert.match(configFeatureSource, /ai/)
  assert.match(config, /<h2>公共 AI<\/h2>/)
  assert.match(config, /config\.ai\.openai_compatible/)
  assert.match(config, /测试模型调用/)
  assert.match(config, /testAIModel/)
  assert.match(apiSource, /testAiModel/)
})

test('settings page keeps downloaders out and gives Telegram its own section', () => {
  assert.match(config, /activeGroup === 'telegram'/)
  assert.match(config, /label: 'Telegram 通知'/)
  assert.match(config, /<h2>Bot 连接<\/h2>/)
  assert.match(config, /<h2>通知事件<\/h2>/)
  assert.match(config, /const \{ downloaders, openlist, \.\.\.configPayload \} = this\.config/)
  assert.doesNotMatch(config, /OpenList \/ 115云盘/)
  assert.doesNotMatch(config, /管理下载源/)
  assert.doesNotMatch(config, /config\.openlist/)
  assert.doesNotMatch(config, /系统通知/)
})

test('interactive filters avoid stale actions and stale pagination', () => {
  assert.match(search, /this\.applySearchPreferences\(\)/)
  assert.match(search, /clearSort\(\{ search = true \} = \{\}\)/)
  assert.match(search, /async activated\(\)[\s\S]*this\.applySearchPreferences\(\)[\s\S]*await this\.loadConfiguredPageSize\(\)[\s\S]*this\.syncRouteQuery\(this\.\$route\.query\)[\s\S]*this\.doSearch\(\)/)
  assert.match(genres, /this\.categoryError = ''[\s\S]*this\.displayedTags = this\.shuffledTags/)
  assert.match(genres, /if \(!this\.categories\.length && !this\.loading\) this\.categoryError = 'stats_failed'/)
})

test('appearance settings are grouped by scope and persist discovery preferences', () => {
  const globalSection = config.slice(config.indexOf('<h3>全局偏好</h3>'), config.indexOf('<h3>影片检索</h3>'))
  const searchSection = config.slice(config.indexOf('<h3>影片检索</h3>'), config.indexOf('<h3>个性推荐</h3>'))
  const discoverySection = config.slice(config.indexOf('<h3>个性推荐</h3>'), config.indexOf('</template>'))
  assert.match(globalSection, /<span class="setting-title">显示语言<\/span>/)
  assert.match(searchSection, /<span class="setting-title">检索页数量<\/span>/)
  assert.match(searchSection, /<span class="setting-title">默认排序<\/span>/)
  assert.match(searchSection, /<span class="setting-title">默认版本筛选<\/span>/)
  assert.match(discoverySection, /<span class="setting-title">演员头像<\/span>/)
  assert.match(discoverySection, /<span class="setting-title">演员每批数量<\/span>/)
  assert.match(discoverySection, /<span class="setting-title">系列每批数量<\/span>/)
  assert.match(config, /<span class="setting-title">题材 \/ 系列气泡视觉<\/span>/)
  assert.doesNotMatch(searchSection, /演员头像/)
  assert.doesNotMatch(discoverySection, /检索页数量/)
  assert.match(configDefaults, /defaultTab: 'genre'/)
  assert.match(configDefaults, /actressPageSize: 36/)
  assert.match(configDefaults, /seriesPageSize: 60/)
  assert.match(config, /seriesPageSizeOptions: \[30, 60, 90, 100\]/)
  assert.match(config, /localStorage\.setItem\('genres_bubble_cfg', JSON\.stringify\(this\.bubbleCfg\)\)/)
})

test('global dropdowns use the unified glass select control', () => {
  for (const [name, source] of Object.entries({
    config,
    inventory,
    supplementFeatureSource,
    translationJobs,
    logs,
    search,
    discoveryDetail,
  })) {
    assert.doesNotMatch(source, /<select\b/, `${name} should not use native select controls`)
  }

  const searchSection = config.slice(config.indexOf('<h3>影片检索</h3>'), config.indexOf('<h3>个性推荐</h3>'))
  const visualSection = config.slice(config.indexOf('<span class="setting-title">色系预设</span>'), config.indexOf(`<template v-if="bubbleCfg.colorMode === 'legendary'">`))

  assert.match(searchSection, /<GlassSelect[\s\S]*v-model="searchPrefs\.defaultSort"/)
  assert.match(searchSection, /<GlassSelect[\s\S]*v-model="searchPrefs\.defaultServiceCode"/)
  assert.match(visualSection, /<GlassSelect[\s\S]*v-model="bubbleCfg\.palette"/)

  assert.match(inventory, /import GlassSelect/)
  assert.match(inventory, /v-model="sortBy"[\s\S]*@change="doSearch"/)
  assert.match(inventory, /v-model="pageSize"[\s\S]*@change="onPageSizeChange"/)
  assert.match(supplement, /v-model="movieFilters\.matched"[\s\S]*matchFilterOptions/)
  assert.match(supplement, /value: false, label: '未匹配'/)
  assert.match(supplement, /providerSourceOptions\(\)/)
  assert.match(logs, /v-model="filterLevel"[\s\S]*levelOptions/)
  assert.match(search, /<GlassSelect[\s\S]*class="version-filter"[\s\S]*@change="doSearch"/)
  assert.match(discoveryDetail, /<GlassSelect[\s\S]*class="version-filter"[\s\S]*@change="doSearch"/)
  assert.match(search, /\.sort-strip[\s\S]*--filter-control-height: 32px/)
  assert.match(search, /\.version-filter[\s\S]*--glass-select-height: var\(--filter-control-height\)/)
  assert.match(search, /\.sort-strip[\s\S]*--filter-control-height: 44px/)
  assert.match(discoveryDetail, /\.chronicle-btn[\s\S]*width: var\(--filter-control-width\)/)

  assert.match(glassSelect, /aria-haspopup="listbox"/)
  assert.match(glassSelect, /event\.key === 'ArrowDown'/)
  assert.match(glassSelect, /event\.key === 'Escape'/)
  assert.match(glassSelect, /emit\('update:modelValue', option\.value\)/)
  assert.match(glassSelect, /<Teleport to="body">/)
  assert.match(glassSelect, /window\.visualViewport\?\.addEventListener\('resize', requestMenuPlacement\)/)
  assert.match(glassSelect, /menuNaturalHeight\(\)/)
  assert.doesNotMatch(glassSelect, /Math\.min\(menuRef\.value\.scrollHeight[\s\S]*360\)/)
  assert.match(mainCss, /\.glass-select--compact[\s\S]*--glass-select-height: 38px/)
  assert.match(mainCss, /\.glass-select__button[\s\S]*min-height: var\(--glass-select-height\)/)
  assert.match(mainCss, /\.glass-select__button[\s\S]*background: var\(--glass-control-bg, rgba\(255, 255, 255, 0\.05\)\)/)
  assert.match(mainCss, /\.glass-select__menu[\s\S]*border-radius: var\(--glass-select-menu-radius, var\(--radius-lg\)\)/)
  assert.match(mainCss, /\.glass-select__menu[\s\S]*backdrop-filter: blur/)
})

test('search preferences drive initial search params', () => {
  assert.match(searchPreferences, /SEARCH_PREFERENCES_KEY = 'javhub_search_preferences'/)
  assert.match(searchPreferences, /defaultSort: 'random'/)
  assert.match(searchPreferences, /defaultServiceCode: ''/)
  assert.match(searchPreferences, /normalizeSearchPreferences/)
  assert.match(config, /loadSearchPreferences/)
  assert.match(config, /saveSearchPreferences/)
  assert.match(search, /import \{ loadSearchPreferences \} from '\.\.\/utils\/searchPreferences\.js'/)
  assert.match(search, /function sortStateFromPreference\(defaultSort = 'random'\)/)
  assert.match(search, /async mounted\(\)[\s\S]*this\.applySearchPreferences\(\{ force: true \}\)[\s\S]*await this\.loadConfiguredPageSize\(\)/)
  assert.match(search, /async loadConfiguredPageSize\(\)[\s\S]*await api\.getConfig\(\)/)
  assert.match(search, /buildSearchParams\(page\)[\s\S]*page_size: this\.pageSize[\s\S]*params\.service_code = this\.serviceCode/)
  assert.match(search, /if \(this\.sortState\.random\)[\s\S]*params\.random = '1'/)
  assert.match(search, /params\.sort_by = sortParts\.join\(','\)/)
})

test('genres page applies series and actor preference settings separately', () => {
  assert.match(genres, /defaultTab: 'genre'/)
  assert.match(genres, /actressAvatarSize: 'medium'/)
  assert.match(genres, /actressPageSize: 36/)
  assert.match(genres, /seriesPageSize: 60/)
  assert.match(genres, /this\.activeTab = this\.tabs\.some\(tab => tab\.key === this\.cfg\.defaultTab\)/)
  assert.match(genres, /actressPageSize\(\)[\s\S]*this\.cfg\.actressPageSize/)
  assert.match(genres, /seriesPageSize\(\)[\s\S]*this\.cfg\.seriesPageSize/)
  assert.match(genres, /const pageSize = this\.seriesPageSize[\s\S]*api\.listSeries\(page, pageSize\)/)
  assert.match(genres, /legendaryBubbleClass\(tag\)[\s\S]*if \(this\.activeTab === 'series'\) return ''/)
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
