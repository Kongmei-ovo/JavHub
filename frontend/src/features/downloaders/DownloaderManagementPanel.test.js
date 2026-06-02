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
  const iconActionPrimary = cssBlock(source, '.icon-action.primary')
  const iconActionCompact = cssBlock(source, '.icon-action.compact')
  const downloaderRow = cssBlock(source, '.downloader-row')
  const downloaderRowHover = cssBlock(source, '.downloader-row:hover')
  const downloaderAvatar = cssBlock(source, '.downloader-avatar')
  const downloaderAvatarMuted = cssBlock(source, '.downloader-avatar.muted')
  const switchTrack = cssBlock(source, '.switch-mini span')
  const downloaderSheetSection = cssBlock(source, '.downloader-sheet-section')
  const inlineDialogOverlay = cssBlock(source, '.inline-dialog-overlay')
  const inlineDialog = cssBlock(source, '.inline-dialog')

  for (const block of [toolbar, iconAction, iconActionCompact, downloaderRow, downloaderAvatar, switchTrack, downloaderSheetSection]) {
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/)
    assert.match(block, /background:\s*var\(--material-glass-control\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  }

  for (const block of [iconActionHover, downloaderRowHover]) {
    assert.match(block, /background:\s*var\(--material-glass-control-hover\)/)
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  }

  assert.match(downloaderAvatarMuted, /background:\s*var\(--material-glass-subtle\)/)
  assert.match(iconActionPrimary, /background:\s*var\(--glass-active-material\)/)
  assert.match(iconActionPrimary, /color:\s*var\(--text-primary\)/)
  assert.match(iconActionPrimary, /border-color:\s*var\(--glass-active-border\)/)
  assert.match(iconActionPrimary, /box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.match(inlineDialogOverlay, /background:\s*var\(--surface-scrim\)/)
  assert.match(inlineDialogOverlay, /z-index:\s*var\(--z-modal\)/)
  assert.match(inlineDialog, /background:\s*var\(--material-glass-sheet\)/)
  assert.match(inlineDialog, /box-shadow:\s*var\(--shadow-sheet\)/)

  assert.doesNotMatch(downloaderRow, /var\(--border\)/)
  assert.doesNotMatch(iconActionPrimary, /background:\s*var\(--accent\)|color:\s*var\(--text-on-accent\)|border-color:\s*var\(--accent\)/)
  assert.doesNotMatch(inlineDialogOverlay, /rgba\(0,\s*0,\s*0/)

  for (const block of [toolbar, iconAction, iconActionPrimary, iconActionCompact, downloaderRow, downloaderAvatar, downloaderAvatarMuted, switchTrack, downloaderSheetSection, inlineDialogOverlay, inlineDialog]) {
    assert.doesNotMatch(block, /var\(--surface-control\)|var\(--bg-card\)|var\(--bg-secondary\)|var\(--border-light\)|rgba\(255,\s*255,\s*255|#fff|#ffffff/i)
  }
})
