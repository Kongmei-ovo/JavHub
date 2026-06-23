import test from 'node:test'
import assert from 'node:assert/strict'
import { readdirSync, readFileSync } from 'node:fs'

const pages = {
  Logs: readFileSync(new URL('../features/operations/LogStreamPanel.vue', import.meta.url), 'utf8'),
}

test('page loading states use AppleSkeleton instead of bare loading text or spinners', () => {
  for (const [name, source] of Object.entries(pages)) {
    assert.match(source, /AppleSkeleton/, `${name} should import and render AppleSkeleton for loading`)
    assert.doesNotMatch(source, /class="(?:loading|loading-panel|loading-wrap|empty-inline)">加载中(?:\.\.\.)?<\/div>/, `${name} should not render bare loading text`)
    assert.doesNotMatch(source, /<div class="spinner-large"><\/div>/, `${name} should not rely on an isolated spinner`)
  }
})

test('page empty states provide explicit next actions through AppleEmptyState', () => {
  for (const [name, source] of Object.entries(pages)) {
    assert.match(source, /AppleEmptyState/, `${name} should import and render AppleEmptyState`)
    assert.match(source, /<AppleEmptyState[\s\S]*?(action-label|secondary-action-label)=/, `${name} empty state should expose a next action`)
    assert.doesNotMatch(source, /class="(?:empty|empty-panel|empty-inline|empty-state)"[^>]*>暂无[^<]*<\/div>/, `${name} should not leave a one-line empty placeholder`)
  }
})

test('page error states use AppleErrorState with recovery actions', () => {
  for (const [name, source] of Object.entries(pages)) {
    assert.match(source, /AppleErrorState/, `${name} should import and render AppleErrorState`)
    assert.match(source, /<AppleErrorState[\s\S]*?(retry-label|secondary-action-label)=/, `${name} error state should expose recovery actions`)
    assert.doesNotMatch(source, /class="(?:error|empty-panel)"[^>]*>\s*(?:\{\{[^}]+error[^}]*\}\}|<h2>[^<]*加载失败<\/h2>)/, `${name} should not render bare error blocks`)
  }
})

test('all view-level blocking states avoid bare spinners and one-line dead ends', () => {
  const viewDir = new URL('./', import.meta.url)
  const ignored = new Set(['pageStates.test.js', 'StateExperience.test.js'])
  const sources = readdirSync(viewDir)
    .filter(file => file.endsWith('.vue') && !ignored.has(file))
    .map(file => [file, readFileSync(new URL(file, viewDir), 'utf8')])

  for (const [file, source] of sources) {
    assert.doesNotMatch(source, /<div class="spinner-large"><\/div>/, `${file} should use AppleSkeleton for blocking loading states`)
    assert.doesNotMatch(source, /class="loading-wrap"[\s\S]{0,180}加载[^<]*<\/p>/, `${file} should not render a bare loading panel`)
    assert.doesNotMatch(source, /<div v-else[^>]*class="empty-state"[\s\S]*?<\/div>/, `${file} blocking empty state should use AppleEmptyState`)
    assert.doesNotMatch(source, /class="empty-panel"[^>]*>暂无[^<]*<\/div>/, `${file} should not leave a one-line empty panel`)
  }
})
