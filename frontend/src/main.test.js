import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./main.js', import.meta.url), 'utf8')
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'))
const viteConfig = readFileSync(new URL('../vite.config.js', import.meta.url), 'utf8')

test('main avoids installing the full Element Plus bundle on first load', () => {
  assert.doesNotMatch(source, /import ElementPlus from 'element-plus'/)
  assert.doesNotMatch(source, /element-plus\/dist\/index\.css/)
  assert.doesNotMatch(source, /element-plus\/es\/components\/message\/style\/css/)
  assert.doesNotMatch(source, /@element-plus\/icons-vue/)
  assert.doesNotMatch(source, /app\.use\(ElementPlus\)/)
})

test('frontend package no longer ships unused Element Plus dependencies', () => {
  assert.ok(!packageJson.dependencies?.['element-plus'])
  assert.ok(!packageJson.dependencies?.['@element-plus/icons-vue'])
  assert.doesNotMatch(viteConfig, /element-plus|@element-plus/)
})
