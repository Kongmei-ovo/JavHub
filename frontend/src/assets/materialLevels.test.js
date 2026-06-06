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

function cssBlock(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = mainCss.match(new RegExp(`${escaped}\\s*\\{([\\s\\S]*?)\\n\\}`))
  return match?.[1] ?? ''
}

function saturateAmount(value) {
  const match = value.match(/saturate\((\d+(?:\.\d+)?)\)/)
  return match ? Number(match[1]) : Number.NaN
}

const properties = customProperties(mainCss)
const levels = ['L1', 'L2', 'L3', 'L4']

test('Apple material levels expose vibrancy and blur tokens', () => {
  const expected = new Map([
    ['--material-L1-vibrancy', 'saturate(1.18) contrast(1.02)'],
    ['--material-L1-blur', 'blur(40px)'],
    ['--material-L2-vibrancy', 'saturate(1.14)'],
    ['--material-L2-blur', 'blur(34px)'],
    ['--material-L3-vibrancy', 'saturate(1.10)'],
    ['--material-L3-blur', 'blur(28px)'],
    ['--material-L4-vibrancy', 'saturate(1.06)'],
    ['--material-L4-blur', 'blur(20px)'],
  ])

  for (const [token, value] of expected) {
    assert.equal(properties.get(token), value)
  }
})

test('Apple material levels expose utility classes with prefixed filters', () => {
  for (const level of levels) {
    const block = cssBlock(`.material-${level}`)
    assert.match(block, new RegExp(`backdrop-filter:\\s*var\\(--material-${level}-blur\\)\\s*var\\(--material-${level}-vibrancy\\);`))
    assert.match(block, new RegExp(`-webkit-backdrop-filter:\\s*var\\(--material-${level}-blur\\)\\s*var\\(--material-${level}-vibrancy\\);`))
  }
})

test('Apple material vibrancy decreases from chrome to popover', () => {
  const values = levels.map((level) => saturateAmount(properties.get(`--material-${level}-vibrancy`) ?? ''))
  assert.deepEqual(values, [...values].sort((a, b) => b - a))
  assert.ok(values.every((value) => Number.isFinite(value)), 'material level vibrancy should use saturate()')
})
