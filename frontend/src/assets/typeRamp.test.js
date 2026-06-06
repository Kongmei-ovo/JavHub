import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const mainCss = readFileSync(new URL('./main.css', import.meta.url), 'utf8')

function customProperties(source) {
  const properties = new Map()
  for (const match of source.matchAll(/(--[\w-]+):\s*([^;]+);/g)) {
    properties.set(match[1], match[2].trim())
  }
  return properties
}

function pxValue(value) {
  const match = value.match(/^(\d+(?:\.\d+)?)px$/)
  return match ? Number(match[1]) : Number.NaN
}

const properties = customProperties(mainCss)

const ramp = [
  ['display-1', '34px', '700', '-0.4px'],
  ['display-2', '28px', '700', '-0.3px'],
  ['title-1', '22px', '700', '-0.2px'],
  ['title-2', '18px', '650', '0px'],
  ['body', '15px', '450', '0px'],
  ['callout', '14px', '500', '0px'],
  ['caption-1', '12px', '500', '0.1px'],
  ['caption-2', '11px', '600', '0.2px'],
]

test('Apple type ramp exposes eight explicit size weight and tracking steps', () => {
  for (const [name, size, weight, tracking] of ramp) {
    assert.equal(properties.get(`--type-${name}`), size)
    assert.equal(properties.get(`--type-${name}-weight`), weight)
    assert.equal(properties.get(`--type-${name}-tracking`), tracking)
  }
})

test('Apple type ramp sizes are monotonic from display to caption', () => {
  const sizes = ramp.map(([name]) => pxValue(properties.get(`--type-${name}`) ?? ''))
  assert.deepEqual(sizes, [...sizes].sort((a, b) => b - a))
  assert.ok(sizes.every((size) => Number.isFinite(size)), 'all type ramp sizes should be px tokens')
})

test('Legacy typography tokens alias into the Apple type ramp', () => {
  assert.equal(properties.get('--type-panel-title'), 'var(--type-title-1)')
  assert.equal(properties.get('--type-card-title'), 'var(--type-title-2)')
  assert.equal(properties.get('--type-control'), 'var(--type-callout)')
  assert.equal(properties.get('--type-caption'), 'var(--type-caption-1)')
  assert.equal(properties.get('--type-micro'), 'var(--type-caption-2)')
})
