import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./ActorPortraitCard.vue', import.meta.url), 'utf8')

function cssRule(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = source.match(new RegExp(`${escaped} \\{([\\s\\S]*?)\\n\\}`))
  assert.ok(match, `Expected CSS rule for ${selector}`)
  return match[1]
}

function exactCssRule(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const matches = Array.from(source.matchAll(new RegExp(`\\n${escaped} \\{([\\s\\S]*?)\\n\\}`, 'g')))
  assert.ok(matches.length, `Expected exact CSS rule for ${selector}`)
  return matches[matches.length - 1][1]
}

function backgroundIncludes(block, token) {
  return new RegExp(`background:\\s*(?:[^;]*,\\s*)*var\\(${token}\\)(?:\\s*,[^;]*)?;`).test(block)
}

function assertLayeredSemanticBackground(block, token, label) {
  assert.ok(backgroundIncludes(block, token), `${label} should keep semantic fill`)
  assert.match(block, /var\(--surface-specular-edge\)/, `${label} should include a specular edge layer`)
  assert.match(block, /var\(--surface-noise\)/, `${label} should include the shared noise layer`)
}

test('ActorPortraitCard exposes the planned public interface', () => {
  assert.match(source, /defineProps\(/)
  for (const prop of [
    'actor',
    'name',
    'subtitle',
    'meta',
    'avatarUrl',
    'badges',
    'density',
    'actionLabel',
    'showFavorite',
    'favorited',
    'showSubscribe',
    'subscribed',
    'subscribeDisabled',
    'subscribeTitle',
  ]) {
    assert.match(source, new RegExp(`${prop}:`), `missing ${prop} prop`)
  }
  assert.match(source, /validator:\s*\(value\)\s*=>\s*\['standard', 'compact'\]\.includes\(value\)/)
})

test('ActorPortraitCard renders accessible lazy portrait media and fallback', () => {
  assert.match(source, /loading="lazy"/)
  assert.match(source, /@error="handleImageError"/)
  assert.match(source, /actor-portrait-card__fallback/)
  assert.match(source, /displayInitial/)
  assert.match(source, /role="button"/)
  assert.match(source, /@keydown\.enter\.prevent="emitOpen"/)
  assert.match(source, /@keydown\.space\.prevent="emitOpen"/)
})

test('ActorPortraitCard shell and portrait well use shared Apple glass surfaces', () => {
  const cardRule = cssRule('.actor-portrait-card')
  const hoverRule = cssRule('.actor-portrait-card:hover')
  const focusRule = cssRule('.actor-portrait-card:focus-visible')
  const mediaRule = cssRule('.actor-portrait-card__media')

  assert.match(cardRule, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-control\)/)
  assert.match(cardRule, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(cardRule, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(cardRule, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)

  assert.match(hoverRule, /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--material-glass-control-hover\)/)
  assert.match(hoverRule, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(hoverRule, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)

  assert.match(focusRule, /var\(--glass-active-shadow\)/)

  assert.match(mediaRule, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-subtle\)/)
  assert.match(mediaRule, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(mediaRule, /box-shadow:\s*var\(--glass-inner-shadow\)/)
  assert.doesNotMatch(mediaRule, /background:\s*var\(--material-glass-subtle\);/)

  for (const rule of [cardRule, hoverRule, mediaRule]) {
    assert.doesNotMatch(rule, /var\(--surface-card\)|var\(--surface-card-hover\)|var\(--shadow-card\)|rgba\(255,\s*255,\s*255/)
  }

  assert.doesNotMatch(source, /@media \(prefers-color-scheme:\s*dark\)[\s\S]*var\(--surface-card\)/)
})

test('ActorPortraitCard mirrors glass hover motion for keyboard focus and action buttons', () => {
  const focusRule = cssRule('.actor-portrait-card:focus-visible')
  const imageFocusRule = cssRule('.actor-portrait-card:focus-visible .actor-portrait-card__media img')
  const actionFocusRule = cssRule('.actor-portrait-card__favorite:focus-visible,\n.actor-portrait-card__subscribe:focus-visible')
  const actionActiveRule = cssRule('.actor-portrait-card__favorite:active,\n.actor-portrait-card__subscribe:active')

  assert.match(focusRule, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(focusRule, /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--material-glass-control-hover\)/)
  assert.match(focusRule, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring-wide\)/)
  assert.match(imageFocusRule, /transform:\s*scale\(1\.045\)/)

  assert.match(actionFocusRule, /outline:\s*none/)
  assert.match(actionFocusRule, /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--material-glass-control-hover\)/)
  assert.match(actionFocusRule, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(actionFocusRule, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring-strong\)/)
  assert.match(actionActiveRule, /transform:\s*scale\(0\.96\)/)
})

test('ActorPortraitCard emits open and favorite actions separately', () => {
  assert.match(source, /defineEmits\(\['open', 'favorite', 'subscribe'\]\)/)
  assert.match(source, /emit\('open'/)
  assert.match(source, /emit\('favorite'/)
  assert.match(source, /@click\.stop="emitFavorite"/)
  assert.match(source, /@keydown\.enter\.stop\.prevent="emitFavorite"/)
  assert.match(source, /@keydown\.space\.stop\.prevent="emitFavorite"/)
})

test('ActorPortraitCard renders subscribe action only when requested', () => {
  assert.match(source, /v-if="showSubscribe"/)
  assert.match(source, /actor-portrait-card__subscribe/)
})

test('ActorPortraitCard emits subscribe without opening the card', () => {
  assert.match(source, /defineEmits\(\['open', 'favorite', 'subscribe'\]\)/)
  assert.match(source, /emit\('subscribe'/)
  assert.match(source, /@click\.stop="emitSubscribe"/)
  assert.match(source, /@keydown\.enter\.stop\.prevent="emitSubscribe"/)
  assert.match(source, /@keydown\.space\.stop\.prevent="emitSubscribe"/)
})

test('ActorPortraitCard exposes subscribed state accessibly and stylistically', () => {
  const activeSubscribeRule = cssRule('.actor-portrait-card.is-subscribed .actor-portrait-card__subscribe')

  assert.match(source, /:aria-label="subscribeAriaLabel"/)
  assert.match(source, /:title="subscribeButtonTitle"/)
  assert.match(source, /'is-subscribed': subscribed/)
  assert.match(source, /props\.subscribeTitle \|\| \(props\.subscribed \? '取消订阅演员' : '订阅演员'\)/)
  assert.match(source, /:disabled="subscribeDisabled"/)
  assert.ok(backgroundIncludes(activeSubscribeRule, '--badge-success-bg'))
  assert.match(activeSubscribeRule, /var\(--surface-specular-edge\)/)
  assert.match(activeSubscribeRule, /var\(--surface-noise\)/)
  assert.match(activeSubscribeRule, /border-color:\s*var\(--badge-success-border\)/)
  assert.match(activeSubscribeRule, /color:\s*var\(--badge-success-text\)/)
  assert.match(activeSubscribeRule, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.doesNotMatch(activeSubscribeRule, /#fff|#ffffff|rgba\(255,\s*255,\s*255|rgba\(52,\s*199,\s*89/i)
})

test('ActorPortraitCard supports badges and action label for reused actor flows', () => {
  assert.match(source, /v-for="badge in normalizedBadges"/)
  assert.match(source, /actor-portrait-card__badge--/)
  assert.match(source, /actionLabel/)
  const sharedBadgeRule = cssRule('.actor-portrait-card__badge,\n.actor-portrait-card__action')
  const neutralBadgeRule = exactCssRule('.actor-portrait-card__badge--neutral')
  const favoriteBadgeRule = exactCssRule('.actor-portrait-card__badge--favorite')
  const successBadgeRule = cssRule('.actor-portrait-card__badge--subscribed,\n.actor-portrait-card__badge--success')
  const warningBadgeRule = exactCssRule('.actor-portrait-card__badge--warning')
  const actionRule = exactCssRule('.actor-portrait-card__action')

  assert.match(source, /actor-portrait-card__action/)
  assert.match(sharedBadgeRule, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(neutralBadgeRule, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-control\)/)
  assert.match(neutralBadgeRule, /border-color:\s*var\(--glass-control-border\)/)
  assert.match(neutralBadgeRule, /color:\s*var\(--text-secondary\)/)
  assertLayeredSemanticBackground(favoriteBadgeRule, '--badge-error-bg', 'favorite badge')
  assert.match(favoriteBadgeRule, /border-color:\s*var\(--badge-error-border\)/)
  assert.match(favoriteBadgeRule, /color:\s*var\(--badge-error-text\)/)
  assertLayeredSemanticBackground(successBadgeRule, '--badge-success-bg', 'success badge')
  assert.match(successBadgeRule, /border-color:\s*var\(--badge-success-border\)/)
  assert.match(successBadgeRule, /color:\s*var\(--badge-success-text\)/)
  assertLayeredSemanticBackground(warningBadgeRule, '--badge-warning-bg', 'warning badge')
  assert.match(warningBadgeRule, /border-color:\s*var\(--badge-warning-border\)/)
  assert.match(warningBadgeRule, /color:\s*var\(--badge-warning-text\)/)
  for (const [rule, name] of [
    [favoriteBadgeRule, 'favorite badge'],
    [successBadgeRule, 'success badge'],
    [warningBadgeRule, 'warning badge'],
  ]) {
    assert.doesNotMatch(rule, /#ff375f|#188038|#946200|rgba\(/i, `${name} should use semantic tokens`)
  }
  assert.match(actionRule, /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--glass-active-material\)/)
  assert.match(actionRule, /color:\s*var\(--text-primary\)/)
  assert.match(actionRule, /border:\s*1px solid var\(--glass-active-border\)/)
  assert.match(actionRule, /box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.match(actionRule, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.doesNotMatch(actionRule, /background:\s*var\(--accent\)|color:\s*var\(--text-on-accent\)/)
})

test('ActorPortraitCard suppresses duplicate subtitle text', () => {
  assert.match(source, /rawSubtitle/)
  assert.match(source, /rawSubtitle\.value && rawSubtitle\.value !== displayNameText\.value/)
})

test('ActorPortraitCard keeps unfavorited heart neutral and reserves red for active favorites', () => {
  const sharedActionRule = cssRule('.actor-portrait-card__favorite,\n.actor-portrait-card__subscribe')
  const favoriteRule = cssRule('.actor-portrait-card__favorite')
  const subscribeRule = exactCssRule('.actor-portrait-card__subscribe')
  const activeFavoriteRule = cssRule('.actor-portrait-card.is-favorited .actor-portrait-card__favorite')

  assert.match(source, /:fill="favorited \? 'currentColor' : 'none'"/)
  assert.match(source, /class="actor-portrait-card__favorite"[\s\S]*stroke="currentColor"/)
  assert.match(sharedActionRule, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-sheet\)/)
  assert.match(sharedActionRule, /border:\s*1px solid var\(--glass-edge\)/)
  assert.match(sharedActionRule, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(sharedActionRule, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.doesNotMatch(sharedActionRule, /rgba\(255,\s*255,\s*255|rgba\(255,255,255/)
  assert.doesNotMatch(sharedActionRule, /color:\s*#ff375f/)
  assert.doesNotMatch(favoriteRule, /color:\s*#ff375f/)
  assert.match(favoriteRule, /color:\s*var\(--text-muted\)/)
  assert.match(subscribeRule, /color:\s*var\(--text-muted\)/)
  assert.doesNotMatch(subscribeRule, /color:\s*var\(--accent\)/)
  assert.ok(backgroundIncludes(activeFavoriteRule, '--badge-error-bg'))
  assert.match(activeFavoriteRule, /var\(--surface-specular-edge\)/)
  assert.match(activeFavoriteRule, /var\(--surface-noise\)/)
  assert.match(activeFavoriteRule, /border-color:\s*var\(--badge-error-border\)/)
  assert.match(activeFavoriteRule, /color:\s*var\(--badge-error-text\)/)
  assert.match(activeFavoriteRule, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.doesNotMatch(activeFavoriteRule, /#fff|#ffffff|rgba\(255,\s*255,\s*255|rgba\(255,\s*55,\s*95/i)
})

test('ActorPortraitCard active quick actions preserve semantic layered glass on hover and focus', () => {
  const activeFavoriteHover = cssRule('.actor-portrait-card.is-favorited .actor-portrait-card__favorite:hover')
  const activeFavoriteFocus = cssRule('.actor-portrait-card.is-favorited .actor-portrait-card__favorite:focus-visible')
  const activeSubscribeHover = cssRule('.actor-portrait-card.is-subscribed .actor-portrait-card__subscribe:hover')
  const activeSubscribeFocus = cssRule('.actor-portrait-card.is-subscribed .actor-portrait-card__subscribe:focus-visible')

  for (const [block, token, border, name] of [
    [activeFavoriteHover, '--badge-error-bg', '--badge-error-border', 'favorite hover'],
    [activeFavoriteFocus, '--badge-error-bg', '--badge-error-border', 'favorite focus'],
    [activeSubscribeHover, '--badge-success-bg', '--badge-success-border', 'subscribe hover'],
    [activeSubscribeFocus, '--badge-success-bg', '--badge-success-border', 'subscribe focus'],
  ]) {
    assert.ok(backgroundIncludes(block, token), `${name} should keep semantic fill`)
    assert.match(block, /var\(--surface-specular-edge-strong\)/, `${name} should strengthen the glass edge`)
    assert.match(block, /var\(--surface-noise\)/, `${name} should preserve texture`)
    assert.match(block, new RegExp(`border-color:\\s*var\\(${border}\\)`), `${name} should keep semantic border`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\)/, `${name} should keep hover depth`)
    assert.match(block, /transform:\s*scale\(1\.07\)/, `${name} should keep tactile lift`)
  }

  assert.match(activeFavoriteFocus, /outline:\s*none/)
  assert.match(activeFavoriteFocus, /0 0 0 3px color-mix\(in srgb,\s*var\(--badge-error-text\) 18%,\s*transparent\)/)
  assert.match(activeSubscribeFocus, /outline:\s*none/)
  assert.match(activeSubscribeFocus, /0 0 0 3px color-mix\(in srgb,\s*var\(--badge-success-text\) 18%,\s*transparent\)/)
  assert.doesNotMatch(`${activeFavoriteFocus}\n${activeSubscribeFocus}`, /rgba\(var\(--accent-rgb\)|rgba\(var\(--error-rgb\)/)
})
