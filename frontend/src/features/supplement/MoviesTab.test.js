import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./MoviesTab.vue', import.meta.url), 'utf8')

test('MoviesTab owns movie fetch state and renders the existing movies panel', () => {
  assert.match(source, /name:\s*'MoviesTab'/)
  assert.match(source, /useSupplementApi\(/)
  assert.match(source, /SupplementMoviesPanel/)
  assert.match(source, /loadMovies\(/)
  assert.match(source, /supplementMovies/)
  assert.match(source, /moviesLoading/)
  assert.match(source, /moviesTotalPages/)
  assert.match(source, /movieFilters/)
  assert.match(source, /matchFilterOptions/)
  assert.match(source, /qualityFilterOptions/)
})

test('MoviesTab performs movie actions through the shared composable', () => {
  assert.match(source, /enrichMovie/)
  assert.match(source, /batchEnrichMovies/)
  assert.match(source, /createDownloadCandidates/)
  assert.match(source, /openMovieSources/)
  assert.match(source, /emit\('jobs-requested'/)
  assert.match(source, /emit\('sources-opened'/)
  assert.match(source, /emit\('filters-change'/)
  assert.match(source, /applyImageFallback/)
})
