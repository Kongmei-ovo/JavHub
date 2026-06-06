import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const vueSource = readFileSync(new URL('./VideoModal.vue', import.meta.url), 'utf8')
const externalStyle = readFileSync(new URL('../features/videoModal/videoModal.css', import.meta.url), 'utf8')
const source = `${vueSource}\n${externalStyle}`

function metadataLoadedFor(video) {
  const match = source.match(/metadataLoaded\(\) \{([\s\S]*?)\n    \},\n    directorsDisplay/)
  assert.ok(match, 'metadataLoaded computed property should be present')
  const metadataLoaded = new Function(`return function metadataLoaded() {${match[1]}\n}`)()
  return metadataLoaded.call({ video })
}

function galleryThumbsFor(video) {
  const match = source.match(/galleryThumbs\(\) \{([\s\S]*?)\n    \},\n  \},/)
  assert.ok(match, 'galleryThumbs computed property should be present')
  const galleryThumbs = new Function(`return function galleryThumbs() {${match[1]}\n}`)()
  return galleryThumbs.call({ video })
}

function summaryDisplayFor(video) {
  const match = source.match(/summaryDisplay\(\) \{([\s\S]*?)\n    \},\n    magnets/)
  assert.ok(match, 'summaryDisplay computed property should be present')
  const summaryDisplay = new Function(`return function summaryDisplay() {${match[1]}\n}`)()
  return summaryDisplay.call({ video })
}

function sourceBlock(source, selector) {
  const pattern = new RegExp(`${selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*\\{([^}]*)\\}`)
  const match = source.match(pattern)
  assert.ok(match, `${selector} should exist`)
  return match[1]
}

test('video modal keeps large scoped styles in a feature stylesheet', () => {
  assert.match(vueSource, /<style scoped src="\.\.\/features\/videoModal\/videoModal\.css"><\/style>/)
  assert.ok(vueSource.split('\n').length < 700, 'VideoModal.vue should stay below 700 lines')
  assert.ok(externalStyle.split('\n').length > 500, 'external stylesheet should contain the moved modal styles')
})

test('metadataLoaded resolves when JavInfo detail loading finishes with empty metadata', () => {
  assert.equal(metadataLoadedFor({
    content_id: 'MIAA-784',
    _loading: { javinfo: false },
  }), true)
})

test('metadataLoaded remains true when legacy callers provide metadata fields', () => {
  assert.equal(metadataLoadedFor({
    content_id: 'MIAA-784',
    summary: 'Metadata summary',
  }), true)
})

test('metadataLoaded remains true when JavInfo directors are present', () => {
  assert.equal(metadataLoadedFor({
    content_id: 'MIAA-784',
    directors: [{ name_kanji: '松田コージ' }],
  }), true)
})

test('galleryThumbs uses supplement sample image urls when present', () => {
  assert.deepEqual(galleryThumbsFor({
    content_id: 'supp:1',
    sample_image_urls: ['https://example.test/1.jpg', 'https://example.test/2.jpg'],
  }), ['https://example.test/1.jpg', 'https://example.test/2.jpg'])
})

test('summaryDisplay prefers translated summary', () => {
  assert.equal(summaryDisplayFor({
    summary: 'Original summary',
    summary_translated: '翻译简介',
  }), '翻译简介')
  assert.equal(summaryDisplayFor({
    summary: 'Original summary',
  }), 'Original summary')
})

test('modal overlay teleports globally and can render inline on the detail page', () => {
  assert.match(source, /<teleport to="body" :disabled="inline">\s*<div v-if="visible" class="modal-overlay"/)
  assert.match(source, /inline:\s*\{ type: Boolean, default: false \}/)
  assert.match(source, /\.modal-overlay\.inline\s*\{[\s\S]*position:\s*static/)
  assert.match(source, /\.modal-overlay\s*\{[\s\S]*z-index:\s*var\(--z-lightbox\)/)
})

test('modal sheet keeps a visible translucent fallback without relying on backdrop filtering', () => {
  assert.match(source, /--modal-sheet-bg/)
  assert.match(source, /--modal-panel-bg/)
  assert.match(source, /\.modal-container\s*\{[\s\S]*background:[\s\S]*var\(--surface-specular-edge-strong\),[\s\S]*var\(--surface-noise\),[\s\S]*var\(--modal-sheet-bg\)/)
  assert.match(source, /\.modal-container\s*\{[\s\S]*backdrop-filter:\s*none/)
  assert.match(source, /\.modal-container\s*\{[\s\S]*-webkit-backdrop-filter:\s*none/)
  assert.doesNotMatch(source, /\.modal-container\s*\{[\s\S]*background:\s*rgba\(255,\s*255,\s*255,\s*0\.01\)/)
})

test('modal material stays readable and consistent over busy result grids', () => {
  const overlayBlock = source.match(/\.modal-overlay\s*\{[^}]*\}/)?.[0] || ''

  assert.match(source, /--modal-scrim-core:\s*var\(--media-blackout\)/)
  assert.match(source, /--modal-scrim-sheet:\s*color-mix\(in srgb,\s*var\(--media-blackout\) 64%,\s*transparent\)/)
  assert.match(source, /--modal-scrim-panel:\s*color-mix\(in srgb,\s*var\(--modal-scrim-core\) 24%,\s*transparent\)/)
  assert.match(source, /--modal-sheet-bg:\s*var\(--modal-scrim-sheet\)/)
  assert.match(source, /--modal-sheet-fallback:\s*var\(--modal-scrim-sheet\)/)
  assert.match(source, /--modal-panel-bg:\s*var\(--modal-scrim-panel\)/)
  assert.match(source, /:root\[data-theme="dark"\]\s+\.modal-overlay\s*\{[\s\S]*--modal-scrim-sheet:\s*color-mix\(in srgb,\s*var\(--media-blackout\) 68%,\s*transparent\)/)
  assert.match(overlayBlock, /backdrop-filter:\s*none/)
  assert.match(overlayBlock, /-webkit-backdrop-filter:\s*none/)
  assert.doesNotMatch(source, /--modal-backdrop-blur/)
  assert.doesNotMatch(source, /--modal-(?:panel|gallery|overlay)-bg:\s*rgba\(0,\s*0,\s*0/)
  assert.doesNotMatch(overlayBlock, /backdrop-filter:\s*blur/)
  assert.match(source, /\.modal-container\s*\{[\s\S]*backdrop-filter:\s*none/)
  assert.match(source, /\.modal-container\s*\{[\s\S]*-webkit-backdrop-filter:\s*none/)
})

test('modal actions use liquid glass control tokens instead of hardcoded pills', () => {
  const actionBlock = source.match(/\.preview-btn,\s*\n\.stream-btn,\s*\n\.favorite-btn\s*\{[\s\S]*?\n\}/)?.[0] || ''
  const primaryBlock = source.match(/\.preview-btn,\s*\n\.stream-btn\s*\{[\s\S]*?\n\}/)?.[0] || ''
  const favoriteActiveBlock = source.match(/\.favorite-btn\.is-active\s*\{[\s\S]*?\n\}/)?.[0] || ''
  const secondaryBlock = source.match(/\.favorite-btn,\s*\n\.stream-download-btn\s*\{[\s\S]*?\n\}/)?.[0] || ''

  assert.match(source, /--modal-action-primary-bg:\s*var\(--glass-active-material\)/)
  assert.match(source, /--modal-action-secondary-bg:\s*var\(--material-glass-control\)/)
  assert.match(actionBlock, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(actionBlock, /box-shadow:\s*var\(--modal-action-shadow\)/)
  assert.match(actionBlock, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--modal-action-secondary-bg\)/)
  assert.match(primaryBlock, /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--modal-action-primary-bg\)/)
  assert.match(primaryBlock, /border-color:\s*var\(--glass-active-border\)/)
  assert.match(favoriteActiveBlock, /border-color:\s*var\(--glass-active-border\)/)
  assert.match(favoriteActiveBlock, /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--modal-action-primary-bg\)/)
  assert.match(secondaryBlock, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--modal-action-secondary-bg\)/)
  assert.match(sourceBlock(source, '.preview-btn:hover,\n.stream-btn:hover:not(:disabled),\n.favorite-btn:hover'), /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--modal-action-secondary-bg-hover\)/)
  assert.match(sourceBlock(source, '.preview-btn:hover,\n.stream-btn:hover:not(:disabled)'), /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--modal-action-primary-bg\)/)
  assert.match(sourceBlock(source, '.stream-download-btn:hover:not(:disabled)'), /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--modal-action-secondary-bg-hover\)/)
  assert.match(sourceBlock(source, '.preview-btn:focus-visible,\n.stream-btn:focus-visible:not(:disabled),\n.favorite-btn:focus-visible'), /outline:\s*none/)
  assert.match(sourceBlock(source, '.preview-btn:focus-visible,\n.stream-btn:focus-visible:not(:disabled),\n.favorite-btn:focus-visible'), /box-shadow:\s*var\(--modal-action-shadow-hover\),\s*var\(--focus-ring-wide\)/)
  assert.match(sourceBlock(source, '.stream-download-btn:focus-visible:not(:disabled)'), /outline:\s*none/)
  assert.match(sourceBlock(source, '.stream-download-btn:focus-visible:not(:disabled)'), /box-shadow:\s*var\(--modal-action-shadow-hover\),\s*var\(--focus-ring-wide\)/)
  assert.doesNotMatch(source, /var\(--active-border\)/)
  assert.doesNotMatch(source, /\.preview-btn\s*\{[^}]*background:\s*rgba\(255,\s*255,\s*255,\s*0\.9\)/)
  assert.doesNotMatch(source, /\.stream-btn\s*\{[^}]*background:\s*rgba\(255,\s*255,\s*255,\s*0\.9\)/)
})

test('mobile modal header keeps code and actions in stable scan rows', () => {
  const mobileBlock = source.match(/@media \(max-width: 768px\)\s*\{([\s\S]*)\n\}/)?.[1] || ''
  const mobileCodeBlock = mobileBlock.match(/\.modal-code-block\s*\{([^}]*)\}/)?.[1] || ''
  const mobileCode = mobileBlock.match(/\.modal-code\s*\{([^}]*)\}/)?.[1] || ''
  const mobileActions = mobileBlock.match(/\.modal-actions\s*\{([^}]*)\}/)?.[1] || ''
  const mobileActionButtons = mobileBlock.match(/\.preview-btn,\s*\n\s*\.stream-btn,\s*\n\s*\.favorite-btn\s*\{([^}]*)\}/)?.[1] || ''

  assert.match(vueSource, /<div class="modal-code-block">[\s\S]*<div class="modal-actions"/)
  assert.match(mobileCodeBlock, /display:\s*grid/)
  assert.match(mobileCodeBlock, /grid-template-columns:\s*minmax\(0,\s*1fr\)/)
  assert.match(mobileCodeBlock, /align-items:\s*start/)
  assert.match(mobileCode, /min-width:\s*0/)
  assert.match(mobileCode, /overflow-wrap:\s*anywhere/)
  assert.match(mobileActions, /grid-template-columns:\s*repeat\(3,\s*minmax\(0,\s*1fr\)\)/)
  assert.match(mobileActions, /align-items:\s*stretch/)
  assert.match(mobileActionButtons, /width:\s*100%/)
  assert.match(mobileActionButtons, /overflow:\s*hidden/)
  assert.match(mobileActionButtons, /text-overflow:\s*ellipsis/)
  assert.doesNotMatch(mobileActions, /repeat\(auto-fit,\s*minmax\(96px,\s*1fr\)\)/)
})

test('modal people chips and lightbox controls use shared glass surfaces', () => {
  const closeBlock = sourceBlock(source, '.modal-close')
  const avatarBlock = sourceBlock(source, '.actress-avatar')
  const avatarHoverBlock = sourceBlock(source, '.actress-avatar-item:hover .actress-avatar')
  const placeholderBlock = sourceBlock(source, '.avatar-placeholder')
  const tagBlock = sourceBlock(source, '.actress-tag')
  const tagHoverBlock = sourceBlock(source, '.actress-tag:hover')
  const lightboxCloseBlock = sourceBlock(source, '.lightbox-close')
  const lightboxNavBlock = sourceBlock(source, '.lightbox-prev, .lightbox-next')

  assert.doesNotMatch(source, /transition:\s*var\(--transition-pro\)/)
  for (const block of [closeBlock, avatarBlock, tagBlock]) {
    assert.match(block, /transition:\s*transform var\(--motion-standard\),\s*opacity var\(--motion-fast\)/)
    assert.doesNotMatch(block, /transition:[^;]*(?:background|border-color|box-shadow|color|filter|backdrop-filter)/)
  }

  assert.match(source, /--modal-chip-bg:\s*var\(--material-glass-control\)/)
  assert.match(source, /--modal-chip-bg-hover:\s*var\(--material-glass-control-hover\)/)
  assert.match(source, /--modal-chip-border:\s*var\(--glass-control-border\)/)
  assert.match(source, /--modal-chip-shadow:\s*var\(--glass-control-shadow\)/)

  for (const block of [closeBlock, avatarBlock, placeholderBlock, tagBlock, lightboxCloseBlock, lightboxNavBlock]) {
    assert.match(block, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--modal-chip-bg\)/)
    assert.match(block, /border(?:|:\s*var\(--stroke-pro\) solid|:\s*1px solid)\s*[^;]*var\(--modal-chip-border\)/)
    assert.match(block, /box-shadow:\s*var\(--modal-chip-shadow\)/)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
    assert.doesNotMatch(block, /rgba\(255,\s*255,\s*255,\s*0\.(?:05|08|1|15|2)\)|blur\(20px\)/)
  }

  for (const block of [avatarHoverBlock, tagHoverBlock]) {
    assert.match(block, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--modal-chip-bg-hover\)/)
    assert.match(block, /border-color:\s*var\(--modal-chip-border-hover\)/)
    assert.match(block, /box-shadow:\s*var\(--modal-chip-shadow-hover\)/)
  }

  assert.match(sourceBlock(source, '.modal-close:hover'), /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--modal-chip-bg-hover\)/)
  assert.match(sourceBlock(source, '.lightbox-close:hover'), /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--modal-chip-bg-hover\)/)
  assert.match(sourceBlock(source, '.lightbox-prev:hover, .lightbox-next:hover'), /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--modal-chip-bg-hover\)/)
  assert.match(sourceBlock(source, '.modal-close:focus-visible'), /outline:\s*none/)
  assert.match(sourceBlock(source, '.modal-close:focus-visible'), /box-shadow:\s*var\(--modal-chip-shadow-hover\),\s*var\(--focus-ring-wide\)/)
  assert.match(sourceBlock(source, '.lightbox-close:focus-visible'), /outline:\s*none/)
  assert.match(sourceBlock(source, '.lightbox-close:focus-visible'), /box-shadow:\s*var\(--modal-chip-shadow-hover\),\s*var\(--focus-ring-wide\)/)
  assert.match(sourceBlock(source, '.lightbox-prev:focus-visible:not(:disabled), .lightbox-next:focus-visible:not(:disabled)'), /outline:\s*none/)
  assert.match(sourceBlock(source, '.lightbox-prev:focus-visible:not(:disabled), .lightbox-next:focus-visible:not(:disabled)'), /box-shadow:\s*var\(--modal-chip-shadow-hover\),\s*var\(--focus-ring-wide\)/)
  assert.match(sourceBlock(source, '.modal-close:active'), /transform:\s*scale\(0\.98\) rotate\(90deg\)/)
  assert.match(sourceBlock(source, '.lightbox-close:active'), /transform:\s*scale\(0\.96\)/)
  assert.match(sourceBlock(source, '.lightbox-prev:active:not(:disabled), .lightbox-next:active:not(:disabled)'), /transform:\s*translateY\(-50%\) scale\(0\.97\)/)
})

test('modal gallery lightbox uses shared Apple glass backdrop and depth', () => {
  const overlayBlock = sourceBlock(source, '.gallery-lightbox')
  const imageBlock = sourceBlock(source, '.lightbox-img')
  const counterBlock = sourceBlock(source, '.lightbox-counter')
  const closeBlock = sourceBlock(source, '.lightbox-close')
  const navBlock = sourceBlock(source, '.lightbox-prev, .lightbox-next')

  assert.match(source, /--modal-lightbox-bg:\s*var\(--surface-scrim,\s*var\(--scrim\)\)/)
  assert.match(source, /--modal-lightbox-image-shadow:\s*var\(--shadow-sheet\)/)
  assert.match(overlayBlock, /background:\s*var\(--modal-lightbox-bg\)/)
  assert.match(overlayBlock, /backdrop-filter:\s*blur\(var\(--glass-blur-sheet\)\)\s*saturate\(var\(--glass-saturate-surface\)\)/)
  assert.match(overlayBlock, /-webkit-backdrop-filter:\s*blur\(var\(--glass-blur-sheet\)\)\s*saturate\(var\(--glass-saturate-surface\)\)/)
  assert.match(overlayBlock, /transition:\s*transform var\(--motion-standard\),\s*opacity var\(--motion-fast\)/)
  assert.doesNotMatch(overlayBlock, /rgba\(0,\s*0,\s*0,\s*0\.95\)|blur\(20px\)|transition:\s*var\(--transition-pro\)/)

  assert.match(imageBlock, /box-shadow:\s*var\(--modal-lightbox-image-shadow\)/)
  assert.match(imageBlock, /border:\s*1px solid var\(--modal-lightbox-border\)/)
  assert.doesNotMatch(imageBlock, /0 20px 80px rgba\(0,\s*0,\s*0,\s*0\.8\)/)

  assert.match(counterBlock, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--modal-chip-bg\)/)
  assert.match(counterBlock, /border:\s*1px solid var\(--modal-chip-border\)/)
  assert.match(counterBlock, /box-shadow:\s*var\(--modal-chip-shadow\)/)
  assert.match(counterBlock, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(counterBlock, /letter-spacing:\s*0/)
  assert.match(counterBlock, /color:\s*var\(--modal-chip-color\)/)
  assert.doesNotMatch(counterBlock, /rgba\(255,\s*255,\s*255,\s*0\.5\)|letter-spacing:\s*0\.1em/)

  for (const block of [closeBlock, navBlock]) {
    assert.match(block, /color:\s*var\(--modal-chip-color\)/)
    assert.match(block, /transition:\s*transform var\(--motion-standard\),\s*opacity var\(--motion-fast\)/)
    assert.doesNotMatch(block, /color:\s*#fff|transition:\s*var\(--transition-pro\)/)
  }
})

test('modal detail labels use inherited modal text tokens without uppercase tracking', () => {
  const sectionTitleBlock = source.match(/\.section-title\s*\{[^}]*\}/)?.[0] || ''
  const metaLabelBlock = source.match(/\.meta-label\s*\{[^}]*\}/)?.[0] || ''

  assert.match(source, /--modal-text-muted:\s*var\(--modal-text-muted-base\)/)
  assert.match(sectionTitleBlock, /color:\s*var\(--modal-text-muted\)/)
  assert.match(sectionTitleBlock, /letter-spacing:\s*0/)
  assert.doesNotMatch(sectionTitleBlock, /text-transform:\s*uppercase/)
  assert.match(metaLabelBlock, /color:\s*var\(--modal-text-muted\)/)
  assert.match(metaLabelBlock, /letter-spacing:\s*0/)
  assert.doesNotMatch(metaLabelBlock, /text-transform:\s*uppercase/)
})

test('modal detail typography and dividers use modal semantic text tokens', () => {
  const modalCodeBlock = sourceBlock(source, '.modal-code-block')
  const modalCode = sourceBlock(source, '.modal-code')
  const titleBlock = sourceBlock(source, '.modal-title-block')
  const title = sourceBlock(source, '.modal-title')
  const modalMeta = sourceBlock(source, '.modal-meta')
  const metaDivider = sourceBlock(source, '.modal-meta::before')
  const metaRow = sourceBlock(source, '.meta-row')
  const metaValue = sourceBlock(source, '.meta-value')
  const metaValueEmpty = sourceBlock(source, '.meta-value--empty')
  const clickable = sourceBlock(source, '.clickable')
  const clickableHover = sourceBlock(source, '.clickable:hover')
  const actressName = sourceBlock(source, '.actress-name')
  const translatedName = sourceBlock(source, '.actress-name .name-translated')
  const actressNameHover = sourceBlock(source, '.actress-avatar-item:hover .actress-name')
  const metaProvider = sourceBlock(source, '.meta-provider')
  const summary = sourceBlock(source, '.summary-text')
  const summaryEmpty = sourceBlock(source, '.summary-text--empty')
  const skeleton = sourceBlock(source, '.skeleton')
  const skeletonAfter = sourceBlock(source, '.skeleton::after')

  assert.match(source, /--modal-text-primary:\s*var\(--media-caption-text\)/)
  assert.match(source, /--modal-text-secondary:\s*var\(--modal-text-secondary-base\)/)
  assert.match(source, /--modal-divider-subtle:\s*var\(--modal-divider-subtle-base\)/)
  assert.match(source, /--modal-skeleton-bg:\s*var\(--modal-skeleton-bg-base\)/)
  assert.match(source, /--modal-text-shadow-strong:\s*0 2px 10px var\(--modal-text-shadow-strong-color\)/)
  assert.match(source, /--modal-text-shadow-soft:\s*0 2px 8px var\(--modal-text-shadow-soft-color\)/)

  assert.match(modalCodeBlock, /border-bottom:\s*1px solid var\(--modal-divider-strong\)/)
  assert.match(titleBlock, /border-bottom:\s*1px solid var\(--modal-divider\)/)
  assert.match(modalMeta, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--modal-panel-bg\)/)
  assert.match(modalMeta, /border:\s*1px solid var\(--modal-panel-border\)/)
  assert.match(metaDivider, /background:\s*var\(--modal-divider-subtle\)/)
  assert.match(metaRow, /border-bottom:\s*1px solid var\(--modal-divider-subtle\)/)

  for (const block of [modalCode, title, metaValue, clickable, clickableHover, translatedName, actressNameHover]) {
    assert.match(block, /color:\s*var\(--modal-text-primary\)/)
  }
  assert.match(modalCode, /text-shadow:\s*var\(--modal-text-shadow-strong\)/)
  assert.match(title, /text-shadow:\s*var\(--modal-text-shadow-soft\)/)
  assert.doesNotMatch(`${modalCode}\n${title}`, /rgba\(0,\s*0,\s*0|rgba\(0,0,0/)

  assert.match(actressName, /color:\s*var\(--modal-text-secondary\)/)
  assert.match(metaProvider, /color:\s*var\(--modal-text-faint\)/)
  assert.match(summary, /color:\s*var\(--modal-text-body\)/)
  assert.match(summary, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--modal-panel-bg\)/)
  assert.match(summary, /border:\s*1px solid var\(--modal-panel-border\)/)
  assert.match(metaValueEmpty, /color:\s*var\(--modal-text-empty\)/)
  assert.match(summaryEmpty, /color:\s*var\(--modal-text-empty\)/)
  assert.match(clickable, /text-decoration-color:\s*var\(--modal-link-underline\)/)
  assert.match(clickableHover, /text-decoration-color:\s*var\(--modal-link-underline-hover\)/)
  assert.match(skeleton, /background:\s*var\(--modal-skeleton-bg\)/)
  assert.match(skeletonAfter, /var\(--modal-skeleton-shine\)/)

  for (const block of [
    modalCodeBlock,
    modalCode,
    titleBlock,
    title,
    metaDivider,
    metaRow,
    metaValue,
    metaValueEmpty,
    clickable,
    clickableHover,
    actressName,
    translatedName,
    actressNameHover,
    metaProvider,
    summary,
    summaryEmpty,
    skeleton,
    skeletonAfter,
  ]) {
    assert.doesNotMatch(block, /#fff|#ffffff|rgba\(255,\s*255,\s*255/i)
  }
})

test('modal sheet edge highlights use modal border tokens', () => {
  const overlay = sourceBlock(source, '.modal-overlay')
  const darkOverlay = source.match(/:root\[data-theme="dark"\]\s+\.modal-overlay\s*\{([^}]*)\}/)?.[1] || ''
  const container = source.match(/\n\.modal-container\s*\{([^}]*)\}/)?.[1] || ''
  assert.ok(container, 'base .modal-container block should exist')

  assert.match(overlay, /--modal-panel-border-base:\s*color-mix\(in srgb,\s*var\(--modal-text-primary\) 18%,\s*transparent\)/)
  assert.match(overlay, /--modal-panel-border:\s*var\(--modal-panel-border-base\)/)
  assert.match(overlay, /--modal-container-edge-highlight:\s*var\(--modal-container-edge-highlight-base\)/)
  assert.match(overlay, /--modal-depth-shadow:\s*color-mix\(in srgb,\s*var\(--modal-scrim-core\) 36%,\s*transparent\)/)
  assert.match(overlay, /--modal-container-shadow:\s*0 42px 120px var\(--modal-depth-shadow\),\s*inset 0 1px 0 var\(--modal-container-edge-highlight\)/)
  assert.match(darkOverlay, /--modal-panel-border-base:\s*color-mix\(in srgb,\s*var\(--modal-text-primary\) 14%,\s*transparent\)/)

  assert.match(container, /border:\s*1px solid var\(--modal-panel-border\)/)
  assert.match(container, /box-shadow:\s*var\(--modal-container-shadow\)/)
  assert.doesNotMatch(overlay, /rgba\(255,\s*255,\s*255/i)
  assert.doesNotMatch(darkOverlay, /rgba\(255,\s*255,\s*255/i)
  assert.doesNotMatch(container, /rgba\(255,\s*255,\s*255/i)
})

test('modal keeps media player and hls libraries out of the base modal chunk', () => {
  assert.match(source, /defineAsyncComponent/)
  assert.match(source, /const VideoPlayerOverlay = defineAsyncComponent\(\(\) => import\('\.\.\/features\/video\/VideoPlayerOverlay\.vue'\)\)/)
  assert.match(source, /const HlsPlayerOverlay = defineAsyncComponent\(\(\) => import\('\.\.\/features\/video\/HlsPlayerOverlay\.vue'\)\)/)
  assert.match(source, /await import\('hls\.js\/dist\/hls\.light\.mjs'\)/)
  assert.doesNotMatch(source, /import Hls from 'hls\.js'/)
  assert.doesNotMatch(source, /import VideoPlayerOverlay from '\.\.\/features\/video\/VideoPlayerOverlay\.vue'/)
  assert.doesNotMatch(source, /import HlsPlayerOverlay from '\.\.\/features\/video\/HlsPlayerOverlay\.vue'/)
})

test('modal uses the lightweight message proxy after removing the Element Plus plugin', () => {
  assert.match(source, /import \{ ElMessage \} from '\.\.\/utils\/message\.js'/)
  assert.doesNotMatch(source, /\$message/)
})

test('modal declares emitted events for async component listeners', () => {
  assert.match(source, /emits:\s*\[\s*'close',\s*'download',\s*'navigate'\s*\]/)
})

test('modal favorites are keyed by concrete service version', () => {
  assert.match(source, /function videoFavoriteId\(video = \{\}\)/)
  assert.match(source, /return id && serviceCode \? `\$\{id\}::\$\{serviceCode\}` : id/)
  assert.match(source, /favoriteState\.isFavorited\('video', id\)/)
  assert.match(source, /favoriteState\.toggle\('video', id, \{[\s\S]*service_code: this\.video\.service_code \|\| ''/)
})

test('mobile modal taxonomy chips stay in a resilient grid on iOS widths', () => {
  assert.match(source, /class="tag-list"/)
  assert.match(source, /class="tag-label"/)
  assert.match(source, /\.tag-list\s*\{[\s\S]*display:\s*flex/)
  assert.match(source, /@media \(max-width: 768px\)\s*\{[\s\S]*\.tag-list\s*\{[\s\S]*display:\s*grid/)
  assert.match(source, /grid-template-columns:\s*repeat\(auto-fill,\s*minmax\(clamp\(108px,\s*31vw,\s*148px\),\s*1fr\)\)/)
  assert.match(source, /\.tag-label\s*\{[\s\S]*-webkit-line-clamp:\s*2/)
  assert.match(source, /\.actress-tag\.clickable\s*\{[\s\S]*text-decoration:\s*none/)
})

test('mobile modal sheet uses stable poster sizing and momentum scrolling', () => {
  assert.match(source, /-webkit-overflow-scrolling:\s*touch/)
  assert.match(source, /\.modal-gallery\s*\{[\s\S]*aspect-ratio:\s*16 \/ 9/)
  assert.match(source, /\.modal-gallery\s*\{[\s\S]*flex:\s*0 0 auto/)
  assert.match(source, /\.modal-gallery\s*\{[\s\S]*height:\s*clamp\(210px,\s*48vh,\s*420px\)[\s\S]*height:\s*clamp\(210px,\s*48dvh,\s*420px\)/)
  assert.match(source, /\.modal-gallery\s*\{[\s\S]*height:\s*clamp\(210px,\s*48dvh,\s*420px\)/)
  assert.match(source, /\.modal-gallery\.image-fallback\s*\{[\s\S]*min-height:\s*clamp\(210px,\s*48vh,\s*420px\)[\s\S]*min-height:\s*clamp\(210px,\s*48dvh,\s*420px\)/)
  assert.match(source, /\.modal-gallery\.image-fallback\s*\{[\s\S]*min-height:\s*clamp\(210px,\s*48dvh,\s*420px\)/)
  assert.match(source, /\.gallery-img\s*\{[\s\S]*height:\s*100%[\s\S]*object-fit:\s*contain/)
  assert.match(source, /@media \(max-width: 768px\)\s*\{[\s\S]*\.modal-gallery\s*\{[\s\S]*height:\s*clamp\(190px,\s*38vh,\s*320px\)[\s\S]*height:\s*clamp\(190px,\s*38dvh,\s*320px\)/)
  assert.match(source, /@media \(max-width: 768px\)\s*\{[\s\S]*\.modal-gallery\s*\{[\s\S]*height:\s*clamp\(190px,\s*38dvh,\s*320px\)/)
  assert.match(source, /@media \(max-width: 768px\)\s*\{[\s\S]*\.modal-gallery\.image-fallback\s*\{[\s\S]*min-height:\s*clamp\(190px,\s*38vh,\s*320px\)[\s\S]*min-height:\s*clamp\(190px,\s*38dvh,\s*320px\)/)
  assert.match(source, /@media \(max-width: 768px\)\s*\{[\s\S]*\.modal-gallery\.image-fallback\s*\{[\s\S]*min-height:\s*clamp\(190px,\s*38dvh,\s*320px\)/)
  assert.match(source, /\.modal-actions\s*\{[\s\S]*grid-template-columns:\s*repeat\(3,\s*minmax\(0,\s*1fr\)\)/)
})
