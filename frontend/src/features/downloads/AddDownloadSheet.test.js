import test from 'node:test'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'

const componentUrl = new URL('./AddDownloadSheet.vue', import.meta.url)
const source = existsSync(componentUrl) ? readFileSync(componentUrl, 'utf8') : ''

test('add-download sheet is a reusable modal with a lockable downloader', () => {
  assert.ok(existsSync(componentUrl), 'AddDownloadSheet.vue should exist')
  assert.match(source, /name:\s*'AddDownloadSheet'/)
  // props that make it reusable across 下载任务 and 115
  assert.match(source, /lockedDownloaderType:/)
  assert.match(source, /defaultCid:/)
  assert.match(source, /emits:\s*\[[^\]]*'close'[^\]]*'added'[^\]]*\]/)
  // shares the extracted parser, not its own copy
  assert.match(source, /import \{ parseMagnetInput, countInputLines \} from '\.\/magnetParse'/)
})

test('locked mode forces 115 offline and disables downloader choice', () => {
  // locked branch renders a read-only downloader, unlocked renders a <select>
  assert.match(source, /v-if="locked"[\s\S]*locked-downloader/)
  assert.match(source, /v-else v-model="selectedDownloaderId"[\s\S]*downloader-select/)
  // 115 path uses the offline endpoint; downloader path uses createDownload
  assert.match(source, /api\.addOpen115Offline\(/)
  assert.match(source, /api\.createDownload\(/)
  // quota shown when locked
  assert.match(source, /getOpen115Quota/)
})

test('continuous add clears the input but keeps the sheet open', () => {
  assert.match(source, /afterAdd\(\)\s*\{[\s\S]*this\.magnetInput = ''/)
  // close only fires on explicit close, never inside afterAdd
  const afterAdd = source.slice(source.indexOf('afterAdd()'), source.indexOf('afterAdd()') + 200)
  assert.doesNotMatch(afterAdd, /\$emit\('close'\)/)
})
