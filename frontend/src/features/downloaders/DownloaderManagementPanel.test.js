import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

let source = ''
try {
  source = readFileSync(new URL('./DownloaderManagementPanel.vue', import.meta.url), 'utf8')
} catch (_) {
  assert.fail('DownloaderManagementPanel.vue should exist as a lazy downloaders child chunk')
}

function cssBlocks(content, selector) {
  const searchable = content.replace(/\/\*[\s\S]*?\*\//g, '')
  const blocks = [...searchable.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
    .filter(([, selectors]) => selectors
      .split(',')
      .map(part => part.trim())
      .includes(selector))
    .map(([, , block]) => block)
  assert.ok(blocks.length, `${selector} block should exist`)
  return blocks
}

function cssBlock(content, selector) {
  return cssBlocks(content, selector).join('\n')
}

function backgroundIncludes(block, token) {
  const match = block.match(/background:\s*([^;]+);/)
  return Boolean(match && match[1].includes(token))
}

test('downloader panel is isolated behind a component contract', () => {
  assert.match(source, /name:\s*'DownloaderManagementPanel'/)
  assert.match(source, /props:\s*\{[\s\S]*downloaders:/)
  assert.match(source, /emits:\s*\[[\s\S]*'refresh'[\s\S]*'save'[\s\S]*'apply-editor'/)
  assert.match(source, /class="downloaders-panel apple-reveal"/)
})

test('downloader panel controls use shared Apple glass materials', () => {
  const toolbar = cssBlock(source, '.downloader-toolbar')
  const iconAction = cssBlock(source, '.icon-action')
  const iconActionHover = cssBlock(source, '.icon-action:hover:not(:disabled)')
  const iconActionFocus = cssBlock(source, '.icon-action:focus-visible:not(:disabled)')
  const iconActionPrimary = cssBlock(source, '.icon-action.primary')
  const iconActionPrimaryFocus = cssBlock(source, '.icon-action.primary:focus-visible')
  const iconActionCompact = cssBlock(source, '.icon-action.compact')
  const iconActionCompactFocus = cssBlock(source, '.icon-action.compact:focus-visible:not(:disabled)')
  const iconActionDanger = cssBlock(source, '.icon-action.danger')
  const iconActionDangerHover = cssBlock(source, '.icon-action.danger:hover:not(:disabled)')
  const iconActionDangerFocus = cssBlock(source, '.icon-action.danger:focus-visible:not(:disabled)')
  const downloaderRow = cssBlock(source, '.downloader-row')
  const downloaderRowHover = cssBlock(source, '.downloader-row:hover')
  const downloaderRowFocus = cssBlock(source, '.downloader-row:focus-visible')
  const downloaderAvatar = cssBlock(source, '.downloader-avatar')
  const downloaderAvatarMuted = cssBlock(source, '.downloader-avatar.muted')
  const switchTrack = cssBlock(source, '.switch-mini span')
  const switchTrackChecked = cssBlock(source, '.switch-mini input:checked + span')
  const downloaderSheetSection = cssBlock(source, '.downloader-sheet-section')
  const inlineDialogOverlay = cssBlock(source, '.inline-dialog-overlay')
  const inlineDialog = cssBlock(source, '.inline-dialog')
  const closeButton = cssBlock(source, '.dialog-close-btn')

  for (const block of [toolbar, iconAction, iconActionCompact, downloaderAvatar, switchTrack, downloaderSheetSection, closeButton]) {
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/)
    assert.ok(backgroundIncludes(block, '--material-glass-control'))
    assert.match(block, /var\(--surface-specular-edge\)/)
    assert.match(block, /var\(--surface-noise\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  }

  for (const block of [iconActionHover]) {
    assert.ok(backgroundIncludes(block, '--material-glass-control-hover'))
    assert.match(block, /var\(--surface-specular-edge-strong\)/)
    assert.match(block, /var\(--surface-noise\)/)
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  }

  for (const [block, name] of [
    [iconActionFocus, 'icon action focus'],
    [iconActionCompactFocus, 'compact icon action focus'],
  ]) {
    assert.ok(backgroundIncludes(block, '--material-glass-control-hover'), `${name} should use hover glass material`)
    assert.match(block, /var\(--surface-specular-edge-strong\)/, `${name} should use strong specular edge`)
    assert.match(block, /var\(--surface-noise\)/, `${name} should keep the shared noise layer`)
    assert.match(block, /outline:\s*none/, `${name} should avoid double native focus chrome`)
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/, `${name} should use shared hover border`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/, `${name} should add a soft focus halo`)
    assert.match(block, /transform:\s*translateY\(-1px\)/, `${name} should lift lightly`)
  }

  assert.match(downloaderRow, /border:\s*1px solid var\(--hairline\)/)
  assert.match(downloaderRow, /background:\s*var\(--card-2\)/)
  assert.match(downloaderRow, /box-shadow:\s*none/)
  assert.doesNotMatch(downloaderRow, /material-glass|surface-specular-edge|surface-noise|backdrop-filter/)
  assert.match(downloaderRowHover, /border-color:\s*var\(--hairline-strong\)/)
  assert.match(downloaderRowHover, /background:\s*var\(--card-hover\)/)
  assert.match(downloaderRowHover, /box-shadow:\s*var\(--shadow-card\)/)
  assert.match(downloaderRowFocus, /outline:\s*none/)
  assert.match(downloaderRowFocus, /border-color:\s*var\(--hairline-strong\)/)
  assert.match(downloaderRowFocus, /background:\s*var\(--card-hover\)/)
  assert.match(downloaderRowFocus, /box-shadow:\s*var\(--shadow-card\),\s*var\(--focus-ring\)/)
  assert.doesNotMatch(`${downloaderRowHover}\n${downloaderRowFocus}`, /material-glass|surface-specular-edge|surface-noise|backdrop-filter/)

  assert.match(downloaderAvatarMuted, /background:\s*var\(--card\)/)
  assert.doesNotMatch(downloaderAvatarMuted, /var\(--surface-specular-edge|var\(--surface-noise\)/)
  assert.doesNotMatch(downloaderAvatarMuted, /var\(--surface-specular-edge|var\(--surface-noise\)/)
  assert.match(switchTrackChecked, /border-color:\s*var\(--badge-success-border\)/)
  assert.ok(backgroundIncludes(switchTrackChecked, '--badge-success-bg'))
  assert.match(switchTrackChecked, /var\(--surface-specular-edge-strong\)/)
  assert.match(switchTrackChecked, /var\(--surface-noise\)/)
  assert.ok(backgroundIncludes(iconActionPrimary, '--glass-active-material'))
  assert.match(iconActionPrimary, /var\(--surface-specular-edge-strong\)/)
  assert.match(iconActionPrimary, /var\(--surface-noise\)/)
  assert.match(iconActionPrimary, /color:\s*var\(--text-primary\)/)
  assert.match(iconActionPrimary, /border-color:\s*var\(--glass-active-border\)/)
  assert.match(iconActionPrimary, /box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.ok(backgroundIncludes(iconActionPrimaryFocus, '--glass-active-material'))
  assert.match(iconActionPrimaryFocus, /outline:\s*none/)
  assert.match(iconActionPrimaryFocus, /border-color:\s*var\(--glass-active-border\)/)
  assert.match(iconActionPrimaryFocus, /box-shadow:\s*var\(--glass-active-shadow\),\s*var\(--focus-ring\)/)
  assert.match(iconActionPrimaryFocus, /transform:\s*translateY\(-1px\)/)
  assert.ok(backgroundIncludes(iconActionDanger, '--badge-error-bg'))
  assert.match(iconActionDanger, /var\(--surface-specular-edge\)/)
  assert.match(iconActionDanger, /var\(--surface-noise\)/)
  assert.match(iconActionDanger, /color:\s*var\(--badge-error-text\)/)
  assert.match(iconActionDanger, /border-color:\s*var\(--badge-error-border\)/)
  assert.ok(backgroundIncludes(iconActionDangerHover, '--badge-error-bg'))
  assert.match(iconActionDangerHover, /var\(--surface-specular-edge-strong\)/)
  assert.match(iconActionDangerHover, /var\(--surface-noise\)/)
  assert.match(iconActionDangerHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.ok(backgroundIncludes(iconActionDangerFocus, '--badge-error-bg'))
  assert.match(iconActionDangerFocus, /outline:\s*none/)
  assert.match(iconActionDangerFocus, /border-color:\s*var\(--badge-error-border\)/)
  assert.match(iconActionDangerFocus, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*0 0 0 3px color-mix\(in srgb,\s*var\(--badge-error-text\) 18%,\s*transparent\)/)
  assert.doesNotMatch(iconActionDangerFocus, /rgba\(var\(--accent-rgb\)|rgba\(var\(--error-rgb\)/)
  assert.match(inlineDialogOverlay, /background:\s*var\(--surface-scrim\)/)
  assert.match(inlineDialogOverlay, /z-index:\s*var\(--z-modal\)/)
  assert.match(inlineDialog, /background:\s*var\(--card\)/)
  assert.doesNotMatch(inlineDialog, /var\(--surface-specular-edge|var\(--surface-noise\)/)
  assert.doesNotMatch(inlineDialog, /var\(--surface-specular-edge|var\(--surface-noise\)/)
  assert.match(inlineDialog, /box-shadow:\s*var\(--shadow-sheet\)/)

  assert.doesNotMatch(downloaderRow, /var\(--border\)/)
  assert.doesNotMatch(iconActionPrimary, /background:\s*var\(--accent\)|color:\s*var\(--text-on-accent\)|border-color:\s*var\(--accent\)/)
  assert.doesNotMatch(inlineDialogOverlay, /rgba\(0,\s*0,\s*0/)

  for (const block of [toolbar, iconAction, iconActionPrimary, iconActionCompact, downloaderRow, downloaderAvatar, downloaderAvatarMuted, switchTrack, downloaderSheetSection, inlineDialogOverlay, inlineDialog, closeButton]) {
    assert.doesNotMatch(block, /var\(--surface-control\)|var\(--bg-card\)|var\(--bg-secondary\)|var\(--border-light\)|rgba\(255,\s*255,\s*255|#fff|#ffffff/i)
  }
})

test('downloader panel glass backgrounds are layered with specular and noise surfaces', () => {
  const singleLayerGlass = /^background:\s*var\(--(?:material-glass-control|material-glass-control-hover|material-glass-sheet|glass-active-material)\);$/gm
  const offenders = [...source.matchAll(singleLayerGlass)].map(match => match[0])

  assert.deepEqual(offenders, [], 'downloader panel primary glass surfaces should not use single-layer glass backgrounds')

  for (const [selector, token] of [
    ['.downloader-toolbar', '--material-glass-control'],
    ['.icon-action', '--material-glass-control'],
    ['.icon-action:hover:not(:disabled)', '--material-glass-control-hover'],
    ['.icon-action.primary', '--glass-active-material'],
    ['.icon-action.compact', '--material-glass-control'],
    ['.icon-action.danger', '--badge-error-bg'],
    ['.icon-action.danger:hover:not(:disabled)', '--badge-error-bg'],
    ['.icon-action.danger:focus-visible:not(:disabled)', '--badge-error-bg'],
    ['.downloader-row', '--card-2'],
    ['.downloader-row:hover', '--card-hover'],
    ['.downloader-row:focus-visible', '--card-hover'],
    ['.downloader-avatar', '--material-glass-control'],
    ['.downloader-avatar.muted', '--card'], // v2 实底
    ['.switch-mini span', '--material-glass-control'],
    ['.switch-mini input:checked + span', '--badge-success-bg'],
    ['.inline-dialog', '--card'], // v2 实底
    ['.dialog-close-btn', '--material-glass-control'],
    ['.downloader-sheet-section', '--material-glass-control'],
  ]) {
    const block = cssBlock(source, selector)
    assert.ok(backgroundIncludes(block, token), `${selector} should include ${token}`)
    if (token.startsWith('--card')) {
      assert.doesNotMatch(block, /var\(--surface-specular-edge|var\(--surface-noise\)/)
      continue
    }
    assert.match(block, /var\(--surface-specular-edge/, `${selector} should include a specular edge layer`)
    assert.match(block, /var\(--surface-noise\)/, `${selector} should include the shared noise layer`)
  }
})
