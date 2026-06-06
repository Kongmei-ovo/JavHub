import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const files = {
  app: readFileSync(new URL('../App.vue', import.meta.url), 'utf8'),
  main: readFileSync(new URL('../assets/main.css', import.meta.url), 'utf8'),
  search: readFileSync(new URL('../features/search/search.css', import.meta.url), 'utf8'),
  home: readFileSync(new URL('../features/home/home.css', import.meta.url), 'utf8'),
  favorites: readFileSync(new URL('../features/favorites/favorites.css', import.meta.url), 'utf8'),
  toastCapsule: readFileSync(new URL('../components/ToastCapsule.vue', import.meta.url), 'utf8'),
  variantGroupDisclosure: readFileSync(new URL('../components/VariantGroupDisclosure.vue', import.meta.url), 'utf8'),
  actorPortraitCard: readFileSync(new URL('../components/ActorPortraitCard.vue', import.meta.url), 'utf8'),
  actor: readFileSync(new URL('../features/actor/actor.css', import.meta.url), 'utf8'),
  subscription: readFileSync(new URL('../features/subscription/subscription.css', import.meta.url), 'utf8'),
  libraryOrganize: readFileSync(new URL('../features/library/libraryOrganize.css', import.meta.url), 'utf8'),
  logs: readFileSync(new URL('./Logs.vue', import.meta.url), 'utf8'),
  supplement: readFileSync(new URL('../features/supplement/supplementManagement.css', import.meta.url), 'utf8'),
  supplementDiagnostics: readFileSync(new URL('../features/supplement/supplementSourceDiagnosticsDialog.css', import.meta.url), 'utf8'),
  operations: readFileSync(new URL('../features/operations/operations.css', import.meta.url), 'utf8'),
  videoModal: readFileSync(new URL('../features/videoModal/videoModal.css', import.meta.url), 'utf8'),
  candidates: readFileSync(new URL('../features/candidates/downloadCandidatePanel.css', import.meta.url), 'utf8'),
  entities: readFileSync(new URL('../features/entities/entities.css', import.meta.url), 'utf8'),
  magnetParse: readFileSync(new URL('./MagnetParse.vue', import.meta.url), 'utf8'),
  config: readFileSync(new URL('../features/config/config.css', import.meta.url), 'utf8'),
  advancedConfig: readFileSync(new URL('../features/config/advancedSettingsPanel.css', import.meta.url), 'utf8'),
  translations: [
    readFileSync(new URL('../features/translations/translationJobs.css', import.meta.url), 'utf8'),
    readFileSync(new URL('../features/translations/translationPanelControls.css', import.meta.url), 'utf8'),
    readFileSync(new URL('../features/translations/translationSourcesPanel.css', import.meta.url), 'utf8'),
    readFileSync(new URL('../features/translations/translationReviewPanel.css', import.meta.url), 'utf8'),
  ].join('\n'),
}

function mobileBlock(source, maxWidth = 768) {
  const start = source.indexOf(`@media (max-width: ${maxWidth}px)`)
  assert.notEqual(start, -1, `expected @media (max-width: ${maxWidth}px) block`)
  const open = source.indexOf('{', start)
  let depth = 0
  for (let index = open; index < source.length; index += 1) {
    if (source[index] === '{') depth += 1
    if (source[index] === '}') depth -= 1
    if (depth === 0) return source.slice(open + 1, index)
  }
  assert.fail(`unterminated @media (max-width: ${maxWidth}px) block`)
}

function allMobileBlocks(source) {
  const blocks = []
  const mediaPattern = /@media\s*\(max-width:\s*(?:980|920|900|860|768|640|560|480)px\)/g
  for (const match of source.matchAll(mediaPattern)) {
    const open = source.indexOf('{', match.index)
    let depth = 0
    for (let index = open; index < source.length; index += 1) {
      if (source[index] === '{') depth += 1
      if (source[index] === '}') depth -= 1
      if (depth === 0) {
        blocks.push(source.slice(open + 1, index))
        break
      }
    }
  }
  return blocks.join('\n')
}

function cssBlocks(source, selector) {
  const blocks = [...source.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
    .filter(([, selectors]) => selectors
      .split(',')
      .map(part => part.trim())
      .includes(selector))
    .map(([, , block]) => block)
  assert.ok(blocks.length, `${selector} should exist`)
  return blocks.join('\n')
}

function mobileCss(fileKey) {
  return allMobileBlocks(files[fileKey])
}

function assertMobileOnlyProperty(fileKey, selector, propertyPattern, label) {
  const block = cssBlocks(mobileCss(fileKey), selector)
  assert.match(block, propertyPattern, label)
}

test('mobile shell reserves iPhone safe area and prevents document-wide horizontal drift', () => {
  const mainMobile = mobileCss('main')
  const appMobile = mobileCss('app')

  assert.match(mainMobile, /--page-bottom-space:\s*calc\(36px \+ 74px \+ env\(safe-area-inset-bottom,\s*0px\)\)/)
  assert.match(mainMobile, /--page-gutter:\s*clamp\(12px,\s*4vw,\s*16px\)/)
  assert.match(mainMobile, /--touch-target:\s*44px\s*!important/)
  assert.match(mainMobile, /html,\s*body,\s*#app\s*\{[\s\S]*overflow-x:\s*clip/)
  assert.match(mainMobile, /\.page-shell,\s*\.page-rail\s*\{[\s\S]*max-width:\s*100%/)
  assert.match(mainMobile, /\.page-bleed\s*\{[\s\S]*overflow-x:\s*clip/)

  assert.match(files.app, /--mobile-bottom-nav-offset:\s*max\(10px,\s*env\(safe-area-inset-bottom,\s*0px\)\)/)
  assert.match(files.app, /--mobile-bottom-nav-reserve:\s*calc\(var\(--mobile-bottom-nav-height\) \+ var\(--mobile-bottom-nav-offset\) \+ 12px\)/)
  assert.match(appMobile, /\.main-content\s*\{[\s\S]*padding-bottom:\s*var\(--mobile-bottom-nav-reserve\)/)
  assert.match(appMobile, /\.bottom-nav\s*\{[\s\S]*padding-bottom:\s*max\(8px,\s*env\(safe-area-inset-bottom,\s*0px\)\)/)
})

test('mobile shared controls use iPhone touch targets without inflating dense cards', () => {
  const mainMobile = mobileCss('main')
  const magnetMobile = mobileCss('magnetParse')
  const favoritesMobile = mobileCss('favorites')

  assert.match(mainMobile, /\.btn,\s*\.btn-mini,\s*\.el-button,\s*\.glass-select__button,\s*\.input\s*\{[\s\S]*min-height:\s*var\(--touch-target\)/)
  assert.match(mainMobile, /\.btn-sm,\s*\.btn-mini,\s*\.segmented-control button,\s*\.tab-btn,\s*\.segment-item\s*\{[\s\S]*min-height:\s*40px/)
  assert.match(mainMobile, /\.results-grid\s*\{[\s\S]*grid-template-columns:\s*repeat\(auto-fit,\s*minmax\(var\(--video-grid-min-mobile\),\s*1fr\)\)/)
  assert.match(mainMobile, /--video-grid-min-mobile:\s*clamp\(126px,\s*42vw,\s*168px\)/)
  assert.match(mainMobile, /--video-grid-gap-mobile:\s*clamp\(9px,\s*2\.8vw,\s*13px\)/)
  assert.match(mainMobile, /--video-card-body-padding-mobile:\s*9px 10px 11px/)
  assert.match(magnetMobile, /\.clear-input-btn,\s*\.clear-results-btn\s*\{[\s\S]*min-height:\s*var\(--touch-target\)/)
  assert.match(favoritesMobile, /\.btn-mini,\s*\.collection-form input\s*\{[\s\S]*min-height:\s*var\(--touch-target\)/)
  assert.match(mobileCss('libraryOrganize'), /\.tab-btn\s*\{[\s\S]*min-height:\s*40px/)
  assert.match(mobileCss('logs'), /\.toolbar input,\s*\.toolbar button\s*\{[\s\S]*min-height:\s*40px/)
  assert.match(mobileCss('logs'), /\.activity-header \.toolbar-btn\s*\{[\s\S]*min-height:\s*40px/)
  assert.match(mobileCss('translations'), /\.segmented-control button\s*\{[\s\S]*min-height:\s*40px/)
  assert.match(mobileCss('actorPortraitCard'), /\.actor-portrait-card__favorite,\s*\.actor-portrait-card__subscribe\s*\{[\s\S]*(?:width:\s*40px[\s\S]*height:\s*40px|inline-size:\s*40px[\s\S]*block-size:\s*40px)/)
  assert.match(mobileCss('config'), /\.settings-sidebar-list \.tab-item\s*\{[\s\S]*min-height:\s*44px/)
  assert.match(mobileCss('config'), /\.settings-footer\s*\{[\s\S]*--settings-mobile-footer-offset:\s*var\(--mobile-bottom-nav-reserve/)
  assert.match(mobileCss('config'), /\.settings-footer\s*\{[\s\S]*bottom:\s*calc\(var\(--settings-mobile-footer-offset\) \+ 8px\)/)
  assert.match(mobileCss('config'), /\.footer-content\s*\{[\s\S]*grid-template-columns:\s*1fr/)
  assert.match(mobileCss('config'), /\.settings-save-actions\s*\{[\s\S]*width:\s*100%/)
  assert.match(mobileCss('config'), /\.input-eye-btn\s*\{[\s\S]*(?:width:\s*40px[\s\S]*height:\s*40px|inline-size:\s*40px[\s\S]*block-size:\s*40px)/)
  assert.match(files.config, /\.input-eye-btn\s*\{[\s\S]*width:\s*36px[\s\S]*height:\s*36px[\s\S]*\}[\s\S]*@media\s*\(max-width:\s*768px\)\s*\{[\s\S]*\.input-eye-btn\s*\{[\s\S]*width:\s*40px[\s\S]*height:\s*40px/)
  assert.match(mobileCss('advancedConfig'), /\.input-eye-btn\s*\{[\s\S]*(?:width:\s*40px[\s\S]*height:\s*40px|inline-size:\s*40px[\s\S]*block-size:\s*40px)/)
  assert.match(mobileCss('actor'), /\.variant-expand-btn,\s*\.year-nav-item\s*\{[\s\S]*min-height:\s*40px/)
  assert.match(mobileCss('operations'), /\.block-head button\s*\{[\s\S]*min-height:\s*40px/)
  assert.match(mobileCss('operations'), /\.quality-progress-action\s*\{[\s\S]*min-height:\s*40px/)
  assert.match(mobileCss('entities'), /\.search-box input\s*\{[\s\S]*min-height:\s*40px/)
  assert.match(mobileCss('toastCapsule'), /\.toast-close\s*\{[\s\S]*width:\s*40px[\s\S]*height:\s*40px/)
  assertMobileOnlyProperty('variantGroupDisclosure', '.variant-group-disclosure__toggle', /min-height:\s*40px/, 'variant toggle should keep a mobile touch target')
  assertMobileOnlyProperty('variantGroupDisclosure', '.variant-group-disclosure__row', /min-height:\s*40px/, 'variant rows should keep mobile touch targets')
})

test('primary mobile pages wrap toolbars and grids instead of creating iPhone overflow', () => {
  const expectations = [
    ['search', '.sort-strip-left', /min-width:\s*0/],
    ['search', '.sort-strip-right', /min-width:\s*0/],
    ['search', '.pagination-bar', /overflow-x:\s*clip/],
    ['home', '.download-tabs', /overflow-x:\s*auto/],
    ['home', '.header-actions', /flex-wrap:\s*wrap/],
    ['favorites', '.segmented-control', /overflow-x:\s*auto/],
    ['actor', '.actor-actions', /flex-wrap:\s*wrap/],
    ['actor', '.supplement-actions', /align-items:\s*stretch/],
    ['subscription', '.hero-actions', /flex-wrap:\s*wrap/],
    ['libraryOrganize', '.organize-workbench', /min-width:\s*0/],
    ['supplement', '.workspace-actions', /flex-wrap:\s*wrap/],
    ['operations', '.header-actions', /grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/],
    ['operations', '.quick-actions', /grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/],
    ['candidates', '.candidate-toolbar', /overflow-x:\s*auto/],
    ['config', '.settings-row', /grid-template-columns:\s*1fr/],
    ['config', '.settings-sidebar', /margin:\s*0/],
    ['config', '.settings-sidebar-list', /max-width:\s*100%/],
    ['translations', '.segmented-control', /overflow-x:\s*auto/],
  ]

  for (const [fileKey, selector, pattern] of expectations) {
    assertMobileOnlyProperty(fileKey, selector, pattern, `${selector} in ${fileKey} should have a mobile overflow guardrail`)
  }
})

test('mobile modal and sheet surfaces leave room for the home indicator', () => {
  assert.match(mobileCss('videoModal'), /\.modal-container\s*\{[\s\S]*max-height:\s*calc\(100dvh - 24px - env\(safe-area-inset-bottom,\s*0px\)\)/)
  assert.match(mobileCss('videoModal'), /\.modal-body\s*\{[\s\S]*padding-bottom:\s*calc\(14px \+ env\(safe-area-inset-bottom,\s*0px\)\)/)
  assert.match(mobileCss('subscription'), /\.sheet\s*\{[\s\S]*padding-bottom:\s*calc\(16px \+ env\(safe-area-inset-bottom,\s*0px\)\)/)
  assert.match(mobileCss('supplementDiagnostics'), /\.diagnostics-panel\s*\{[\s\S]*max-height:\s*calc\(100dvh - 24px - env\(safe-area-inset-bottom,\s*0px\)\)/)
})
