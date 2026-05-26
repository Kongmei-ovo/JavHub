import test from 'node:test'
import assert from 'node:assert/strict'
import { nextTick } from 'vue'
import { modalState, openVideoModal, resetModal } from './modalState.js'

test('openVideoModal ignores stale detail responses from previous modal', async () => {
  resetModal()
  let resolveFirst
  const api = {
    getVideo: (contentId) => new Promise(resolve => {
      if (contentId === 'MIAA-784') {
        resolveFirst = resolve
      } else {
        resolve({ data: { title_ja: 'Second full title' } })
      }
    }),
  }

  openVideoModal({ content_id: 'MIAA-784', title_ja: 'First base title' }, '/search', api)
  openVideoModal({ content_id: 'SONE-436', title_ja: 'Second base title' }, '/search', api)
  resolveFirst({ data: { title_ja: 'First full title' } })

  await Promise.resolve()
  await Promise.resolve()
  await nextTick()

  assert.equal(modalState.visible, true)
  assert.equal(modalState.selectedVideo.content_id, 'SONE-436')
  assert.equal(modalState.selectedVideo.title_ja, 'Second full title')

  resetModal()
})

test('openVideoModal keeps modal usable when detail request fails', async () => {
  resetModal()
  const api = {
    getVideo: () => Promise.reject(new Error('Not Found')),
  }

  openVideoModal({ content_id: 'MIAA-784', title_ja: 'Base title' }, '/search', api)
  await Promise.resolve()
  await Promise.resolve()
  await nextTick()

  assert.equal(modalState.visible, true)
  assert.equal(modalState.selectedVideo.title_ja, 'Base title')
  assert.equal(modalState.selectedVideo._loading.javinfo, false)
  assert.equal(modalState.selectedVideo._errors.javinfo, 'Not Found')

  resetModal()
})

test('openVideoModal passes service_code to primary detail lookup', async () => {
  resetModal()
  const calls = []
  const api = {
    getVideo: (contentId, options) => {
      calls.push([contentId, options])
      return Promise.resolve({ data: { title_ja: 'Digital detail' } })
    },
  }

  openVideoModal({
    content_id: 'miaa00784',
    service_code: 'digital',
    title_ja: 'Base title',
  }, '/search', api)
  await Promise.resolve()
  await Promise.resolve()
  await nextTick()

  assert.deepEqual(calls, [['miaa00784', { service_code: 'digital' }]])
  assert.equal(modalState.selectedVideo.title_ja, 'Digital detail')

  resetModal()
})

test('openVideoModal does not request primary detail APIs for supplement-only videos', async () => {
  resetModal()
  let getVideoCalls = 0
  const api = {
    getVideo: () => {
      getVideoCalls += 1
      return Promise.resolve({ data: { title_ja: 'Unexpected primary detail' } })
    },
  }

  openVideoModal({
    content_id: 'supp:1',
    resolved_id: 'supp:1',
    data_origin: 'supplement',
    dvd_id: 'UMD-1010',
    title_ja: 'Supplement title',
  }, '/actor/糸井瑠花', api)
  await Promise.resolve()
  await nextTick()

  assert.equal(modalState.visible, true)
  assert.equal(modalState.selectedVideo.title_ja, 'Supplement title')
  assert.equal(modalState.selectedVideo._loading.javinfo, false)
  assert.equal(getVideoCalls, 0)

  resetModal()
})

test('openVideoModal uses existing supplement data without loading source details', async () => {
  resetModal()
  let supplementSourcesCalls = 0
  const api = {
    getVideo: () => Promise.reject(new Error('primary detail should not be requested')),
    getSupplementMovieSources: (movieId) => {
      supplementSourcesCalls += 1
      return Promise.resolve({
        data: {
          chosen_fields: [
            { field_name: 'summary', field_value: 'Unexpected source summary' },
          ],
        },
      })
    },
  }

  openVideoModal({
    content_id: 'supp:1',
    resolved_id: 'supp:1',
    data_origin: 'supplement',
    dvd_id: 'UMD-1010',
    title_ja: 'Supplement title',
    summary: 'Stored summary',
    summary_translated: '已有简介',
    sample_url: 'https://example.test/stored-sample.mp4',
    categories: [{ id: 'stored', name_ja: 'Stored category' }],
  }, '/actor/糸井瑠花', api)
  await Promise.resolve()
  await Promise.resolve()
  await nextTick()

  assert.equal(supplementSourcesCalls, 0)
  assert.equal(modalState.selectedVideo.summary, 'Stored summary')
  assert.equal(modalState.selectedVideo.summary_translated, '已有简介')
  assert.equal(modalState.selectedVideo.sample_url, 'https://example.test/stored-sample.mp4')
  assert.deepEqual(modalState.selectedVideo.categories, [{ id: 'stored', name_ja: 'Stored category' }])
  assert.equal(modalState.selectedVideo._loading.supplement, false)

  resetModal()
})
