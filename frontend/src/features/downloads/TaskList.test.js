import test from 'node:test'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'

const componentUrl = new URL('./TaskList.vue', import.meta.url)
const source = existsSync(componentUrl) ? readFileSync(componentUrl, 'utf8') : ''

test('task list owns compact task rows, retry/delete events, and empty state actions', () => {
  assert.ok(existsSync(componentUrl), 'TaskList.vue should exist')
  assert.match(source, /name:\s*'TaskList'/)
  assert.match(source, /import AppleEmptyState from '\.\.\/\.\.\/components\/AppleEmptyState\.vue'/)
  assert.match(source, /props:\s*\{[\s\S]*tasks:[\s\S]*retryingTasks:[\s\S]*statusBadge:[\s\S]*statusLabel:[\s\S]*formatTime:/)
  assert.match(source, /emits:\s*\[[^\]]*'retry'[^\]]*'remove'[^\]]*'empty-action'[^\]]*'parse'[^\]]*\]/)
  assert.match(source, /v-for="task in tasks"/)
  assert.match(source, /class="task-status"/)
  assert.match(source, /\$emit\('retry', task\)/)
  assert.match(source, /\$emit\('remove', task\.id\)/)
  assert.match(source, /<AppleEmptyState[\s\S]*@action="\$emit\('empty-action'\)"[\s\S]*@secondary-action="\$emit\('parse'\)"/)
  assert.match(source, /<style scoped src="\.\/downloads\.css"><\/style>/)
  assert.match(source, /默认下载器/)
  assert.doesNotMatch(source, /默认下载源/)
  assert.doesNotMatch(source, /progress-bar-fill-demo|处理下载候选/)
})
