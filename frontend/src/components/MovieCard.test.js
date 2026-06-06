import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const movieCardSource = readFileSync(new URL('./MovieCard.vue', import.meta.url), 'utf8')
const appleCardSource = readFileSync(new URL('./AppleVideoCard.vue', import.meta.url), 'utf8')

test('MovieCard controls the poster media ratio through the shared Apple video card', () => {
  assert.match(movieCardSource, /:style="cardStyle"/)
  assert.match(movieCardSource, /coverAspectRatio:\s*\{ type: String, default: '3 \/ 4' \}/)
  assert.match(movieCardSource, /const cardStyle = computed\(\(\) => \(\{[\s\S]*'--movie-card-cover-aspect': props\.coverAspectRatio/)
  assert.match(appleCardSource, /aspect-ratio:\s*var\(--movie-card-cover-aspect,\s*3 \/ 4\)/)
})
