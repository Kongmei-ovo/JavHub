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
  assert.match(source, /:aria-label="subscribeAriaLabel"/)
  assert.match(source, /:title="subscribeButtonTitle"/)
  assert.match(source, /'is-subscribed': subscribed/)
  assert.match(source, /props\.subscribeTitle \|\| \(props\.subscribed \? '取消订阅演员' : '订阅演员'\)/)
  assert.match(source, /:disabled="subscribeDisabled"/)
})

test('ActorPortraitCard supports badges and action label for reused actor flows', () => {
  assert.match(source, /v-for="badge in normalizedBadges"/)
  assert.match(source, /actor-portrait-card__badge--/)
  assert.match(source, /actionLabel/)
  assert.match(source, /actor-portrait-card__action/)
})

test('ActorPortraitCard suppresses duplicate subtitle text', () => {
  assert.match(source, /rawSubtitle/)
  assert.match(source, /rawSubtitle\.value && rawSubtitle\.value !== displayNameText\.value/)
})

test('ActorPortraitCard keeps unfavorited heart neutral and reserves red for active favorites', () => {
  const sharedActionRule = cssRule('.actor-portrait-card__favorite,\n.actor-portrait-card__subscribe')
  const favoriteRule = cssRule('.actor-portrait-card__favorite')
  const activeFavoriteRule = cssRule('.actor-portrait-card.is-favorited .actor-portrait-card__favorite')

  assert.match(source, /:fill="favorited \? 'currentColor' : 'none'"/)
  assert.match(source, /class="actor-portrait-card__favorite"[\s\S]*stroke="currentColor"/)
  assert.doesNotMatch(sharedActionRule, /color:\s*#ff375f/)
  assert.doesNotMatch(favoriteRule, /color:\s*#ff375f/)
  assert.match(favoriteRule, /color:\s*var\(--text-muted\)/)
  assert.match(activeFavoriteRule, /background:\s*rgba\(255,\s*55,\s*95,\s*0\.92\)/)
  assert.match(activeFavoriteRule, /color:\s*#fff/)
})
