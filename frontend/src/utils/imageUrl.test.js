import test from 'node:test'
import assert from 'node:assert/strict'
import { videoCardCoverUrl } from './imageUrl.js'

test('videoCardCoverUrl returns empty string when no cover fields exist', () => {
  assert.equal(videoCardCoverUrl({}), '')
})

test('videoCardCoverUrl preserves original cover url for card fallback candidates', () => {
  assert.equal(
    videoCardCoverUrl({
      jacket_thumb_url: 'https://pics.dmm.co.jp/mono/movie/miaa784/miaa784ps.jpg',
    }),
    'https://pics.dmm.co.jp/mono/movie/miaa784/miaa784ps.jpg',
  )
})
