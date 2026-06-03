import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { THEMES } from './themes.js'

const mainCss = readFileSync(new URL('./main.css', import.meta.url), 'utf8')
const app = readFileSync(new URL('../App.vue', import.meta.url), 'utf8')
const search = [
  readFileSync(new URL('../views/Search.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/search/search.css', import.meta.url), 'utf8'),
].join('\n')
const genres = readFileSync(new URL('../views/Genres.vue', import.meta.url), 'utf8')
const config = [
  readFileSync(new URL('../views/Config.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/config/config.css', import.meta.url), 'utf8'),
].join('\n')
const videoModal = [
  readFileSync(new URL('../components/VideoModal.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/videoModal/videoModal.css', import.meta.url), 'utf8'),
].join('\n')
const actressCard = readFileSync(new URL('../components/ActressCard.vue', import.meta.url), 'utf8')
const actor = [
  readFileSync(new URL('../views/Actor.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/actor/actor.css', import.meta.url), 'utf8'),
].join('\n')
const supplementManagement = [
  readFileSync(new URL('../views/SupplementManagement.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/supplement/supplementManagement.css', import.meta.url), 'utf8'),
].join('\n')
const inventoryActor = readFileSync(new URL('../views/InventoryActor.vue', import.meta.url), 'utf8')
const subscription = [
  readFileSync(new URL('../views/Subscription.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/subscription/subscription.css', import.meta.url), 'utf8'),
].join('\n')
const duplicates = readFileSync(new URL('../views/Duplicates.vue', import.meta.url), 'utf8')
const home = [
  readFileSync(new URL('../views/Home.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/home/home.css', import.meta.url), 'utf8'),
].join('\n')
const translationJobs = [
  readFileSync(new URL('../views/TranslationJobs.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/translations/translationJobs.css', import.meta.url), 'utf8'),
].join('\n')
const libraryOrganize = [
  readFileSync(new URL('../views/LibraryOrganize.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/library/libraryOrganize.css', import.meta.url), 'utf8'),
].join('\n')

function cssBlock(selector) {
  const pattern = new RegExp(`${selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*\\{([\\s\\S]*?)\\n\\}`)
  const match = mainCss.match(pattern)
  assert.ok(match, `${selector} should exist in main.css`)
  return match[1]
}

function sourceBlock(source, selector) {
  const pattern = new RegExp(`${selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*\\{([\\s\\S]*?)\\n\\}`)
  const match = source.match(pattern)
  assert.ok(match, `${selector} should exist`)
  return match[1]
}

function backgroundIncludes(token) {
  return new RegExp(`background:[\\s\\S]*var\\(--${token}\\)`)
}

test('theme materials include refractive liquid glass layers', () => {
  const requiredTokens = [
    '--glass-control-material',
    '--glass-control-material-hover',
    '--glass-card-material',
    '--glass-sheet-material',
    '--glass-control-shadow',
    '--glass-control-shadow-hover',
    '--glass-surface-shadow',
    '--glass-specular-edge',
    '--glass-specular-edge-strong',
    '--glass-surface-noise',
    '--glass-surface-overlay-opacity',
    '--glass-blur-control',
    '--glass-blur-surface',
    '--glass-saturate-control',
    '--app-backdrop-texture',
    '--content-material',
    '--content-material-border',
    '--chrome-floating-shadow',
    '--surface-specular-edge',
    '--surface-specular-edge-strong',
    '--surface-noise',
    '--surface-overlay-opacity',
    '--media-blackout',
    '--media-edge-mask-strong',
    '--media-edge-mask-clear',
    '--media-caption-scrim-clear',
    '--media-caption-scrim-strong',
    '--media-caption-text',
  ]

  for (const [key, theme] of Object.entries(THEMES)) {
    for (const token of requiredTokens) {
      assert.ok(theme.vars[token], `${key} should define ${token}`)
    }
    assert.match(theme.vars['--glass-control-material'], /linear-gradient/)
    assert.match(theme.vars['--glass-control-shadow'], /inset 0 1px 0/)
    assert.match(theme.vars['--glass-specular-edge'], /linear-gradient/)
    assert.match(theme.vars['--glass-specular-edge-strong'], /linear-gradient/)
    assert.match(theme.vars['--glass-surface-noise'], /repeating-linear-gradient/)
    assert.equal(theme.vars['--surface-specular-edge'], 'var(--glass-specular-edge)')
    assert.equal(theme.vars['--surface-specular-edge-strong'], 'var(--glass-specular-edge-strong)')
    assert.equal(theme.vars['--surface-noise'], 'var(--glass-surface-noise)')
    assert.equal(theme.vars['--surface-overlay-opacity'], 'var(--glass-surface-overlay-opacity)')
  }

  assert.notEqual(THEMES['apple-dark'].vars['--glass-control-bg'], 'rgba(255, 255, 255, 0.060)')
  assert.match(THEMES['apple-dark'].vars['--glass-control-bg'], /rgba\(18,\s*19,\s*21,\s*0\.36\)/)
  assert.match(THEMES['apple-light'].vars['--glass-control-shadow'], /0 10px 26px/)
  assert.match(THEMES['apple-light'].vars['--app-backdrop-texture'], /linear-gradient/)
  assert.match(THEMES['apple-light'].vars['--glass-specular-edge'], /rgba\(255,255,255,0\.78\)/)
  assert.match(THEMES['apple-light'].vars['--glass-surface-noise'], /rgba\(29,29,31,0\.016\)/)
  assert.equal(THEMES['apple-light'].vars['--glass-surface-overlay-opacity'], '0.72')
  assert.match(THEMES['apple-dark'].vars['--glass-specular-edge'], /rgba\(5,5,6,0\.28\)/)
  assert.match(THEMES['apple-dark'].vars['--glass-surface-noise'], /rgba\(255,255,255,0\.024\)/)
  assert.equal(THEMES['apple-dark'].vars['--glass-surface-overlay-opacity'], '0.64')
  assert.match(mainCss, /--glass-specular-edge:\s*linear-gradient/)
  assert.match(mainCss, /--surface-specular-edge:\s*var\(--glass-specular-edge\)/)
  assert.match(THEMES['apple-dark'].vars['--content-material'], /rgba\(10,\s*10,\s*12,\s*0\.72\)/)
  assert.notEqual(THEMES['apple-light'].vars['--media-blackout'], '#000000')
  assert.notEqual(THEMES['apple-dark'].vars['--media-blackout'], '#000000')
  assert.match(mainCss, /--media-blackout:\s*#030304/)
  assert.match(THEMES['apple-light'].vars['--media-edge-mask-strong'], /color-mix\(in srgb,\s*var\(--text-primary\) 76%,\s*transparent\)/)
  assert.match(THEMES['apple-dark'].vars['--media-edge-mask-strong'], /color-mix\(in srgb,\s*var\(--text-primary\) 72%,\s*transparent\)/)
  assert.equal(THEMES['apple-light'].vars['--media-edge-mask-clear'], 'transparent')
  assert.equal(THEMES['apple-dark'].vars['--media-edge-mask-clear'], 'transparent')
  assert.equal(THEMES['apple-light'].vars['--media-caption-scrim-clear'], 'transparent')
  assert.equal(THEMES['apple-dark'].vars['--media-caption-scrim-clear'], 'transparent')
  assert.match(THEMES['apple-light'].vars['--media-caption-scrim-strong'], /color-mix\(in srgb,\s*var\(--media-blackout\) 82%,\s*transparent\)/)
  assert.match(THEMES['apple-dark'].vars['--media-caption-scrim-strong'], /color-mix\(in srgb,\s*var\(--media-blackout\) 86%,\s*transparent\)/)
  assert.equal(THEMES['apple-light'].vars['--media-caption-text'], '#F5F5F7')
  assert.equal(THEMES['apple-dark'].vars['--media-caption-text'], '#F5F5F7')
})

test('global controls use shared liquid glass material instead of flat tint', () => {
  const buttonBlock = cssBlock('.btn')
  const primaryButtonBlock = cssBlock('.btn-primary')
  const primaryButtonHoverBlock = cssBlock('.btn-primary:hover')

  assert.match(buttonBlock, /transition:\s*transform var\(--motion-standard\),\s*background var\(--motion-standard\),\s*border-color var\(--motion-standard\),\s*box-shadow var\(--motion-standard\),\s*color var\(--motion-fast\),\s*opacity var\(--motion-fast\)/)
  assert.match(buttonBlock, /letter-spacing:\s*0/)
  assert.doesNotMatch(buttonBlock, /letter-spacing:\s*-0\.01em/)
  assert.match(primaryButtonBlock, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--glass-active-material\)/)
  assert.match(primaryButtonBlock, /border-color:\s*var\(--glass-active-border\)/)
  assert.match(primaryButtonBlock, /color:\s*var\(--text-primary\)/)
  assert.match(primaryButtonBlock, /box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.match(primaryButtonBlock, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.doesNotMatch(primaryButtonBlock, /background:\s*var\(--accent\)|color:\s*var\(--text-on-accent\)|box-shadow:\s*none/)
  assert.match(primaryButtonHoverBlock, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-control-hover\)/)
  assert.match(primaryButtonHoverBlock, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(primaryButtonHoverBlock, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.doesNotMatch(primaryButtonHoverBlock, /background:\s*var\(--accent-light\)/)

  assert.match(cssBlock('.btn-ghost'), /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-control\)/)
  assert.match(cssBlock('.btn-ghost'), /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(cssBlock('.glass-select__button'), /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-control, var\(--glass-control-bg/)
  assert.match(cssBlock('.glass-select__menu'), /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--material-glass-sheet\)/)
  assert.match(cssBlock('.el-input__wrapper, .input'), /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--surface-input\)\s*!important/)
  assert.match(cssBlock('.el-input__wrapper:hover, .input:hover'), /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--surface-control-hover\)\s*!important/)
  assert.match(cssBlock('.el-input__wrapper.is-focus, .input:focus'), /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--surface-input-focus\)\s*!important/)
  assert.match(cssBlock('.el-dialog, .el-card, .el-popover, .el-dropdown-menu'), /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--material-glass-sheet\)\s*!important/)
  assert.match(cssBlock('.el-input__wrapper, .el-textarea__inner, .el-select .el-input__wrapper'), /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--surface-input\)\s*!important/)
  assert.match(cssBlock('.el-button--default'), /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--surface-control\)\s*!important/)
  assert.match(cssBlock('.el-button--default:hover'), /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--surface-control-hover\)\s*!important/)
  const appleSurfaceBlock = cssBlock('.apple-surface')
  const appleSurfaceAfterBlock = cssBlock('.apple-surface::after')
  const appleSurfaceChildBlock = cssBlock('.apple-surface > *')
  const appleSurfaceElevatedBlock = cssBlock('.apple-surface-elevated')
  const appleSurfaceElevatedAfterBlock = cssBlock('.apple-surface-elevated::after')

  assert.match(appleSurfaceBlock, /position:\s*relative/)
  assert.match(appleSurfaceBlock, /isolation:\s*isolate/)
  assert.match(appleSurfaceBlock, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--surface-card\)/)
  assert.match(appleSurfaceBlock, /border:\s*1px solid var\(--glass-edge\)/)
  assert.match(appleSurfaceBlock, /box-shadow:\s*var\(--glass-surface-shadow\)/)
  assert.match(appleSurfaceAfterBlock, /content:\s*""/)
  assert.match(appleSurfaceAfterBlock, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\)/)
  assert.match(appleSurfaceAfterBlock, /opacity:\s*var\(--surface-overlay-opacity\)/)
  assert.match(appleSurfaceAfterBlock, /pointer-events:\s*none/)
  assert.match(appleSurfaceAfterBlock, /z-index:\s*0/)
  assert.match(appleSurfaceChildBlock, /position:\s*relative/)
  assert.match(appleSurfaceChildBlock, /z-index:\s*1/)
  assert.match(appleSurfaceElevatedBlock, /position:\s*relative/)
  assert.match(appleSurfaceElevatedBlock, /isolation:\s*isolate/)
  assert.match(appleSurfaceElevatedBlock, /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--material-glass-elevated\)/)
  assert.match(appleSurfaceElevatedBlock, /border:\s*1px solid var\(--glass-edge-strong\)/)
  assert.match(appleSurfaceElevatedAfterBlock, /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\)/)
  assert.match(appleSurfaceElevatedAfterBlock, /pointer-events:\s*none/)
  assert.match(search, /\.sort-pill\s*\{[\s\S]*background:[\s\S]*var\(--material-glass-control\)[\s\S]*box-shadow:\s*var\(--glass-control-shadow\)[\s\S]*backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)/)
  assert.match(search, /\.sort-pill:hover\s*\{[\s\S]*background:[\s\S]*var\(--material-glass-control-hover\)[\s\S]*box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.match(search, /\.filter-item\s*\{[\s\S]*background:[\s\S]*var\(--material-glass-control\)[\s\S]*box-shadow:\s*var\(--glass-control-shadow\)[\s\S]*backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)/)
  assert.match(search, /\.filter-item:hover\s*\{[\s\S]*background:[\s\S]*var\(--material-glass-control-hover\)[\s\S]*box-shadow:\s*var\(--glass-control-shadow-hover\)/)
})

test('active states resolve to refractive glass rather than flat rgba tint', () => {
  for (const [key, theme] of Object.entries(THEMES)) {
    assert.equal(theme.vars['--nav-active-bg'], 'var(--glass-active-material)', `${key} nav active material should stay refractive`)
  }

  assert.match(app, /\.nav-item\.active\s*\{[\s\S]*background:[\s\S]*var\(--glass-active-material\)/)
  assert.match(cssBlock('.glass-select__option.is-selected'), /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--glass-active-material\)/)
})

test('segmented controls and settings rows use shared glass materials', () => {
  assert.match(genres, /\.shuffle-btn\s*\{[\s\S]*background:\s*var\(--material-glass-control\)[\s\S]*box-shadow:\s*var\(--glass-control-shadow\)[\s\S]*backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)/)
  assert.match(genres, /\.tab-bar\s*\{[\s\S]*background:\s*var\(--material-glass-control\)[\s\S]*box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(genres, /\.tab-btn\.active\s*\{[\s\S]*background:\s*var\(--glass-active-material\)/)

  assert.match(config, /\.settings-tabs\s*\{[\s\S]*background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-control\)[\s\S]*box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(config, /\.appearance-setting-row\s*\{[\s\S]*background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-control\)[\s\S]*box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(config, /\.segmented-mini button\.active\s*\{[\s\S]*background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--glass-active-material\)/)
})

test('native form controls use active glass accents instead of raw theme accent paint', () => {
  for (const [name, source] of [
    ['Config', config],
    ['Home', home],
    ['TranslationJobs', translationJobs],
  ]) {
    assert.doesNotMatch(source, /accent-color:\s*var\(--accent\)/, `${name} should not use the raw accent color on native controls`)
  }

  assert.match(config, /\.form-group\.checkbox input\s*\{[^}]*accent-color:\s*var\(--glass-active-border\)/)
  assert.match(config, /\.source-check-item input\s*\{[^}]*accent-color:\s*var\(--glass-active-border\)/)
  assert.match(config, /\.threshold-slider\s*\{[^}]*accent-color:\s*var\(--glass-active-border\)/)
  assert.match(home, /\.candidate-select input\s*\{[^}]*accent-color:\s*var\(--glass-active-border\)/)
  assert.match(translationJobs, /\.check-row input,\s*[\s\S]*?\.provider-row input\s*\{[^}]*accent-color:\s*var\(--glass-active-border\)/)
})

test('video modal sheet uses a translucent material without backdrop-filter differences', () => {
  assert.match(videoModal, /--modal-scrim-sheet:\s*rgba\(18,\s*18,\s*20,\s*0\.64\)/)
  assert.match(videoModal, /--modal-sheet-bg:\s*var\(--modal-scrim-sheet\)/)
  assert.match(videoModal, /--modal-sheet-fallback:\s*var\(--modal-scrim-sheet\)/)
  assert.match(videoModal, /:root\[data-theme="dark"\]\s+\.modal-overlay\s*\{[\s\S]*--modal-scrim-sheet:\s*rgba\(14,\s*14,\s*16,\s*0\.68\)/)
  assert.match(videoModal, /\.modal-container\s*\{[\s\S]*background:\s*var\(--modal-sheet-fallback\)[\s\S]*background:\s*var\(--modal-sheet-bg\)/)
  assert.match(videoModal, /\.modal-container\s*\{[\s\S]*backdrop-filter:\s*none[\s\S]*-webkit-backdrop-filter:\s*none/)
  assert.doesNotMatch(videoModal, /--modal-(?:panel|gallery|overlay)-bg:\s*rgba\(0,\s*0,\s*0/)
})

test('image fallback placeholders use theme glass instead of hardcoded SVG data URLs', () => {
  for (const [name, source] of [
    ['ActressCard', actressCard],
    ['VideoModal', videoModal],
    ['Actor', actor],
    ['Genres', genres],
    ['SupplementManagement', supplementManagement],
    ['InventoryActor', inventoryActor],
    ['Subscription', subscription],
  ]) {
    assert.doesNotMatch(source, /data:image\/svg\+xml/, `${name} should not inject hardcoded SVG fallbacks`)
    assert.match(source, /applyImageFallback/, `${name} should use the shared image fallback helper`)
    assert.doesNotMatch(source, /\$event\.target\.style\.display\s*=\s*['"]none['"]/, `${name} should not hide failed media`)
    assert.doesNotMatch(source, /\$event\.target\.src\s*=/, `${name} should not rewrite failed media inline`)
  }

  const fallbackBlock = cssBlock('.image-fallback')
  assert.match(fallbackBlock, /background:\s*var\(--material-glass-subtle\)/)
  assert.match(fallbackBlock, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(fallbackBlock, /box-shadow:\s*var\(--glass-inner-shadow\)/)
  assert.match(fallbackBlock, /color:\s*var\(--text-muted\)/)
  assert.doesNotMatch(fallbackBlock, /#|rgba\(0,\s*0,\s*0|rgba\(255,\s*255,\s*255/)
})

test('secondary utility controls avoid one-off fog materials', () => {
  assert.match(actor, /\.year-nav\s*\{[\s\S]*background:\s*var\(--material-glass-sheet\)[\s\S]*backdrop-filter:\s*blur\(var\(--glass-blur-sheet\)\)\s*saturate\(var\(--glass-saturate-surface\)\)/)
  assert.match(duplicates, /\.action-btn\.ignore\s*\{[\s\S]*background:\s*var\(--material-glass-control\)/)
  assert.match(home, /\.dialog-close-btn\s*\{[\s\S]*background:[\s\S]*var\(--material-glass-control\)[\s\S]*box-shadow:\s*var\(--glass-control-shadow\)/)
})

test('page status colors use semantic badge tokens instead of hardcoded hues', () => {
  const bannedStatusPaint = /(?:#(?:ef5350|fa8c16|52c41a|32D74B|32d74b|b45309|f87171|4ade80)|rgba\((?:239,\s*68,\s*68|34,\s*197,\s*94|245,\s*158,\s*11|244,\s*63,\s*94|255,\s*181,\s*71))/i
  for (const [name, source] of [
    ['Actor', actor],
    ['Config', config],
    ['Home', home],
    ['LibraryOrganize', libraryOrganize],
    ['Subscription', subscription],
  ]) {
    assert.doesNotMatch(source, bannedStatusPaint, `${name} should use badge semantic status tokens`)
  }
})

test('home dashboard metrics use shared liquid glass controls', () => {
  const statCardBlock = sourceBlock(home, '.stat-card')
  const statCardHoverBlock = sourceBlock(home, '.stat-card:hover')
  const statIconBlock = sourceBlock(home, '.stat-icon')
  const candidateMetricBlock = sourceBlock(home, '.candidate-metric')
  const candidateMetricHoverBlock = sourceBlock(home, '.candidate-metric:hover')
  const mobileBlock = home.match(/@media \(max-width:\s*768px\)\s*\{[\s\S]*\n\}/)?.[0] || ''

  assert.match(statCardBlock, backgroundIncludes('material-glass-control'))
  assert.match(statCardBlock, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(statCardBlock, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(statCardBlock, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(statCardHoverBlock, backgroundIncludes('material-glass-control-hover'))
  assert.match(statCardHoverBlock, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(statCardHoverBlock, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.doesNotMatch(statCardBlock, /blur\(20px\)|var\(--surface-control\)|var\(--bg-card\)|rgba\(255,\s*255,\s*255,\s*0\.05\)/)

  assert.match(statIconBlock, /background:\s*var\(--material-glass-subtle\)/)
  assert.match(statIconBlock, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(statIconBlock, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.doesNotMatch(statIconBlock, /!important|rgba\(255,\s*255,\s*255/)

  assert.match(candidateMetricBlock, backgroundIncludes('material-glass-control'))
  assert.match(candidateMetricBlock, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(candidateMetricBlock, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(candidateMetricBlock, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)/)
  assert.match(candidateMetricHoverBlock, backgroundIncludes('material-glass-control-hover'))
  assert.match(candidateMetricHoverBlock, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)

  assert.match(mobileBlock, /\.candidate-overview\s*\{[\s\S]*grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/)
  assert.match(mobileBlock, /\.candidate-metric\s*\{[\s\S]*min-width:\s*0/)
})

test('translation jobs workbench surfaces use shared Apple glass controls', () => {
  const segmentedBlock = sourceBlock(translationJobs, '.segmented-control')
  const segmentedActiveBlock = sourceBlock(translationJobs, '.segmented-control button.active')
  const overviewSurfaceBlock = translationJobs.match(/\.coverage-hero,\n\.metadata-overview,\n\.signal-card,\n\.job-control-card\s*\{([\s\S]*?)\n\}/)?.[1] || ''
  const inputBlock = sourceBlock(translationJobs, '.input')
  const inputFocusBlock = sourceBlock(translationJobs, '.input:focus')
  const noticeBlock = sourceBlock(translationJobs, '.notice-row')
  const reviewStatsBlock = sourceBlock(translationJobs, '.review-stats div')

  assert.match(segmentedBlock, /background:\s*var\(--material-glass-control\)/)
  assert.match(segmentedBlock, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(segmentedBlock, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(segmentedBlock, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(segmentedActiveBlock, /background:\s*var\(--glass-active-material\)/)
  assert.match(segmentedActiveBlock, /box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.doesNotMatch(segmentedBlock, /rgba\(255,\s*255,\s*255,\s*0\.045\)/)
  assert.doesNotMatch(segmentedActiveBlock, /rgba\(255,\s*255,\s*255,\s*0\.12\)/)

  assert.match(overviewSurfaceBlock, /background:\s*var\(--material-glass-control\)/)
  assert.match(overviewSurfaceBlock, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(overviewSurfaceBlock, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(overviewSurfaceBlock, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)/)
  assert.doesNotMatch(overviewSurfaceBlock, /var\(--surface-control\)|var\(--border\)|rgba\(255,\s*255,\s*255,\s*0\.035\)/)

  for (const block of [inputBlock, noticeBlock, reviewStatsBlock]) {
    assert.match(block, /background:\s*var\(--material-glass-control\)/)
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)/)
    assert.doesNotMatch(block, /var\(--surface-control\)|rgba\(255,\s*255,\s*255,\s*0\.0[345]\)|var\(--border\)/)
  }

  assert.match(inputFocusBlock, /background:\s*var\(--material-glass-control-hover\)/)
  assert.match(inputFocusBlock, /box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.doesNotMatch(inputFocusBlock, /var\(--surface-input-focus\)/)
})
