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

test('openVideoModal enriches supplement-only videos from chosen supplement fields', async () => {
  resetModal()
  let supplementSourcesId = null
  const api = {
    getVideo: () => Promise.reject(new Error('primary detail should not be requested')),
    getSupplementMovieSources: (movieId) => {
      supplementSourcesId = movieId
      return Promise.resolve({
        data: {
          chosen_fields: [
            { field_name: 'maker_name', field_value: 'LEO' },
            { field_name: 'label_name', field_value: 'LEO', field_value_translated: '狮子厂牌' },
            { field_name: 'series_name', field_value: '----' },
            { field_name: 'summary', field_value: 'Original summary', field_value_translated: '翻译简介' },
            { field_name: 'category_names', field_value: '["姉・妹"]', field_value_translated: '["姐妹"]' },
            { field_name: 'actor_names', field_value: '["糸井瑠花","凰華りん"]', field_value_translated: '["糸井瑠花","凰华凛"]' },
            { field_name: 'cover_url', field_value: 'https://example.test/pl.jpg' },
            { field_name: 'cover_thumb_url', field_value: 'https://example.test/ps.jpg' },
            { field_name: 'sample_movie_url', field_value: 'https://example.test/sample.mp4' },
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
  }, '/actor/糸井瑠花', api)
  await Promise.resolve()
  await Promise.resolve()
  await nextTick()

  assert.equal(supplementSourcesId, 1)
  assert.deepEqual(modalState.selectedVideo.maker, { name_ja: 'LEO', name_en: 'LEO' })
  assert.deepEqual(modalState.selectedVideo.label, {
    name_ja: 'LEO',
    name_en: 'LEO',
    name_ja_translated: '狮子厂牌',
    name_en_translated: '狮子厂牌',
    name_translated: '狮子厂牌',
  })
  assert.equal(modalState.selectedVideo.series, undefined)
  assert.deepEqual(modalState.selectedVideo.categories, [{
    id: '姉・妹',
    name_ja: '姉・妹',
    name_en: '姉・妹',
    name_ja_translated: '姐妹',
    name_en_translated: '姐妹',
  }])
  assert.deepEqual(modalState.selectedVideo.actresses, [
    { id: '糸井瑠花', name_kanji: '糸井瑠花', name_romaji: '糸井瑠花' },
    {
      id: '凰華りん',
      name_kanji: '凰華りん',
      name_romaji: '凰華りん',
      name_kanji_translated: '凰华凛',
      name_romaji_translated: '凰华凛',
    },
  ])
  assert.equal(modalState.selectedVideo.summary, 'Original summary')
  assert.equal(modalState.selectedVideo.summary_translated, '翻译简介')
  assert.equal(modalState.selectedVideo.jacket_full_url, 'https://example.test/pl.jpg')
  assert.equal(modalState.selectedVideo.jacket_thumb_url, 'https://example.test/ps.jpg')
  assert.equal(modalState.selectedVideo.sample_url, 'https://example.test/sample.mp4')
  assert.equal(modalState.selectedVideo._loading.supplement, false)

  resetModal()
})
