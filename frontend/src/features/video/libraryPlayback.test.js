import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const mixinSource = readFileSync(new URL('./libraryPlaybackMixin.js', import.meta.url), 'utf8')
const modalSource = readFileSync(new URL('../../components/VideoModal.vue', import.meta.url), 'utf8')
const apiSource = readFileSync(new URL('../../api/index.js', import.meta.url), 'utf8')
const todaySource = readFileSync(new URL('../../views/Today.vue', import.meta.url), 'utf8')

test('video modal mounts the library playback mixin and exposes the cloud play button', () => {
  assert.match(modalSource, /import libraryPlaybackMixin from '\.\.\/features\/video\/libraryPlaybackMixin\.js'/)
  assert.match(modalSource, /mixins: \[libraryPlaybackMixin\]/)
  assert.match(modalSource, /v-if="libraryPlayInfo" class="stream-btn library-play-btn"/)
  assert.match(modalSource, /library-badge/)
})

test('library play info never persists the resolved direct url', () => {
  // checkLibraryStatus 只保留 file/files/progress；play(直链)必须丢弃
  const match = mixinSource.match(/this\.libraryPlayInfo = \{([^}]*)\}/)
  assert.ok(match, 'checkLibraryStatus should assign libraryPlayInfo')
  assert.ok(!match[1].includes('play'), 'libraryPlayInfo must not retain the resolved play url')
  // 复制直链/外部播放器在使用前必须重新换链
  const copyBlock = mixinSource.slice(mixinSource.indexOf('async copyLibraryLink'))
  assert.match(copyBlock, /getLibraryPlay\(code\)/)
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

test('library play error path retries the link exactly once', () => {
  assert.match(mixinSource, /libraryRetryUsed/)
  const errBlock = mixinSource.slice(mixinSource.indexOf('async onLibraryPlayError'))
  assert.match(errBlock, /this\.libraryRetryUsed = true/)
})

test('api client exposes playback and library index endpoints', () => {
  for (const needle of [
    "/v1/playback/library/", "/v1/playback/progress/", "/v1/playback/continue",
    "/v1/library/summary", "/v1/library/scan", "/v1/library/files",
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
