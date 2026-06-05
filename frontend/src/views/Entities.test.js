import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const vueSource = readFileSync(new URL('./Entities.vue', import.meta.url), 'utf8')
const externalStyle = readFileSync(new URL('../features/entities/entities.css', import.meta.url), 'utf8')
const source = `${vueSource}\n${externalStyle}`
const actorPortraitCard = readFileSync(new URL('../components/ActorPortraitCard.vue', import.meta.url), 'utf8')

function cssRule(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = source.match(new RegExp(`${escaped} \\{([\\s\\S]*?)\\n\\}`))
  assert.ok(match, `Expected CSS rule for ${selector}`)
  return match[1]
}

function backgroundIncludes(token) {
  return new RegExp(`background:[\\s\\S]*var\\(--${token}\\)`)
}

function singleLayerGlassBackgrounds(css) {
  return css
    .split('\n')
    .map((line, index) => ({ line: index + 1, text: line.trim() }))
    .filter(({ text }) => /^background:\s*var\(--(?:material-glass-subtle|material-glass-control|material-glass-control-hover|material-glass-elevated|material-glass-sheet|glass-active-material)\);$/.test(text))
}

test('entities page keeps large scoped styles in a feature stylesheet', () => {
  assert.match(vueSource, /<style scoped src="\.\.\/features\/entities\/entities\.css"><\/style>/)
  assert.ok(vueSource.split('\n').length < 420, 'Entities.vue should stay below 420 lines')
  assert.ok(externalStyle.split('\n').length > 500, 'external stylesheet should contain the moved entities styles')
})

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

test('entities directory controls use shared liquid glass tokens without hardcoded theme fog', () => {
  const hero = cssRule('.entities-hero')
  const heroBefore = cssRule('.entities-hero::before')
  const listCard = cssRule('.entity-list-card')
  const listCardHover = cssRule('.entity-list-card:hover')
  const entityTab = cssRule('.entity-tab')
  const entityTabHover = cssRule('.entity-tab:hover')
  const entityTabActive = cssRule('.entity-tab.active')
  const searchBox = cssRule('.search-box')
  const searchFocus = cssRule('.search-box:focus-within')
  const searchClear = cssRule('.search-box button')
  const searchClearHover = cssRule('.search-box button:hover')
  const entityType = cssRule('.entity-list-card__type')
  const favoriteButton = cssRule('.entity-list-card__favorite')
  const favoriteButtonHover = cssRule('.entity-list-card__favorite:hover')
  const favoriteButtonActive = cssRule('.entity-list-card__favorite.active')
  const favoriteButtonActiveHover = cssRule('.entity-list-card__favorite.active:hover')

  assert.match(hero, backgroundIncludes('material-glass-sheet'))
  assert.match(hero, /border:\s*1px solid var\(--glass-edge-strong\)/)
  assert.match(hero, /box-shadow:\s*var\(--glass-surface-shadow\)/)
  assert.match(hero, /backdrop-filter:\s*blur\(var\(--glass-blur-surface\)\)\s*saturate\(var\(--glass-saturate-surface\)\)/)
  assert.doesNotMatch(hero, /rgba\(255,\s*255,\s*255|rgba\(255,255,255|var\(--surface-card\)/)
  assert.match(heroBefore, /--entities-hero-mask-start:\s*var\(--media-edge-mask-strong\)/)
  assert.match(heroBefore, /--entities-hero-mask-end:\s*var\(--media-edge-mask-clear\)/)
  assert.match(heroBefore, /mask-image:\s*linear-gradient\(90deg,\s*var\(--entities-hero-mask-start\),\s*var\(--entities-hero-mask-end\) 72%\)/)
  assert.doesNotMatch(heroBefore, /rgba\(0,\s*0,\s*0|rgba\(0,0,0|#000|#000000/i)

  assert.match(listCard, backgroundIncludes('material-glass-sheet'))
  assert.match(listCard, /border:\s*1px solid var\(--glass-edge-strong\)/)
  assert.match(listCard, /box-shadow:\s*var\(--glass-surface-shadow\)/)
  assert.match(listCard, /backdrop-filter:\s*blur\(var\(--glass-blur-surface\)\)\s*saturate\(var\(--glass-saturate-surface\)\)/)
  assert.doesNotMatch(listCard, /rgba\(255,\s*255,\s*255|rgba\(255,255,255|var\(--surface-card\)/)
  assert.match(listCardHover, backgroundIncludes('material-glass-elevated'))
  assert.match(listCardHover, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(listCardHover, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--glass-surface-shadow\)/)
  assert.doesNotMatch(listCardHover, /var\(--surface-card-hover\)|var\(--shadow-floating\)/)

  assert.match(entityTab, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(entityTab, backgroundIncludes('material-glass-control'))
  assert.match(entityTab, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(entityTab, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(entityTabHover, backgroundIncludes('material-glass-control-hover'))
  assert.match(entityTabHover, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(entityTabHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.match(entityTabActive, /border-color:\s*var\(--glass-active-border\)/)
  assert.match(entityTabActive, backgroundIncludes('glass-active-material'))

  assert.match(searchBox, backgroundIncludes('material-glass-control'))
  assert.match(searchBox, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(searchFocus, backgroundIncludes('material-glass-control-hover'))
  assert.match(searchFocus, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(searchFocus, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*0 0 0 4px rgba\(var\(--accent-rgb\),\s*0\.09\)/)

  assert.match(searchClear, backgroundIncludes('material-glass-subtle'))
  assert.match(searchClear, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(searchClear, /box-shadow:\s*var\(--glass-inner-shadow\)/)
  assert.match(searchClear, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(searchClearHover, backgroundIncludes('material-glass-control-hover'))
  assert.match(searchClearHover, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(searchClearHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)

  assert.match(entityType, backgroundIncludes('material-glass-control'))
  assert.match(entityType, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(entityType, /box-shadow:\s*var\(--glass-inner-shadow\)/)

  assert.match(favoriteButton, backgroundIncludes('material-glass-sheet'))
  assert.match(favoriteButton, /border:\s*1px solid var\(--glass-edge\)/)
  assert.match(favoriteButton, /color:\s*var\(--badge-error-text\)/)
  assert.match(favoriteButton, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(favoriteButton, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(favoriteButtonHover, backgroundIncludes('material-glass-control-hover'))
  assert.match(favoriteButtonHover, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(favoriteButtonHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.match(favoriteButtonActive, backgroundIncludes('badge-error-bg'))
  assert.match(favoriteButtonActive, /var\(--surface-specular-edge\)/)
  assert.match(favoriteButtonActive, /var\(--surface-noise\)/)
  assert.match(favoriteButtonActive, /border-color:\s*var\(--badge-error-border\)/)
  assert.match(favoriteButtonActive, /color:\s*var\(--badge-error-text\)/)
  assert.match(favoriteButtonActiveHover, backgroundIncludes('badge-error-bg'))
  assert.match(favoriteButtonActiveHover, /var\(--surface-specular-edge-strong\)/)
  assert.match(favoriteButtonActiveHover, /var\(--surface-noise\)/)
  assert.match(favoriteButtonActiveHover, /border-color:\s*var\(--badge-error-border\)/)
  assert.doesNotMatch(favoriteButtonActive, /#fff|#ffffff|rgba\(255,\s*55,\s*95/i)

  assert.doesNotMatch(source, /\.entity-tab:hover\s*\{[\s\S]*rgba\(255,255,255,0\.46\)/)
  assert.doesNotMatch(source, /\.search-box\s*\{[\s\S]*rgba\(255,255,255,0\.48\)/)
  assert.doesNotMatch(source, /\.entity-list-card__favorite\s*\{[\s\S]*#ff375f/)
  assert.doesNotMatch(source, /:global\(:root\[data-theme="dark"\] \.search-box\)[\s\S]*linear-gradient\(145deg, rgba\(255,255,255,0\.155\)/)
})

test('entities keyboard focus mirrors hover glass control treatment', () => {
  const tabFocus = cssRule('.entity-tab:focus-visible')
  const searchClearFocus = cssRule('.search-box button:focus-visible')
  const listCardFocus = cssRule('.entity-list-card:focus-within')
  const openFocus = cssRule('.entity-list-card__open:focus-visible')
  const favoriteFocus = cssRule('.entity-list-card__favorite:focus-visible')
  const favoriteActiveFocus = cssRule('.entity-list-card__favorite.active:focus-visible')
  const darkListCardFocus = cssRule(':global(:root[data-theme="dark"] .entity-list-card:focus-within)')

  assert.match(tabFocus, /outline:\s*none/)
  assert.match(tabFocus, backgroundIncludes('material-glass-control-hover'))
  assert.match(tabFocus, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(tabFocus, /color:\s*var\(--text-primary\)/)
  assert.match(tabFocus, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*0 0 0 3px rgba\(var\(--accent-rgb\),\s*0\.12\)/)

  assert.match(searchClearFocus, /outline:\s*none/)
  assert.match(searchClearFocus, backgroundIncludes('material-glass-control-hover'))
  assert.match(searchClearFocus, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(searchClearFocus, /color:\s*var\(--text-primary\)/)
  assert.match(searchClearFocus, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*0 0 0 3px rgba\(var\(--accent-rgb\),\s*0\.12\)/)

  assert.match(listCardFocus, /transform:\s*translateY\(-3px\)/)
  assert.match(listCardFocus, backgroundIncludes('material-glass-elevated'))
  assert.match(listCardFocus, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(listCardFocus, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--glass-surface-shadow\)/)

  assert.match(openFocus, /outline:\s*none/)
  assert.match(openFocus, /box-shadow:\s*inset 0 0 0 4px rgba\(var\(--accent-rgb\),\s*0\.14\)/)

  assert.match(favoriteFocus, /outline:\s*none/)
  assert.match(favoriteFocus, /transform:\s*scale\(1\.06\)/)
  assert.match(favoriteFocus, backgroundIncludes('material-glass-control-hover'))
  assert.match(favoriteFocus, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(favoriteFocus, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*0 0 0 3px rgba\(var\(--accent-rgb\),\s*0\.12\)/)
  assert.match(favoriteActiveFocus, /outline:\s*none/)
  assert.match(favoriteActiveFocus, /transform:\s*scale\(1\.06\)/)
  assert.match(favoriteActiveFocus, backgroundIncludes('badge-error-bg'))
  assert.match(favoriteActiveFocus, /var\(--surface-specular-edge-strong\)/)
  assert.match(favoriteActiveFocus, /var\(--surface-noise\)/)
  assert.match(favoriteActiveFocus, /border-color:\s*var\(--badge-error-border\)/)
  assert.match(favoriteActiveFocus, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*0 0 0 3px color-mix\(in srgb,\s*var\(--badge-error-text\) 18%,\s*transparent\)/)
  assert.doesNotMatch(favoriteActiveFocus, /rgba\(var\(--accent-rgb\)|rgba\(var\(--error-rgb\)/)

  assert.match(darkListCardFocus, /border-color:\s*var\(--glass-edge-strong\)/)
  assert.match(darkListCardFocus, backgroundIncludes('material-glass-control-hover'))
  assert.match(darkListCardFocus, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--glass-surface-shadow\)/)
})

test('entities dark list cards reuse shared material tokens', () => {
  const darkHero = cssRule(':global(:root[data-theme="dark"] .entities-hero)')
  const darkListCard = cssRule(':global(:root[data-theme="dark"] .entity-list-card)')
  const darkListCardHover = cssRule(':global(:root[data-theme="dark"] .entity-list-card:hover)')
  const darkType = cssRule(':global(:root[data-theme="dark"] .entity-list-card__type)')

  assert.match(darkHero, backgroundIncludes('material-glass-elevated'))
  assert.match(darkHero, /var\(--surface-specular-edge-strong\)/)
  assert.match(darkHero, /var\(--surface-noise\)/)
  assert.match(darkHero, /border-color:\s*var\(--glass-edge-strong\)/)

  assert.match(darkListCard, /border-color:\s*var\(--glass-edge\)/)
  assert.match(darkListCard, backgroundIncludes('material-glass-elevated'))
  assert.match(darkListCard, /var\(--surface-specular-edge-strong\)/)
  assert.match(darkListCard, /var\(--surface-noise\)/)
  assert.match(darkListCard, /box-shadow:\s*var\(--glass-surface-shadow\)/)

  assert.match(darkListCardHover, /border-color:\s*var\(--glass-edge-strong\)/)
  assert.match(darkListCardHover, backgroundIncludes('material-glass-control-hover'))
  assert.match(darkListCardHover, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--glass-surface-shadow\)/)
  assert.doesNotMatch(darkListCardHover, /var\(--surface-card-hover\)|var\(--shadow-floating\)/)

  assert.match(darkType, backgroundIncludes('material-glass-control'))
  assert.match(darkType, /border-color:\s*var\(--glass-control-border\)/)
  assert.doesNotMatch(darkType, /rgba\(255,255,255/)
})

test('entities glass backgrounds are layered with specular and noise surfaces', () => {
  assert.deepEqual(singleLayerGlassBackgrounds(externalStyle), [])
})
