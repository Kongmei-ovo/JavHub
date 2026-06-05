import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { nextTick } from 'vue'
import { normalizeVideo, videoCodeOf, videoCoverCandidates } from '../utils/videoNormalize.js'

/**
 * Tests for AppleVideoCard behaviour.
 *
 * We validate the component's setup logic (normalization, fallback, events)
 * by extracting the <script setup> block from the SFC source and evaluating
 * it inside a function that receives props as a local variable.
 */

const source = readFileSync(new URL('./AppleVideoCard.vue', import.meta.url), 'utf8')
const styleSource = source.match(/<style scoped>([\s\S]*?)<\/style>/)?.[1] || ''

function cssBlock(selector) {
  const searchable = styleSource.replace(/\/\*[\s\S]*?\*\//g, '')
  const blocks = [...searchable.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
    .filter(([, selectors]) => selectors
      .split(',')
      .map(part => part.trim())
      .includes(selector))
    .map(([, , block]) => block)
  assert.ok(blocks.length, `${selector} should exist in AppleVideoCard.vue`)
  return blocks.join('\n')
}

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
  const rawProps = {
    video: {
      content_id: 'MIAA-784',
      title_ja: 'Title',
      jacket_thumb_url: 'cover.jpg',
      release_date: '2026-05-06',
      runtime_mins: 120,
      sample_url: 'sample.mp4',
      display_code: 'MIAA-784',
      variant_labels: [],
      ...propsOverride.video,
    },
    coverUrl: '',
    favorited: false,
    showFavorite: true,
    ...propsOverride,
  }
  return import('vue').then(({ computed, reactive, ref, watch }) => {
    const props = reactive(rawProps)
    const body = getSetupBody()
    // `props` is injected as a parameter, matching what defineProps() would provide.
    const fn = new Function(
      'computed', 'ref', 'watch', 'normalizeVideo', 'videoCoverCandidates', 'props',
      `${body}\nreturn { imageError, wideImage, coverIndex, normalized, coverCandidates, coverUrl, titleText, displayCode, fallbackText, serviceLabel, variantLabels, variantTooltip, onImageError, onImageLoad }`
    )
    return { ...fn(computed, ref, watch, normalizeVideo, videoCoverCandidates, props), props }
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
  assert.deepEqual(r.coverCandidates.value, ['override.jpg', 'cover.jpg'])
})

test('AppleVideoCard advances through cover candidates before fallback', async () => {
  const r = await runSetup({
    video: {
      jacket_thumb_url: 'first.jpg',
      jacket_full_url: 'second.jpg',
    },
  })

  assert.equal(r.coverUrl.value, 'first.jpg')
  r.onImageError()
  assert.equal(r.coverUrl.value, 'second.jpg')
  assert.equal(r.imageError.value, false)
  r.onImageError()
  assert.equal(r.coverUrl.value, '')
  assert.equal(r.imageError.value, true)
})

test('AppleVideoCard resets failed cover state when candidates change', async () => {
  const props = {
    video: {
      content_id: 'OLD-001',
      title_ja: 'Old',
      jacket_thumb_url: 'old.jpg',
    },
    coverUrl: '',
  }
  const r = await runSetup(props)

  r.onImageError()
  assert.equal(r.imageError.value, true)
  r.props.video = {
    content_id: 'NEW-001',
    title_ja: 'New',
    jacket_thumb_url: 'new.jpg',
  }
  await nextTick()

  assert.equal(r.imageError.value, false)
  assert.equal(r.coverIndex.value, 0)
  assert.equal(r.coverUrl.value, 'new.jpg')
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

test('AppleVideoCard prefers backend display_code over raw identifiers', async () => {
  const r = await runSetup({ video: { content_id: 'miaa00784', dvd_id: '', display_code: 'MIAA-784' } })
  assert.equal(r.displayCode.value, 'MIAA-784')
})

test('AppleVideoCard exposes compact variant labels and explanation tooltip', async () => {
  const r = await runSetup({
    video: {
      variant_labels: [
        { key: 'digital', label: '数字版', short_label: '数字' },
        { key: 'bod', label: 'BOD 蓝光按需', short_label: 'BOD' },
        { key: 'bonus', label: 'FANZA限定特典', short_label: '特典' },
      ],
      variant_explanations: [
        { label: 'BOD 蓝光按需', meaning: 'Blu-ray Disc On Demand', evidence: '官方说明' },
      ],
    },
  })
  assert.deepEqual(r.variantLabels.value.map(label => label.short_label), ['数字', 'BOD'])
  assert.match(r.variantTooltip.value, /BOD 蓝光按需：Blu-ray Disc On Demand/)
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

test('AppleVideoCard renders variant labels on the cover', () => {
  assert.match(source, /apple-video-card__variant-stack/)
  assert.match(source, /v-for="label in variantLabels"/)
  assert.match(source, /:title="variantTooltip"/)
})

test('AppleVideoCard variant labels use shared Apple glass material', () => {
  const variantPill = cssBlock('.apple-video-card__variant-pill')

  assert.match(variantPill, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-sheet\)/)
  assert.match(variantPill, /border:\s*1px solid var\(--glass-edge\)/)
  assert.match(variantPill, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(variantPill, /color:\s*var\(--text-primary\)/)
  assert.match(variantPill, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.doesNotMatch(variantPill, /#fff|#ffffff|rgba\(255,\s*255,\s*255/i)
})

test('AppleVideoCard card shell and cover use shared Apple glass materials', () => {
  const card = cssBlock('.apple-video-card')
  const cardHover = cssBlock('.apple-video-card:hover')
  const cardFocus = cssBlock('.apple-video-card:focus-visible')
  const imageFocus = cssBlock('.apple-video-card:focus-visible .apple-video-card__image')
  const cover = cssBlock('.apple-video-card__cover')
  const fallback = cssBlock('.apple-video-card__fallback')

  assert.match(card, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-control\)/)
  assert.match(card, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(card, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(card, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.doesNotMatch(card, /var\(--surface-card\)|var\(--shadow-card\)|rgba\(255,\s*255,\s*255/)
  assert.match(cardHover, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(cardHover, /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--material-glass-control-hover\)/)
  assert.match(cardHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.doesNotMatch(cardHover, /var\(--border-light\)|var\(--surface-card-hover\)|var\(--shadow-floating\)|var\(--glass-surface-shadow\)/)
  assert.match(cardFocus, /outline:\s*none/)
  assert.match(cardFocus, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(cardFocus, /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--material-glass-control-hover\)/)
  assert.match(cardFocus, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*0 0 0 4px rgba\(var\(--accent-rgb\),\s*0\.12\)/)
  assert.match(imageFocus, /transform:\s*scale\(1\.045\)/)
  assert.match(imageFocus, /filter:\s*saturate\(1\.08\)/)

  for (const [block, label] of [[cover, 'cover'], [fallback, 'fallback']]) {
    assert.match(block, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-control\)/, `${label} should use shared control material`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/, `${label} should use shared control shadow`)
    assert.doesNotMatch(block, /var\(--surface-control\)|var\(--border-light\)|rgba\(255,\s*255,\s*255|#fff|#ffffff/i)
  }
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
