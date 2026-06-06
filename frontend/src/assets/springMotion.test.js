import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const mainCss = readFileSync(new URL('./main.css', import.meta.url), 'utf8')

function blockFor(prefix) {
  const start = mainCss.indexOf(prefix)
  if (start === -1) return ''

  const open = mainCss.indexOf('{', start)
  let depth = 1
  let index = open + 1
  while (index < mainCss.length && depth > 0) {
    if (mainCss[index] === '{') depth += 1
    if (mainCss[index] === '}') depth -= 1
    index += 1
  }

  return mainCss.slice(open + 1, index - 1)
}

function customProperties(source) {
  const properties = new Map()
  for (const match of source.matchAll(/(--[\w-]+):\s*([^;]+);/g)) {
    properties.set(match[1], match[2].trim())
  }
  return properties
}

function mediaBlock(query) {
  const start = mainCss.indexOf(`@media ${query}`)
  if (start === -1) return ''

  const open = mainCss.indexOf('{', start)
  let depth = 1
  let index = open + 1
  while (index < mainCss.length && depth > 0) {
    if (mainCss[index] === '{') depth += 1
    if (mainCss[index] === '}') depth -= 1
    index += 1
  }

  return mainCss.slice(open + 1, index - 1)
}

const properties = customProperties(blockFor(':root'))

test('Apple spring motion exposes soft snappy and overshoot easing tokens', () => {
  assert.equal(properties.get('--ease-spring-soft'), 'cubic-bezier(0.34, 1.56, 0.64, 1)')
  assert.equal(properties.get('--ease-spring-snappy'), 'cubic-bezier(0.5, 1.7, 0.6, 1)')
  assert.equal(properties.get('--ease-spring-overshoot'), 'cubic-bezier(0.2, 1.8, 0.4, 1)')
})

test('Apple spring motion exposes standard and emphasized duration tokens', () => {
  assert.equal(properties.get('--motion-spring'), '280ms var(--ease-spring-soft)')
  assert.equal(properties.get('--motion-spring-emphasized'), '420ms var(--ease-spring-snappy)')
})

test('Reduced motion compresses spring motion durations to 1ms', () => {
  const reducedMotion = mediaBlock('(prefers-reduced-motion: reduce)')

  assert.match(reducedMotion, /--motion-spring:\s*1ms var\(--ease-spring-soft\);/)
  assert.match(reducedMotion, /--motion-spring-emphasized:\s*1ms var\(--ease-spring-snappy\);/)
})
