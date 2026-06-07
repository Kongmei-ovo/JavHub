import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./ToastCapsule.vue', import.meta.url), 'utf8')
const rawColorPattern = /#[0-9a-fA-F]{3,8}\b|(?:rgb|hsl)a?\s*\(/g

function sourceBlock(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = source.match(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`))
  assert.ok(match, `${selector} should exist`)
  return match[1]
}

function assertLayeredToastBackground(block, materialToken) {
  assert.match(block, new RegExp(`background:\\s*var\\(--b4-local-specular-edge(?:-strong)?\\),\\s*var\\(--b4-local-surface-noise\\),\\s*var\\(${materialToken}\\)`))
}

test('toast capsule uses shared Apple glass sheet and controls', () => {
  const capsuleBlock = sourceBlock('.toast-capsule')
  const actionBlock = sourceBlock('.toast-action')
  const actionHoverBlock = sourceBlock('.toast-action:hover')
  const actionFocusBlock = sourceBlock('.toast-action:focus-visible')
  const actionActiveBlock = sourceBlock('.toast-action:active')
  const closeBlock = sourceBlock('.toast-close')
  const closeHoverBlock = sourceBlock('.toast-close:hover')
  const closeFocusBlock = sourceBlock('.toast-close:focus-visible')
  const closeActiveBlock = sourceBlock('.toast-close:active')
  const enterBlock = sourceBlock('.toast-slide-enter-active')
  const leaveBlock = sourceBlock('.toast-slide-leave-active')

  assert.match(source, /--b4-local-sheet-bg:\s*var\(--material-glass-sheet,\s*var\(--glass-sheet-material,\s*none\)\)/)
  assert.match(source, /--b4-local-control-bg:\s*var\(--material-glass-control,\s*var\(--glass-control-material,\s*none\)\)/)
  assert.match(source, /--b4-local-action-bg:\s*var\(--glass-active-material,\s*var\(--material-glass-control,\s*none\)\)/)
  assert.match(source, /--toast-sheet-bg:\s*var\(--b4-local-sheet-bg\)/)
  assert.match(source, /--toast-control-bg:\s*var\(--b4-local-control-bg\)/)
  assert.match(source, /--toast-action-bg:\s*var\(--b4-local-action-bg\)/)

  assertLayeredToastBackground(capsuleBlock, '--toast-sheet-bg')
  assert.match(capsuleBlock, /border:\s*1px solid var\(--toast-sheet-border\)/)
  assert.match(capsuleBlock, /box-shadow:\s*var\(--b4-local-sheet-shadow\)/)
  assert.match(capsuleBlock, /backdrop-filter:\s*blur\(var\(--b4-local-blur-sheet\)\)\s*saturate\(var\(--b4-local-saturate-surface\)\)/)

  assertLayeredToastBackground(actionBlock, '--toast-action-bg')
  assert.match(actionBlock, /border:\s*1px solid var\(--toast-action-border\)/)
  assert.match(actionBlock, /box-shadow:\s*var\(--toast-action-shadow\)/)
  assert.match(actionBlock, /backdrop-filter:\s*blur\(var\(--b4-local-blur-control\)\)\s*saturate\(var\(--b4-local-saturate-control\)\)/)
  assert.doesNotMatch(actionBlock, /background:\s*var\(--accent\)|border:\s*none|transition:\s*var\(--transition-pro\)/)

  assertLayeredToastBackground(actionHoverBlock, '--toast-action-bg-hover')
  assert.match(actionHoverBlock, /border-color:\s*var\(--toast-action-border-hover\)/)
  assert.match(actionHoverBlock, /box-shadow:\s*var\(--toast-control-shadow-hover\)/)
  assert.match(actionFocusBlock, /outline:\s*none/)
  assert.match(actionFocusBlock, /box-shadow:\s*var\(--toast-control-shadow-hover\),\s*var\(--b4-local-focus-ring\)/)
  assert.match(actionActiveBlock, /transform:\s*translateY\(0\)\s*scale\(0\.97\)/)

  assertLayeredToastBackground(closeBlock, '--toast-control-bg')
  assert.match(closeBlock, /border:\s*1px solid var\(--toast-control-border\)/)
  assert.match(closeBlock, /box-shadow:\s*var\(--toast-control-shadow\)/)
  assert.match(closeBlock, /backdrop-filter:\s*blur\(var\(--b4-local-blur-control\)\)\s*saturate\(var\(--b4-local-saturate-control\)\)/)
  assert.doesNotMatch(closeBlock, /background:\s*var\(--surface-control\)|transition:\s*var\(--transition-pro\)/)

  assertLayeredToastBackground(closeHoverBlock, '--toast-control-bg-hover')
  assert.match(closeHoverBlock, /border-color:\s*var\(--toast-control-border-hover\)/)
  assert.match(closeHoverBlock, /box-shadow:\s*var\(--toast-control-shadow-hover\)/)
  assert.doesNotMatch(closeHoverBlock, /background:\s*var\(--surface-control-hover\)/)
  assert.match(closeFocusBlock, /outline:\s*none/)
  assert.match(closeFocusBlock, /box-shadow:\s*var\(--toast-control-shadow-hover\),\s*var\(--b4-local-focus-ring\)/)
  assert.match(closeActiveBlock, /transform:\s*translateY\(0\)\s*scale\(0\.97\)/)

  for (const block of [enterBlock, leaveBlock]) {
    assert.doesNotMatch(block, /transition:\s*all\b|var\(--transition-pro\)/)
    // Use shared motion tokens directly (the global motion-token guard
    // forbids local indirections like --b4-local-*-motion).
    assert.match(block, /transition:\s*opacity var\(--motion-spring,\s*\d+ms[\s\S]*?\),\s*transform var\(--motion-spring-emphasized,\s*\d+ms/)
  }
})

test('toast capsule morphs from the top notch with spring motion and rubber-band width', () => {
  const rootBlock = sourceBlock('.toast-capsule')
  const enterActiveBlock = sourceBlock('.toast-slide-enter-active')
  const leaveActiveBlock = sourceBlock('.toast-slide-leave-active')
  const enterFromBlock = sourceBlock('.toast-slide-enter-from')
  const enterToBlock = sourceBlock('.toast-slide-enter-to')
  const leaveToBlock = sourceBlock('.toast-slide-leave-to')

  // Motion tokens are referenced directly with inline fallbacks (the
  // b4-local indirections were dropped to satisfy the global
  // motion-token guard; spring values still come from main.css).
  assert.match(source, /var\(--motion-spring-emphasized,\s*420ms cubic-bezier\(0\.5,\s*1\.7,\s*0\.6,\s*1\)\)/)
  assert.match(source, /var\(--motion-spring,\s*280ms cubic-bezier\(0\.34,\s*1\.56,\s*0\.64,\s*1\)\)/)
  assert.match(rootBlock, /top:\s*max\(env\(safe-area-inset-top,\s*0px\),\s*0px\)/)
  assert.match(rootBlock, /bottom:\s*auto/)
  assert.match(rootBlock, /width:\s*min\(calc\(100vw - var\(--space-6,\s*24px\)\),\s*480px\)/)
  assert.match(rootBlock, /max-width:\s*480px/)
  assert.match(rootBlock, /transform:\s*translate3d\(-50%,\s*var\(--toast-stack-y,\s*8px\),\s*0\)\s*scale\(var\(--toast-stack-scale,\s*1\)\)/)
  assert.match(rootBlock, /opacity:\s*var\(--toast-stack-opacity,\s*1\)/)
  assert.match(rootBlock, /z-index:\s*calc\(var\(--z-toast,\s*1000\) \+ var\(--toast-stack-z,\s*0\)\)/)

  // Use shared motion tokens (motion-spring-emphasized + motion-fast)
  // instead of B4-local indirections — the global motion-token guard
  // requires direct references.
  assert.match(enterActiveBlock, /transition:\s*opacity var\(--motion-spring,\s*\d+ms[\s\S]*?\),\s*transform var\(--motion-spring-emphasized/)
  assert.match(leaveActiveBlock, /transition:\s*opacity var\(--motion-spring,\s*\d+ms[\s\S]*?\),\s*transform var\(--motion-spring-emphasized/)
  assert.match(enterFromBlock, /opacity:\s*0/)
  // Entry/exit scale clamps to 0.96 (lightest entry transform permitted by
  // the entry-and-exit-transforms-stay-light guard). Visual still morphs
  // from above with translateY(-100%).
  assert.match(enterFromBlock, /transform:\s*translate3d\(-50%,\s*-100%,\s*0\)\s*scale\(0\.96\)/)
  assert.match(enterToBlock, /transform:\s*translate3d\(-50%,\s*8px,\s*0\)\s*scale\(1\)/)
  assert.match(leaveToBlock, /opacity:\s*0/)
  assert.match(leaveToBlock, /transform:\s*translate3d\(-50%,\s*-100%,\s*0\)\s*scale\(0\.96\)/)
})

test('toast capsule keeps a local five item Dynamic Island visual stack without changing the message bus', () => {
  assert.match(source, /const MAX_TOAST_STACK = 5/)
  assert.match(source, /const STACK_STEP = 12/)
  assert.match(source, /const STACK_SCALE_STEP = 0\.08/)
  assert.match(source, /const STACK_OPACITY_STEP = 0\.3/)
  assert.match(source, /const stackItems = ref\(\[\]\)/)
  assert.match(source, /watch\(\s*\(\) => \[props\.visible,\s*props\.message,\s*props\.showOrganize\]/)
  assert.match(source, /\.slice\(0,\s*MAX_TOAST_STACK\)/)
  assert.match(source, /'--toast-stack-y':\s*`\$\{8 \+ item\.index \* STACK_STEP\}px`/)
  assert.match(source, /'--toast-stack-scale':\s*String\(Math\.max\(0\.76,\s*1 - item\.index \* STACK_SCALE_STEP\)\)/)
  assert.match(source, /'--toast-stack-opacity':\s*String\(Math\.max\(0\.4,\s*1 - item\.index \* STACK_OPACITY_STEP\)\)/)
  assert.match(source, /'--toast-stack-z':\s*String\(MAX_TOAST_STACK - item\.index\)/)
  assert.match(source, /:class="\['toast-capsule', \{ 'toast-capsule--stacked': item\.index > 0 \}\]"/)
  assert.match(source, /:aria-hidden="item\.index > 0 \? 'true' : undefined"/)
  assert.match(source, /v-if="item\.index === 0 && showOrganize"/)
  assert.match(source, /v-if="item\.index === 0"/)
})

test('toast capsule listens to the existing message bus so repeated identical messages can stack', () => {
  assert.match(source, /import \{ MESSAGE_EVENT \} from '\.\.\/utils\/message\.js'/)
  assert.match(source, /import \{ computed, onMounted, onUnmounted, ref, watch \} from 'vue'/)
  assert.match(source, /let pendingMessageBusEcho = null/)
  assert.match(source, /function normalizeToastMessage\(input\)/)
  assert.match(source, /function handleMessageEvent\(event\)/)
  assert.match(source, /const message = normalizeToastMessage\(event\?\.detail\?\.message\)/)
  assert.match(source, /pendingMessageBusEcho = \{ message, showOrganize: false, time: Date\.now\(\) \}/)
  assert.match(source, /pushToast\(message, false\)/)
  assert.match(source, /function shouldSkipMessageBusEcho\(message, showOrganize\)/)
  assert.match(source, /shouldSkipMessageBusEcho\(message, showOrganize\)/)
  assert.match(source, /window\.addEventListener\(MESSAGE_EVENT, handleMessageEvent\)/)
  assert.match(source, /window\.removeEventListener\(MESSAGE_EVENT, handleMessageEvent\)/)
})

test('toast capsule follows raw color, Phase A fallback, and transition guards', () => {
  assert.deepEqual(source.match(rawColorPattern) || [], [])
  assert.doesNotMatch(source, /var\(--(?:motion|space|radius|shadow|z|text)-[\w-]+\)(?!\s*,)/)

  for (const transition of source.matchAll(/transition:\s*([^;]+);/g)) {
    assert.doesNotMatch(transition[1], /\b(?:color|background|border-color|box-shadow|stroke-dashoffset|filter)\b/)
    assert.match(transition[1], /\b(?:transform|opacity)\b/)
  }
})
