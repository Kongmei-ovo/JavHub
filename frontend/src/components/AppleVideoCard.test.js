import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { normalizeVideo, videoCodeOf } from '../utils/videoNormalize.js'

/**
 * Tests for AppleVideoCard behaviour.
 *
 * We validate the component's setup logic (normalization, fallback, events)
 * by extracting the <script setup> block from the SFC source and evaluating
 * it inside a function that receives props as a local variable.
 */

const source = readFileSync(new URL('./AppleVideoCard.vue', import.meta.url), 'utf8')

function getSetupBody() {
  const match = source.match(/<script setup>([\s\S]*?)<\/script>/)
  assert.ok(match, 'Should find <script setup> block in AppleVideoCard.vue')
  // Strip import statements (dependencies are injected as parameters),
  // and Vue SFC compiler macros (defineProps, defineEmits) which are no-ops at test time.
  return match[1]
    .replace(/^import\s+.*?from\s+.*?$/gm, '')
    .replace(/const props = defineProps\([\s\S]*?\)\n/, '')
    .replace(/const emit = defineEmits\([\s\S]*?\)\n?/, 'const emit = () => {}\n')
    .replace(/defineEmits\([\s\S]*?\)\n?/, '')
    .trim()
}

function runSetup(propsOverride = {}) {
  const props = {
    video: {
      content_id: 'MIAA-784',
      title_ja: 'Title',
      jacket_thumb_url: 'cover.jpg',
      release_date: '2026-05-06',
      runtime_mins: 120,
      sample_url: 'sample.mp4',
      ...propsOverride.video,
    },
    coverUrl: '',
    favorited: false,
    showFavorite: true,
    ...propsOverride,
  }
  return import('vue').then(({ computed, ref }) => {
    const body = getSetupBody()
    // `props` is injected as a parameter, matching what defineProps() would provide.
    const fn = new Function(
      'computed', 'ref', 'normalizeVideo', 'props',
      `${body}\nreturn { imageError, wideImage, normalized, coverUrl, titleText, displayCode, fallbackText, serviceLabel, onImageLoad }`
    )
    return fn(computed, ref, normalizeVideo, props)
  })
}

test('AppleVideoCard normalizes video fields into computed properties', async () => {
  const r = await runSetup()
  assert.equal(r.normalized.value.content_id, 'MIAA-784')
  assert.equal(r.normalized.value.title_ja, 'Title')
  assert.equal(r.normalized.value.jacket_thumb_url, 'cover.jpg')
  assert.equal(r.normalized.value.release_date, '2026-05-06')
  assert.equal(r.normalized.value.runtime_mins, 120)
  assert.equal(r.normalized.value.sample_url, 'sample.mp4')
})

test('AppleVideoCard computes coverUrl from video when prop is empty', async () => {
  const r = await runSetup()
  assert.equal(r.coverUrl.value, 'cover.jpg')
})

test('AppleVideoCard uses coverUrl prop when provided', async () => {
  const r = await runSetup({ coverUrl: 'override.jpg' })
  assert.equal(r.coverUrl.value, 'override.jpg')
})

test('AppleVideoCard uses fallback title when no title fields', async () => {
  const r = await runSetup({ video: { content_id: 'TEST-001' } })
  assert.equal(r.titleText.value, 'Untitled')
})

test('AppleVideoCard shows fallback text when no cover image', async () => {
  const r = await runSetup({ video: { content_id: 'NOIMG-01' } })
  assert.equal(r.fallbackText.value, 'NOIMG-01')
})

test('AppleVideoCard displays dvd_id before internal content_id', async () => {
  const r = await runSetup({ video: { content_id: 'cid-12345', dvd_id: 'MIAA-784' } })
  assert.equal(r.displayCode.value, 'MIAA-784')
  assert.equal(r.fallbackText.value, 'MIAA-784')
})

test('AppleVideoCard shows service badge for known service codes', async () => {
  const r = await runSetup({ video: { content_id: 'X', service_code: 'mono' } })
  assert.equal(r.serviceLabel.value, 'DVD')
})

test('AppleVideoCard returns empty badge for unknown service codes', async () => {
  const r = await runSetup({ video: { content_id: 'X' } })
  assert.equal(r.serviceLabel.value, '')
})

test('AppleVideoCard uses videoCodeOf for content_id fallback', () => {
  assert.equal(videoCodeOf({ dvd_id: 'DVD-123' }), 'DVD-123')
  assert.equal(videoCodeOf({ code: 'ABCD-001' }), 'ABCD-001')
})

test('normalizeVideo sets fallback fields from alternative sources', () => {
  const nv = normalizeVideo({ id: 'MISC-99', title_en: 'English Title', date: '2026-01-01' })
  assert.equal(nv.content_id, 'MISC-99')
  assert.equal(nv.title_ja, 'English Title')
  assert.equal(nv.release_date, '2026-01-01')
})

test('AppleVideoCard keeps cover free of overlay actions', () => {
  assert.doesNotMatch(source, /apple-video-card__favorite/, 'cover should not render favorite button')
  assert.doesNotMatch(source, /apple-video-card__preview/, 'cover should not render preview badge')
  assert.doesNotMatch(source, /toggle-favorite/, 'card should not emit favorite toggles')
  assert.ok(source.includes('loading="lazy"'), 'image should use lazy loading')
})

test('AppleVideoCard exposes button semantics on the card root', () => {
  const rootTag = source.match(/<article\b[\s\S]*?>/)
  assert.ok(rootTag, 'should render article as the card root')
  assert.match(rootTag[0], /\brole="button"/, 'card root should expose button role')
  assert.match(rootTag[0], /\btabindex="0"/, 'card root should be keyboard focusable')
})

test('AppleVideoCard opens from Enter and Space without repeated keydown triggers', () => {
  const rootTag = source.match(/<article\b[\s\S]*?>/)
  assert.ok(rootTag, 'should render article as the card root')
  assert.match(rootTag[0], /@keydown=/, 'card root should handle keyboard activation')
  assert.match(source, /event\.key !== 'Enter'/, 'keyboard activation should allow Enter')
  assert.match(source, /event\.key !== ' '/, 'keyboard activation should allow Space')
  assert.match(source, /event\.repeat/, 'keyboard activation should ignore repeated keydown events')
})

test('AppleVideoCard only declares open event', () => {
  assert.ok(source.includes("'open'"), 'should declare open event')
  assert.doesNotMatch(source, /'toggle-favorite'/, 'should not declare toggle-favorite event')
})
