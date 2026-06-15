# Downloads v2 Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the legacy `/downloads -> Home.vue` route with a focused v2 `Downloads.vue` page that only owns real download tasks and downloader configuration.

**Architecture:** Move the existing download and downloader Options API logic into a named Downloads view, remove all candidate-summary state, and keep route-query synchronization local to the page. Reuse focused child components, restyle the task list as solid v2 rows, and enforce the ownership boundary with source-contract tests.

**Tech Stack:** Vue 3 Options API, Vue Router, Vite, Node test runner, native CSS design tokens.

---

### Task 1: Add the migration contract tests

**Files:**
- Create: `frontend/src/views/Downloads.test.js`
- Modify: `frontend/src/App.test.js`

- [ ] **Step 1: Write failing route and ownership tests**

Add tests that read `Downloads.vue`, `router/index.js`, and `Home.vue` if present:

```js
test('downloads route owns a dedicated v2 view', () => {
  assert.match(routerSource, /path:\s*'\/downloads'[\s\S]*views\/Downloads\.vue/)
  assert.doesNotMatch(routerSource, /views\/Home\.vue/)
  assert.match(downloadsSource, /name:\s*'Downloads'/)
})

test('downloads page has no candidate workspace dependency', () => {
  assert.doesNotMatch(downloadsSource, /candidateStats|getDownloadCandidateSummary|CandidateOverview|openCandidatePreset/)
  assert.doesNotMatch(downloadsSource, /待确认候选|待补磁力|可批准/)
})

test('legacy candidate deep links remain compatible', () => {
  assert.match(downloadsSource, /query\.tab === 'candidates'/)
  assert.match(downloadsSource, /path:\s*'\/candidates'/)
  assert.match(downloadsSource, /delete next\.tab/)
})
```

Update `App.test.js` so the root-route test expects `Downloads.vue` and explicitly rejects `Home.vue`.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
cd frontend
node --test src/views/Downloads.test.js src/App.test.js
```

Expected: FAIL because `Downloads.vue` does not exist and the route still imports `Home.vue`.

- [ ] **Step 3: Commit the red tests**

```bash
git add frontend/src/views/Downloads.test.js frontend/src/App.test.js
git commit -m "test: define downloads v2 migration contract"
```

### Task 2: Create the dedicated Downloads page

**Files:**
- Create: `frontend/src/views/Downloads.vue`
- Create: `frontend/src/features/downloads/downloads.css`
- Modify: `frontend/src/router/index.js`
- Delete: `frontend/src/views/Home.vue`

- [ ] **Step 1: Copy only real download responsibilities into Downloads**

Create `Downloads.vue` with:

```vue
<template>
  <div class="downloads-page page-shell page-shell--workspace">
    <header class="page-header">
      <div class="header-left">
        <h1>下载任务</h1>
        <p class="header-subtitle">{{ totalTaskCount }} 个任务<span v-if="stats.downloading"> · {{ stats.downloading }} 个下载中</span></p>
      </div>
      <div class="header-actions">
        <button class="btn btn-ghost" type="button" @click="$router.push('/search')">浏览影库</button>
        <button class="btn btn-ghost" type="button" @click="$router.push('/parse')">磁链解析</button>
        <button class="btn btn-primary" type="button" @click="loadTasks">刷新</button>
      </div>
    </header>
    <DownloadStatsBar :stats="stats" :stats-loaded="statsLoaded" @select-status="setTaskStatus" />
    <div v-if="filterStatus" class="filter-bar" @click="clearTaskStatus">
      <span class="filter-hint">筛选: <strong>{{ statusLabel(filterStatus) }}</strong>（点击清除）</span>
    </div>
    <div class="download-tabs">
      <button class="tab-btn" type="button" :class="{ active: activeTab === 'tasks' }" @click="openTaskTab">下载任务</button>
      <button class="tab-btn" type="button" :class="{ active: activeTab === 'downloaders' }" @click="openDownloaderTab">下载源</button>
    </div>
    <DownloaderManagementPanel v-if="activeTab === 'downloaders'" />
    <TaskList
      v-else
      :tasks="filteredTasks"
      :retrying-tasks="retryingTasks"
      :status-badge="statusBadge"
      :status-label="statusLabel"
      :format-time="formatTime"
      :downloader-type-label="downloaderTypeLabel"
      :task-empty-title="taskEmptyTitle"
      :task-empty-hint="taskEmptyHint"
      :task-empty-primary-label="taskEmptyPrimaryLabel"
      @retry="retry"
      @remove="remove"
      @empty-action="handleTaskEmptyAction"
      @parse="$router.push('/parse')"
    />
  </div>
</template>
```

Move the existing task and downloader state/methods from `Home.vue`, but remove:

- `candidateStats`
- `loadCandidateSummary`
- `openCandidatePreset`
- candidate-aware empty-state branches
- any call to `getDownloadCandidateSummary`

Use these empty-state values:

```js
taskEmptyHint() {
  if (this.filterStatus) return '当前筛选没有任务，可以清除筛选查看全部。'
  return '可以从影库或磁链解析添加下载任务。'
},
taskEmptyPrimaryLabel() {
  return this.filterStatus ? '清除筛选' : '浏览影库'
},
handleTaskEmptyAction() {
  if (this.filterStatus) this.clearTaskStatus()
  else this.$router.push('/search')
},
```

Keep the existing candidate deep-link redirect:

```js
candidateRedirectQuery(query = {}) {
  const next = { ...query }
  delete next.tab
  return cleanObject(next)
}
```

- [ ] **Step 2: Move page styles to the downloads feature**

Create `features/downloads/downloads.css` from the download-owned selectors in `features/home/home.css`. Use solid content rows:

```css
.tasks-grid {
  display: flex;
  flex-direction: column;
  gap: var(--space-2, 8px);
}

.task-card {
  display: grid;
  grid-template-columns: 56px minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-4, 16px);
  padding: var(--space-3, 12px) var(--space-4, 16px);
  background: var(--card);
  border: 1px solid var(--hairline);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
}
```

Do not add progress, speed, pause, or resume presentation.

- [ ] **Step 3: Switch the route and retire Home**

Change:

```js
{ path: '/downloads', name: 'Downloads', component: () => import('../views/Downloads.vue') },
```

Delete `Home.vue` after its real download logic exists in `Downloads.vue`.

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run:

```bash
cd frontend
node --test src/views/Downloads.test.js src/App.test.js
```

Expected: PASS.

- [ ] **Step 5: Commit the page migration**

```bash
git add frontend/src/views/Downloads.vue frontend/src/features/downloads/downloads.css frontend/src/router/index.js frontend/src/views/Home.vue frontend/src/views/Downloads.test.js frontend/src/App.test.js
git commit -m "feat: migrate downloads to dedicated v2 page"
```

### Task 3: Remove candidate coupling from shared download components

**Files:**
- Modify: `frontend/src/features/home/DownloadStatsBar.vue`
- Modify: `frontend/src/features/home/DownloadStatsBar.test.js`
- Modify: `frontend/src/features/home/TaskList.vue`
- Modify: `frontend/src/features/home/TaskList.test.js`

- [ ] **Step 1: Write failing component contract tests**

Change the stats test to require only task status ownership:

```js
assert.doesNotMatch(source, /CandidateOverview|candidateStats|open-preset/)
assert.match(source, /props:\s*\{[\s\S]*stats:[\s\S]*statsLoaded:/)
assert.match(source, /emits:\s*\[[^\]]*'select-status'[^\]]*\]/)
```

Change the task-list test to require a real status column and downloads stylesheet:

```js
assert.match(source, /class="task-status"/)
assert.match(source, /<style scoped src="\.\.\/downloads\/downloads\.css"><\/style>/)
assert.doesNotMatch(source, /progress-bar-fill-demo|处理下载候选/)
```

- [ ] **Step 2: Run component tests and verify RED**

Run:

```bash
cd frontend
node --test src/features/home/DownloadStatsBar.test.js src/features/home/TaskList.test.js
```

Expected: FAIL because candidate props/components and demo progress remain.

- [ ] **Step 3: Implement minimal shared-component changes**

In `DownloadStatsBar.vue`:

- remove `CandidateOverview` import and render
- remove `candidateStats` prop
- remove `open-preset` emit
- retain four clickable status cards
- point its scoped stylesheet to `../downloads/downloads.css`

In `TaskList.vue`:

- replace poster-card layout with the compact task row
- render status with `statusBadge()` and `statusLabel()`
- retain retry and remove emits
- remove demo progress markup
- change empty-state next step to `可以清除筛选，或从影库和磁链解析添加新任务。`
- point its scoped stylesheet to `../downloads/downloads.css`

- [ ] **Step 4: Run component tests and verify GREEN**

Run:

```bash
cd frontend
node --test src/features/home/DownloadStatsBar.test.js src/features/home/TaskList.test.js
```

Expected: PASS.

- [ ] **Step 5: Commit component cleanup**

```bash
git add frontend/src/features/home/DownloadStatsBar.vue frontend/src/features/home/DownloadStatsBar.test.js frontend/src/features/home/TaskList.vue frontend/src/features/home/TaskList.test.js frontend/src/features/downloads/downloads.css
git commit -m "refactor: isolate download task presentation"
```

### Task 4: Update global UI and workflow guards

**Files:**
- Modify: `frontend/src/assets/liquidGlass.test.js`
- Modify: `frontend/src/assets/typography.test.js`
- Modify: `frontend/src/assets/visualContract.test.js`
- Modify: `frontend/src/views/WorkflowIntegration.test.js`
- Delete: `frontend/src/views/Home.test.js`

- [ ] **Step 1: Replace old file references**

Replace all `Home.vue` reads and labels with `Downloads.vue`. Remove the large-file exception for `src/views/Home.vue`; the new view must remain below the default 900-line limit.

In `WorkflowIntegration.test.js`, split the combined source:

```js
const downloadsVue = readFileSync(new URL('./Downloads.vue', import.meta.url), 'utf8')
const candidatesSource = [
  readFileSync(new URL('./Candidates.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/candidates/useDownloadCandidates.js', import.meta.url), 'utf8'),
].join('\n')
```

Assert task retry behavior against `downloadsVue`, and candidate mutation behavior against `candidatesSource`. Delete the obsolete test requiring the downloads page to fetch a candidate summary.

- [ ] **Step 2: Run affected guard tests**

Run:

```bash
cd frontend
node --test \
  src/assets/liquidGlass.test.js \
  src/assets/typography.test.js \
  src/assets/visualContract.test.js \
  src/views/WorkflowIntegration.test.js
```

Expected: PASS with no references to `Home.vue`.

- [ ] **Step 3: Search for stale ownership references**

Run:

```bash
rg -n "views/Home\\.vue|Home\\.vue|candidateStats|getDownloadCandidateSummary" frontend/src/views/Downloads.vue frontend/src/router frontend/src/App.test.js frontend/src/assets frontend/src/views/WorkflowIntegration.test.js
```

Expected: no `Home.vue` references and no candidate-summary references inside `Downloads.vue`.

- [ ] **Step 4: Commit guard updates**

```bash
git add frontend/src/assets frontend/src/views/WorkflowIntegration.test.js frontend/src/views/Home.test.js
git commit -m "test: guard downloads v2 ownership"
```

### Task 5: Full verification and browser QA

**Files:**
- Modify only if verification exposes a scoped regression.

- [ ] **Step 1: Run full frontend verification**

Run:

```bash
cd frontend
npm test
npm run build
```

Expected: all tests pass and Vite exits with code 0.

- [ ] **Step 2: Verify services**

Run:

```bash
scripts/services.sh ensure
scripts/services.sh status
```

Expected: frontend `5174`, backend `18090`, and JavInfo `8080` healthy.

- [ ] **Step 3: Browser-check desktop**

Open `http://127.0.0.1:5174/downloads` and verify:

- only real download counters appear
- no candidate summary or candidate action appears
- status filtering changes the `task_status` query
- downloader tab opens
- empty state links to the library and magnet parser

- [ ] **Step 4: Browser-check compatibility and mobile**

Verify:

- `/downloads?tab=candidates&source=inventory` resolves to `/candidates?source=inventory`
- `/downloads?tab=downloaders` opens downloader management
- at a mobile viewport, task rows stack without horizontal overflow
- `/candidates` still renders its candidate workspace

- [ ] **Step 5: Review final diff**

Run:

```bash
git diff --check
git status --short
git diff -- frontend/src/views/Downloads.vue frontend/src/features/downloads/downloads.css frontend/src/features/home/TaskList.vue frontend/src/features/home/DownloadStatsBar.vue frontend/src/router/index.js
```

Expected: no whitespace errors; diff contains only the scoped downloads migration plus pre-existing concurrent changes.
