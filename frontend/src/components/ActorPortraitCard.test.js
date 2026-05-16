import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./ActorPortraitCard.vue', import.meta.url), 'utf8')

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
  assert.match(source, /defineEmits\(\['open', 'favorite'\]\)/)
  assert.match(source, /emit\('open'/)
  assert.match(source, /emit\('favorite'/)
  assert.match(source, /@click\.stop="emitFavorite"/)
  assert.match(source, /@keydown\.enter\.stop/)
  assert.match(source, /@keydown\.space\.stop/)
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
