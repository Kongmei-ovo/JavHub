import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./Entities.vue', import.meta.url), 'utf8')
const actorPortraitCard = readFileSync(new URL('../components/ActorPortraitCard.vue', import.meta.url), 'utf8')

function cssRule(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = source.match(new RegExp(`${escaped} \\{([\\s\\S]*?)\\n\\}`))
  assert.ok(match, `Expected CSS rule for ${selector}`)
  return match[1]
}

test('entities portrait directories reuse actor portrait cards with API image fields', () => {
  assert.match(source, /import ActorPortraitCard from '\.\.\/components\/ActorPortraitCard\.vue'/)
  assert.match(source, /import \{ actressImgUrl \} from '\.\.\/utils\/imageUrl\.js'/)
  assert.match(source, /components:\s*\{\s*ActorPortraitCard\s*\}/)
  assert.match(source, /<ActorPortraitCard[\s\S]*v-for="item in items"/)
  assert.match(source, /:actor="entityActorCard\(item\)"/)
  assert.match(source, /:name="displayName\(item\)"/)
  assert.match(source, /:subtitle="secondaryName\(item\)"/)
  assert.match(source, /:avatar-url="entityAvatarUrl\(item\)"/)
  assert.match(source, /:meta="entityMeta\(item\) \|\| activeConfig\.label"/)
  assert.match(source, /:show-favorite="canFavoriteEntity"/)
  assert.match(source, /:favorited="canFavoriteEntity && isEntityFavorited\(item\)"/)
  assert.match(source, /@open="openEntity\(item\)"/)
  assert.match(source, /@favorite="toggleEntityFavorite\(item\)"/)
  assert.match(source, /entityAvatarUrl\(item\)/)
  assert.match(source, /item\.image_url \|\| item\.avatar_url \|\| item\.javinfo_avatar_url/)
})

test('entities separates JavInfo data actors from Emby library actors in labels and favorites', () => {
  assert.match(source, /key: 'actresses'[\s\S]*label: '资料库演员'[\s\S]*favorite: true/)
  assert.match(source, /key: 'actors'[\s\S]*label: 'Emby演员'[\s\S]*favorite: false/)
  assert.match(source, /canFavoriteEntity\(\) \{[\s\S]*return this\.activeConfig\.favorite !== false/)
  assert.match(source, /v-if="canFavoriteEntity"[\s\S]*class="entity-list-card__favorite"/)
  assert.match(source, /async toggleEntityFavorite\(item\) \{[\s\S]*if \(!this\.canFavoriteEntity\) return false/)
})

test('entities portrait cards delegate image fallback to the shared card', () => {
  assert.match(actorPortraitCard, /actor-portrait-card__fallback/)
  assert.match(actorPortraitCard, /@error="handleImageError"/)
  assert.doesNotMatch(source, /imageFailures: new Set\(\)/)
  assert.doesNotMatch(source, /markImageFailed\(item\)/)
  assert.doesNotMatch(source, /class="entity-card__favorite"/)
})

test('people entities render portrait media cards while metadata stays text-only', () => {
  assert.match(source, /v-if="usesPortraitCards"/)
  assert.match(source, /v-else :class="\['entity-list-grid', \{ 'entity-list-grid--wide': usesWideTextCards \}\]"/)
  assert.match(source, /usesPortraitCards\(\) \{[\s\S]*return this\.activeConfig\.portrait === true/)
  assert.match(source, /key: 'actresses'[\s\S]*portrait: true/)
  assert.match(source, /key: 'actors'[\s\S]*loader: 'listInventoryActors', paged: true, portrait: true, inventoryRoute: true, favorite: false/)
  assert.match(source, /key: 'categories'[\s\S]*loader: 'listCategories', paged: false \}/)
})

test('entities actor tab uses inventory actors so portraits can come from Emby', () => {
  assert.match(source, /listInventoryActors: \(_page, _pageSize, options\) => api\.listInventoryActors\(\{/)
  assert.match(source, /search: options\.q/)
  assert.match(source, /sort_by: 'total_videos'/)
  assert.match(source, /sort_order: 'desc'/)
  assert.match(source, /if \(cfg\.inventoryRoute\) \{[\s\S]*\/inventory\/actors\/\$\{encodeURIComponent\(String\(value\)\)\}/)
})

test('entities page keeps chrome lean and hides raw ids', () => {
  assert.doesNotMatch(source, /<p>\{\{ heroDescription \}\}<\/p>/)
  assert.doesNotMatch(source, /heroDescription\(\)/)
  assert.doesNotMatch(source, /当前目录/)
  assert.doesNotMatch(source, /\.entities-hero__metrics div/)
  assert.doesNotMatch(source, /ID \$\{id\}/)
  assert.doesNotMatch(source, /点击查看相关作品/)
  assert.match(source, /entityActorCard\(item\)/)
  assert.doesNotMatch(source, /entityInitial\(item\)/)
})

test('text entity cards wrap full long series and metadata names', () => {
  const titleRule = cssRule('.entity-list-card__open strong')
  const subtitleRule = cssRule('.entity-list-card__subtitle')

  assert.match(source, /:class="\['entity-list-grid', \{ 'entity-list-grid--wide': usesWideTextCards \}\]"/)
  assert.match(source, /key: 'series'[\s\S]*wideText: true/)
  assert.match(source, /usesWideTextCards\(\) \{[\s\S]*return this\.activeConfig\.wideText === true/)
  assert.match(source, /grid-template-columns: repeat\(auto-fill, minmax\(320px, 1fr\)\)/)
  assert.match(source, /\.entity-list-grid--wide[\s\S]*grid-template-columns: repeat\(auto-fit, minmax\(min\(100%, 420px\), 1fr\)\)/)
  assert.match(titleRule, /white-space: normal/)
  assert.match(titleRule, /overflow-wrap: anywhere/)
  assert.match(subtitleRule, /white-space: normal/)
  assert.match(subtitleRule, /overflow-wrap: anywhere/)
  assert.doesNotMatch(titleRule, /line-clamp/)
  assert.doesNotMatch(subtitleRule, /line-clamp/)
})

test('entities directory uses an Apple-style media-first grid and glass controls', () => {
  assert.match(source, /class="entities-hero apple-surface"/)
  assert.match(source, /class="entity-tab-count"/)
  assert.match(source, /:show-favorite="canFavoriteEntity"/)
  assert.match(source, /backdrop-filter: blur/)
  assert.match(actorPortraitCard, /aspect-ratio: 3 \/ 4/)
  assert.match(source, /:global\(:root\[data-theme="dark"\] \.entities-hero\)/)
})
