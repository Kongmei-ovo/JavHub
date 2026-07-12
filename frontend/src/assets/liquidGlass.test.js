import test from 'node:test'
import assert from 'node:assert/strict'
import { readdirSync, readFileSync } from 'node:fs'
import { THEMES } from './themes.js'

const mainCss = readFileSync(new URL('./main.css', import.meta.url), 'utf8')
const app = readFileSync(new URL('../App.vue', import.meta.url), 'utf8')
const search = [
  readFileSync(new URL('../views/Search.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/search/search.css', import.meta.url), 'utf8'),
].join('\n')
const config = [
  readFileSync(new URL('../views/Config.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/config/AdvancedSettingsPanel.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/config/config.css', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/config/configAppearance.css', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/config/advancedSettingsPanel.css', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/config/advancedSettingsPanelResponsive.css', import.meta.url), 'utf8'),
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
const subscription = [
  readFileSync(new URL('../views/Subscription.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/subscription/subscription.css', import.meta.url), 'utf8'),
].join('\n')
const downloads = [
  readFileSync(new URL('../views/Downloads.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/downloads/DownloadStatsBar.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/downloads/TaskList.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/downloads/downloads.css', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/downloaders/DownloaderManagementPanel.vue', import.meta.url), 'utf8'),
].join('\n')
const candidates = [
  readFileSync(new URL('../views/Candidates.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/candidates/DownloadCandidatePanel.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/candidates/candidates.css', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/candidates/downloadCandidatePanel.css', import.meta.url), 'utf8'),
].join('\n')
const translationJobs = [
  readFileSync(new URL('../views/TranslationJobs.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/translations/TranslationSourcesPanel.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/translations/TranslationReviewPanel.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/translations/translationJobs.css', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/translations/translationPanelControls.css', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/translations/translationSourcesPanel.css', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/translations/translationReviewPanel.css', import.meta.url), 'utf8'),
].join('\n')

function cssBlock(selector) {
  const pattern = new RegExp(`${selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*\\{([\\s\\S]*?)\\n\\}`)
  const match = mainCss.match(pattern)
  assert.ok(match, `${selector} should exist in main.css`)
  return match[1]
}

function cssRuleBlock(source, selector) {
  const pattern = new RegExp(`${selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*\\{([^}]*)\\}`)
  const match = source.match(pattern)
  assert.ok(match, `${selector} should exist`)
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

function rootVar(name) {
  const match = mainCss.match(new RegExp(`${name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}:\\s*([^;]+);`))
  assert.ok(match, `:root should define ${name}`)
  return match[1].trim()
}

function productionStyleFiles(dirUrl = new URL('../', import.meta.url)) {
  return readdirSync(dirUrl, { withFileTypes: true }).flatMap((entry) => {
    const entryUrl = new URL(entry.name + (entry.isDirectory() ? '/' : ''), dirUrl)
    if (entry.isDirectory()) return productionStyleFiles(entryUrl)
    if (!/\.(css|vue)$/.test(entry.name)) return []
    return [entryUrl]
  })
}

test('root defaults stay aligned with every light theme runtime token', () => {
  for (const [token, value] of Object.entries(THEMES['apple-light'].vars)) {
    assert.equal(rootVar(token), value, `${token} should match apple-light before applyTheme() runs`)
  }
})

test('global motion and radius tokens use the shared glass contract', () => {
  const expectedSharedTokens = {
    '--ease-pro': 'cubic-bezier(0.16, 1, 0.3, 1)',
    '--transition-pro': 'transform var(--motion-standard), opacity var(--motion-fast)',
    '--motion-fast': '140ms var(--ease-pro)',
    '--motion-standard': '260ms var(--ease-pro)',
    '--motion-emphasized': '420ms var(--ease-pro)',
    '--motion-reveal': '380ms var(--ease-pro)',
    '--radius-xs': '6px',
    '--radius-sm': '8px',
    '--radius-md': '12px',
    '--radius-lg': '16px',
    '--radius-xl': '20px',
    '--radius-card': '22px',
    '--radius-sheet': '28px',
    '--radius-control': '12px',
    '--radius-pill': '999px',
  }

  for (const [token, value] of Object.entries(expectedSharedTokens)) {
    assert.equal(rootVar(token), value, `:root should define ${token} from the shared contract`)
    for (const [themeKey, theme] of Object.entries(THEMES)) {
      assert.equal(theme.vars[token], value, `${themeKey} should share ${token}`)
    }
  }

  const globalMotionBlocks = [
    cssBlock('.skip-link'),
    cssBlock('.badge'),
    cssBlock('.btn'),
    cssBlock('.glass-select__button'),
    cssBlock('.glass-select__option'),
    cssBlock('.av-card'),
    cssBlock('.apple-reveal'),
    cssBlock('.progress-bar-fill'),
  ].join('\n')

  assert.doesNotMatch(globalMotionBlocks, /(?:0\.[0-9]+s|[1-9]\d+ms)\s+cubic-bezier\(/)
  assert.doesNotMatch(globalMotionBlocks, /(?:0\.[0-9]+s|[1-9]\d+ms)\s+ease(?:[;\s,)]|$)/)
  assert.match(cssBlock('.av-card'), /transition:\s*transform var\(--motion-standard\),\s*opacity var\(--motion-fast\)/)
  assert.match(cssBlock('.progress-bar-fill'), /transition:\s*transform var\(--motion-emphasized\)/)
})

test('global glass controls keep material state changes off expensive transition properties', () => {
  const compositedTransitionPattern = /transition:\s*transform var\(--motion-(?:fast|standard|emphasized)\)(?:,\s*opacity var\(--motion-fast\))?/

  for (const selector of [
    '.badge',
    '.btn',
    '.glass-select__button',
    '.glass-select__option',
    '.el-input__wrapper, .input',
    '.el-input__wrapper, .el-textarea__inner, .el-select .el-input__wrapper',
  ]) {
    const block = cssBlock(selector)
    assert.match(block, compositedTransitionPattern, `${selector} should use composited motion tokens`)
    assert.doesNotMatch(block, /transition:[^;]*(?:background|border-color|box-shadow|color|filter|backdrop-filter)/, `${selector} should not animate paint-heavy glass material changes`)
  }
})

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
    '--focus-ring',
    '--focus-ring-strong',
    '--focus-ring-wide',
    '--focus-ring-wide-strong',
    '--focus-ring-inset',
    '--focus-outline',
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
  const buttonFocusBlock = cssBlock('.btn:focus-visible')
  const buttonDisabledBlock = cssBlock('.btn:disabled,\n.btn.btn-disabled')
  const iconButtonBlock = cssBlock('.btn-icon')
  const buttonSvgBlock = cssBlock('.btn svg')
  const smallButtonBlock = cssBlock('.btn-sm')
  const xsmallButtonBlock = cssBlock('.btn-xs')
  const dangerButtonBlock = cssBlock('.btn.danger')
  const dangerButtonHoverBlock = cssBlock('.btn.danger:hover')
  const dangerButtonFocusBlock = cssBlock('.btn.danger:focus-visible')
  const primaryButtonBlock = cssBlock('.btn-primary')
  const primaryButtonHoverBlock = cssBlock('.btn-primary:hover')
  const secondaryButtonBlock = cssBlock('.btn-secondary')
  const secondaryButtonHoverBlock = cssBlock('.btn-secondary:hover')

  assert.match(buttonBlock, /transition:\s*transform var\(--motion-standard\),\s*opacity var\(--motion-fast\)/)
  assert.match(buttonBlock, /letter-spacing:\s*0/)
  assert.doesNotMatch(buttonBlock, /letter-spacing:\s*-0\.01em/)
  assert.match(buttonFocusBlock, /outline:\s*none/)
  assert.match(buttonFocusBlock, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(buttonFocusBlock, /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--material-glass-control-hover\)/)
  assert.match(buttonFocusBlock, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/)
  assert.doesNotMatch(buttonFocusBlock, /box-shadow:\s*0 0 0 4px rgba\(var\(--accent-rgb\),\s*0\.16\)/)
  assert.match(buttonDisabledBlock, /cursor:\s*not-allowed/)
  assert.match(buttonDisabledBlock, /opacity:\s*0\.48/)
  assert.match(buttonDisabledBlock, /transform:\s*none/)
  assert.match(buttonDisabledBlock, /color:\s*var\(--text-muted\)/)
  assert.match(buttonDisabledBlock, /border-color:\s*var\(--glass-control-border\)/)
  assert.match(buttonDisabledBlock, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-control\)/)
  assert.match(buttonDisabledBlock, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(buttonDisabledBlock, /filter:\s*saturate\(0\.82\)/)
  assert.match(iconButtonBlock, /inline-size:\s*var\(--touch-target\)/)
  assert.match(iconButtonBlock, /block-size:\s*var\(--touch-target\)/)
  assert.match(iconButtonBlock, /min-inline-size:\s*var\(--touch-target\)/)
  assert.match(iconButtonBlock, /padding:\s*0/)
  assert.match(iconButtonBlock, /border-radius:\s*50%/)
  assert.match(iconButtonBlock, /aspect-ratio:\s*1/)
  assert.match(buttonSvgBlock, /flex-shrink:\s*0/)
  assert.match(smallButtonBlock, /min-height:\s*36px/)
  assert.match(smallButtonBlock, /padding:\s*7px 12px/)
  assert.match(smallButtonBlock, /font-size:\s*var\(--type-caption\)/)
  assert.match(smallButtonBlock, /line-height:\s*1/)
  assert.match(smallButtonBlock, /letter-spacing:\s*0/)
  assert.match(xsmallButtonBlock, /min-height:\s*28px/)
  assert.match(xsmallButtonBlock, /padding:\s*5px 9px/)
  assert.match(xsmallButtonBlock, /font-size:\s*var\(--type-micro\)/)
  assert.match(xsmallButtonBlock, /line-height:\s*1/)
  assert.match(xsmallButtonBlock, /letter-spacing:\s*0/)
  assert.match(dangerButtonBlock, /color:\s*var\(--badge-error-text\)/)
  assert.match(dangerButtonBlock, /border-color:\s*var\(--badge-error-border\)/)
  assert.match(dangerButtonBlock, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--badge-error-bg\)/)
  assert.match(dangerButtonBlock, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(dangerButtonHoverBlock, /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--badge-error-bg\)/)
  assert.match(dangerButtonHoverBlock, /border-color:\s*var\(--badge-error-border\)/)
  assert.match(dangerButtonHoverBlock, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.match(dangerButtonFocusBlock, /outline:\s*none/)
  assert.match(dangerButtonFocusBlock, /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--badge-error-bg\)/)
  assert.match(dangerButtonFocusBlock, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*0 0 0 3px color-mix\(in srgb,\s*var\(--badge-error-text\) 18%,\s*transparent\)/)
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

  assert.match(secondaryButtonBlock, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-control\)/)
  assert.match(secondaryButtonBlock, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(secondaryButtonBlock, /color:\s*var\(--text-primary\)/)
  assert.match(secondaryButtonBlock, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(secondaryButtonBlock, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(secondaryButtonHoverBlock, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-control-hover\)/)
  assert.match(secondaryButtonHoverBlock, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(secondaryButtonHoverBlock, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.match(cssBlock('.btn-ghost'), /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-control\)/)
  assert.match(cssBlock('.btn-ghost'), /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(cssBlock('.glass-select__button'), /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-control, var\(--glass-control-bg/)
  assert.match(cssBlock('.glass-select__button:focus-visible'), /border-color:\s*var\(--glass-control-border-hover/)
  assert.match(cssBlock('.glass-select__button:focus-visible'), /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--material-glass-control-hover/)
  assert.match(cssBlock('.glass-select__button:focus-visible'), /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/)
  assert.doesNotMatch(cssBlock('.glass-select__button:focus-visible'), /border-color:\s*var\(--accent\)/)
  // 下拉菜单是浮层 chrome，保留玻璃
  assert.match(cssBlock('.glass-select__menu'), /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--material-glass-sheet\)/)
  assert.match(cssBlock('.glass-select__option:hover,\n.glass-select__option.is-active'), /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-control-hover\)/)
  assert.match(cssBlock('.glass-select__option:focus-visible'), /outline:\s*none/)
  assert.match(cssBlock('.glass-select__option:focus-visible'), /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-control-hover\)/)
  assert.match(cssBlock('.glass-select__option:focus-visible'), /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/)
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
  // v2 内容层去玻璃：共享面板 = 实底
  assert.match(appleSurfaceBlock, /background:\s*var\(--card\)/)
  assert.match(appleSurfaceBlock, /border:\s*1px solid var\(--glass-edge\)/)
  assert.match(appleSurfaceBlock, /box-shadow:\s*var\(--shadow-card\)/)
  assert.doesNotMatch(appleSurfaceBlock, /backdrop-filter/)
  assert.match(appleSurfaceAfterBlock, /content:\s*""/)
  assert.match(appleSurfaceAfterBlock, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\)/)
  assert.match(appleSurfaceAfterBlock, /opacity:\s*var\(--surface-overlay-opacity\)/)
  assert.match(appleSurfaceAfterBlock, /pointer-events:\s*none/)
  assert.match(appleSurfaceAfterBlock, /z-index:\s*0/)
  assert.match(appleSurfaceChildBlock, /position:\s*relative/)
  assert.match(appleSurfaceChildBlock, /z-index:\s*1/)
  assert.match(appleSurfaceElevatedBlock, /position:\s*relative/)
  assert.match(appleSurfaceElevatedBlock, /isolation:\s*isolate/)
  assert.match(appleSurfaceElevatedBlock, /background:\s*var\(--card-elevated, var\(--card\)\)/)
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

test('segmented controls stay glass while settings rows use solid content surfaces', () => {
  assert.match(config, /\.settings-tabs\s*\{[\s\S]*background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-control\)[\s\S]*box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(config, /\.appearance-setting-row\s*\{[\s\S]*background:\s*var\(--card-2\)[\s\S]*box-shadow:\s*none/)
  assert.match(config, /\.segmented-mini button\.active\s*\{[\s\S]*background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--glass-active-material\)/)
})

test('native form controls use active glass accents instead of raw theme accent paint', () => {
  for (const [name, source] of [
    ['Config', config],
    ['Candidates', candidates],
    ['TranslationJobs', translationJobs],
  ]) {
    assert.doesNotMatch(source, /accent-color:\s*var\(--accent\)/, `${name} should not use the raw accent color on native controls`)
  }

  assert.match(config, /\.form-group\.checkbox input\s*\{[^}]*accent-color:\s*var\(--glass-active-border\)/)
  assert.match(config, /\.source-check-item input\s*\{[^}]*accent-color:\s*var\(--glass-active-border\)/)
  assert.match(config, /\.threshold-slider\s*\{[^}]*accent-color:\s*var\(--glass-active-border\)/)
  // .candidate-select 在 v2 wave A 重做后已不存在(DownloadCandidatePanel 改海报卡片),
  // 此 assertion 暂时撤掉;negative doesNotMatch 仍会拦截误引入的 raw --accent。
  assert.match(translationJobs, /\.check-row input,\s*[\s\S]*?\.mini-toggle input\s*\{[^}]*accent-color:\s*var\(--glass-active-border\)/)
  assert.match(translationJobs, /\.provider-row input\s*\{[^}]*accent-color:\s*var\(--glass-active-border\)/)
})

test('video modal sheet uses a translucent material without backdrop-filter differences', () => {
  assert.match(videoModal, /--modal-scrim-core:\s*var\(--media-blackout\)/)
  assert.match(videoModal, /--modal-scrim-sheet:\s*color-mix\(in srgb,\s*var\(--media-blackout\) 64%,\s*transparent\)/)
  assert.match(videoModal, /--modal-sheet-bg:\s*var\(--modal-scrim-sheet\)/)
  assert.match(videoModal, /--modal-sheet-fallback:\s*var\(--modal-scrim-sheet\)/)
  assert.match(videoModal, /:root\[data-theme="dark"\]\s+\.modal-overlay\s*\{[\s\S]*--modal-scrim-sheet:\s*color-mix\(in srgb,\s*var\(--media-blackout\) 68%,\s*transparent\)/)
  assert.match(videoModal, /\.modal-container\s*\{[\s\S]*background:[\s\S]*var\(--surface-specular-edge-strong\),[\s\S]*var\(--surface-noise\),[\s\S]*var\(--modal-sheet-bg\)/)
  assert.match(videoModal, /\.modal-container\s*\{[\s\S]*backdrop-filter:\s*none[\s\S]*-webkit-backdrop-filter:\s*none/)
  assert.doesNotMatch(videoModal, /--modal-(?:panel|gallery|overlay)-bg:\s*rgba\(0,\s*0,\s*0/)
})

test('image fallback placeholders use theme glass instead of hardcoded SVG data URLs', () => {
  for (const [name, source] of [
    ['ActressCard', actressCard],
    ['VideoModal', videoModal],
    ['Actor', actor],
    ['Subscription', subscription],
  ]) {
    assert.doesNotMatch(source, /data:image\/svg\+xml/, `${name} should not inject hardcoded SVG fallbacks`)
    assert.match(source, /applyImageFallback/, `${name} should use the shared image fallback helper`)
    assert.doesNotMatch(source, /\$event\.target\.style\.display\s*=\s*['"]none['"]/, `${name} should not hide failed media`)
    assert.doesNotMatch(source, /\$event\.target\.src\s*=/, `${name} should not rewrite failed media inline`)
  }

  const fallbackBlock = cssBlock('.image-fallback')
  // v2 内容层去玻璃：媒体占位 = 实底
  assert.match(fallbackBlock, /background:\s*var\(--card-2, var\(--card\)\)/)
  assert.match(fallbackBlock, /border:\s*1px solid var\(--hairline\)/)
  assert.match(fallbackBlock, /box-shadow:\s*none/)
  assert.match(fallbackBlock, /color:\s*var\(--text-muted\)/)
  assert.doesNotMatch(fallbackBlock, /background:\s*var\(--material-glass-subtle\);/)
  assert.doesNotMatch(fallbackBlock, /#|rgba\(0,\s*0,\s*0|rgba\(255,\s*255,\s*255/)
})

test('secondary utility controls avoid one-off fog materials', () => {
  // year-nav 是 fixed 浮动 chrome，保留玻璃
  const actorYearNav = sourceBlock(actor, '.year-nav')
  assert.match(actorYearNav, /background:[\s\S]*var\(--material-glass-sheet\)/)
  assert.match(actorYearNav, /var\(--surface-specular-edge-strong\)/)
  assert.match(actorYearNav, /var\(--surface-noise\)/)
  assert.match(actorYearNav, /backdrop-filter:\s*blur\(var\(--glass-blur-sheet\)\)/)
  assert.match(downloads, /\.dialog-close-btn\s*\{[\s\S]*background:[\s\S]*var\(--material-glass-control\)[\s\S]*box-shadow:\s*var\(--glass-control-shadow\)/)
})

test('page status colors use semantic badge tokens instead of hardcoded hues', () => {
  const bannedStatusPaint = /(?:#(?:ef5350|fa8c16|52c41a|32D74B|32d74b|b45309|f87171|4ade80)|rgba\((?:239,\s*68,\s*68|34,\s*197,\s*94|245,\s*158,\s*11|244,\s*63,\s*94|255,\s*181,\s*71))/i
  for (const [name, source] of [
    ['Actor', actor],
    ['Config', config],
    ['Downloads', downloads],
    ['Candidates', candidates],
    ['Subscription', subscription],
  ]) {
    assert.doesNotMatch(source, bannedStatusPaint, `${name} should use badge semantic status tokens`)
  }
})

test('global semantic badge utilities use layered liquid glass materials', () => {
  for (const [selector, token, textToken, borderToken] of [
    ['.badge-success', '--badge-success-bg', '--badge-success-text', '--badge-success-border'],
    ['.badge-warning', '--badge-warning-bg', '--badge-warning-text', '--badge-warning-border'],
    ['.badge-error', '--badge-error-bg', '--badge-error-text', '--badge-error-border'],
    ['.badge-info', '--badge-info-bg', '--badge-info-text', '--badge-info-border'],
    ['.badge-pending', '--badge-pending-bg', '--badge-pending-text', '--badge-pending-border'],
  ]) {
    const block = cssRuleBlock(mainCss, selector)

    assert.match(block, new RegExp(`background:\\s*var\\(--surface-specular-edge\\),\\s*var\\(--surface-noise\\),\\s*var\\(${token}\\)`))
    assert.match(block, new RegExp(`color:\\s*var\\(${textToken}\\)`))
    assert.match(block, new RegExp(`border:\\s*1px solid var\\(${borderToken}\\)`))
  }
})

test('production semantic badge surfaces avoid single-layer fills', () => {
  const offenders = []
  const singleLayerBadge = /^\s*background:\s*var\(--badge-(?:success|warning|error|info|pending)-bg\);\s*$/gm

  for (const fileUrl of productionStyleFiles()) {
    const source = readFileSync(fileUrl, 'utf8')
    for (const match of source.matchAll(singleLayerBadge)) {
      const line = source.slice(0, match.index).split('\n').length
      offenders.push(`${fileUrl.pathname.replace(/^.*\/frontend\/src\//, 'frontend/src/')}:${line}:${match[0].trim()}`)
    }
  }

  assert.deepEqual(offenders, [])
})

test('production backdrop blur uses shared glass tokens', () => {
  const offenders = []
  const hardcodedBlur = /^\s*(?:-webkit-)?backdrop-filter:\s*blur\((?!var\(|0\))[^)]*\)[^;]*;\s*$/gm

  for (const fileUrl of productionStyleFiles()) {
    const name = fileUrl.pathname.replace(/^.*\/frontend\/src\//, 'frontend/src/')
    const source = readFileSync(fileUrl, 'utf8')
    for (const match of source.matchAll(hardcodedBlur)) {
      const line = source.slice(0, match.index).split('\n').length
      offenders.push(`${name}:${line}:${match[0].trim()}`)
    }
  }

  // 历史 token 债基线:ratchet 锁当前计数、挡新增;裸 blur(px) 待专门精修轮迁成 --glass-blur-* token。
  assert.equal(offenders.length, 2, offenders.join('\n'))
})

test('production stacking layers use the shared z-index scale', () => {
  const offenders = []
  const hardcodedZIndex = /z-index:\s*(-?\d+)\b/g

  for (const fileUrl of productionStyleFiles()) {
    const source = readFileSync(fileUrl, 'utf8')
    for (const match of source.matchAll(hardcodedZIndex)) {
      const value = Number(match[1])
      if (Math.abs(value) <= 3) continue
      const line = source.slice(0, match.index).split('\n').length
      offenders.push(`${fileUrl.pathname.replace(/^.*\/frontend\/src\//, 'frontend/src/')}:${line}:z-index: ${value}`)
    }
  }

  assert.deepEqual(offenders, [])
})

test('download metrics use solid v2 content surfaces', () => {
  const statCardBlock = sourceBlock(downloads, '.stat-card')
  const statCardHoverBlock = sourceBlock(downloads, '.stat-card:hover')
  const statIconBlock = sourceBlock(downloads, '.stat-icon')

  // v2 内容层去玻璃：仪表盘统计卡 = 实底（--card + --hairline），对齐 Today
  assert.match(statCardBlock, /background:\s*var\(--card\)/)
  assert.match(statCardBlock, /border:\s*1px solid var\(--hairline\)/)
  assert.doesNotMatch(statCardBlock, /backdrop-filter/)
  assert.match(statCardHoverBlock, /border-color:\s*var\(--hairline-strong\)/)
  assert.match(statCardHoverBlock, /box-shadow:\s*var\(--shadow-card\)/)
  assert.doesNotMatch(statCardBlock, /blur\(20px\)|var\(--surface-control\)|var\(--bg-card\)|rgba\(255,\s*255,\s*255,\s*0\.05\)/)

  assert.match(statIconBlock, /background:\s*var\(--card-2, var\(--card\)\)/)
  assert.match(statIconBlock, /border:\s*1px solid var\(--hairline\)/)
  assert.doesNotMatch(statIconBlock, /!important|rgba\(255,\s*255,\s*255|backdrop-filter/)
})

test('translation jobs workbench separates solid content surfaces from glass controls', () => {
  const segmentedBlock = sourceBlock(translationJobs, '.segmented-control')
  const segmentedActiveBlock = sourceBlock(translationJobs, '.segmented-control button.active')
  const overviewSurfaceBlock = translationJobs.match(/\.coverage-hero,\n\.metadata-overview,\n\.signal-card,\n\.job-control-card\s*\{([\s\S]*?)\n\}/)?.[1] || ''
  const inputBlock = sourceBlock(translationJobs, '.input')
  const inputFocusBlock = sourceBlock(translationJobs, '.input:focus')
  const noticeBlock = sourceBlock(translationJobs, '.notice-row')
  const reviewStatsBlock = sourceBlock(translationJobs, '.review-stats div')

  assert.match(segmentedBlock, backgroundIncludes('material-glass-control'))
  assert.match(segmentedBlock, /var\(--surface-specular-edge\)/)
  assert.match(segmentedBlock, /var\(--surface-noise\)/)
  assert.match(segmentedBlock, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(segmentedBlock, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(segmentedBlock, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(segmentedActiveBlock, backgroundIncludes('glass-active-material'))
  assert.match(segmentedActiveBlock, /var\(--surface-specular-edge-strong\)/)
  assert.match(segmentedActiveBlock, /var\(--surface-noise\)/)
  assert.match(segmentedActiveBlock, /box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.doesNotMatch(segmentedBlock, /rgba\(255,\s*255,\s*255,\s*0\.045\)/)
  assert.doesNotMatch(segmentedActiveBlock, /rgba\(255,\s*255,\s*255,\s*0\.12\)/)

  assert.match(overviewSurfaceBlock, /background:\s*var\(--card\)/)
  assert.match(overviewSurfaceBlock, /border:\s*1px solid var\(--hairline\)/)
  assert.match(overviewSurfaceBlock, /box-shadow:\s*var\(--shadow-card\)/)
  assert.doesNotMatch(overviewSurfaceBlock, /material-glass|surface-specular-edge|surface-noise|backdrop-filter/)
  assert.doesNotMatch(overviewSurfaceBlock, /var\(--surface-control\)|var\(--border\)|rgba\(255,\s*255,\s*255,\s*0\.035\)/)

  for (const block of [inputBlock]) {
    assert.match(block, backgroundIncludes('material-glass-control'))
    assert.match(block, /var\(--surface-specular-edge\)/)
    assert.match(block, /var\(--surface-noise\)/)
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)/)
    assert.doesNotMatch(block, /var\(--surface-control\)|rgba\(255,\s*255,\s*255,\s*0\.0[345]\)|var\(--border\)/)
  }

  assert.match(inputFocusBlock, backgroundIncludes('material-glass-control-hover'))
  assert.match(inputFocusBlock, /var\(--surface-specular-edge-strong\)/)
  assert.match(inputFocusBlock, /var\(--surface-noise\)/)
  assert.match(inputFocusBlock, /box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.doesNotMatch(inputFocusBlock, /var\(--surface-input-focus\)/)
})
