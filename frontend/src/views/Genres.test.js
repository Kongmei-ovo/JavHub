import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./Genres.vue', import.meta.url), 'utf8')

test('genres page only loads data needed for the initial tab', () => {
  assert.match(source, /const initialLoads = \[\]/)
  assert.match(source, /if \(this\.activeTab === 'genre'\) initialLoads\.push\(this\.loadCategories\(\)\)/)
  assert.doesNotMatch(source, /const initialLoads = \[[\s\S]*this\.loadActresses\(\),[\s\S]*\]/)
})

test('genres page loads categories lazily when the genre tab is opened', () => {
  assert.match(source, /if \(tab === 'genre' && !this\.categories\.length && !this\.loading\) \{[\s\S]*this\.loadCategories\(\)/)
})

test('genres page loads actresses lazily when the actress tab is opened', () => {
  assert.match(source, /if \(tab === 'actress' && !this\.actressRawPage\.length && !this\.actressesLoading\) \{[\s\S]*this\.loadActresses\(this\.actressPage\)/)
  assert.match(source, /'cfg\.actressAvatarSize'\(\) \{[\s\S]*if \(this\.activeTab === 'actress'\) this\.loadActresses\(1\)/)
  assert.match(source, /'cfg\.actressPageSize'\(\) \{[\s\S]*if \(this\.activeTab === 'actress'\) this\.loadActresses\(1\)/)
})

test('genres tab state is restored from and written to the route query', () => {
  assert.match(source, /tabFromRoute\(query = this\.\$route\.query\)/)
  assert.match(source, /this\.activeTab = this\.tabFromRoute\(\) \|\| \(this\.tabs\.some\(tab => tab\.key === this\.cfg\.defaultTab\) \? this\.cfg\.defaultTab : 'genre'\)/)
  assert.match(source, /'\$route\.query\.tab'\(\) \{[\s\S]*this\.applyRouteTab\(\)/)
  assert.match(source, /switchTab\(tab\) \{[\s\S]*this\.\$router\.push\(\{ path: this\.\$route\.path, query: \{ \.\.\.this\.\$route\.query, tab \} \}\)/)
})
