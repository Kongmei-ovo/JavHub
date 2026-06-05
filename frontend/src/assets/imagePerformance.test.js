import test from 'node:test'
import assert from 'node:assert/strict'
import { readdirSync, readFileSync } from 'node:fs'

function productionVueSources(path = new URL('../', import.meta.url)) {
  return readdirSync(path, { withFileTypes: true }).flatMap((entry) => {
    const child = new URL(`${entry.name}${entry.isDirectory() ? '/' : ''}`, path)
    if (entry.isDirectory()) return productionVueSources(child)
    if (!entry.name.endsWith('.vue')) return []
    return [[child.pathname.replace(/.*\/src\//, 'src/'), readFileSync(child, 'utf8')]]
  })
}

function imageTags(source) {
  return [...source.matchAll(/<img\b[\s\S]*?(?:\/>|>)/g)].map((match) => ({
    tag: match[0],
    index: match.index,
  }))
}

function sourceLine(source, index) {
  return source.slice(0, index).split('\n').length
}

test('production images declare async decoding and an explicit loading strategy', () => {
  const offenders = []

  for (const [name, source] of productionVueSources()) {
    for (const { tag, index } of imageTags(source)) {
      const line = sourceLine(source, index)
      if (!/\bdecoding="async"/.test(tag) || !/\bloading="(?:lazy|eager)"/.test(tag)) {
        offenders.push(`${name}:${line}:${tag.replace(/\s+/g, ' ').trim()}`)
      }
    }
  }

  assert.deepEqual(offenders, [])
})
