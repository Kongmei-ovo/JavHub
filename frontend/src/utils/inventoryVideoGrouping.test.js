import assert from 'node:assert/strict'
import test from 'node:test'

import {
  extractCode,
  groupEmbyVideosByYear,
  groupMissingVideosByYear,
} from './inventoryVideoGrouping.js'

test('extractCode extracts video code from title and uppercases it', () => {
  assert.equal(extractCode('miaa-784 some title 2024'), 'MIAA-784')
  assert.equal(extractCode('Some prefix abp-123-hack suffix'), 'ABP-123')
  assert.equal(extractCode('no recognizable code'), '')
})

test('groupEmbyVideosByYear groups by production year, premiere date, then title year in ascending order', () => {
  const grouped = groupEmbyVideosByYear([
    { item_id: 'unknown', title: 'MIAA-001 No year' },
    { item_id: 'title-year', title: 'IPX-777 2019 title year' },
    { item_id: 'production-year', title: 'ABP-123 2024 title ignored', production_year: 2001 },
    { item_id: 'premiere-date', title: 'SSIS-555', premiere_date: '2020-04-03T00:00:00Z' },
  ])

  assert.deepEqual(Object.keys(grouped), ['2001', '2019', '2020', '未知'])
  assert.deepEqual(grouped['2001'].map((video) => video.item_id), ['production-year'])
  assert.deepEqual(grouped['2019'].map((video) => video.item_id), ['title-year'])
  assert.deepEqual(grouped['2020'].map((video) => video.item_id), ['premiere-date'])
  assert.deepEqual(grouped['未知'].map((video) => video.item_id), ['unknown'])
})

test('groupEmbyVideosByYear does not mutate videos and returns display code on new objects', () => {
  const original = Object.freeze({ item_id: '1', title: 'miaa-784 sample', production_year: 2024 })
  const grouped = groupEmbyVideosByYear([original])
  const [video] = grouped['2024']

  assert.notEqual(video, original)
  assert.equal(video.displayCode, 'MIAA-784')
  assert.equal(Object.hasOwn(original, 'displayCode'), false)
  assert.equal(Object.hasOwn(original, '_code'), false)
})

test('groupMissingVideosByYear groups missing videos by release date and title year in ascending order', () => {
  const grouped = groupMissingVideosByYear([
    { content_id: 'unknown', title: 'Missing without year' },
    { content_id: 'title-year', title: 'MIAA-784 2021' },
    { content_id: 'release-date', title: 'ABP-123 2024 ignored', release_date: '2018-12-01' },
  ])

  assert.deepEqual(Object.keys(grouped), ['2018', '2021', '未知'])
  assert.deepEqual(grouped['2018'].map((video) => video.content_id), ['release-date'])
  assert.deepEqual(grouped['2021'].map((video) => video.content_id), ['title-year'])
  assert.deepEqual(grouped['未知'].map((video) => video.content_id), ['unknown'])
})
