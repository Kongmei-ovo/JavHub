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
  assert.match(source, /return this\.movies\.length >= this\.moviePage \* MOVIE_PAGE_SIZE/)
  assert.match(source, /appendMoviePage\(data,\s*\{\s*trustTotals = false\s*\} = \{\}\)/)
  assert.match(source, /Number\.isInteger\(data\.total_count\) && data\.total_count >= 0/)
  assert.match(source, /if \(!this\.catalogTotalCount\) this\.catalogTotalCount = data\.total_count/)
  assert.match(source, /else if \(!this\.totalCount\)[\s\S]*this\.totalCount = this\.movies\.length/)
  assert.match(source, /Number\.isInteger\(data\.total_pages\) && data\.total_pages >= 0/)
  assert.match(source, /this\.appendMoviePage\(first,\s*\{\s*trustTotals:\s*true\s*\}\)/)
  assert.match(source, /this\.appendMoviePage\(data\)/)
})

test('actor page surfaces download candidate handoff', () => {
  assert.match(source, /candidateSummary/)
  assert.match(source, /下载候选/)
  assert.match(source, /待补磁力/)
  assert.match(source, /api\.getDownloadCandidateSummary/)
  assert.doesNotMatch(source, /api\.listDownloadCandidates/)
  assert.doesNotMatch(source, /limit:\s*100000/)
  assert.match(source, /goDownloadCandidates/)
  assert.match(source, /path: '\/downloads'/)
  assert.match(source, /tab: 'candidates'/)
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
  assert.match(source, /const first = await this\.fetchActorMoviePage\(1,\s*\{\s*includeTotal:\s*true\s*\}\)/)
})

test('actor page uses backend variant groups and can expand all versions', () => {
  assert.match(source, /合并版本/)
  assert.match(source, /展开版本/)
  assert.match(source, /showVariants/)
  assert.match(source, /variant_group_items/)
  assert.match(source, /displayMovies\(\)[\s\S]*flattenVariantGroups/)
  assert.match(source, /variant_group_count/)
  assert.match(source, /variant_scope:\s*'indexed'/)
  assert.doesNotMatch(source, /groupByVariant/)
  assert.doesNotMatch(source, /variantLabel\(/)
  assert.doesNotMatch(source, /from '..\/utils\/videoVariant\.js'/)
})

test('actor variant count hint is a clickable flow control outside card metadata', () => {
  assert.match(vueSource, /<button\s+v-if="movie\.variant_group_count > 1 && !showVariants"\s+class="variant-label"[\s\S]*@click\.stop="showVariants = true"/)

  const movieCardWrap = cssBlock('.movie-card-wrap')
  const movieCard = cssBlock('.movie-card-wrap > .apple-video-card')
  const variantLabel = cssBlock('.variant-label')
  assert.match(movieCardWrap, /display:\s*flex/)
  assert.match(movieCardWrap, /flex-direction:\s*column/)
  assert.match(movieCardWrap, /align-items:\s*stretch/)
  assert.match(movieCardWrap, /contain-intrinsic-size:\s*1px\s+450px/)
  assert.doesNotMatch(movieCardWrap, /contain-intrinsic-size:\s*1px\s+390px/)
  assert.doesNotMatch(movieCardWrap, /align-items:\s*flex-start/)
  assert.match(movieCard, /flex:\s*0 0 auto/)
  assert.match(movieCard, /width:\s*100%/)
  assert.match(variantLabel, /display:\s*inline-flex/)
  assert.match(variantLabel, /align-self:\s*flex-start/)
  assert.match(variantLabel, /margin-top:\s*8px/)
  assert.match(variantLabel, /cursor:\s*pointer/)
  assert.doesNotMatch(variantLabel, /position:\s*absolute/)
  assert.doesNotMatch(variantLabel, /pointer-events:\s*none/)
})

test('actor page version and year controls use shared Apple glass materials', () => {
  const variantSwitch = cssBlock('.variant-switch')
  const switchButton = cssBlock('.switch-btn')
  const switchButtonHover = cssBlock('.switch-btn:hover')
  const switchButtonActive = cssBlock('.switch-btn.active')
  const variantBadge = cssBlock('.variant-badge')
  const variantLabel = cssBlock('.variant-label')
  const yearNav = cssBlock('.year-nav')
  const yearNavItem = cssBlock('.year-nav-item')
  const yearNavItemHover = cssBlock('.year-nav-item:hover')
  const yearNavItemActive = cssBlock('.year-nav-item.active')

  assert.ok(backgroundIncludes(variantSwitch, '--material-glass-control'))
  assert.match(variantSwitch, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(variantSwitch, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.doesNotMatch(variantSwitch, /rgba\(255,\s*255,\s*255/)

  assert.match(switchButton, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.ok(backgroundIncludes(switchButton, '--material-glass-subtle'))
  assert.match(switchButton, /var\(--surface-specular-edge/)
  assert.match(switchButton, /var\(--surface-noise\)/)
  assert.ok(backgroundIncludes(switchButtonHover, '--material-glass-control-hover'))
  assert.match(switchButtonHover, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.ok(backgroundIncludes(switchButtonActive, '--glass-active-material'))
  assert.match(switchButtonActive, /border-color:\s*var\(--glass-active-border\)/)

  assert.ok(backgroundIncludes(variantBadge, '--material-glass-control'))
  assert.match(variantBadge, /border:\s*1px solid var\(--glass-control-border\)/)

  assert.ok(backgroundIncludes(variantLabel, '--glass-active-material'))
  assert.match(variantLabel, /border:\s*1px solid var\(--glass-active-border\)/)
  assert.match(variantLabel, /box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.match(variantLabel, /color:\s*var\(--text-primary\)/)
  assert.doesNotMatch(variantLabel, /#fff|#ffffff|rgba\(255,\s*255,\s*255/i)

  assert.match(yearNav, /border:\s*1px solid var\(--glass-edge\)/)
  assert.match(yearNav, /box-shadow:\s*var\(--glass-surface-shadow\)/)
  assert.match(yearNavItem, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.ok(backgroundIncludes(yearNavItem, '--material-glass-subtle'))
  assert.match(yearNavItem, /var\(--surface-specular-edge/)
  assert.match(yearNavItem, /var\(--surface-noise\)/)
  assert.match(yearNavItem, /box-shadow:\s*var\(--glass-inner-shadow\)/)
  assert.doesNotMatch(yearNavItem, /transparent/)
  assert.ok(backgroundIncludes(yearNavItemHover, '--material-glass-control-hover'))
  assert.match(yearNavItemHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.ok(backgroundIncludes(yearNavItemActive, '--glass-active-material'))
  assert.match(yearNavItemActive, /border-color:\s*var\(--glass-active-border\)/)
  assert.doesNotMatch(yearNavItemHover, /rgba\(255,\s*255,\s*255/)
})

test('actor page loading and year empty states use shared subtle materials', () => {
  const spinner = cssBlock('.spinner-large')
  const yearHeader = cssBlock('.year-header')
  const yearEmpty = cssBlock('.year-empty')

  assert.match(spinner, /border:\s*3px solid var\(--glass-control-border\)/)
  assert.match(spinner, /border-top-color:\s*var\(--glass-active-border\)/)
  assert.doesNotMatch(spinner, /border-top-color:\s*var\(--accent\)/)
  assert.doesNotMatch(spinner, /rgba\(255,255,255/)

  assert.match(yearHeader, /border-bottom:\s*1px solid var\(--glass-control-border\)/)
  assert.doesNotMatch(yearHeader, /rgba\(255,\s*255,\s*255/)

  assert.match(yearEmpty, /border:\s*1px dashed var\(--glass-control-border\)/)
  assert.ok(backgroundIncludes(yearEmpty, '--material-glass-subtle'))
  assert.match(yearEmpty, /var\(--surface-specular-edge/)
  assert.match(yearEmpty, /var\(--surface-noise\)/)
  assert.match(yearEmpty, /box-shadow:\s*var\(--glass-inner-shadow\)/)
  assert.doesNotMatch(yearEmpty, /rgba\(255,\s*255,\s*255/)
})

test('actor hero and supplement workspace use shared Apple glass controls', () => {
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
  const supplementCard = cssBlock('.supplement-card')

  assert.ok(backgroundIncludes(actorHero, '--material-glass-sheet'))
  assert.match(actorHero, /border:\s*1px solid var\(--glass-edge\)/)
  assert.match(actorHero, /box-shadow:\s*var\(--glass-surface-shadow\)/)
  assert.doesNotMatch(actorHero, /var\(--bg-secondary\)|var\(--bg-primary\)/)

  assert.ok(backgroundIncludes(actorAvatar, '--material-glass-control'))
  assert.match(actorAvatar, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(actorAvatar, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.doesNotMatch(actorAvatar, /var\(--bg-card\)|rgba\(255,\s*255,\s*255/)

  for (const block of [actionButton, metaFavorite, metaSubscribed, supplementCard]) {
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
    '.variant-label',
    '.year-nav',
    '.year-nav-item',
    '.year-nav-item:hover',
    '.year-nav-item.active',
    '.year-empty',
    '.supplement-card',
  ]) {
    const block = cssBlock(selector)
    assert.match(block, /var\(--surface-specular-edge/)
    assert.match(block, /var\(--surface-noise\)/)
  }
})
