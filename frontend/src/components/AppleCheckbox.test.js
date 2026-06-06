import test from 'node:test'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'

const componentUrl = new URL('./AppleCheckbox.vue', import.meta.url)
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

test('AppleCheckbox exposes checkbox semantics including indeterminate state', () => {
  assert.notEqual(source, '', 'AppleCheckbox.vue should exist')
  assert.match(source, /import '\.\.\/assets\/formControls\.css'/)
  assert.match(source, /modelValue:\s*\{\s*type:\s*Boolean,\s*default:\s*false\s*\}/)
  assert.match(source, /indeterminate:\s*\{\s*type:\s*Boolean,\s*default:\s*false\s*\}/)
  assert.match(source, /defineEmits\(\[\s*'update:modelValue',\s*'change'\s*\]\)/)
  assert.match(source, /role="checkbox"/)
  assert.match(source, /:aria-checked="ariaChecked"/)
  assert.match(source, /ariaChecked = computed\(\(\) => props\.indeterminate \? 'mixed' : props\.modelValue \? 'true' : 'false'\)/)
  assert.match(source, /v-if="indeterminate"/)
  assert.match(source, /v-else/)
  assert.match(source, /@click="toggle"/)
  assert.doesNotMatch(source, /type=["']checkbox["']|accent-color/)
})

test('AppleCheckbox matches iOS checkbox geometry and animated check stroke', () => {
  assert.notEqual(css, '', 'formControls.css should exist')
  const root = cssBlock('.apple-checkbox')
  const box = cssBlock('.apple-checkbox__box')
  const checkedBox = cssBlock('.apple-checkbox--checked .apple-checkbox__box')
  const mark = cssBlock('.apple-checkbox__mark')
  const checkedMark = cssBlock('.apple-checkbox--checked .apple-checkbox__mark')
  const mixedLine = cssBlock('.apple-checkbox__mixed-line')
  const mixedLineOn = cssBlock('.apple-checkbox--indeterminate .apple-checkbox__mixed-line')
  const focus = cssBlock('.apple-checkbox:focus-visible .apple-checkbox__box')

  assert.match(root, /min-width:\s*var\(--apple-form-hit-target\)/)
  assert.match(root, /min-height:\s*var\(--apple-form-hit-target\)/)
  assert.match(root, /padding:\s*var\(--apple-checkbox-hit-padding\)/)
  assert.match(box, /width:\s*18px/)
  assert.match(box, /height:\s*18px/)
  assert.match(box, /border-radius:\s*5px/)
  assert.match(box, /background:\s*var\(--b2-local-track-bg\)/)
  // Global motion guard restricts transitions to transform/opacity; checkbox
  // color/border/box-shadow snap on state change rather than animate.
  assert.doesNotMatch(box, /transition:[^;]*\b(?:background|border-color|box-shadow)\b/)
  assert.match(checkedBox, /background:\s*var\(--b2-local-track-bg-on\)/)
  assert.match(mark, /stroke-dasharray:\s*18/)
  assert.match(mark, /stroke-dashoffset:\s*18/)
  assert.doesNotMatch(mark, /transition:[^;]*\bstroke-dashoffset\b/)
  assert.match(checkedMark, /stroke-dashoffset:\s*0/)
  assert.match(mixedLine, /stroke-dasharray:\s*12/)
  assert.match(mixedLine, /stroke-dashoffset:\s*12/)
  assert.match(mixedLineOn, /stroke-dashoffset:\s*0/)
  assert.match(focus, /box-shadow:\s*var\(--apple-form-track-shadow-on\),\s*var\(--focus-ring\)/)
})

test('AppleCheckbox form controls avoid raw colors and use Phase A token fallbacks', () => {
  assert.deepEqual(css.match(rawColorPattern) || [], [])
  assert.match(css, /--apple-form-motion-spring:\s*var\(--motion-spring,\s*280ms cubic-bezier\(0\.34,\s*1\.56,\s*0\.64,\s*1\)\)/)
  assert.match(css, /--apple-form-hit-target:\s*var\(--space-10,\s*44px\)/)
  assert.match(css, /font-size:\s*var\(--type-callout,\s*14px\)/)
  assert.match(css, /line-height:\s*var\(--space-4,\s*16px\)/)
})
