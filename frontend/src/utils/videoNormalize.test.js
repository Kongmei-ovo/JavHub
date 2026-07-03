import test from 'node:test'
import assert from 'node:assert/strict'
import { normalizeVideo, videoCodeOf, videoCoverCandidates } from './videoNormalize.js'

test('normalizeVideo maps alternate card fields into canonical video fields', () => {
  const video = normalizeVideo({
    id: 'ALT-001',
    code: 'ALT-001',
    title: 'Alternate title',
    cover_url: 'thumb.jpg',
    date: '2026-05-06',
  })

  assert.equal(video.content_id, 'ALT-001')
  assert.equal(video.dvd_id, 'ALT-001')
  assert.equal(video.title_ja, 'Alternate title')
  assert.equal(video.jacket_thumb_url, 'thumb.jpg')
  assert.equal(video.release_date, '2026-05-06')
})

test('normalizeVideo preserves existing canonical fields', () => {
  const video = normalizeVideo({
    content_id: 'MIAA-784',
    dvd_id: 'MIAA-784',
    title_ja: 'Japanese title',
    jacket_thumb_url: 'canonical.jpg',
    release_date: '2026-01-02',
  })

  assert.equal(video.content_id, 'MIAA-784')
  assert.equal(video.dvd_id, 'MIAA-784')
  assert.equal(video.title_ja, 'Japanese title')
  assert.equal(video.jacket_thumb_url, 'canonical.jpg')
  assert.equal(video.release_date, '2026-01-02')
})

test('videoCodeOf returns first available stable identifier', () => {
  assert.equal(videoCodeOf({ content_id: 'CID', dvd_id: 'DVD' }), 'CID')
  assert.equal(videoCodeOf({ dvd_id: 'DVD', code: 'CODE' }), 'DVD')
  assert.equal(videoCodeOf({ code: 'CODE', id: 'ID' }), 'CODE')
  assert.equal(videoCodeOf({ id: 123 }), '123')
  assert.equal(videoCodeOf({}), '')
})

test('videoCodeOf skips empty string identifiers while preserving numeric zero', () => {
  assert.equal(videoCodeOf({ content_id: '', dvd_id: 'DVD-001' }), 'DVD-001')
  assert.equal(videoCodeOf({ content_id: '', dvd_id: '', code: 'CODE-001' }), 'CODE-001')
  assert.equal(videoCodeOf({ content_id: 0, dvd_id: 'DVD-001' }), '0')
})

test('videoCoverCandidates keeps the raw portrait ps when the code cannot be re-derived', () => {
  const candidates = videoCoverCandidates({
    jacket_thumb_url: 'https://pics.dmm.co.jp/mono/movie/144ohdr0077r/144ohdr0077rps.jpg',
  })

  // Leading-digit id can't be padded → no digital twin; portrait ps stays as-is (never pl).
  assert.deepEqual(candidates, [
    'https://pics.dmm.co.jp/mono/movie/144ohdr0077r/144ohdr0077rps.jpg',
  ])
})

test('videoCoverCandidates upgrades to the HD digital-twin ps and dedupes', () => {
  const candidates = videoCoverCandidates({
    jacket_thumb_url: 'https://pics.dmm.co.jp/mono/movie/miaa784/miaa784ps.jpg',
    jacket_full_url: 'https://pics.dmm.co.jp/mono/movie/miaa784/miaa784ps.jpg',
    cover_url: 'https://pics.dmm.co.jp/mono/movie/miaa784/miaa784ps.jpg',
  })

  assert.deepEqual(candidates, [
    'https://awsimgsrc.dmm.co.jp/pics_dig/digital/video/miaa00784/miaa00784ps.jpg',
    'https://pics.dmm.co.jp/mono/movie/miaa784/miaa784ps.jpg',
  ])
})
