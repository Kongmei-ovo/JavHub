import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./Actor.vue', import.meta.url), 'utf8')

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
  assert.doesNotMatch(source, /groupByVariant/)
  assert.doesNotMatch(source, /variantLabel\(/)
  assert.doesNotMatch(source, /from '..\/utils\/videoVariant\.js'/)
})
