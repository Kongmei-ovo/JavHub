import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./Genres.vue', import.meta.url), 'utf8')

test('genres page only loads data needed for the initial tab', () => {
  assert.match(source, /const initialLoads = \[\s*this\.loadCategories\(\),\s*\]/)
  assert.doesNotMatch(source, /const initialLoads = \[[\s\S]*this\.loadActresses\(\),[\s\S]*\]/)
})

test('genres page loads actresses lazily when the actress tab is opened', () => {
  assert.match(source, /if \(tab === 'actress' && !this\.actressRawPage\.length && !this\.actressesLoading\) \{[\s\S]*this\.loadActresses\(this\.actressPage\)/)
  assert.match(source, /'cfg\.actressAvatarSize'\(\) \{[\s\S]*if \(this\.activeTab === 'actress'\) this\.loadActresses\(1\)/)
  assert.match(source, /'cfg\.actressPageSize'\(\) \{[\s\S]*if \(this\.activeTab === 'actress'\) this\.loadActresses\(1\)/)
})
