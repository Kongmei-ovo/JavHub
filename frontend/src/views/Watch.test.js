import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const watchSource = readFileSync(new URL('./Watch.vue', import.meta.url), 'utf8')
const routerSource = readFileSync(new URL('../router/index.js', import.meta.url), 'utf8')
const apiSource = readFileSync(new URL('../api/index.js', import.meta.url), 'utf8')

test('router registers the first-party /watch/:movieId route', () => {
  assert.match(routerSource, /path: '\/watch\/:movieId'/)
  assert.match(routerSource, /import\('\.\.\/views\/Watch\.vue'\)/)
})

test('api exposes the acquisition session endpoints', () => {
  assert.match(apiSource, /startAcquisition\(movieId/)
  assert.match(apiSource, /getAcquisition\(sessionId\)/)
  assert.match(apiSource, /acquisitions/)
})

test('Watch shortcuts to autoplay when a ready resource already exists (no session)', () => {
  assert.match(watchSource, /getMovieResources/)
  assert.match(watchSource, /movieResourceStreamUrl/)
  assert.match(watchSource, /readyVideo/)
  // The has-resource branch plays and returns before any startAcquisition call.
  const bootstrap = watchSource.slice(watchSource.indexOf('async bootstrap'))
  const playIdx = bootstrap.indexOf('this.playResource(resource')
  const acquireIdx = bootstrap.indexOf('startAcquisition')
  assert.ok(playIdx > -1 && acquireIdx > -1 && playIdx < acquireIdx)
})

test('Watch drives the acquisition waiting flow with four stages and polling', () => {
  assert.match(watchSource, /startAcquisition/)
  assert.match(watchSource, /getAcquisition/) // polled session snapshot
  assert.match(watchSource, /setInterval/)
  for (const stage of ['搜索', '115', '登记', '自动起播']) {
    assert.ok(watchSource.includes(stage), `waiting flow should show stage: ${stage}`)
  }
  assert.match(watchSource, /this\.status === 'ready'/) // ready → autoplay
  assert.match(watchSource, /this\.status === 'failed'/) // failure surfaced
})

test('Watch reuses the shared VideoPlayerOverlay kernel', () => {
  assert.match(watchSource, /VideoPlayerOverlay/)
  assert.match(watchSource, /from '\.\.\/features\/video\/VideoPlayerOverlay\.vue'/)
  assert.match(watchSource, /:visible="playerVisible"/) // overlay visibility is bound, not just v-if
})

test('Watch passes downloaded subtitle tracks into the player', () => {
  assert.match(watchSource, /movieResourceSubtitleUrl/)
  assert.match(watchSource, /subtitleTracksFor/)
  assert.match(watchSource, /:subtitles="subtitleTracks"/)
  assert.match(apiSource, /movieResourceSubtitleUrl\(resourceId\)/)
})
