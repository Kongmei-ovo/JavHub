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
    getVideoMetadata: () => Promise.resolve({ data: {} }),
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

test('openVideoModal keeps modal usable when metadata request fails', async () => {
  resetModal()
  const api = {
    getVideo: () => Promise.resolve({ data: { title_ja: 'Full title', runtime_mins: 120 } }),
    getVideoMetadata: () => Promise.reject(new Error('Not Found')),
  }

  openVideoModal({ content_id: 'MIAA-784', title_ja: 'Base title' }, '/search', api)
  await Promise.resolve()
  await Promise.resolve()
  await nextTick()

  assert.equal(modalState.visible, true)
  assert.equal(modalState.selectedVideo.title_ja, 'Full title')
  assert.equal(modalState.selectedVideo.runtime_mins, 120)
  assert.equal(modalState.selectedVideo._loading.javinfo, false)
  assert.equal(modalState.selectedVideo._loading.metatube, false)
  assert.equal(modalState.selectedVideo._errors.metatube, 'Not Found')

  resetModal()
})
