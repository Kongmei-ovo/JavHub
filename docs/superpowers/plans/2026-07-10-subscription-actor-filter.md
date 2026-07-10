# Subscription Actor Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an immediate, multilingual filter for the current actor subscriptions while keeping totals global and bulk selection scoped to visible results.

**Architecture:** A focused pure helper builds and matches normalized search text from a subscription row plus hydrated actor metadata. `Subscription.vue` owns the keyword and derives visible subscriptions reactively; the existing feature stylesheet supplies a page-level search control matching the supplement workspace.

**Tech Stack:** Vue 3 Composition API, JavaScript ES modules, Node test runner, scoped CSS, Vite

## Global Constraints

- Filter only actors already present in the current subscription list.
- Match translated Chinese names, Japanese kanji, kana, romaji, subscription names, and actress IDs with case-insensitive substring matching.
- Do not add backend APIs, pinyin conversion, edit distance, or server pagination.
- Keep hero totals based on all subscriptions.
- In edit mode, “select all” and “all selected” operate on visible filtered subscriptions only.
- Keep existing selections when the keyword changes or is cleared.

---

## File Structure

- Create `frontend/src/features/subscription/subscriptionFilter.js`: pure keyword normalization and subscription matching.
- Create `frontend/src/features/subscription/subscriptionFilter.test.js`: behavioral unit tests for multilingual fields, IDs, partial matches, case folding, whitespace, and missing metadata.
- Modify `frontend/src/views/Subscription.vue`: filter state, computed visible list, search UI, no-match state, and visible-only select-all behavior.
- Modify `frontend/src/views/Subscription.test.js`: structural and styling contract tests for the new list filter.
- Modify `frontend/src/features/subscription/subscription.css`: search control, clear button, responsive sizing, and no-match spacing.

### Task 1: Pure subscription filter

**Files:**
- Create: `frontend/src/features/subscription/subscriptionFilter.js`
- Create: `frontend/src/features/subscription/subscriptionFilter.test.js`

**Interfaces:**
- Consumes: a subscription object, an optional actor metadata object, and a string keyword.
- Produces: `normalizeSubscriptionKeyword(value): string` and `subscriptionMatchesKeyword(subscription, actorMeta, keyword): boolean`.

- [ ] **Step 1: Write the failing behavioral tests**

```js
import test from 'node:test'
import assert from 'node:assert/strict'
import { normalizeSubscriptionKeyword, subscriptionMatchesKeyword } from './subscriptionFilter.js'

const subscription = { actress_id: 321, actress_name: '田中ねね' }
const metadata = {
  name_kanji_translated: '田中宁宁',
  name_romaji_translated: '田中寧寧',
  name_kanji: '田中ねね',
  name_kana: 'たなかねね',
  name_romaji: 'Tanaka Nene',
}

test('normalizes surrounding whitespace and latin case', () => {
  assert.equal(normalizeSubscriptionKeyword('  NENE  '), 'nene')
})

test('matches partial translated, Japanese, kana, romaji, subscription, and ID values', () => {
  for (const keyword of ['宁宁', '寧寧', '中ね', 'なかね', 'nAkA Ne', '田中', '21']) {
    assert.equal(subscriptionMatchesKeyword(subscription, metadata, keyword), true, keyword)
  }
})

test('treats blank keywords as unfiltered and tolerates missing metadata', () => {
  assert.equal(subscriptionMatchesKeyword(subscription, null, '   '), true)
  assert.equal(subscriptionMatchesKeyword(subscription, null, '田中'), true)
  assert.equal(subscriptionMatchesKeyword(subscription, null, '白石'), false)
})
```

- [ ] **Step 2: Run the unit test and verify RED**

Run: `cd frontend && node --test src/features/subscription/subscriptionFilter.test.js`

Expected: FAIL because `subscriptionFilter.js` does not exist.

- [ ] **Step 3: Implement the minimal pure helper**

```js
export function normalizeSubscriptionKeyword(value) {
  return String(value ?? '').trim().toLocaleLowerCase()
}

export function subscriptionMatchesKeyword(subscription, actorMeta, keyword) {
  const normalizedKeyword = normalizeSubscriptionKeyword(keyword)
  if (!normalizedKeyword) return true

  const meta = actorMeta || {}
  const searchable = [
    meta.name_kanji_translated,
    meta.name_romaji_translated,
    meta.name_kanji,
    meta.name_kana,
    meta.name_romaji,
    subscription?.actress_name,
    subscription?.actress_id,
  ]
    .filter(value => value !== null && value !== undefined && value !== '')
    .join(' ')
    .toLocaleLowerCase()

  return searchable.includes(normalizedKeyword)
}
```

- [ ] **Step 4: Run the unit test and verify GREEN**

Run: `cd frontend && node --test src/features/subscription/subscriptionFilter.test.js`

Expected: 3 tests pass, 0 fail.

### Task 2: Subscription list filter UI and edit-mode semantics

**Files:**
- Modify: `frontend/src/views/Subscription.vue`
- Modify: `frontend/src/views/Subscription.test.js`
- Modify: `frontend/src/features/subscription/subscription.css`
- Test: `frontend/src/features/subscription/subscriptionFilter.test.js`

**Interfaces:**
- Consumes: `subscriptionMatchesKeyword(subscription, actorMeta, keyword)` from Task 1.
- Produces: reactive `subscriptionFilterKeyword`, computed `filteredSubscriptions`, a “筛选订阅演员” control, and visible-only select-all behavior.

- [ ] **Step 1: Add failing source-contract tests**

Append assertions to `frontend/src/views/Subscription.test.js` that require:

```js
test('subscription list provides an immediate multilingual filter and a clearable no-match state', () => {
  assert.match(vueSource, /v-model="subscriptionFilterKeyword"/)
  assert.match(vueSource, /placeholder="筛选订阅演员"/)
  assert.match(vueSource, /aria-label="筛选订阅演员"/)
  assert.match(vueSource, /filteredSubscriptions/)
  assert.match(vueSource, /subscriptionMatchesKeyword/)
  assert.match(vueSource, /v-for="sub in filteredSubscriptions"/)
  assert.match(vueSource, /没有匹配演员/)
  assert.match(vueSource, /当前关键词没有匹配到订阅演员/)
  assert.match(vueSource, /@action="clearSubscriptionFilter"/)

  const search = cssBlock('.subscription-list-search')
  const clear = cssBlock('.subscription-list-search-clear')
  assert.match(search, /width:\s*100%/)
  assert.match(search, /background:\s*var\(--subscription-control-bg\)/)
  assert.match(search, /border:\s*1px solid var\(--subscription-control-border\)/)
  assert.match(search, /box-shadow:\s*var\(--subscription-control-shadow\)/)
  assert.match(clear, /border-radius:\s*999px/)
})

test('subscription edit select-all is scoped to visible filtered subscriptions', () => {
  assert.match(vueSource, /filteredSubscriptions\.value\.length > 0/)
  assert.match(vueSource, /filteredSubscriptions\.value\.every/)
  assert.match(vueSource, /for \(const sub of filteredSubscriptions\.value\)/)
  assert.match(vueSource, /new Set\(selectedSubscriptionIds\.value\)/)
})
```

- [ ] **Step 2: Run the subscription view test and verify RED**

Run: `cd frontend && node --test src/views/Subscription.test.js`

Expected: the two new tests fail because the list filter markup, state, and styles are absent.

- [ ] **Step 3: Add filter state and computed subscriptions**

Import `subscriptionMatchesKeyword`, add `const subscriptionFilterKeyword = ref('')`, and derive:

```js
const filteredSubscriptions = computed(() => subs.value.filter(sub => (
  subscriptionMatchesKeyword(sub, subMeta(sub), subscriptionFilterKeyword.value)
)))
```

Keep `totalNewMovies`, `totalNeedsMagnet`, and the hero count based on `subs`. Change `allSubscriptionsSelected` and `selectAllSubscriptions` to visible-only behavior:

```js
const allSubscriptionsSelected = computed(() => (
  filteredSubscriptions.value.length > 0
  && filteredSubscriptions.value.every(sub => selectedSubscriptionIds.value.has(subscriptionKey(sub)))
))

function selectAllSubscriptions() {
  const next = new Set(selectedSubscriptionIds.value)
  for (const sub of filteredSubscriptions.value) {
    const key = subscriptionKey(sub)
    if (key) next.add(key)
  }
  selectedSubscriptionIds.value = next
}

function clearSubscriptionFilter() {
  subscriptionFilterKeyword.value = ''
}
```

- [ ] **Step 4: Add the search and filtered states to the template**

Immediately inside `.subscription-content`, before the edit toolbar, render the search only after a non-empty list has loaded:

```vue
<label v-if="!loading && subs.length" class="subscription-list-search">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
    <circle cx="11" cy="11" r="7"></circle>
    <path d="M16.5 16.5 21 21"></path>
  </svg>
  <input v-model="subscriptionFilterKeyword" type="search" placeholder="筛选订阅演员" aria-label="筛选订阅演员" />
  <button v-if="subscriptionFilterKeyword" type="button" class="subscription-list-search-clear" aria-label="清除筛选" @click.prevent="clearSubscriptionFilter">×</button>
</label>
```

Change the card condition and loop to `filteredSubscriptions`. Insert a compact `AppleEmptyState` between the filtered grid and the existing no-subscription state:

```vue
<AppleEmptyState
  v-else-if="subs.length > 0"
  class="empty-state compact subscription-filter-empty"
  title="没有匹配演员"
  description="当前关键词没有匹配到订阅演员。"
  next-step="换一个名字，或清除筛选回到全部订阅演员。"
  action-label="清除筛选"
  density="compact"
  @action="clearSubscriptionFilter"
/>
```

- [ ] **Step 5: Style the list filter with subscription glass tokens**

Add the following focused styles:

```css
.subscription-list-search {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-width: 0;
  min-height: 38px;
  margin-bottom: 18px;
  padding: 0 12px;
  border: 1px solid var(--subscription-control-border);
  border-radius: 16px;
  background: var(--subscription-control-bg);
  box-shadow: var(--subscription-control-shadow), var(--glass-inner-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}

.subscription-list-search:focus-within {
  border-color: var(--glass-active-border);
  background: var(--subscription-active-bg);
  box-shadow: var(--glass-active-shadow);
}

.subscription-list-search svg {
  width: 16px;
  height: 16px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.subscription-list-search input {
  flex: 1;
  min-width: 0;
  min-height: 36px;
  padding: 0;
  color: var(--text-primary);
  background: transparent;
  border: 0;
  outline: none;
  font-size: var(--type-control);
}

.subscription-list-search input::-webkit-search-cancel-button { display: none; }

.subscription-list-search-clear {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 18px;
  height: 18px;
  padding: 0;
  border: 0;
  border-radius: 999px;
  background: var(--card-2);
  color: var(--text-muted);
  font-size: var(--type-card-title);
  line-height: 1;
  cursor: pointer;
}

.subscription-list-search-clear:hover { color: var(--text-primary); }
.subscription-filter-empty { margin: 20px auto; }
```

- [ ] **Step 6: Run focused tests and verify GREEN**

Run: `cd frontend && node --test src/features/subscription/subscriptionFilter.test.js src/views/Subscription.test.js`

Expected: all focused tests pass with 0 failures.

### Task 3: Full verification and browser acceptance

**Files:**
- Verify only; fix Task 1 or Task 2 files if a check reveals a defect.

**Interfaces:**
- Consumes: the completed filter helper and subscription UI.
- Produces: verified test, build, and browser evidence.

- [ ] **Step 1: Run the full frontend test suite**

Run: `cd frontend && npm test`

Expected: all tests pass, 0 fail.

- [ ] **Step 2: Build the production frontend**

Run: `cd frontend && npm run build`

Expected: Vite exits 0 and writes the production bundle.

- [ ] **Step 3: Confirm local services**

Run: `scripts/services.sh ensure && scripts/services.sh status`

Expected: javinfo, backend, and frontend health checks are all `ok`; frontend listens on port 5174.

- [ ] **Step 4: Verify in Chrome**

Open `http://localhost:5174/subscription` and verify:

- “筛选订阅演员” is full width above the cards.
- Partial Chinese, Japanese/kana, romaji, and ID inputs show only matching subscribed actors.
- Clearing restores all cards; a miss shows “没有匹配演员”.
- Hero totals remain unchanged while filtering.
- In edit mode, “全选” selects only visible results and retains prior intentional selections.
- Dark, light, and narrow viewport layouts have no overlap or horizontal overflow.

- [ ] **Step 5: Inspect the final diff**

Run: `git diff --check && git status --short && git diff -- frontend/src/features/subscription frontend/src/views/Subscription.vue frontend/src/views/Subscription.test.js`

Expected: no whitespace errors and only the planned implementation files are modified or created.
