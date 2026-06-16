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
  assert.match(source, /emit\('filters-change'/)
  assert.match(source, /applyImageFallback/)
})

test('MoviesTab owns the diagnostics drawer (no tab swap, addressed by ?work)', () => {
  // Work-first restructure: 诊断 opens a right-side drawer here instead of emitting
  // sources-opened to swap to a separate 来源诊断 tab.
  assert.match(source, /SupplementSourceDiagnosticsDialog/)
  assert.match(source, /drawer/)
  assert.match(source, /route\.query\.work/)
  assert.match(source, /work:\s*String\(movie\.id\)/)
  assert.doesNotMatch(source, /emit\('sources-opened'/)
})
