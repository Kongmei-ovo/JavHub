import test from 'node:test'
import assert from 'node:assert/strict'
import { videoCardCoverUrl, dmmCoverCandidates } from './imageUrl.js'

test('videoCardCoverUrl returns empty string when no cover fields exist', () => {
  assert.equal(videoCardCoverUrl({}), '')
})

// Cards show the 竖版封面 (ps). A mono thumb upgrades to the HD-CDN digital-twin ps (portrait).
test('videoCardCoverUrl upgrades a mono thumb to the HD digital-twin ps (portrait)', () => {
  assert.equal(
    videoCardCoverUrl({
      jacket_thumb_url: 'https://pics.dmm.co.jp/mono/movie/miaa784/miaa784ps.jpg',
    }),
    'https://awsimgsrc.dmm.co.jp/pics_dig/digital/video/miaa00784/miaa00784ps.jpg',
  )
})

test('cards return the portrait ps only — never the landscape pl', () => {
  const cands = dmmCoverCandidates({ jacket_full_url: 'https://pics.dmm.co.jp/digital/video/achj00017/achj00017pl.jpg' })
  assert.deepEqual(cands, [
    'https://awsimgsrc.dmm.co.jp/pics_dig/digital/video/achj00017/achj00017ps.jpg',
    'https://pics.dmm.co.jp/digital/video/achj00017/achj00017ps.jpg',
  ])
  assert.ok(!cands.some(u => /pl\.jpg$/.test(u)), 'no pl (landscape) in card candidates')
})

test('modal (hd) shows the 大图 pl: HD 2184px CDN first, legacy 800px fallback', () => {
  assert.deepEqual(
    dmmCoverCandidates(
      { jacket_full_url: 'https://pics.dmm.co.jp/digital/video/achj00017/achj00017pl.jpg' },
      { hd: true },
    ),
    [
      'https://awsimgsrc.dmm.co.jp/pics_dig/digital/video/achj00017/achj00017pl.jpg',
      'https://pics.dmm.co.jp/digital/video/achj00017/achj00017pl.jpg',
    ],
  )
})

// The actress-videos catalog endpoint gives only a mono-cid ps thumb (portrait), full_url=null.
test('actor-page mono thumb: card = HD digital-twin ps then raw ps (both portrait)', () => {
  assert.deepEqual(
    dmmCoverCandidates({ jacket_thumb_url: 'https://awsimgsrc.dmm.com/dig/mono/movie/jur740/jur740ps.jpg' }),
    [
      'https://awsimgsrc.dmm.co.jp/pics_dig/digital/video/jur00740/jur00740ps.jpg',
      'https://awsimgsrc.dmm.com/dig/mono/movie/jur740/jur740ps.jpg',
    ],
  )
})

test('actor-page mono thumb: modal = HD digital-twin pl, legacy 800px pl, raw fallback', () => {
  assert.deepEqual(
    dmmCoverCandidates(
      { jacket_thumb_url: 'https://awsimgsrc.dmm.com/dig/mono/movie/jur740/jur740ps.jpg' },
      { hd: true },
    ),
    [
      'https://awsimgsrc.dmm.co.jp/pics_dig/digital/video/jur00740/jur00740pl.jpg',
      'https://pics.dmm.co.jp/mono/movie/jur740/jur740pl.jpg',
      'https://awsimgsrc.dmm.com/dig/mono/movie/jur740/jur740ps.jpg',
    ],
  )
})

// A messy code (leading digit) can't be padded → no twin; card keeps the raw portrait ps.
test('messy code: card falls back to the raw portrait ps unchanged', () => {
  assert.deepEqual(
    dmmCoverCandidates({ jacket_thumb_url: 'https://pics.dmm.co.jp/mono/movie/144ohdr0077r/144ohdr0077rps.jpg' }),
    ['https://pics.dmm.co.jp/mono/movie/144ohdr0077r/144ohdr0077rps.jpg'],
  )
})

test('a DMM pl full_url is flipped to ps for cards (no landscape leak)', () => {
  const cands = dmmCoverCandidates({ jacket_full_url: 'https://pics.dmm.co.jp/mono/movie/144ohdr0077r/144ohdr0077rpl.jpg' })
  assert.deepEqual(cands, ['https://pics.dmm.co.jp/mono/movie/144ohdr0077r/144ohdr0077rps.jpg'])
})

test('non-DMM covers (蛋源/鸡源) pass straight through on both card and modal', () => {
  assert.deepEqual(
    dmmCoverCandidates({ cover_url: 'https://www.javbus.com/pics/cover/abc.jpg' }),
    ['https://www.javbus.com/pics/cover/abc.jpg'],
  )
  assert.deepEqual(
    dmmCoverCandidates({ jacket_full_url: 'https://x.dvd/cover.jpg' }, { hd: true }),
    ['https://x.dvd/cover.jpg'],
  )
})
