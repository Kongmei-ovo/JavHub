import test from 'node:test'
import assert from 'node:assert/strict'
import { readdirSync, readFileSync } from 'node:fs'

const sources = [
  ['main.css', readFileSync(new URL('./main.css', import.meta.url), 'utf8')],
  ['App.vue', readFileSync(new URL('../App.vue', import.meta.url), 'utf8')],
  ['Search.vue', [
    readFileSync(new URL('../views/Search.vue', import.meta.url), 'utf8'),
    readFileSync(new URL('../features/search/search.css', import.meta.url), 'utf8'),
  ].join('\n')],
  ['Downloads.vue', [
    readFileSync(new URL('../views/Downloads.vue', import.meta.url), 'utf8'),
    readFileSync(new URL('../features/downloads/downloads.css', import.meta.url), 'utf8'),
  ].join('\n')],
]

function productionStyleSources(path = new URL('../', import.meta.url)) {
  return readdirSync(path, { withFileTypes: true }).flatMap((entry) => {
    const child = new URL(`${entry.name}${entry.isDirectory() ? '/' : ''}`, path)
    if (entry.isDirectory()) return productionStyleSources(child)
    if (!entry.name.endsWith('.vue') && !entry.name.endsWith('.css')) return []
    return [[child.pathname.replace(/.*\/src\//, 'src/'), readFileSync(child, 'utf8')]]
  })
}

// Candidates wave A 走 v2 设计语言,在用户决定 A/B 之前不纳入
// focus-ring / uppercase 等扫描契约;ratchet 计数(font-size / spacing)仍然
// 全文件参与,以便保留"整体趋势不回退"的护栏。
const v2IslandPaths = new Set([
  'src/features/candidates/DownloadCandidatePanel.vue',
  'src/features/candidates/downloadCandidatePanel.css',
])

test('Apple typography avoids negative letter spacing across shell and primary pages', () => {
  for (const [name, source] of sources) {
    assert.doesNotMatch(
      source,
      /letter-spacing:\s*-[0-9.]+(?:em|px|rem)/,
      `${name} should not use negative letter spacing`
    )
  }
})

test('Production UI styles avoid transition-all repaint traps', () => {
  for (const [name, source] of productionStyleSources()) {
    assert.doesNotMatch(
      source,
      /(?:transition|--transition-pro):\s*all\b/,
      `${name} should transition explicit properties instead of all`
    )
  }
})

test('Production UI styles avoid layout-property transitions', () => {
  const layoutTransition = /^\s*transition:\s*[^;]*\b(?:width|height|top|right|bottom|left|min-width|max-width|min-height|max-height)\b[^;]*;/gm
  const offenders = []

  for (const [name, source] of productionStyleSources()) {
    for (const match of source.matchAll(layoutTransition)) {
      const line = source.slice(0, match.index).split('\n').length
      offenders.push(`${name}:${line}:${match[0].trim()}`)
    }
  }

  assert.deepEqual(offenders, [])
})

test('Production progress meters avoid inline width bindings', () => {
  const inlineWidthBinding = /:style="\{\s*width:\s*[^"]+\}"/g
  const offenders = []

  for (const [name, source] of productionStyleSources()) {
    for (const match of source.matchAll(inlineWidthBinding)) {
      if (!/%|percent/i.test(match[0])) continue
      const line = source.slice(0, match.index).split('\n').length
      offenders.push(`${name}:${line}:${match[0]}`)
    }
  }

  assert.deepEqual(offenders, [])
})

test('Production focus halos use shared focus ring tokens', () => {
  const rawAccentFocusRing = /(?:outline:\s*3px solid\s+rgba\(var\(--accent-rgb\),\s*0\.\d+\)|(?:inset\s+)?0 0 0 [34]px rgba\(var\(--accent-rgb\),\s*0\.\d+\))/g
  const offenders = []

  for (const [name, source] of productionStyleSources()) {
    if (v2IslandPaths.has(name)) continue
    for (const match of source.matchAll(rawAccentFocusRing)) {
      const line = source.slice(0, match.index).split('\n').length
      const lineText = source.split('\n')[line - 1] || ''
      if (/--focus-(?:ring|outline)/.test(lineText)) continue
      offenders.push(`${name}:${line}:${match[0]}`)
    }
  }

  assert.deepEqual(offenders, [])
})

test('Apple-style microcopy avoids forced uppercase labels', () => {
  for (const [name, source] of productionStyleSources()) {
    if (v2IslandPaths.has(name)) continue
    assert.doesNotMatch(
      source,
      /text-transform:\s*uppercase\b/,
      `${name} should use natural-case microcopy instead of forced uppercase labels`
    )
  }
})

test('Production UI styles ratchet raw font sizes toward shared type tokens', () => {
  const rawFontSize = /font-size:\s*\d+(?:\.\d+)?px\b/g
  const offenders = []
  const tokenSources = new Set(['src/assets/main.css'])
  // Today 页面 hero h1 用 30px,不在 --type-* ramp 上(--type-display-2=28 / --type-page-title-mobile=26)。
  // 视觉精修要求页面标题立起来,留作单点豁免,后续若加 30px 档再迁。
  const existingRawFontSizeCount = 210

  for (const [name, source] of productionStyleSources()) {
    if (tokenSources.has(name)) continue

    for (const match of source.matchAll(rawFontSize)) {
      const line = source.slice(0, match.index).split('\n').length
      offenders.push(`${name}:${line}:${match[0]}`)
    }
  }

  assert.equal(
    offenders.length,
    existingRawFontSizeCount,
    `raw font-size px declarations changed; migrate to --type-* tokens instead:\n${offenders.join('\n')}`
  )
})
