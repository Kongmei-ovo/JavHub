import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const favorites = styleSource('./Favorites.vue')
const magnetParse = styleSource('./MagnetParse.vue')
const subscription = styleSource('./Subscription.vue')
const globalStyles = readFileSync(new URL('../assets/main.css', import.meta.url), 'utf8')

function styleSource(path) {
  const fileUrl = new URL(path, import.meta.url)
  const source = readFileSync(fileUrl, 'utf8')
  const external = source.match(/<style[^>]*src="([^"]+)"[^>]*><\/style>/)
  if (external) {
    return readFileSync(new URL(external[1], fileUrl), 'utf8')
  }
  const match = source.match(/<style[^>]*>([\s\S]*?)<\/style>/)
  assert.ok(match, `${path} should include a style block`)
  return match[1]
}

function cssBlock(source, selector) {
  const blocks = [...source.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
  const match = blocks.find(([, selectors]) => selectors
    .split(',')
    .map(part => part.trim())
    .includes(selector))
  assert.ok(match, `${selector} block should exist`)
  return match[2]
}

function assertUsesPageRail(block, label) {
  assert.doesNotMatch(block, /max-width\s*:/, `${label} should not add a secondary max width`)
  assert.doesNotMatch(block, /width\s*:\s*min\(/, `${label} should not add a secondary width rail`)
  assert.doesNotMatch(block, /margin(?:-inline)?\s*:\s*[^;]*auto/, `${label} should not recenter inside page-shell`)
}

test('favorites header surfaces use the global page rail', () => {
  assertUsesPageRail(cssBlock(favorites, '.curate-header-main'), 'favorites header')
  assertUsesPageRail(cssBlock(favorites, '.collection-manager'), 'favorites collection manager')
})

test('magnet parser workbench surfaces use the global page rail', () => {
  for (const selector of ['.parse-console', '.result-section', '.issue-panel', '.empty-state']) {
    assertUsesPageRail(cssBlock(magnetParse, selector), selector)
  }
})

test('subscription grid keeps the global page rail without local offsets', () => {
  assert.doesNotMatch(cssBlock(subscription, '.sub-page'), /--page-max\s*:/)
  assert.doesNotMatch(cssBlock(subscription, '.tab-content'), /padding\s*:\s*0\s+\d/)
})

test('global grid helpers do not offset the download task stats rail', () => {
  assert.doesNotMatch(globalStyles, /\.results-grid\s*,\s*\.stats-bar/)
  assert.doesNotMatch(globalStyles, /\.stats-bar\s*\{[\s\S]*?padding\s*:\s*20px/)
})
