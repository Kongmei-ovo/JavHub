import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const vueSource = readFileSync(new URL('./Actor.vue', import.meta.url), 'utf8')
const externalStyle = readFileSync(new URL('../features/actor/actor.css', import.meta.url), 'utf8')
const source = `${vueSource}\n${externalStyle}`

function cssBlock(selector) {
  const searchable = source.replace(/\/\*[\s\S]*?\*\//g, '')
  const blocks = [...searchable.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
    .filter(([, selectors]) => selectors
      .split(',')
      .map(part => part.trim())
      .includes(selector))
    .map(([, , block]) => block)
  assert.ok(blocks.length, `${selector} should exist in Actor.vue`)
  return blocks.join('\n')
}

function backgroundIncludes(block, token) {
  return new RegExp(`background:\\s*(?:[^;]*,\\s*)*var\\(${token}\\)(?:\\s*,[^;]*)?;`).test(block)
}

function singleLayerGlassBackgrounds(css) {
  return css
    .split('\n')
    .map(line => line.trim())
    .filter(line => /^background:\s*var\(--(?:material-glass-subtle|material-glass-control|material-glass-control-hover|material-glass-elevated|material-glass-sheet|glass-active-material)\);$/.test(line))
}

test('actor page keeps large scoped styles in a feature stylesheet', () => {
  assert.match(vueSource, /<style scoped src="\.\.\/features\/actor\/actor\.css"><\/style>/)
  assert.ok(vueSource.split('\n').length < 850, 'Actor.vue should stay below 850 lines')
  assert.ok(externalStyle.split('\n').length > 500, 'external stylesheet should contain the moved actor styles')
})

test('actor page treats supplement as part of the default catalog', () => {
  assert.equal(source.includes('包含补全'), false)
  assert.equal(source.includes('supplement-toggle'), false)
  assert.equal(source.includes('includeSupplement'), false)
  assert.equal(source.includes('查看补全影片'), false)
  assert.match(source, /const requestOptions = \{[\s\S]*include_supplement:\s*'1'[\s\S]*include_total:\s*includeTotal/)
  assert.match(source, /api\.getActressVideos\(this\.actressId,\s*page,\s*pageSize,\s*requestOptions\)/)
  assert.match(source, /:serviceCode="displayServiceCode\(movie\)"/)
  assert.match(source, /if \(movie\._raw\?\.data_origin === 'supplement'\) return ''/)
})

test('actor page keeps loading more when totals are unknown', () => {
  assert.match(source, /if \(this\.totalCount < 0 \|\| this\.movieTotalPages < 0\)/)
  assert.match(source, /return this\.movies\.length >= this\.moviePage \* this\.moviePageSize/)
  assert.match(source, /appendMoviePage\(data,\s*\{\s*trustTotals = false\s*\} = \{\}\)/)
  assert.match(source, /Number\.isInteger\(data\.total_count\) && data\.total_count >= 0/)
  assert.match(source, /if \(!this\.catalogTotalCount\) this\.catalogTotalCount = data\.total_count/)
  assert.match(source, /else if \(!this\.totalCount\)[\s\S]*this\.totalCount = this\.movies\.length/)
  assert.match(source, /Number\.isInteger\(data\.total_pages\) && data\.total_pages >= 0/)
  assert.match(source, /this\.appendMoviePage\(first,\s*\{\s*trustTotals:\s*true\s*\}\)/)
  assert.match(source, /this\.appendMoviePage\(data\)/)
})

test('actor page offers lightweight first-screen recovery after catalog load failures', () => {
  assert.match(source, /const MOVIE_PAGE_SIZE = 100/)
  assert.match(source, /const RECOVERY_MOVIE_PAGE_SIZE = 24/)
  assert.match(source, /moviePageSize:\s*MOVIE_PAGE_SIZE/)
  assert.match(vueSource, /<AppleErrorState[\s\S]*secondary-action-label="轻量加载首屏"/)
  assert.match(vueSource, /@secondary-action="loadActorMoviesCompact"/)
  assert.match(source, /async loadActorMovies\(\{\s*pageSize = MOVIE_PAGE_SIZE\s*\} = \{\}\)/)
  assert.match(source, /const first = await this\.fetchActorMoviePage\(1,\s*\{\s*pageSize,\s*includeTotal:\s*true\s*\}\)/)
  assert.match(source, /this\.moviePageSize = pageSize/)
  assert.match(source, /const data = await this\.fetchActorMoviePage\(nextPage,\s*\{\s*pageSize:\s*this\.moviePageSize\s*\}\)/)
  assert.match(source, /async loadActorMoviesCompact\(\)[\s\S]*return this\.loadActorMovies\(\{\s*pageSize:\s*RECOVERY_MOVIE_PAGE_SIZE\s*\}\)/)
})

test('actor page no longer owns the retired supplement workbench', () => {
  assert.doesNotMatch(vueSource, /supplementStatus|candidateSummary|goSupplement|startSupplement/)
  assert.doesNotMatch(vueSource, /补全状态|处理候选|刷新版本条目/)
})

test('actor page reloads the catalog when route identity changes', () => {
  assert.match(source, /routeIdentity\(\)/)
  assert.match(source, /routeIdentity\(newIdentity,\s*oldIdentity\)/)
  assert.match(source, /if \(newIdentity !== oldIdentity\) this\.loadRouteActor\(\)/)
  assert.match(source, /async loadRouteActor\(\)/)
})

test('actor year navigator can jump to years that are not loaded yet', () => {
  assert.match(source, /v-for="item in yearNavItems"/)
  assert.match(source, /@click="scrollToYear\(item\.year\)"/)
  assert.match(source, /async scrollToYear\(year\)[\s\S]*await this\.loadYearMovies\(year\)[\s\S]*scrollIntoView/)
  assert.match(source, /async loadYearMovies\(year\)[\s\S]*this\.fetchActorMoviePage\(1,\s*\{[\s\S]*year:\s*targetYear,[\s\S]*includeTotal:\s*true/)
})

test('actor page builds year navigation from a lightweight oldest-release probe', () => {
  assert.match(source, /async loadYearBounds\(/)
  assert.match(source, /this\.fetchActorMoviePage\(1,\s*\{[\s\S]*pageSize:\s*1,[\s\S]*sortBy:\s*'release_date:asc'/)
  assert.match(source, /buildYearRange\(latestYear,\s*earliestYear\)/)
})

test('actor page shows API totals separately from loaded movie counts', () => {
  assert.match(source, /\{\{ actorMovieCountLabel \}\}/)
  assert.match(source, /\{\{ sectionMovieCountLabel \}\}/)
  assert.doesNotMatch(source, /\{\{ variantInfo\.canonical\.length \}\} 部作品/)
  assert.match(source, /actorMovieCountLabel\(\)[\s\S]*this\.catalogTotalCount/)
  assert.match(source, /sectionMovieCountLabel\(\)[\s\S]*已显示/)
  assert.match(source, /const first = await this\.fetchActorMoviePage\(1,\s*\{\s*pageSize,\s*includeTotal:\s*true\s*\}\)/)
})

test('actor page uses backend variant groups and can expand all versions', () => {
  assert.match(source, /合并版本/)
  assert.match(source, /展开版本/)
  assert.match(source, /showVariants/)
  assert.match(source, /expandedVariantGroups/)
  assert.match(source, /variant_group_items/)
  assert.match(source, /displayMovies\(\)[\s\S]*flattenVariantGroups/)
  assert.match(source, /variant_group_count/)
  assert.match(source, /variant_scope:\s*'indexed'/)
  assert.doesNotMatch(source, /groupByVariant/)
  assert.doesNotMatch(source, /variantLabel\(/)
  assert.doesNotMatch(source, /from '..\/utils\/videoVariant\.js'/)
})

test('actor variant count hint expands only the current movie group inline', () => {
  assert.match(vueSource, /import \{ variantGroupKey, visibleVariantItems \} from '\.\.\/utils\/videoVariantPresentation\.js'/)
  // Actor cards keep MovieCard's default portrait aspect (3 / 4) so JAV
  // covers render at their natural proportions; the older 16 / 9 override
  // was a visual regression flagged in the field.
  assert.doesNotMatch(vueSource, /coverAspectRatio/)
  assert.match(vueSource, /<button\s+v-if="movie\.variant_group_count > 1 && !showVariants"\s+class="variant-expand-btn"[\s\S]*@click\.stop="toggleVariantGroup\(movie\)"/)
  assert.match(vueSource, /<span v-if="isVariantGroupExpanded\(movie\)">收起版本<\/span>/)
  assert.match(vueSource, /<div v-if="isVariantGroupExpanded\(movie\)" class="variant-inline-list">/)
  assert.match(vueSource, /v-for="variant in variantGroupItems\(movie\)"/)
  assert.match(vueSource, /@click\.stop="openModal\(variant\)"/)
  assert.doesNotMatch(vueSource, /@click\.stop="showVariants = true"/)

  const movieCardWrap = cssBlock('.movie-card-wrap')
  const movieCard = cssBlock('.movie-card-wrap > .apple-video-card')
  const variantButton = cssBlock('.variant-expand-btn')
  const variantRow = cssBlock('.variant-inline-item')
  const variantLabel = cssBlock('.variant-inline-labels span')
  assert.match(movieCardWrap, /display:\s*flex/)
  assert.match(movieCardWrap, /flex-direction:\s*column/)
  assert.match(movieCardWrap, /align-items:\s*stretch/)
  assert.match(movieCardWrap, /contain-intrinsic-size:\s*1px\s+520px/)
  assert.doesNotMatch(movieCardWrap, /contain-intrinsic-size:\s*1px\s+390px/)
  assert.doesNotMatch(movieCardWrap, /align-items:\s*flex-start/)
  assert.match(movieCard, /flex:\s*0 0 auto/)
  assert.match(movieCard, /width:\s*100%/)
  assert.match(variantButton, /width:\s*100%/)
  assert.match(variantButton, /margin-top:\s*8px/)
  assert.match(variantButton, /cursor:\s*pointer/)
  assert.match(variantRow, /grid-template-columns:\s*minmax\(0,\s*1fr\)\s*auto/)
  assert.match(variantRow, /cursor:\s*pointer/)
  assert.match(variantLabel, /border:\s*1px solid var\(--badge-info-border\)/)
  assert.doesNotMatch(`${variantButton}\n${variantRow}`, /position:\s*absolute|pointer-events:\s*none/)
})

test('actor page keeps version controls glass and variant rows solid', () => {
  const variantSwitch = cssBlock('.variant-switch')
  const switchButton = cssBlock('.switch-btn')
  const switchButtonHover = cssBlock('.switch-btn:hover')
  const switchButtonActive = cssBlock('.switch-btn.active')
  const variantBadge = cssBlock('.variant-badge')
  const variantButton = cssBlock('.variant-expand-btn')
  const variantRow = cssBlock('.variant-inline-item')
  const variantRowHover = cssBlock('.variant-inline-item:hover')
  const variantRowFocus = cssBlock('.variant-inline-item:focus-visible')
  const variantInlineLabel = cssBlock('.variant-inline-labels span')
  const yearNav = cssBlock('.year-nav')
  const yearNavItem = cssBlock('.year-nav-item')
  const yearNavItemHover = cssBlock('.year-nav-item:hover')
  const yearNavItemActive = cssBlock('.year-nav-item.active')

  assert.ok(backgroundIncludes(variantSwitch, '--material-glass-control'))
  assert.match(variantSwitch, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(variantSwitch, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.doesNotMatch(variantSwitch, /rgba\(255,\s*255,\s*255/)

  assert.match(switchButton, /border:\s*1px solid var\(--hairline\)/)
  assert.match(switchButton, /background:\s*var\(--card\)/)
  assert.doesNotMatch(switchButton, /var\(--surface-specular-edge|var\(--surface-noise\)/)
  assert.doesNotMatch(switchButton, /var\(--surface-specular-edge|var\(--surface-noise\)/)
  assert.ok(backgroundIncludes(switchButtonHover, '--material-glass-control-hover'))
  assert.match(switchButtonHover, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.ok(backgroundIncludes(switchButtonActive, '--glass-active-material'))
  assert.match(switchButtonActive, /border-color:\s*var\(--glass-active-border\)/)

  assert.ok(backgroundIncludes(variantBadge, '--material-glass-control'))
  assert.match(variantBadge, /border:\s*1px solid var\(--glass-control-border\)/)

  assert.ok(backgroundIncludes(variantButton, '--material-glass-control'))
  assert.match(variantButton, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(variantButton, /box-shadow:\s*var\(--glass-control-shadow\)/)

  assert.match(variantRow, /background:\s*var\(--card-2\)/)
  assert.match(variantRow, /border:\s*1px solid var\(--hairline\)/)
  assert.match(variantRow, /box-shadow:\s*none/)
  assert.doesNotMatch(variantRow, /material-glass|surface-specular-edge|surface-noise|backdrop-filter/)
  assert.match(variantRowHover, /background:\s*var\(--card-hover\)/)
  assert.match(variantRowHover, /border-color:\s*var\(--hairline-strong\)/)
  assert.match(variantRowHover, /box-shadow:\s*var\(--shadow-card\)/)
  assert.match(variantRowFocus, /background:\s*var\(--card-hover\)/)
  assert.match(variantRowFocus, /border-color:\s*var\(--hairline-strong\)/)
  assert.match(variantRowFocus, /box-shadow:\s*var\(--shadow-card\),\s*var\(--focus-ring-wide-strong\)/)
  assert.doesNotMatch(`${variantRowHover}\n${variantRowFocus}`, /material-glass|surface-specular-edge|surface-noise|backdrop-filter/)
  assert.ok(backgroundIncludes(variantInlineLabel, '--badge-info-bg'))
  assert.match(variantInlineLabel, /border:\s*1px solid var\(--badge-info-border\)/)
  assert.match(variantInlineLabel, /color:\s*var\(--badge-info-text\)/)

  // year-nav 是 fixed 浮动 chrome，保留玻璃；item 为实底
  assert.match(yearNav, /border:\s*1px solid var\(--glass-edge\)/)
  assert.match(yearNav, /box-shadow:\s*var\(--glass-surface-shadow\)/)
  assert.match(yearNavItem, /border:\s*1px solid var\(--hairline\)/)
  assert.match(yearNavItem, /background:\s*var\(--card\)/)
  assert.doesNotMatch(yearNavItem, /var\(--surface-specular-edge|var\(--surface-noise\)/)
  assert.doesNotMatch(yearNavItem, /transparent/)
  assert.ok(backgroundIncludes(yearNavItemHover, '--material-glass-control-hover'))
  assert.match(yearNavItemHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.ok(backgroundIncludes(yearNavItemActive, '--glass-active-material'))
  assert.match(yearNavItemActive, /border-color:\s*var\(--glass-active-border\)/)
  assert.doesNotMatch(yearNavItemHover, /rgba\(255,\s*255,\s*255/)
})

test('actor page loading and year empty states use shared subtle materials', () => {
  const yearHeader = cssBlock('.year-header')
  const yearEmpty = cssBlock('.year-empty')

  assert.match(vueSource, /import AppleSkeleton from '\.\.\/components\/AppleSkeleton\.vue'/)
  assert.match(vueSource, /import AppleEmptyState from '\.\.\/components\/AppleEmptyState\.vue'/)
  assert.match(vueSource, /import AppleErrorState from '\.\.\/components\/AppleErrorState\.vue'/)
  assert.match(vueSource, /<AppleSkeleton\s+v-if="loading"[\s\S]*label="演员作品加载中"/)
  assert.match(vueSource, /<AppleEmptyState[\s\S]*title="暂无演员作品"[\s\S]*action-label="重新加载"/)
  assert.match(vueSource, /<AppleErrorState[\s\S]*title="演员作品加载失败"[\s\S]*retry-label="重新加载"/)
  assert.doesNotMatch(vueSource, /<div class="spinner-large"><\/div>/)

  assert.match(yearHeader, /border-bottom:\s*1px solid var\(--glass-control-border\)/)
  assert.doesNotMatch(yearHeader, /rgba\(255,\s*255,\s*255/)

  assert.match(yearEmpty, /border:\s*1px dashed var\(--glass-control-border\)/)
  assert.match(yearEmpty, /background:\s*var\(--card\)/)
  assert.doesNotMatch(yearEmpty, /var\(--surface-specular-edge|var\(--surface-noise\)/)
  assert.doesNotMatch(yearEmpty, /var\(--surface-specular-edge|var\(--surface-noise\)/)
  assert.match(yearEmpty, /box-shadow:\s*none/)
  assert.doesNotMatch(yearEmpty, /rgba\(255,\s*255,\s*255/)
})

test('actor hero uses shared Apple glass controls', () => {
  const actorHero = cssBlock('.actor-hero')
  const actorAvatar = cssBlock('.actor-avatar')
  const actionButton = cssBlock('.actor-action-btn')
  const actionButtonHover = cssBlock('.actor-action-btn:hover')
  const actionButtonActive = cssBlock('.actor-action-btn.active')
  const actionButtonActiveHover = cssBlock('.actor-action-btn.active:hover')
  const actionButtonActiveFocus = cssBlock('.actor-action-btn.active:focus-visible')
  const subscribeButtonActive = cssBlock('.actor-action-btn--subscribe.active')
  const subscribeButtonActiveHover = cssBlock('.actor-action-btn--subscribe.active:hover')
  const subscribeButtonActiveFocus = cssBlock('.actor-action-btn--subscribe.active:focus-visible')
  const metaFavorite = cssBlock('.meta-item--favorite')
  const metaSubscribed = cssBlock('.meta-item--subscribed')
  const sectionHeader = cssBlock('.section-header')

  assert.match(actorHero, /background:\s*var\(--card\)/)
  assert.match(actorHero, /border:\s*1px solid var\(--glass-edge\)/)
  assert.match(actorHero, /box-shadow:\s*var\(--shadow-card\)/)
  assert.doesNotMatch(actorHero, /var\(--bg-secondary\)|var\(--bg-primary\)/)

  assert.ok(backgroundIncludes(actorAvatar, '--material-glass-control'))
  assert.match(actorAvatar, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(actorAvatar, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.doesNotMatch(actorAvatar, /var\(--bg-card\)|rgba\(255,\s*255,\s*255/)

  for (const block of [actionButton, metaFavorite, metaSubscribed]) {
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/)
    assert.ok(backgroundIncludes(block, '--material-glass-control'))
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/)
    assert.doesNotMatch(block, /var\(--surface-control\)|var\(--surface-card-hover\)|var\(--bg-secondary\)|var\(--border-light\)|rgba\(255,\s*255,\s*255|#fff|#ffffff/i)
  }

  assert.ok(backgroundIncludes(actionButtonHover, '--material-glass-control-hover'))
  assert.match(actionButtonHover, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(actionButtonHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.doesNotMatch(actionButtonHover, /var\(--surface-card-hover\)|var\(--glass-edge-strong\)/)

  assert.ok(backgroundIncludes(actionButtonActive, '--badge-error-bg'))
  assert.match(actionButtonActive, /var\(--surface-specular-edge\)/)
  assert.match(actionButtonActive, /var\(--surface-noise\)/)
  assert.match(actionButtonActive, /border-color:\s*var\(--badge-error-border\)/)
  assert.match(actionButtonActive, /color:\s*var\(--badge-error-text\)/)
  assert.ok(backgroundIncludes(subscribeButtonActive, '--badge-success-bg'))
  assert.match(subscribeButtonActive, /var\(--surface-specular-edge\)/)
  assert.match(subscribeButtonActive, /var\(--surface-noise\)/)
  assert.match(subscribeButtonActive, /border-color:\s*var\(--badge-success-border\)/)
  assert.match(subscribeButtonActive, /color:\s*var\(--badge-success-text\)/)
  for (const [block, token, border, name] of [
    [actionButtonActiveHover, '--badge-error-bg', '--badge-error-border', 'favorite active hover'],
    [actionButtonActiveFocus, '--badge-error-bg', '--badge-error-border', 'favorite active focus'],
    [subscribeButtonActiveHover, '--badge-success-bg', '--badge-success-border', 'subscribe active hover'],
    [subscribeButtonActiveFocus, '--badge-success-bg', '--badge-success-border', 'subscribe active focus'],
  ]) {
    assert.ok(backgroundIncludes(block, token), `${name} should keep semantic fill`)
    assert.match(block, /var\(--surface-specular-edge-strong\)/, `${name} should strengthen the glass edge`)
    assert.match(block, /var\(--surface-noise\)/, `${name} should preserve texture`)
    assert.match(block, new RegExp(`border-color:\\s*var\\(${border}\\)`), `${name} should keep semantic border`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\)/, `${name} should keep hover depth`)
    assert.match(block, /transform:\s*translateY\(-1px\)/, `${name} should keep the hero action lift`)
  }
  assert.match(actionButtonActiveFocus, /outline:\s*none/)
  assert.match(actionButtonActiveFocus, /0 0 0 3px color-mix\(in srgb,\s*var\(--badge-error-text\) 18%,\s*transparent\)/)
  assert.match(subscribeButtonActiveFocus, /outline:\s*none/)
  assert.match(subscribeButtonActiveFocus, /0 0 0 3px color-mix\(in srgb,\s*var\(--badge-success-text\) 18%,\s*transparent\)/)
  assert.doesNotMatch(`${actionButtonActive}\n${subscribeButtonActive}\n${actionButtonActiveFocus}\n${subscribeButtonActiveFocus}`, /#ff375f|#34c759|rgba\(255,\s*55,\s*95|rgba\(52,\s*199,\s*89|rgba\(var\(--accent-rgb\)|rgba\(var\(--error-rgb\)/i)

  assert.match(sectionHeader, /border-bottom:\s*1px solid var\(--glass-control-border\)/)
})

test('actor glass backgrounds are layered with specular and noise surfaces', () => {
  assert.deepEqual(singleLayerGlassBackgrounds(externalStyle), [])

  for (const selector of [
    '.actor-hero',
    '.actor-avatar',
    '.meta-item--favorite',
    '.actor-action-btn',
    '.actor-action-btn:hover',
    '.actor-action-btn.active',
    '.actor-action-btn.active:hover',
    '.variant-switch',
    '.switch-btn',
    '.switch-btn:hover',
    '.switch-btn.active',
    '.variant-badge',
    '.variant-expand-btn',
    '.variant-inline-item',
    '.variant-inline-labels span',
    '.year-nav',
    '.year-nav-item',
    '.year-nav-item:hover',
    '.year-nav-item.active',
    '.year-empty',
  ]) {
    const block = cssBlock(selector)
    // v2：实底块不得有玻璃分层；仍是玻璃的块（chrome/控件态）必须分层完整
    if (/background:\s*var\(--card\b/.test(block)) {
      assert.doesNotMatch(block, /var\(--surface-specular-edge|var\(--surface-noise\)/, `${selector} solid block should not keep glass layers`)
    } else if (/var\(--material-glass|var\(--glass-active-material\)|var\(--badge-\w+-bg\)/.test(block)) {
      assert.match(block, /var\(--surface-specular-edge/, `${selector} glass block should keep a specular edge layer`)
      assert.match(block, /var\(--surface-noise\)/, `${selector} glass block should keep the shared noise layer`)
    }
  }
})
