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
  ['Home.vue', [
    readFileSync(new URL('../views/Home.vue', import.meta.url), 'utf8'),
    readFileSync(new URL('../features/home/home.css', import.meta.url), 'utf8'),
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

test('Apple-style microcopy avoids forced uppercase labels', () => {
  for (const [name, source] of productionStyleSources()) {
    assert.doesNotMatch(
      source,
      /text-transform:\s*uppercase\b/,
      `${name} should use natural-case microcopy instead of forced uppercase labels`
    )
  }
})
