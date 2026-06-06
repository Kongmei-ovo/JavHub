import test from 'node:test'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'

const componentUrl = new URL('./AppleSwitch.vue', import.meta.url)
const cssUrl = new URL('../assets/formControls.css', import.meta.url)
const source = existsSync(componentUrl) ? readFileSync(componentUrl, 'utf8') : ''
const css = existsSync(cssUrl) ? readFileSync(cssUrl, 'utf8') : ''
const rawColorPattern = /#[0-9a-fA-F]{3,8}\b|(?:rgb|hsl)a?\s*\(/g

function cssBlock(selector) {
  const searchable = css.replace(/\/\*[\s\S]*?\*\//g, '')
  const blocks = [...searchable.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
    .filter(([, selectors]) => selectors
      .split(',')
      .map(part => part.trim())
      .includes(selector))
    .map(([, , block]) => block)
  assert.ok(blocks.length, `${selector} should exist in formControls.css`)
  return blocks.join('\n')
}

test('AppleSwitch exposes v-model switch semantics without native checkbox replacement', () => {
  assert.notEqual(source, '', 'AppleSwitch.vue should exist')
  assert.match(source, /import '\.\.\/assets\/formControls\.css'/)
  assert.match(source, /modelValue:\s*\{\s*type:\s*Boolean,\s*default:\s*false\s*\}/)
  assert.match(source, /disabled:\s*\{\s*type:\s*Boolean,\s*default:\s*false\s*\}/)
  assert.match(source, /defineEmits\(\[\s*'update:modelValue',\s*'change'\s*\]\)/)
  assert.match(source, /role="switch"/)
  assert.match(source, /:aria-checked="modelValue \? 'true' : 'false'"/)
  assert.match(source, /@click="toggle"/)
  assert.doesNotMatch(source, /type=["']checkbox["']|accent-color/)
})

test('AppleSwitch matches the compact iOS geometry and spring thumb motion', () => {
  assert.notEqual(css, '', 'formControls.css should exist')
  const root = cssBlock('.apple-switch')
  const track = cssBlock('.apple-switch__track')
  const thumb = cssBlock('.apple-switch__thumb')
  const onTrack = cssBlock('.apple-switch--on .apple-switch__track')
  const onThumb = cssBlock('.apple-switch--on .apple-switch__thumb')
  const focus = cssBlock('.apple-switch:focus-visible .apple-switch__track')

  assert.match(root, /min-width:\s*var\(--apple-form-hit-target\)/)
  assert.match(root, /min-height:\s*var\(--apple-form-hit-target\)/)
  assert.match(root, /padding:\s*var\(--apple-switch-hit-padding-block\)\s*var\(--apple-switch-hit-padding-inline\)/)
  assert.match(track, /width:\s*30px/)
  assert.match(track, /height:\s*18px/)
  assert.match(track, /background:\s*var\(--b2-local-track-bg\)/)
  // Global motion guard restricts transitions to transform/opacity; track
  // color/shadow snap on toggle while the thumb springs across.
  assert.doesNotMatch(track, /transition:[^;]*\b(?:background|box-shadow|border-color)\b/)
  assert.match(thumb, /width:\s*14px/)
  assert.match(thumb, /height:\s*14px/)
  assert.match(thumb, /transform:\s*translateX\(0\)/)
  assert.match(thumb, /transition:\s*transform/)
  assert.doesNotMatch(thumb, /transition:[^;]*\bbox-shadow\b/)
  assert.match(onTrack, /background:\s*var\(--b2-local-track-bg-on\)/)
  assert.match(onThumb, /transform:\s*translateX\(12px\)/)
  assert.doesNotMatch(onThumb, /left:\s*/)
  assert.match(focus, /box-shadow:\s*var\(--apple-form-track-shadow-on\),\s*var\(--focus-ring\)/)
  assert.match(css, /--apple-form-motion-spring:\s*var\(--motion-spring,\s*280ms cubic-bezier\(0\.34,\s*1\.56,\s*0\.64,\s*1\)\)/)
  assert.match(css, /--apple-form-hit-target:\s*var\(--space-10,\s*44px\)/)
})

test('AppleSwitch form controls avoid raw colors and keep local tokens mapped to main tokens', () => {
  assert.deepEqual(css.match(rawColorPattern) || [], [])

  const tokens = cssBlock(':root')
  assert.match(tokens, /--b2-local-track-bg:\s*var\(--accent-bg\)/)
  assert.match(tokens, /--b2-local-track-bg-on:\s*var\(--accent\)/)
  assert.match(tokens, /--b2-local-track-border:\s*var\(--glass-control-border\)/)
  assert.match(tokens, /--b2-local-track-shadow:\s*var\(--glass-inner-shadow\)/)
  assert.match(tokens, /--b2-local-track-shadow-on:\s*var\(--glass-active-shadow\)/)
  assert.match(tokens, /--b2-local-thumb-bg:\s*var\(--bg-primary\)/)
  assert.match(tokens, /--b2-local-thumb-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(tokens, /--b2-local-glyph-stroke:\s*var\(--bg-primary\)/)
})
