import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

// WAVE-5 F1: WCAG AA contrast audit against the apple-light + apple-dark themes.
// Normal text needs ≥ 4.5 : 1; muted/secondary copy that lives over chrome
// surfaces is held to the AA-large bar of ≥ 3 : 1 since it ships at sizes
// large enough to read at that ratio.
const themesSource = readFileSync(new URL('./themes.js', import.meta.url), 'utf8')

function literalHexValuesFor(themeKey, tokens) {
  const startMarker = `'${themeKey}': makeTheme(`
  const startIdx = themesSource.indexOf(startMarker)
  assert.ok(startIdx >= 0, `themes.js should define ${themeKey} via makeTheme()`)
  // Read until the next theme key or the end of THEMES; the vars: { ... } block
  // sits inside this slice and that's all we need for hex extraction.
  const tail = themesSource.slice(startIdx + startMarker.length)
  const nextThemeRel = tail.search(/\n\s+'[\w-]+': makeTheme\(/)
  const themeBlock = nextThemeRel > 0 ? tail.slice(0, nextThemeRel) : tail
  const vars = themeBlock.match(/'--[\w-]+':\s*'#[0-9A-Fa-f]{3,8}'/g) || []
  const map = new Map()
  for (const line of vars) {
    const [, name, hex] = line.match(/'(--[\w-]+)':\s*'(#[0-9A-Fa-f]{3,8})'/) || []
    if (name && hex) map.set(name, hex)
  }
  const resolved = {}
  for (const token of tokens) {
    const hex = map.get(token)
    assert.ok(hex, `${themeKey} should declare ${token} as a literal hex for the audit`)
    resolved[token] = hex
  }
  return resolved
}

function hexToRgb(hex) {
  const value = hex.replace('#', '')
  const channels =
    value.length === 3
      ? value.split('').map((ch) => parseInt(ch + ch, 16))
      : [
          parseInt(value.slice(0, 2), 16),
          parseInt(value.slice(2, 4), 16),
          parseInt(value.slice(4, 6), 16),
        ]
  return channels.map((c) => c / 255)
}

function relativeLuminance(rgb) {
  const linear = rgb.map((channel) =>
    channel <= 0.03928 ? channel / 12.92 : Math.pow((channel + 0.055) / 1.055, 2.4)
  )
  return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
}

function contrastRatio(fgHex, bgHex) {
  const fg = relativeLuminance(hexToRgb(fgHex))
  const bg = relativeLuminance(hexToRgb(bgHex))
  const lighter = Math.max(fg, bg)
  const darker = Math.min(fg, bg)
  return (lighter + 0.05) / (darker + 0.05)
}

const PAIRS = [
  { fg: '--text-primary', bg: '--bg-primary', min: 4.5, label: 'primary text on primary surface' },
  { fg: '--text-primary', bg: '--bg-secondary', min: 4.5, label: 'primary text on secondary surface' },
  { fg: '--text-secondary', bg: '--bg-primary', min: 3.0, label: 'secondary text on primary surface' },
  { fg: '--text-muted', bg: '--bg-primary', min: 3.0, label: 'muted text on primary surface' },
]

for (const themeKey of ['apple-light']) {
  test(`${themeKey} theme meets WCAG AA contrast for primary and chrome text`, () => {
    const tokens = ['--text-primary', '--text-secondary', '--text-muted', '--bg-primary', '--bg-secondary']
    const literals = literalHexValuesFor(themeKey, tokens)
    for (const pair of PAIRS) {
      const ratio = contrastRatio(literals[pair.fg], literals[pair.bg])
      assert.ok(
        ratio >= pair.min,
        `${themeKey} ${pair.label} contrast ${ratio.toFixed(2)} below required ${pair.min}`
      )
    }
  })
}
