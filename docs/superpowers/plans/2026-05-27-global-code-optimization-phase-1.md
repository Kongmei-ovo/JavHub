# Global Code Optimization Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve JavHub's repository-wide maintainability by making backend tests easier to run, reducing test-client warning noise, standardizing inventory scheduler logging, decomposing backend database initialization, and extracting a focused frontend translation-provider helper.

**Architecture:** Keep runtime behavior unchanged. This phase changes development/test entry points, moves repeated test-client construction into `backend/test_support`, replaces raw scheduler stdout writes with module logging, splits one large initializer into private helpers that preserve existing SQL order, and moves pure frontend provider-label logic into a tested utility module.

**Tech Stack:** FastAPI, pytest, httpx ASGITransport, PostgreSQL test support, Python logging, Vue 3 Options API, Node `node:test`, Vite.

---

## File Structure

- Create `pytest.ini`: root pytest discovery and import-path configuration.
- Create `backend/test_support/client.py`: synchronous helper around `httpx.AsyncClient` and `httpx.ASGITransport` for isolated FastAPI router tests.
- Create `backend/test_support/test_client.py`: focused helper tests proving no deprecated app-shortcut warning is emitted.
- Modify direct route tests that construct `TestClient(app)`:
  - `backend/test_logs_route.py`
  - `backend/test_health_route.py`
  - `backend/test_favorites.py`
  - `backend/test_video_variant_index_router.py`
  - `backend/test_videos_metadata_route.py`
  - `backend/test_downloaders.py`
  - `backend/test_categories_route.py`
  - `backend/test_actress_videos_supplement.py`
  - `backend/test_makers_route.py`
  - `backend/test_javinfo_imports.py`
- Create `backend/test_inventory_logging.py`: static regression tests for inventory scheduler logging.
- Modify `backend/scheduler/inventory_tasks.py`: replace direct `print(...)` calls with a module logger.
- Create `backend/test_database_init_structure.py`: structural regression test for `init_db()` helper decomposition and order.
- Modify `backend/database/base.py`: split `init_db()` into private helper functions while keeping SQL blocks and post-commit migrations in the same order.
- Create `frontend/src/utils/translationProviders.js`: pure translation-provider presentation helpers.
- Create `frontend/src/utils/translationProviders.test.js`: focused Node tests for the extracted helpers.
- Modify `frontend/src/views/TranslationJobs.vue`: import and delegate to the extracted provider helpers.

---

### Task 1: Root Backend Test Entry Point

**Files:**
- Create: `pytest.ini`

- [ ] **Step 1: Run the root backend test command red**

Run from `/Users/kongmei/Code/JavHub`:

```bash
.venv/bin/python -m pytest -q
```

Expected before this task: FAIL during collection with import errors like:

```text
ModuleNotFoundError: No module named 'routers'
ModuleNotFoundError: No module named 'test_support'
```

- [ ] **Step 2: Add root pytest configuration**

Create `pytest.ini`:

```ini
[pytest]
testpaths =
    backend
    tests
pythonpath =
    backend
    .
norecursedirs =
    .git
    .venv
    .worktrees
    backend/node_modules
    frontend/node_modules
    frontend/dist
```

- [ ] **Step 3: Verify the new root command is green**

Run from `/Users/kongmei/Code/JavHub`:

```bash
.venv/bin/python -m pytest -q
```

Expected after this task: PASS. Warnings from existing `TestClient(app)` usage may still appear here; Task 2 handles those call sites.

- [ ] **Step 4: Verify the documented command still works**

Run from `/Users/kongmei/Code/JavHub`:

```bash
PYTHONPATH=backend .venv/bin/python -m pytest -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pytest.ini
git commit -m "test: configure root pytest entry point"
```

---

### Task 2: Shared FastAPI Test Client Helper

**Files:**
- Create: `backend/test_support/client.py`
- Create: `backend/test_support/test_client.py`
- Modify: `backend/test_logs_route.py`
- Modify: `backend/test_health_route.py`
- Modify: `backend/test_favorites.py`
- Modify: `backend/test_video_variant_index_router.py`
- Modify: `backend/test_videos_metadata_route.py`
- Modify: `backend/test_downloaders.py`
- Modify: `backend/test_categories_route.py`
- Modify: `backend/test_actress_videos_supplement.py`
- Modify: `backend/test_makers_route.py`
- Modify: `backend/test_javinfo_imports.py`

- [ ] **Step 1: Write the failing helper test**

Create `backend/test_support/test_client.py`:

```python
from __future__ import annotations

import warnings

from fastapi import FastAPI

from test_support.client import create_test_client


def test_create_test_client_sends_requests_without_httpx_app_shortcut_warning():
    app = FastAPI()

    @app.get("/ok")
    def ok():
        return {"ok": True}

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        response = create_test_client(app).get("/ok")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert not [
        warning for warning in caught
        if "app shortcut is now deprecated" in str(warning.message)
    ]
```

- [ ] **Step 2: Run the helper test red**

Run:

```bash
.venv/bin/python -m pytest backend/test_support/test_client.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'test_support.client'`.

- [ ] **Step 3: Implement the helper**

Create `backend/test_support/client.py`:

```python
from __future__ import annotations

from typing import Any

import anyio
import httpx


class ASGITestClient:
    """Small sync wrapper for isolated FastAPI route tests."""

    def __init__(
        self,
        app: Any,
        *,
        base_url: str = "http://testserver",
        raise_app_exceptions: bool = True,
    ) -> None:
        self.app = app
        self.base_url = base_url
        self.raise_app_exceptions = raise_app_exceptions

    def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        async def send() -> httpx.Response:
            transport = httpx.ASGITransport(
                app=self.app,
                raise_app_exceptions=self.raise_app_exceptions,
            )
            async with httpx.AsyncClient(
                transport=transport,
                base_url=self.base_url,
            ) as client:
                response = await client.request(method, url, **kwargs)
                await response.aread()
                return response

        return anyio.run(send)

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("PUT", url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("DELETE", url, **kwargs)


def create_test_client(app: Any, **kwargs: Any) -> ASGITestClient:
    return ASGITestClient(app, **kwargs)
```

- [ ] **Step 4: Run the helper test green**

Run:

```bash
.venv/bin/python -m pytest backend/test_support/test_client.py -q
```

Expected: PASS.

- [ ] **Step 5: Convert route tests to the helper**

Apply these replacement patterns:

```python
from fastapi.testclient import TestClient
```

becomes:

```python
from test_support.client import ASGITestClient, create_test_client
```

Methods typed as `TestClient` become `ASGITestClient`:

```python
def _client(self) -> ASGITestClient:
```

Direct construction:

```python
return TestClient(app)
client = TestClient(app)
response = TestClient(app).post("/api/v1/actresses/batch_videos", json={"ids": [26225]})
```

becomes:

```python
return create_test_client(app)
client = create_test_client(app)
response = create_test_client(app).post("/api/v1/actresses/batch_videos", json={"ids": [26225]})
```

For tests with local imports, replace:

```python
from fastapi.testclient import TestClient
```

with:

```python
from test_support.client import create_test_client
```

- [ ] **Step 6: Verify converted route tests**

Run:

```bash
.venv/bin/python -m pytest \
  backend/test_support/test_client.py \
  backend/test_logs_route.py \
  backend/test_health_route.py \
  backend/test_favorites.py \
  backend/test_video_variant_index_router.py \
  backend/test_videos_metadata_route.py \
  backend/test_downloaders.py \
  backend/test_categories_route.py \
  backend/test_actress_videos_supplement.py \
  backend/test_makers_route.py \
  backend/test_javinfo_imports.py \
  -q
```

Expected: PASS with no `httpx._client.py:680` app-shortcut deprecation warning in this targeted output.

- [ ] **Step 7: Commit**

```bash
git add \
  backend/test_support/client.py \
  backend/test_support/test_client.py \
  backend/test_logs_route.py \
  backend/test_health_route.py \
  backend/test_favorites.py \
  backend/test_video_variant_index_router.py \
  backend/test_videos_metadata_route.py \
  backend/test_downloaders.py \
  backend/test_categories_route.py \
  backend/test_actress_videos_supplement.py \
  backend/test_makers_route.py \
  backend/test_javinfo_imports.py
git commit -m "test: use shared asgi route client"
```

---

### Task 3: Inventory Scheduler Logging

**Files:**
- Create: `backend/test_inventory_logging.py`
- Modify: `backend/scheduler/inventory_tasks.py`

- [ ] **Step 1: Write the failing static logging tests**

Create `backend/test_inventory_logging.py`:

```python
from __future__ import annotations

import ast
from pathlib import Path


SOURCE_PATH = Path(__file__).parent / "scheduler" / "inventory_tasks.py"


def _tree() -> ast.AST:
    return ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))


def test_inventory_tasks_do_not_call_print_directly():
    print_calls = [
        node.lineno
        for node in ast.walk(_tree())
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "print"
    ]

    assert print_calls == []


def test_inventory_tasks_define_module_logger():
    source = SOURCE_PATH.read_text(encoding="utf-8")

    assert "import logging" in source
    assert "logger = logging.getLogger(__name__)" in source
```

- [ ] **Step 2: Run the logging tests red**

Run:

```bash
.venv/bin/python -m pytest backend/test_inventory_logging.py -q
```

Expected: FAIL because `backend/scheduler/inventory_tasks.py` still contains direct `print(...)` calls and no module logger.

- [ ] **Step 3: Add module logger**

In `backend/scheduler/inventory_tasks.py`, change the imports at the top from:

```python
import asyncio
import threading
```

to:

```python
import asyncio
import logging
import threading
```

Add below the imports:

```python
logger = logging.getLogger(__name__)
```

- [ ] **Step 4: Replace direct prints**

Replace each `print(...)` call with the matching logger call:

```python
logger.warning("[Inventory] Job %s not found", job_id)
logger.info("[Inventory] Starting collection job %s", job_id)
logger.info("[Inventory] Created snapshot key: %s", snapshot_key)
logger.info("[Inventory] Collected %s actors, %s total movies", len(actors_data), total)
logger.info(
    "[Inventory] Actor auto-match completed. Checked: %s, Confirmed: %s, Candidates: %s",
    actor_mapping_result.get("checked", 0),
    actor_mapping_result.get("auto_confirmed", 0),
    actor_mapping_result.get("candidates_created", 0),
)
logger.exception("[Inventory] Actor auto-match failed after collect")
logger.info("[Inventory] Collection job %s completed. Snapshot: %s", job_id, snapshot_key)
logger.exception("[Inventory] Collection job %s failed", job_id)
logger.info("[Inventory] Starting compare job %s, snapshot: %s", job_id, snapshot_key)
logger.info("[Inventory] Comparing %s actors from snapshot %s", len(actors), snapshot_key)
logger.warning(
    "[Inventory] Fetch failed for mapped actor %s->%s",
    emby_actor_id,
    javinfo_actress_id,
    exc_info=True,
)
logger.info(
    "[Inventory] Compare job %s completed. Scanned: %s, Missing: %s, Unmapped: %s",
    job_id,
    scanned,
    missing_total,
    unmapped,
)
logger.exception("[Inventory] Compare job %s failed", job_id)
logger.info("[Inventory] Starting actor compare job %s for actress %s", job_id, actress_id)
logger.info("[Inventory] Actor compare skipped unmapped Emby actor %s", actress_id)
logger.info("[Inventory] Actor compare job %s completed. Total: %s, Missing: %s", job_id, total, missing)
logger.exception("[Inventory] Actor compare job %s failed", job_id)
```

When replacing exception handlers, keep existing state updates immediately after logging:

```python
update_inventory_job(job_id, "failed", str(e))
update_inventory_progress(job_id, 0)
```

- [ ] **Step 5: Verify logging tests and inventory tests**

Run:

```bash
.venv/bin/python -m pytest backend/test_inventory_logging.py backend/test_watchlist_pipeline.py backend/test_operations_route.py -q
```

Expected: PASS.

- [ ] **Step 6: Verify no direct prints remain in the scheduler file**

Run:

```bash
rg -n "print\\(" backend/scheduler/inventory_tasks.py
```

Expected: exit code 1 with no matches.

- [ ] **Step 7: Commit**

```bash
git add backend/test_inventory_logging.py backend/scheduler/inventory_tasks.py
git commit -m "chore: use logging for inventory scheduler"
```

---

### Task 4: Database Initializer Decomposition

**Files:**
- Create: `backend/test_database_init_structure.py`
- Modify: `backend/database/base.py`

- [ ] **Step 1: Write the failing structure test**

Create `backend/test_database_init_structure.py`:

```python
from __future__ import annotations

import inspect

from database import base


def test_init_db_delegates_to_domain_helpers_in_order():
    source = inspect.getsource(base.init_db)
    expected_order = [
        "_init_translation_and_favorites",
        "_init_core_state_tables",
        "_init_inventory_tables",
        "_init_actor_mapping_tables",
        "_init_download_candidate_tables",
        "_init_video_variant_tables",
        "_init_emby_snapshot_tables",
        "_migrate_subscriptions",
        "_create_indexes",
    ]

    positions = [source.index(f"{name}(") for name in expected_order]

    assert positions == sorted(positions)


def test_database_initializer_helpers_exist():
    for name in [
        "_init_translation_and_favorites",
        "_init_core_state_tables",
        "_init_inventory_tables",
        "_init_actor_mapping_tables",
        "_init_download_candidate_tables",
        "_init_video_variant_tables",
        "_init_emby_snapshot_tables",
    ]:
        assert callable(getattr(base, name))
```

- [ ] **Step 2: Run the structure test red**

Run:

```bash
.venv/bin/python -m pytest backend/test_database_init_structure.py -q
```

Expected: FAIL because the private initializer helpers do not exist yet.

- [ ] **Step 3: Replace `init_db()` with helper orchestration**

In `backend/database/base.py`, replace the body of `init_db()` with:

```python
def init_db():
    """Initialize all PostgreSQL tables used by JavHub state."""
    _init_translation_and_favorites()

    conn = get_db_orig()
    try:
        cursor = conn.cursor()
        _init_core_state_tables(cursor)
        _init_inventory_tables(cursor)
        _init_actor_mapping_tables(cursor)
        _init_download_candidate_tables(cursor)
        _init_video_variant_tables(cursor)
        _init_emby_snapshot_tables(cursor)
        conn.commit()
    finally:
        conn.close()

    _migrate_subscriptions()
    _create_indexes()
```

- [ ] **Step 4: Add helper functions with mechanical SQL extraction**

Create these helper functions immediately below `init_db()` by cutting the
current SQL statements from `init_db()` into the named helper bodies:

```python
def _init_translation_and_favorites() -> None:
    from database.translation import init_translation_db
    init_translation_db()
    from translations.category_decensor import repair_masked_category_translations
    repair_masked_category_translations()
    from database.favorite import init_favorite_db
    init_favorite_db()
```

Extraction map:

| Helper | Cut from current `init_db()` | Contents |
|---|---:|---|
| `_init_core_state_tables` | `backend/database/base.py:296` | `download_tasks`, the `download_tasks` ALTER loop, `subscriptions`, `logs`, `ignored_duplicates`, and `actress_missing_summary` |
| `_init_inventory_tables` | `backend/database/base.py:365` | `inventory_jobs`, the `inventory_jobs` ALTER loop, `inventory_actors`, `inventory_videos`, `missing_videos`, and `exempt_videos` |
| `_init_actor_mapping_tables` | `backend/database/base.py:435` | `actor_aliases`, `actor_mappings`, the `actor_mappings` ALTER loop, and `idx_actor_mappings_pair` |
| `_init_download_candidate_tables` | `backend/database/base.py:486` | `download_candidates`, `download_candidates.error_msg` ALTER, `idx_download_candidates_content_source`, `download_candidate_events`, `idx_download_candidate_events_candidate`, `candidate_process_runs`, and `idx_candidate_process_runs_created` |
| `_init_video_variant_tables` | `backend/database/base.py:546` | `video_variant_groups`, `video_variant_group_items`, the primary-key migration `DO $$` block, and `video_variant_group_jobs` |
| `_init_emby_snapshot_tables` | `backend/database/base.py:610` | `emby_snapshots`, `emby_actors`, and the `emby_actors.image_tag` ALTER |

The completed helper bodies must contain the exact SQL statements listed in the
extraction map, in the same order they appear before the refactor. The helper
names and signatures are:

```python
def _init_core_state_tables(cursor) -> None:
def _init_inventory_tables(cursor) -> None:
def _init_actor_mapping_tables(cursor) -> None:
def _init_download_candidate_tables(cursor) -> None:
def _init_video_variant_tables(cursor) -> None:
def _init_emby_snapshot_tables(cursor) -> None:
```

- [ ] **Step 5: Run structure test green**

Run:

```bash
.venv/bin/python -m pytest backend/test_database_init_structure.py -q
```

Expected: PASS.

- [ ] **Step 6: Run database-focused tests**

Run:

```bash
.venv/bin/python -m pytest \
  backend/test_database_init_structure.py \
  backend/test_database_postgres.py \
  backend/test_config.py \
  backend/test_downloaders.py \
  backend/test_favorites.py \
  backend/test_video_variant_index_database.py \
  backend/test_translation_service.py \
  -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/test_database_init_structure.py backend/database/base.py
git commit -m "refactor: split javhub database initialization"
```

---

### Task 5: Translation Provider Frontend Helper

**Files:**
- Create: `frontend/src/utils/translationProviders.js`
- Create: `frontend/src/utils/translationProviders.test.js`
- Modify: `frontend/src/views/TranslationJobs.vue`

- [ ] **Step 1: Write the failing frontend helper tests**

Create `frontend/src/utils/translationProviders.test.js`:

```js
import assert from 'node:assert/strict'
import test from 'node:test'

import {
  PROVIDER_KEYS,
  PROVIDER_META,
  firstNetworkProvider,
  normalizeProvider,
  providerLabel,
  providerOrderLabel
} from './translationProviders.js'

test('translation provider metadata exposes configured network providers', () => {
  assert.deepEqual(PROVIDER_KEYS, ['google_free', 'baidu', 'deepl', 'microsoft', 'ai'])
  assert.equal(PROVIDER_META.google_free.label, 'Google 免费接口')
  assert.equal(PROVIDER_META.ai.label, '智能兜底')
})

test('providerLabel names known pipeline and network providers', () => {
  assert.equal(providerLabel('cache'), '缓存')
  assert.equal(providerLabel('mapping'), '映射')
  assert.equal(providerLabel('google_free'), 'Google 免费接口')
  assert.equal(providerLabel('openai_compatible'), '智能兜底')
  assert.equal(providerLabel('translation_service'), '批量源')
  assert.equal(providerLabel('manual'), '人工')
  assert.equal(providerLabel('custom_provider'), 'custom_provider')
  assert.equal(providerLabel(''), '')
})

test('providerOrderLabel joins known labels and falls back when empty', () => {
  assert.equal(providerOrderLabel(['cache', 'mapping', 'google_free']), '缓存 -> 映射 -> Google 免费接口')
  assert.equal(providerOrderLabel(['', null, undefined]), '未记录')
  assert.equal(providerOrderLabel(null), '未记录')
})

test('normalizeProvider maps legacy ai key and falls back safely', () => {
  assert.equal(normalizeProvider('openai_compatible'), 'ai')
  assert.equal(normalizeProvider('deepl'), 'deepl')
  assert.equal(normalizeProvider('manual'), 'google_free')
  assert.equal(normalizeProvider(''), 'google_free')
})

test('firstNetworkProvider skips cache and mapping providers', () => {
  assert.equal(firstNetworkProvider(['cache', 'mapping', 'baidu']), 'baidu')
  assert.equal(firstNetworkProvider(['cache', 'openai_compatible']), 'ai')
  assert.equal(firstNetworkProvider(['cache', 'mapping']), '')
  assert.equal(firstNetworkProvider('google_free'), '')
})
```

- [ ] **Step 2: Run the frontend helper test red**

Run:

```bash
npm test -- src/utils/translationProviders.test.js
```

from `/Users/kongmei/Code/JavHub/frontend`.

Expected: FAIL with `Cannot find module` and `translationProviders.js` in the error text.

- [ ] **Step 3: Implement provider helper module**

Create `frontend/src/utils/translationProviders.js`:

```js
export const PROVIDER_META = {
  google_free: { label: 'Google 免费接口', hint: '无密钥，适合标题和短名称批量翻译。' },
  baidu: { label: '百度翻译', hint: '使用百度通用文本翻译 API，适合已有免费 key 的低成本翻译。' },
  deepl: { label: 'DeepL', hint: '质量更高，需要配置密钥。' },
  microsoft: { label: 'Microsoft 翻译', hint: 'Azure 翻译接口，需要密钥和可选区域。' },
  ai: { label: '智能兜底', hint: '使用设置页当前公共智能模型，适合低成本源效果不好时补充。' },
}

export const PROVIDER_KEYS = Object.keys(PROVIDER_META)

const PROVIDER_LABELS = {
  cache: '缓存',
  mapping: '映射',
  google_free: 'Google 免费接口',
  baidu: '百度翻译',
  deepl: 'DeepL',
  microsoft: 'Microsoft 翻译',
  ai: '智能兜底',
  openai_compatible: '智能兜底',
  translation_service: '批量源',
  import: '导入',
  manual: '人工',
}

export function providerLabel(key) {
  return PROVIDER_LABELS[key] || key || ''
}

export function providerOrderLabel(order) {
  const labels = (order || []).map(key => providerLabel(key)).filter(Boolean)
  return labels.length ? labels.join(' -> ') : '未记录'
}

export function normalizeProvider(provider) {
  const key = provider === 'openai_compatible' ? 'ai' : provider
  return PROVIDER_META[key] ? key : 'google_free'
}

export function firstNetworkProvider(order) {
  if (!Array.isArray(order)) return ''
  const found = order.find(key => PROVIDER_META[key === 'openai_compatible' ? 'ai' : key])
  return found ? normalizeProvider(found) : ''
}
```

- [ ] **Step 4: Update `TranslationJobs.vue` to use the helper**

In `frontend/src/views/TranslationJobs.vue`, add this import:

```js
import {
  PROVIDER_KEYS,
  PROVIDER_META,
  firstNetworkProvider,
  normalizeProvider,
  providerLabel,
  providerOrderLabel,
} from '../utils/translationProviders.js'
```

Remove the local `PROVIDER_META` and `PROVIDER_KEYS` constants. In the `methods` block, replace the current four provider methods with direct delegates:

```js
providerLabel,
providerOrderLabel,
normalizeProvider,
firstNetworkProvider,
```

Keep all existing template and computed references unchanged.

- [ ] **Step 5: Verify frontend helper tests**

Run from `/Users/kongmei/Code/JavHub/frontend`:

```bash
npm test -- src/utils/translationProviders.test.js
```

Expected: PASS.

- [ ] **Step 6: Verify existing frontend tests**

Run from `/Users/kongmei/Code/JavHub/frontend`:

```bash
npm test
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add \
  frontend/src/utils/translationProviders.js \
  frontend/src/utils/translationProviders.test.js \
  frontend/src/views/TranslationJobs.vue
git commit -m "refactor: extract translation provider helpers"
```

---

### Task 6: Full Phase Verification

**Files:**
- No new files. Verify all changed files from Tasks 1-5.

- [ ] **Step 1: Check service health with the project helper**

Run from `/Users/kongmei/Code/JavHub`:

```bash
scripts/services.sh status
```

Expected: JavInfoApi, backend, and frontend HTTP health checks are `ok`.

- [ ] **Step 2: Verify root pytest command**

Run from `/Users/kongmei/Code/JavHub`:

```bash
.venv/bin/python -m pytest -q
```

Expected: PASS.

- [ ] **Step 3: Verify documented pytest command**

Run from `/Users/kongmei/Code/JavHub`:

```bash
PYTHONPATH=backend .venv/bin/python -m pytest -q
```

Expected: PASS.

- [ ] **Step 4: Verify inventory scheduler print cleanup**

Run:

```bash
rg -n "print\\(" backend/scheduler/inventory_tasks.py
```

Expected: exit code 1 with no matches.

- [ ] **Step 5: Verify frontend tests**

Run from `/Users/kongmei/Code/JavHub/frontend`:

```bash
npm test
```

Expected: PASS.

- [ ] **Step 6: Verify frontend production build**

Run from `/Users/kongmei/Code/JavHub/frontend`:

```bash
npm run build
```

Expected: PASS.

- [ ] **Step 7: Inspect final diff**

Run from `/Users/kongmei/Code/JavHub`:

```bash
git status --short
git log --oneline -8
```

Expected: working tree clean after Task 5 commit, with commits for the spec and each implementation task visible in recent history.
