import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const vueSource = readFileSync(new URL('./Subscription.vue', import.meta.url), 'utf8')
const externalStyle = readFileSync(new URL('../features/subscription/subscription.css', import.meta.url), 'utf8')
const filterStyle = readFileSync(new URL('../features/subscription/subscriptionFilter.css', import.meta.url), 'utf8')
const source = `${vueSource}\n${externalStyle}\n${filterStyle}`

function cssBlock(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = source.match(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`))
  assert.ok(match, `${selector} should exist`)
  return match[1]
}

function layeredSemanticBackground(token) {
  return new RegExp(`background:\\s*var\\(--surface-specular-edge\\),\\s*var\\(--surface-noise\\),\\s*var\\(--${token}\\)`)
}

function cssGroupedBlock(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = source.match(new RegExp(`${escaped}[\\s\\S]*?\\{([^}]*)\\}`))
  assert.ok(match, `${selector} should exist`)
  return match[1]
}

test('subscription page keeps large scoped styles in a feature stylesheet', () => {
  assert.match(vueSource, /<style scoped src="\.\.\/features\/subscription\/subscription\.css"><\/style>/)
  assert.match(vueSource, /<style scoped src="\.\.\/features\/subscription\/subscriptionFilter\.css"><\/style>/)
  assert.ok(vueSource.split('\n').length < 600, 'Subscription.vue should stay below 600 lines')
  assert.ok(externalStyle.split('\n').length > 530, 'external stylesheet should contain the moved subscription styles')
})

test('subscription chrome and sheets use shared Apple glass controls', () => {
  const pageBlock = cssBlock('.sub-page')
  const sheetOverlayBlock = cssBlock('.sheet-overlay')
  const sheetBlock = cssBlock('.sheet')
  const sheetTopBarBlock = cssBlock('.sheet-top-bar')

  for (const block of [pageBlock, sheetOverlayBlock]) {
    assert.match(block, /--subscription-control-bg:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-control\)/)
    assert.match(block, /--subscription-control-bg-hover:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--material-glass-control-hover\)/)
    assert.match(block, /--subscription-active-bg:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--glass-active-material\)/)
    assert.match(block, /--subscription-active-bg-hover:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--material-glass-control-hover\)/)
    assert.match(block, /--subscription-sheet-bg:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-sheet\)/)
    assert.match(block, /--subscription-sticky-bg:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-elevated\)/)
  }
  assert.match(pageBlock, /--subscription-control-border:\s*var\(--glass-control-border\)/)
  assert.match(pageBlock, /--subscription-control-shadow:\s*var\(--glass-control-shadow\)/)

  for (const selector of [
    '.hero-metrics span',
    '.search-bar',
    '.pill-btn',
    '.top-action-btn',
    '.name-pill',
    '.toggle-pill',
    '.action-btn',
  ]) {
    const block = cssBlock(selector)
    assert.match(block, /background:\s*var\(--subscription-control-bg\)/, `${selector} should use shared glass background`)
    assert.match(block, /border:\s*1px solid var\(--subscription-control-border\)/, `${selector} should use shared glass border`)
    assert.match(block, /box-shadow:\s*var\(--subscription-control-shadow\)/, `${selector} should use shared glass shadow`)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/, `${selector} should use shared control blur`)
    assert.doesNotMatch(block, /rgba\(255,\s*255,\s*255,\s*0\.(?:03|04|05|06|08|1|12)\)|blur\((?:40|80)px\)/, `${selector} should not keep legacy flat white glass`)
  }

  const skeletonCard = cssBlock('.skel-card')
  assert.match(skeletonCard, /background:\s*var\(--card\)/)
  assert.match(skeletonCard, /border:\s*1px solid var\(--hairline\)/)
  assert.match(skeletonCard, /box-shadow:\s*none/)
  assert.doesNotMatch(skeletonCard, /material-glass|surface-specular-edge|surface-noise|backdrop-filter/)

  for (const selector of ['.pill-btn', '.top-action-btn', '.toggle-pill', '.action-btn']) {
    const block = cssBlock(selector)
    assert.doesNotMatch(block, /transition:\s*all\b/, `${selector} should avoid transition-all so theme glass tokens settle correctly`)
    assert.doesNotMatch(block, /transition:[^;]*(?:border-color|box-shadow)/, `${selector} should not transition tokenized glass edges across theme changes`)
  }

  for (const selector of [
    '.pill-btn:hover',
    '.top-action-btn:hover',
    '.toggle-pill:hover',
    '.action-btn:hover',
  ]) {
    const block = cssBlock(selector)
    assert.match(block, /background:\s*var\(--subscription-control-bg-hover\)/, `${selector} should use shared hover material`)
    assert.match(block, /border-color:\s*var\(--subscription-control-border-hover\)/, `${selector} should use shared hover border`)
    assert.match(block, /box-shadow:\s*var\(--subscription-control-shadow-hover\)/, `${selector} should use shared hover shadow`)
  }

  for (const selector of [
    '.clear-btn:focus-visible',
    '.pill-btn:focus-visible',
    '.top-action-btn:focus-visible',
    '.toggle-pill:focus-visible',
    '.action-btn:focus-visible',
  ]) {
    const block = cssBlock(selector)
    assert.match(block, /outline:\s*none/, `${selector} should avoid native focus outlines over glass`)
    assert.match(block, /box-shadow:\s*var\(--subscription-control-shadow-hover\),\s*var\(--focus-ring-wide\)/, `${selector} should use a restrained glass focus ring`)
  }

  for (const selector of [
    '.clear-btn:active',
    '.pill-btn:active',
    '.toggle-pill:active',
  ]) {
    const block = cssBlock(selector)
    assert.match(block, /transform:\s*translateY\(0\)\s*scale\(0\.97\)/, `${selector} should use compact pressed feedback`)
  }

  assert.match(sheetBlock, /background:\s*var\(--subscription-sheet-bg\)/)
  assert.match(sheetBlock, /border:\s*1px solid var\(--subscription-sheet-border\)/)
  assert.match(sheetBlock, /box-shadow:\s*var\(--shadow-sheet\)/)
  assert.match(sheetBlock, /backdrop-filter:\s*blur\(var\(--glass-blur-sheet\)\)/)
  assert.doesNotMatch(sheetBlock, /rgba\(22,\s*22,\s*24,\s*0\.85\)|blur\(80px\)/)

  assert.match(sheetTopBarBlock, /background:\s*var\(--subscription-sticky-bg\)/)
  assert.match(sheetTopBarBlock, /backdrop-filter:\s*blur\(var\(--glass-blur-surface\)\)/)
  assert.doesNotMatch(sheetTopBarBlock, /rgba\(22,\s*22,\s*24,\s*0\.7\)|blur\(20px\)/)
})

test('subscription primary actions use active glass instead of solid accent fills', () => {
  for (const selector of ['.pill-btn-primary', '.top-action-btn.primary', '.action-btn.primary']) {
    const block = cssBlock(selector)
    assert.match(block, /background:\s*var\(--subscription-active-bg\)/, `${selector} should use active glass material`)
    assert.match(block, /color:\s*var\(--text-primary\)/, `${selector} should keep text on glass`)
    assert.match(block, /border-color:\s*var\(--glass-active-border\)/, `${selector} should use active glass border`)
    assert.match(block, /box-shadow:\s*var\(--glass-active-shadow\)/, `${selector} should use active glass shadow`)
    assert.doesNotMatch(block, /background:\s*var\(--accent\)|color:\s*var\(--text-on-accent\)|border-color:\s*transparent/, `${selector} should not keep legacy solid primary styles`)
  }

  for (const selector of ['.pill-btn-primary:hover', '.top-action-btn.primary:hover', '.action-btn.primary:hover']) {
    const block = cssBlock(selector)
    assert.match(block, /background:\s*var\(--subscription-active-bg-hover\)/, `${selector} should use shared hover material`)
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/, `${selector} should use shared hover border`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\)/, `${selector} should use shared hover shadow`)
    assert.doesNotMatch(block, /background:\s*var\(--accent-light\)|color:\s*var\(--text-on-accent\)/, `${selector} should not keep legacy solid hover styles`)
  }
})

test('subscription badges and discovery clear control use semantic glass tokens', () => {
  const badge = cssBlock('.inline-badge')
  const clearButton = cssBlock('.clear-btn')
  const clearButtonHover = cssBlock('.clear-btn:hover')

  assert.match(badge, /border:\s*1px solid var\(--badge-error-border\)/)
  assert.match(badge, layeredSemanticBackground('badge-error-bg'))
  assert.match(badge, /color:\s*var\(--badge-error-text\)/)
  assert.match(badge, /box-shadow:\s*var\(--subscription-control-shadow\)/)
  assert.match(badge, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.doesNotMatch(badge, /#fff|#ffffff|#ff375f/i)

  assert.match(clearButton, /border:\s*1px solid var\(--subscription-control-border\)/)
  assert.match(clearButton, /background:\s*var\(--subscription-control-bg\)/)
  assert.match(clearButton, /box-shadow:\s*var\(--subscription-control-shadow\)/)
  assert.match(clearButton, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.doesNotMatch(clearButton, /background:\s*(?:none|transparent)|border:\s*(?:none|0)/)

  assert.match(clearButtonHover, /background:\s*var\(--subscription-control-bg-hover\)/)
  assert.match(clearButtonHover, /border-color:\s*var\(--subscription-control-border-hover\)/)
  assert.match(clearButtonHover, /box-shadow:\s*var\(--subscription-control-shadow-hover\)/)
})

test('subscription danger actions use semantic error tokens', () => {
  const pageBlock = cssBlock('.sub-page')
  const sheetOverlayBlock = cssBlock('.sheet-overlay')
  const dangerButton = cssBlock('.top-action-btn.danger')
  const dangerHover = cssBlock('.top-action-btn.danger:hover')
  const dangerFocus = cssBlock('.top-action-btn.danger:focus-visible')

  for (const block of [pageBlock, sheetOverlayBlock]) {
    assert.match(block, /--subscription-danger-bg:\s*var\(--badge-error-bg\)/)
    assert.match(block, /--subscription-danger-border:\s*var\(--badge-error-border\)/)
    assert.doesNotMatch(block, /#ff375f/i)
  }

  assert.match(dangerButton, /color:\s*var\(--badge-error-text\)/)
  assert.match(dangerButton, /border-color:\s*var\(--badge-error-border\)/)
  assert.match(dangerButton, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--badge-error-bg\)/)
  assert.doesNotMatch(dangerButton, /#ff375f/i)
  assert.match(dangerHover, /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--badge-error-bg\)/)
  assert.match(dangerHover, /border-color:\s*var\(--badge-error-border\)/)
  assert.match(dangerFocus, /outline:\s*none/)
  assert.match(dangerFocus, /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--badge-error-bg\)/)
  assert.match(dangerFocus, /border-color:\s*var\(--badge-error-border\)/)
  assert.match(dangerFocus, /box-shadow:\s*var\(--subscription-control-shadow-hover\),\s*0 0 0 4px color-mix\(in srgb,\s*var\(--badge-error-text\) 18%,\s*transparent\)/)
  assert.doesNotMatch(dangerFocus, /rgba\(var\(--error-rgb\)|rgba\(var\(--accent-rgb\)/)
})

test('subscription loading spinners use shared glass border tokens', () => {
  const spinnerSmall = cssBlock('.spinner-small')
  const spinnerTiny = cssBlock('.spinner-tiny')

  assert.match(spinnerSmall, /border:\s*2px solid var\(--glass-control-border\)/)
  assert.match(spinnerTiny, /border:\s*1\.5px solid var\(--glass-control-border\)/)
  for (const block of [spinnerSmall, spinnerTiny]) {
    assert.match(block, /border-top-color:\s*var\(--text-primary\)/)
    assert.doesNotMatch(block, /var\(--border\)/)
  }
})

test('subscription liquid glass controls keep inner edge highlights and compact press states', () => {
  for (const [selector, shadowToken] of [
    ['.hero-metrics span', 'subscription-control-shadow'],
    ['.inline-badge', 'subscription-control-shadow'],
    ['.search-bar', 'subscription-control-shadow'],
    ['.clear-btn', 'subscription-control-shadow'],
    ['.pill-btn', 'subscription-control-shadow'],
    ['.sheet', 'shadow-sheet'],
    ['.sheet-top-bar', 'subscription-control-shadow'],
    ['.top-action-btn', 'subscription-control-shadow'],
    ['.sheet-avatar', 'subscription-control-shadow'],
    ['.name-pill', 'subscription-control-shadow'],
    ['.toggle-pill', 'subscription-control-shadow'],
    ['.action-btn', 'subscription-control-shadow'],
  ]) {
    const block = cssBlock(selector)
    assert.match(block, new RegExp(`box-shadow:\\s*var\\(--${shadowToken}\\),\\s*var\\(--glass-inner-shadow\\)`), `${selector} should keep a refractive inner edge`)
  }

  for (const selector of [
    '.top-action-btn:active',
    '.action-btn:active',
  ]) {
    const block = cssBlock(selector)
    assert.match(block, /transform:\s*translateY\(0\)\s*scale\(0\.9[78]\)/, `${selector} should use the same pressed motion as compact controls`)
  }
})

test('subscription sheets expose a liquid grabber and loading shimmer', () => {
  const sheetTopBarBefore = cssBlock('.sheet-top-bar::before')
  const skelCover = cssBlock('.skel-cover')
  const skelLine = cssBlock('.skel-line')
  const skelCoverShine = cssGroupedBlock('.skel-cover::after,')
  const skelLineShine = cssBlock('.skel-line::after')

  assert.match(sheetTopBarBefore, /content:\s*""/)
  assert.match(sheetTopBarBefore, /width:\s*42px/)
  assert.match(sheetTopBarBefore, /height:\s*4px/)
  assert.match(sheetTopBarBefore, /border-radius:\s*999px/)
  assert.match(sheetTopBarBefore, /background:\s*var\(--subscription-control-bg-hover\)/)
  assert.match(sheetTopBarBefore, /box-shadow:\s*var\(--glass-inner-shadow\)/)

  for (const block of [skelCover, skelLine]) {
    assert.match(block, /position:\s*relative/)
    assert.match(block, /overflow:\s*hidden/)
  }

  for (const block of [skelCoverShine, skelLineShine]) {
    assert.match(block, /content:\s*""/)
    assert.match(block, /background:\s*linear-gradient\(100deg,\s*transparent 0%,\s*var\(--skeleton-highlight\) 46%,\s*transparent 72%\)/)
    assert.match(block, /animation:\s*subscription-skeleton-shimmer 1\.8s ease-in-out infinite/)
  }
})

test('subscription empty states are centered glass callouts', () => {
  const emptyState = cssBlock('.empty-state')
  const emptyStateIcon = cssGroupedBlock('.empty-state svg')

  assert.match(emptyState, /max-width:\s*min\(520px,\s*100%\)/)
  assert.match(emptyState, /margin:\s*36px auto/)
  assert.match(emptyState, /border:\s*1px solid var\(--subscription-control-border\)/)
  assert.match(emptyState, /background:\s*var\(--subscription-sheet-bg\)/)
  assert.match(emptyState, /box-shadow:\s*var\(--shadow-card\)/)
  assert.doesNotMatch(emptyState, /backdrop-filter/)

  assert.match(emptyStateIcon, /border:\s*1px solid var\(--subscription-control-border\)/)
  assert.match(emptyStateIcon, /background:\s*var\(--subscription-control-bg\)/)
  assert.match(emptyStateIcon, /box-shadow:\s*var\(--subscription-control-shadow\),\s*var\(--glass-inner-shadow\)/)
})

test('subscription page supports edit mode and bulk unsubscribe management', () => {
  assert.match(vueSource, /subscriptionEditMode/)
  assert.match(vueSource, /selectedSubscriptionIds/)
  assert.match(vueSource, /selectedSubscriptionCount/)
  assert.match(vueSource, /allSubscriptionsSelected/)
  assert.match(vueSource, /toggleSubscriptionEditMode/)
  assert.match(vueSource, /selectAllSubscriptions/)
  assert.match(vueSource, /clearSubscriptionSelection/)
  assert.match(vueSource, /removeSelectedSubscriptions/)
  assert.match(vueSource, /class="subscription-management-bar"[\s\S]*role="toolbar"[\s\S]*aria-label="订阅批量操作"/)
  assert.match(vueSource, /class="subscription-select-button"/)
  assert.match(vueSource, /取消订阅 \{\{ selectedSubscriptionCount/)

  const managementBar = cssBlock('.subscription-management-bar')
  const managementSummary = cssBlock('.subscription-management-summary')
  const managementSummaryStrong = cssBlock('.subscription-management-summary strong')
  const subscriptionGridEditing = cssBlock('.card-grid.is-subscription-editing')
  const selectable = cssBlock('.subscription-selectable')
  const selectableSelected = cssBlock('.subscription-selectable.is-selected')
  const selectButton = cssBlock('.subscription-select-button')
  const selectedSelectButton = cssBlock('.subscription-selectable.is-selected .subscription-select-button')

  assert.match(managementBar, /display:\s*flex/)
  assert.match(managementBar, /justify-content:\s*space-between/)
  assert.match(managementBar, /border:\s*1px solid var\(--subscription-control-border\)/)
  assert.match(managementBar, /background:\s*var\(--subscription-sheet-bg\)/)
  assert.match(managementBar, /box-shadow:\s*var\(--shadow-card\)/)
  assert.match(managementSummary, /display:\s*grid/)
  assert.match(managementSummaryStrong, /font-variant-numeric:\s*tabular-nums/)
  assert.match(subscriptionGridEditing, /user-select:\s*none/)
  assert.match(selectable, /position:\s*relative/)
  assert.match(selectableSelected, /outline:\s*2px solid var\(--glass-active-border\)/)
  assert.match(selectButton, /background:\s*var\(--subscription-control-bg\)/)
  assert.match(selectButton, /box-shadow:\s*var\(--subscription-control-shadow\),\s*var\(--glass-inner-shadow\)/)
  assert.match(selectedSelectButton, /background:\s*var\(--subscription-active-bg\)/)
  assert.match(selectedSelectButton, /border-color:\s*var\(--glass-active-border\)/)
})

test('subscription edit mode supports bulk monitoring and auto policy updates', () => {
  assert.match(vueSource, /class="sheet-top-actions subscription-batch-actions"/)
  assert.match(vueSource, /@click="pauseSelectedSubscriptions"[\s\S]*暂停监控/)
  assert.match(vueSource, /@click="resumeSelectedSubscriptions"[\s\S]*恢复监控/)
  assert.match(vueSource, /@click="enableSelectedAutoDownload"[\s\S]*开启自动策略/)
  assert.match(vueSource, /@click="disableSelectedAutoDownload"[\s\S]*关闭自动策略/)
  assert.match(vueSource, /updateSelectedSubscriptions/)
  assert.match(vueSource, /api\.updateSubscription\(sub\.id,\s*patch\)/)
  assert.match(vueSource, /subs\.value = subs\.value\.map/)
  assert.match(vueSource, /clearSubscriptionSelection\(\)/)

  const batchActions = cssBlock('.subscription-batch-actions')
  assert.match(batchActions, /display:\s*flex/)
  assert.match(batchActions, /flex-wrap:\s*wrap/)
  assert.match(batchActions, /justify-content:\s*flex-end/)
})

test('subscription cards surface since-last additions and open an expanded list', () => {
  assert.match(vueSource, /sinceLastCount/)
  assert.match(vueSource, /sinceLastSummary/)
  assert.match(vueSource, /formatSinceLastElapsed/)
  assert.match(vueSource, /class="subscription-since-chip"/)
  assert.match(vueSource, /aria-label="查看自上次以来新增"/)
  assert.match(vueSource, /@click\.stop="openSinceLastSheet\(sub\)"/)
  assert.match(vueSource, /v-if="sinceLastSheetSub"/)
  assert.match(vueSource, /class="sheet since-last-sheet"/)
  assert.match(vueSource, /自上次以来新增/)
  assert.match(vueSource, /v-for="movie in sinceLastSheetMovies"/)
  assert.match(vueSource, /sinceLastMovieKey/)
  assert.match(vueSource, /新增 \{\{ sinceLastCount\(sub\) \}\}/)
  assert.match(vueSource, /formatSinceLastElapsed\(sub\.last_run_at\)/)

  const chip = cssBlock('.subscription-since-chip')
  const sheet = cssBlock('.since-last-sheet')
  const list = cssBlock('.since-last-list')
  const item = cssBlock('.since-last-item')
  const itemTitle = cssBlock('.since-last-title')
  const itemMeta = cssBlock('.since-last-meta')

  assert.match(chip, /position:\s*absolute/)
  assert.match(chip, /top:\s*10px/)
  assert.match(chip, /right:\s*10px/)
  assert.match(chip, /background:\s*var\(--subscription-active-bg\)/)
  assert.match(chip, /border:\s*1px solid var\(--glass-active-border\)/)
  assert.match(chip, /box-shadow:\s*var\(--glass-active-shadow\),\s*var\(--glass-inner-shadow\)/)
  assert.match(chip, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(sheet, /max-width:\s*620px/)
  assert.match(list, /display:\s*grid/)
  assert.match(item, /background:\s*var\(--subscription-control-bg\)/)
  assert.match(item, /border:\s*1px solid var\(--subscription-control-border\)/)
  assert.match(item, /box-shadow:\s*var\(--subscription-control-shadow\),\s*var\(--glass-inner-shadow\)/)
  assert.match(itemTitle, /font-weight:\s*650/)
  assert.match(itemMeta, /color:\s*var\(--text-muted\)/)
})

test('subscription sheet exposes cadence controls and persists cadence minutes', () => {
  assert.match(vueSource, /cadenceOptions/)
  assert.match(vueSource, /cadenceHours/)
  assert.match(vueSource, /cadenceLabel/)
  assert.match(vueSource, /updateCadence/)
  assert.match(vueSource, /@click="updateCadence\(sheetSub,\s*option\.minutes\)"/)
  assert.match(vueSource, /每 \{\{ cadenceHours\(sheetSub\.cadence_minutes\) \}\} 小时检查/)
  assert.match(vueSource, /api\.updateSubscription\(sub\.id,\s*\{\s*cadence_minutes:\s*minutes\s*\}\)/)
  assert.match(vueSource, /sheetSub\.value = \{\s*\.\.\.sheetSub\.value,\s*cadence_minutes:\s*minutes\s*\}/)
  assert.match(vueSource, /subs\.value = subs\.value\.map\(item => item\.id === sub\.id \? \{ \.\.\.item, cadence_minutes: minutes \} : item\)/)

  const cadence = cssBlock('.cadence-control')
  const cadenceOptions = cssBlock('.cadence-options')
  const cadenceButton = cssBlock('.cadence-option')
  const activeCadenceButton = cssBlock('.cadence-option.is-active')

  assert.match(cadence, /display:\s*grid/)
  assert.match(cadence, /justify-items:\s*center/)
  assert.match(cadenceOptions, /display:\s*flex/)
  assert.match(cadenceOptions, /flex-wrap:\s*wrap/)
  assert.match(cadenceButton, /background:\s*var\(--subscription-control-bg\)/)
  assert.match(cadenceButton, /border:\s*1px solid var\(--subscription-control-border\)/)
  assert.match(cadenceButton, /box-shadow:\s*var\(--subscription-control-shadow\),\s*var\(--glass-inner-shadow\)/)
  assert.match(activeCadenceButton, /background:\s*var\(--subscription-active-bg\)/)
  assert.match(activeCadenceButton, /border-color:\s*var\(--glass-active-border\)/)
})

test('subscription discovery sheet has a default landing and retryable empty search state', () => {
  assert.match(vueSource, /class="discover-kicker"/)
  assert.match(vueSource, /订阅发现/)
  assert.match(vueSource, /class="discover-suggestions"/)
  assert.match(vueSource, /v-else-if="!searched"/)
  assert.match(vueSource, /最近订阅/)
  assert.match(vueSource, /v-for="sub in recentSubscriptions"/)
  assert.match(vueSource, /recentSubscriptions/)
  assert.match(vueSource, /class="empty-state compact"/)
  assert.match(vueSource, /重新搜索/)

  const discoverHead = cssBlock('.discover-head')
  const discoverKicker = cssBlock('.discover-kicker')
  const discoverSuggestions = cssBlock('.discover-suggestions')
  const suggestionChip = cssBlock('.suggestion-chip')
  const compactEmpty = cssBlock('.empty-state.compact')

  assert.match(discoverHead, /text-align:\s*left/)
  assert.match(discoverKicker, /font-size:\s*var\(--type-caption\)/)
  assert.match(discoverKicker, /color:\s*var\(--text-muted\)/)
  assert.match(discoverSuggestions, /display:\s*flex/)
  assert.match(discoverSuggestions, /flex-wrap:\s*wrap/)
  assert.match(suggestionChip, /background:\s*var\(--subscription-control-bg\)/)
  assert.match(suggestionChip, /border:\s*1px solid var\(--subscription-control-border\)/)
  assert.match(suggestionChip, /box-shadow:\s*var\(--subscription-control-shadow\),\s*var\(--glass-inner-shadow\)/)
  assert.match(compactEmpty, /padding:\s*36px 20px/)
  assert.match(compactEmpty, /margin:\s*20px auto/)
})

test('subscription list preloads actor metadata so portraits render on direct entry', () => {
  assert.match(vueSource, /hydrateSubscriptionActorMeta/)
  assert.match(vueSource, /loadSubscriptionActorMetaForSubs/)
  assert.match(vueSource, /await loadSubscriptionActorMetaForSubs\(items\)/)
  assert.match(vueSource, /api\.getActress/)
  assert.match(vueSource, /subCoverUrl\(sub\)/)
})

test('subscription list provides an immediate multilingual filter and a clearable no-match state', () => {
  assert.match(vueSource, /v-model="subscriptionFilterKeyword"/)
  assert.match(vueSource, /placeholder="筛选订阅演员"/)
  assert.match(vueSource, /aria-label="筛选订阅演员"/)
  assert.match(vueSource, /filteredSubscriptions/)
  assert.match(vueSource, /subscriptionMatchesKeyword/)
  assert.match(vueSource, /v-for="sub in filteredSubscriptions"/)
  assert.match(vueSource, /没有匹配演员/)
  assert.match(vueSource, /当前关键词没有匹配到订阅演员/)
  assert.match(vueSource, /@action="clearSubscriptionFilter"/)

  const search = cssBlock('.subscription-list-search')
  const clear = cssBlock('.subscription-list-search-clear')
  assert.match(search, /width:\s*100%/)
  assert.match(search, layeredSemanticBackground('material-glass-control'))
  assert.match(search, /border:\s*1px solid var\(--subscription-control-border\)/)
  assert.match(search, /box-shadow:\s*var\(--subscription-control-shadow\)/)
  assert.match(clear, /border-radius:\s*999px/)
})

test('subscription edit select-all is scoped to visible filtered subscriptions', () => {
  assert.match(vueSource, /filteredSubscriptions\.value\.length > 0/)
  assert.match(vueSource, /filteredSubscriptions\.value\.every/)
  assert.match(vueSource, /for \(const sub of filteredSubscriptions\.value\)/)
  assert.match(vueSource, /new Set\(selectedSubscriptionIds\.value\)/)
})
