import assert from 'node:assert/strict'
import test from 'node:test'
import viteConfig from './vite.config.js'

const resolvedConfig = typeof viteConfig === 'function'
  ? await viteConfig({ command: 'build', mode: 'production' })
  : viteConfig

test('production CSS targets preserve both unprefixed and WebKit backdrop filters', () => {
  const cssTarget = resolvedConfig.build?.cssTarget

  assert.ok(Array.isArray(cssTarget), 'build.cssTarget should be an explicit browser target list')
  for (const target of ['chrome107', 'firefox103', 'safari15']) {
    assert.ok(cssTarget.includes(target), `build.cssTarget should include ${target}`)
  }
  assert.equal(resolvedConfig.build?.cssMinify, false, 'CSS minification should preserve unprefixed backdrop-filter declarations')
})
