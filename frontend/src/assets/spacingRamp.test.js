import test from 'node:test'
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { readFileSync } from 'node:fs'

const mainCss = readFileSync(new URL('./main.css', import.meta.url), 'utf8')

function customProperties(source) {
  const properties = new Map()
  for (const match of source.matchAll(/(--[\w-]+):\s*([^;]+);/g)) {
    properties.set(match[1], match[2].trim())
  }
  return properties
}

function trackedProductionStyleFiles() {
  return execFileSync('git', ['ls-files', 'src'], { encoding: 'utf8' })
    .trim()
    .split('\n')
    .filter(Boolean)
    .filter((file) => /\.(css|vue)$/.test(file) && !/\.test\./.test(file))
}

function srcName(file) {
  return file.replace(/^frontend\//, '')
}

const properties = customProperties(mainCss)
const ramp = [
  ['--space-1', '4px'],
  ['--space-2', '8px'],
  ['--space-3', '12px'],
  ['--space-4', '16px'],
  ['--space-5', '20px'],
  ['--space-6', '24px'],
  ['--space-7', '28px'],
  ['--space-8', '32px'],
  ['--space-9', '36px'],
  ['--space-10', '44px'],
  ['--space-11', '56px'],
  ['--space-12', '72px'],
]

test('Apple spacing ramp exposes twelve explicit 4px-based steps', () => {
  for (const [token, value] of ramp) {
    assert.equal(properties.get(token), value)
  }
})

test('Apple spacing ramp semantic aliases resolve to shared steps', () => {
  assert.equal(properties.get('--space-card-inner'), 'var(--space-4)')
  assert.equal(properties.get('--space-card-gap'), 'var(--space-5)')
  assert.equal(properties.get('--space-section'), 'var(--space-8)')
  assert.equal(properties.get('--space-hero'), 'var(--space-12)')
})

test('Production spacing declarations ratchet non-ramp px values', () => {
  const declaration = /^\s*(padding(?:-[\w-]+)?|margin(?:-[\w-]+)?|gap|row-gap|column-gap|inset(?:-[\w-]+)?|top|right|bottom|left)\s*:\s*([^;{}]+);/gm
  const existingOffRampSpacingCount = 749
  const offenders = []

  for (const file of trackedProductionStyleFiles()) {
    const source = readFileSync(file, 'utf8')
    for (const match of source.matchAll(declaration)) {
      const value = match[2]
      const hasOffRampPx = [...value.matchAll(/(-?\d*\.?\d+)px\b/g)].some((px) => {
        const numeric = Math.abs(Number(px[1]))
        return numeric > 4 && numeric % 4 !== 0
      })
      if (!hasOffRampPx) continue

      const line = source.slice(0, match.index).split('\n').length
      offenders.push(`${srcName(file)}:${line}:${match[0].trim()}`)
    }
  }

  assert.equal(
    offenders.length,
    existingOffRampSpacingCount,
    `off-ramp spacing declarations changed; use --space-* tokens for new spacing:\n${offenders.join('\n')}`
  )
})
