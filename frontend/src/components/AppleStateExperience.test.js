import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const emptySource = readFileSync(new URL('./AppleEmptyState.vue', import.meta.url), 'utf8')
const errorSource = readFileSync(new URL('./AppleErrorState.vue', import.meta.url), 'utf8')
const skeletonSource = readFileSync(new URL('./AppleSkeleton.vue', import.meta.url), 'utf8')

function cssBlock(source, selector) {
  const style = source.match(/<style scoped>([\s\S]*)<\/style>/)?.[1] || source
  const blocks = [...style.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
    .filter(([, selectors]) => selectors
      .split(',')
      .map(part => part.trim())
      .includes(selector))
    .map(([, , block]) => block)
  assert.ok(blocks.length, `${selector} should exist`)
  return blocks.join('\n')
}

test('AppleEmptyState exposes an explicit next step and primary plus secondary actions', () => {
  assert.match(emptySource, /nextStep:\s*\{\s*type:\s*String,\s*default:\s*''\s*\}/)
  assert.match(emptySource, /secondaryActionLabel:\s*\{\s*type:\s*String,\s*default:\s*''\s*\}/)
  assert.match(emptySource, /defineEmits\(\['action',\s*'secondary-action'\]\)/)
  assert.match(emptySource, /<p v-if="nextStep" class="empty-next-step">\{\{ nextStep \}\}<\/p>/)
  assert.match(emptySource, /<div v-if="hasActions" class="apple-state-actions">/)
  assert.match(emptySource, /class="empty-action empty-action--secondary"/)
  assert.match(emptySource, /@click="\$emit\('secondary-action'\)"/)

  const actions = cssBlock(emptySource, '.apple-state-actions')
  const secondary = cssBlock(emptySource, '.empty-action--secondary')
  assert.match(actions, /display:\s*flex/)
  assert.match(actions, /justify-content:\s*center/)
  assert.match(secondary, /--apple-state-action-bg:\s*var\(--material-glass-control\)/)
  assert.match(secondary, /--apple-state-action-border:\s*var\(--glass-control-border\)/)
})

test('AppleErrorState separates what happened from the next recovery action', () => {
  assert.match(errorSource, /nextStep:\s*\{\s*type:\s*String,\s*default:\s*'请重试，或检查相关服务后再刷新。'\s*\}/)
  assert.match(errorSource, /secondaryActionLabel:\s*\{\s*type:\s*String,\s*default:\s*''\s*\}/)
  assert.match(errorSource, /defineEmits\(\['retry',\s*'secondary-action'\]\)/)
  assert.match(errorSource, /<p v-if="nextStep" class="error-next-step">\{\{ nextStep \}\}<\/p>/)
  assert.match(errorSource, /<div v-if="hasActions" class="apple-state-actions">/)
  assert.match(errorSource, /class="error-action error-action--secondary"/)
  assert.match(errorSource, /@click="\$emit\('secondary-action'\)"/)

  const root = cssBlock(errorSource, '.apple-error-state')
  const actions = cssBlock(errorSource, '.apple-state-actions')
  const secondary = cssBlock(errorSource, '.error-action--secondary')
  assert.match(root, /align-items:\s*flex-start/)
  assert.match(actions, /display:\s*flex/)
  assert.match(actions, /flex-wrap:\s*wrap/)
  assert.match(secondary, /--apple-state-action-bg:\s*var\(--material-glass-control\)/)
  assert.match(secondary, /--apple-state-action-border:\s*var\(--glass-control-border\)/)
})

test('AppleSkeleton can describe the loading content for assistive technology', () => {
  assert.match(skeletonSource, /label:\s*\{\s*type:\s*String,\s*default:\s*'内容加载中'\s*\}/)
  assert.match(skeletonSource, /:aria-label="label"/)
  assert.match(skeletonSource, /aria-busy="true"/)
  assert.doesNotMatch(skeletonSource, /aria-hidden="true"/)
})
