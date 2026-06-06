import test from 'node:test'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'

const componentUrl = new URL('./AppleTextField.vue', import.meta.url)
const styleUrl = new URL('../assets/textField.css', import.meta.url)
const componentSource = existsSync(componentUrl) ? readFileSync(componentUrl, 'utf8') : ''
const styleSource = existsSync(styleUrl) ? readFileSync(styleUrl, 'utf8') : ''

function cssBlock(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = styleSource.match(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`))
  assert.ok(match, `${selector} should exist in textField.css`)
  return match[1]
}

test('AppleTextField exposes the shared single-line input contract', () => {
  assert.ok(componentSource, 'AppleTextField.vue should exist')
  assert.match(componentSource, /import '..\/assets\/textField\.css'/)
  assert.match(componentSource, /modelValue:\s*\{\s*type:\s*\[String,\s*Number\]/)
  assert.match(componentSource, /placeholder:\s*\{\s*type:\s*String,\s*default:\s*''\s*\}/)
  assert.match(componentSource, /clearable:\s*\{\s*type:\s*Boolean,\s*default:\s*false\s*\}/)
  assert.match(componentSource, /prefixIcon:\s*\{\s*type:\s*String,\s*default:\s*''\s*\}/)
  assert.match(componentSource, /validator:\s*value\s*=>\s*\['regular',\s*'compact'\]\.includes\(value\)/)
  assert.match(componentSource, /validator:\s*value\s*=>\s*\['default',\s*'search'\]\.includes\(value\)/)
  assert.match(componentSource, /defineEmits\(\['update:modelValue',\s*'clear'\]\)/)
})

test('AppleTextField template includes icon, input, and accessible clear button', () => {
  assert.match(componentSource, /<label[\s\S]*class="apple-text-field"/)
  assert.match(componentSource, /`apple-text-field--\$\{size\}`/)
  assert.match(componentSource, /`apple-text-field--\$\{tone\}`/)
  assert.match(componentSource, /<span v-if="prefixIcon" class="apple-text-field__icon"/)
  assert.match(componentSource, /{{ prefixIcon }}/)
  assert.match(componentSource, /<input[\s\S]*class="apple-text-field__input"[\s\S]*:value="modelValue"[\s\S]*:placeholder="placeholder"[\s\S]*@input="handleInput"/)
  assert.match(componentSource, /<button[\s\S]*v-if="showClearButton"[\s\S]*class="apple-text-field__clear"[\s\S]*type="button"[\s\S]*aria-label="清除输入"[\s\S]*@click="clearInput"/)
  assert.match(componentSource, /const showClearButton = computed\(\(\) => props\.clearable && String\(props\.modelValue \?\? ''\)\.length > 0\)/)
  assert.match(componentSource, /emit\('update:modelValue', event\.target\.value\)/)
  assert.match(componentSource, /emit\('update:modelValue', ''\)/)
  assert.match(componentSource, /emit\('clear'\)/)
})

test('AppleTextField styles use Phase A glass tokens and springy focus motion', () => {
  assert.ok(styleSource, 'textField.css should exist')
  const rootBlock = cssBlock('.apple-text-field')
  const compactBlock = cssBlock('.apple-text-field--compact')
  const searchBlock = cssBlock('.apple-text-field--search')
  const focusWithinBlock = cssBlock('.apple-text-field:focus-within')
  const inputBlock = cssBlock('.apple-text-field__input')
  const placeholderBlock = cssBlock('.apple-text-field__input::placeholder')
  const clearBlock = cssBlock('.apple-text-field__clear')
  const clearHoverBlock = cssBlock('.apple-text-field__clear:hover')
  const clearFocusBlock = cssBlock('.apple-text-field__clear:focus-visible')
  const clearActiveBlock = cssBlock('.apple-text-field__clear:active')

  assert.doesNotMatch(styleSource, /#[0-9a-fA-F]{3,8}\b|(?:rgba?|hsla?)\(/, 'AppleTextField styles should not use raw colors')
  assert.match(rootBlock, /--apple-text-field-motion:\s*var\(--motion-spring,\s*280ms cubic-bezier\(0\.34,\s*1\.56,\s*0\.64,\s*1\)\)/)
  assert.match(rootBlock, /height:\s*var\(--space-10,\s*44px\)/)
  assert.match(rootBlock, /padding:\s*0 var\(--space-4,\s*16px\)/)
  assert.match(rootBlock, /border-radius:\s*999px/)
  assert.match(rootBlock, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--apple-text-field-bg\)/)
  assert.match(rootBlock, /--apple-text-field-bg:\s*var\(--material-glass-control\)/)
  assert.match(rootBlock, /--apple-text-field-bg-hover:\s*var\(--material-glass-control-hover\)/)
  assert.match(rootBlock, /--apple-text-field-bg-focus:\s*var\(--glass-active-material\)/)
  assert.match(rootBlock, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(rootBlock, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  // Global motion guard restricts transitions to transform/opacity; field
  // hover/focus color shifts are instant while the focus scale springs.
  assert.match(rootBlock, /transition:\s*transform/)
  assert.doesNotMatch(rootBlock, /transition:[^;]*\b(?:background|border-color|box-shadow)\b/)

  assert.match(compactBlock, /height:\s*var\(--space-7,\s*32px\)/)
  assert.match(searchBlock, /--apple-text-field-bg:\s*var\(--surface-input\)/)
  assert.match(focusWithinBlock, /transform:\s*scale\(1\.005\)/)
  assert.match(focusWithinBlock, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/)
  assert.match(focusWithinBlock, /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--apple-text-field-bg-focus\)/)

  assert.match(inputBlock, /color:\s*var\(--text-primary\)/)
  assert.match(inputBlock, /font-size:\s*var\(--type-callout,\s*14px\)/)
  assert.match(placeholderBlock, /color:\s*var\(--text-muted\)/)

  assert.match(clearBlock, /border-radius:\s*999px/)
  assert.match(clearBlock, /font-size:\s*var\(--type-caption-1,\s*12px\)/)
  assert.match(clearBlock, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-control\)/)
  assert.match(clearHoverBlock, /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--material-glass-control-hover\)/)
  assert.match(clearFocusBlock, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/)
  assert.match(clearActiveBlock, /transform:\s*scale\(0\.96\)/)
})
