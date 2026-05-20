import test from 'node:test'
import assert from 'node:assert/strict'
import { openVideoDetail, shouldFallbackToVideoModal } from './videoDetailNavigation.js'

test('openVideoDetail routes normal videos to the detail route', () => {
  const pushes = []
  const router = { push: target => pushes.push(target) }
  let fallbackCalls = 0

  openVideoDetail({ content_id: 'MIAA-784' }, router, { fullPath: '/search?q=miaa&page=2' }, () => {
    fallbackCalls += 1
  })

  assert.deepEqual(pushes, [{ name: 'VideoDetail', params: { contentId: 'MIAA-784' } }])
  assert.equal(fallbackCalls, 0)
})

test('openVideoDetail preserves the selected service version on the detail route', () => {
  const pushes = []
  const router = { push: target => pushes.push(target) }

  openVideoDetail({ content_id: 'MIAA-784', service_code: 'mono' }, router, { fullPath: '/search' }, () => {})

  assert.deepEqual(pushes, [{
    name: 'VideoDetail',
    params: { contentId: 'MIAA-784' },
    query: { service_code: 'mono' },
  }])
})

test('openVideoDetail falls back to the modal for supplement-only videos', () => {
  const pushes = []
  const fallbackCalls = []
  const router = { push: target => pushes.push(target) }
  const video = { content_id: 'supp:1', resolved_id: 'supp:1', data_origin: 'supplement' }

  openVideoDetail(video, router, { fullPath: '/actor/糸井瑠花' }, (item, routePath) => {
    fallbackCalls.push({ item, routePath })
  })

  assert.equal(pushes.length, 0)
  assert.deepEqual(fallbackCalls, [{ item: video, routePath: '/actor/糸井瑠花' }])
})

test('shouldFallbackToVideoModal detects supplement origins', () => {
  assert.equal(shouldFallbackToVideoModal({ content_id: 'supp:1' }), true)
  assert.equal(shouldFallbackToVideoModal({ resolved_id: 'supp:2' }), true)
  assert.equal(shouldFallbackToVideoModal({ data_origin: 'supplement' }), true)
  assert.equal(shouldFallbackToVideoModal({ content_id: 'MIAA-784' }), false)
})
