import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const mixinSource = readFileSync(new URL('./libraryPlaybackMixin.js', import.meta.url), 'utf8')
const modalSource = readFileSync(new URL('../../components/VideoModal.vue', import.meta.url), 'utf8')
const apiSource = readFileSync(new URL('../../api/index.js', import.meta.url), 'utf8')
const todaySource = readFileSync(new URL('../../views/Today.vue', import.meta.url), 'utf8')

test('video modal mounts the resource playback mixin and exposes the 115 play button', () => {
  assert.match(modalSource, /import libraryPlaybackMixin from '\.\.\/features\/video\/libraryPlaybackMixin\.js'/)
  assert.match(modalSource, /mixins: \[libraryPlaybackMixin\]/)
  assert.match(modalSource, /v-if="libraryPlayInfo" class="stream-btn library-play-btn"/)
  assert.match(modalSource, /115 播放/)
  assert.doesNotMatch(modalSource, />已入库</)
})

test('resource play info keeps durable refs and never persists a 115 direct url', () => {
  const match = mixinSource.match(/this\.libraryPlayInfo = \{([^}]*)\}/)
  assert.ok(match, 'checkLibraryStatus should assign libraryPlayInfo')
  assert.ok(!match[1].includes('play'), 'libraryPlayInfo must not retain the resolved play url')
  const copyBlock = mixinSource.slice(mixinSource.indexOf('async copyLibraryLink'))
  assert.match(copyBlock, /stableResourceUrl/)
  assert.doesNotMatch(copyBlock, /getLibraryPlay/)
  assert.match(copyBlock, /navigator\.clipboard\.writeText/)
  assert.match(mixinSource, /movieResourceStreamUrl/)
})

test('progress reporting is throttled and shared between library and online playback', () => {
  assert.match(mixinSource, /now - this\.lastProgressReport < 10000/)
  assert.match(mixinSource, /this\.playbackMode === 'library' \? 'library' : 'online'/)
  // 在线播放路径也挂进度上报
  assert.match(modalSource, /this\.setupProgressReporting\(video\)/)
  // 关闭播放器时上报最终进度
  const closeBlock = modalSource.slice(modalSource.indexOf('closeStreamPlayer() {'))
  assert.match(closeBlock, /this\.reportProgress\(video\)/)
})

test('progress reporting removes both listeners when the playback source changes', () => {
  const setupBlock = mixinSource.slice(
    mixinSource.indexOf('    setupProgressReporting(video) {'),
    mixinSource.indexOf('    reportProgress(video) {'),
  )
  assert.match(setupBlock, /const pauseHandler = \(\) => this\.reportProgress\(video\)/)
  assert.match(setupBlock, /video\.addEventListener\('pause', pauseHandler\)/)
  assert.match(setupBlock, /this\.progressReportHandler = \{ video, handler, pauseHandler \}/)
  assert.match(setupBlock, /video\.removeEventListener\('pause', pauseHandler\)/)
})

test('115 play error path retries the stable entry exactly once', () => {
  assert.match(mixinSource, /libraryRetryUsed/)
  const errBlock = mixinSource.slice(mixinSource.indexOf('async onLibraryPlayError'))
  assert.match(errBlock, /this\.libraryRetryUsed = true/)
})

test('api client exposes movie resources and stable playback endpoints', () => {
  for (const needle of [
    "/v1/movies/", "/resources", "/v1/playback/resources/",
    "/v1/playback/progress/", "/v1/playback/continue",
  ]) {
    assert.ok(apiSource.includes(needle), `api/index.js should call ${needle}`)
  }
})

test('today view renders a continue-watching rail with progress ratio', () => {
  assert.match(todaySource, /继续观看/)
  assert.match(todaySource, /loadContinueWatching/)
  assert.match(todaySource, /continueRatio/)
  // 失败静默：区块加载失败不渲染错误态
  const block = todaySource.slice(todaySource.indexOf('async loadContinueWatching'))
  assert.match(block.slice(0, 600), /this\.continueItems = \[\]/)
})
