import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./VideoDetail.vue', import.meta.url), 'utf8')

test('VideoDetail loads the version selected in the route query', () => {
  assert.match(source, /const serviceCode = this\.\$route\.query\.service_code/)
  assert.match(source, /api\.getVideo\(contentId, \{ service_code: serviceCode \}\)/)
})

test('VideoDetail labels the selected route version before detail data returns', () => {
  assert.match(source, /selectedServiceCode\(\)/)
  assert.match(source, /return String\(this\.video\?\.service_code \|\| this\.\$route\.query\.service_code \|\| ''\)/)
  assert.match(source, /return SERVICE_LABELS\[this\.selectedServiceCode\] \|\| '具体版本'/)
})

test('VideoDetail reloads when the selected service version changes', () => {
  assert.match(source, /'\$route\.query\.service_code'\(\)/)
})

test('VideoDetail returns to search when no in-app back route exists', () => {
  assert.match(source, /window\.history\.state\?\.back/)
  assert.match(source, /this\.\$router\.replace\('\/search'\)/)
})
