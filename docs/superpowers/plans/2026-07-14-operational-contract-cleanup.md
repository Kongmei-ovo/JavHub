# Operational Contract Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make variant-index POSTs truly return a retained queued job and remove Emby compatibility operations from OpenAPI without removing any runtime route.

**Architecture:** The synchronous index builder remains unchanged, but every manual start is wrapped in `asyncio.to_thread` and owned by a module-level task/future registry with terminal-state callbacks. The router becomes async so it always schedules from a persistent request loop. OpenAPI cleanup is limited to the three existing Emby router registrations.

**Tech Stack:** Python 3, asyncio, concurrent futures, FastAPI, Starlette TestClient, PostgreSQL-backed tests, pytest/unittest.

---

## Execution Constraints

- The implementation depends on the current uncommitted project state. Do not create a clean worktree from `HEAD` unless it first receives the current tracked and untracked baseline; `backend/test_main_app_boundary.py` does not exist in clean `HEAD`.
- The commit blocks below define logical boundaries. In the current dirty checkout, never broadly stage `backend/main.py`, `backend/test_main_app_boundary.py`, or another pre-dirty path; isolate exact new hunks or leave the checkpoint uncommitted.
- Do not modify `backend/test_support/client.py` or `backend/routers/emby_compat.py` for this subproject.
- Preserve the POST response status code and all existing GET payloads.

## File Map

- Modify `backend/services/video_variant_index.py:292-351`: task/future ownership, queued snapshot, enqueue failure, terminal callback, and initial running-state error boundary.
- Modify `backend/test_video_variant_index_service.py:108-177`: dispatch and terminal-state regressions.
- Modify `backend/routers/video_variant_index.py:19-22`: make only the POST handler async.
- Modify `backend/test_video_variant_index_router.py:11-48`: persistent-loop POST behavior and GET route compatibility.
- Modify `backend/test_sync_route_dispatch.py:12-40`: classify the POST handler as async while keeping DB reads sync.
- Modify `backend/main.py:233-236`: exclude exactly three Emby registrations from schema.
- Modify `backend/test_main_app_boundary.py`: OpenAPI uniqueness/warning and hidden-but-live route tests.

### Task 1: Own Every Variant-Index Background Execution

**Files:**
- Modify: `backend/services/video_variant_index.py:1-35,292-351`
- Modify: `backend/test_video_variant_index_service.py:108-177`

- [ ] **Step 1: Add failing running-loop and no-loop ownership tests**

Add `VariantIndexDispatchTest` coverage that patches `run_variant_index_job`, starts work from an `IsolatedAsyncioTestCase`, and asserts the returned value remains a detached `queued` snapshot while `_variant_index_tasks` contains the live task. Release the worker, await the task, and assert the registry is empty.

For the no-loop path, patch `scheduler.worker_loop.submit` to return a `concurrent.futures.Future`, call `start_variant_index_job()` from a normal `unittest.TestCase`, assert `_variant_index_futures` owns it, complete it, and assert callback cleanup.

Representative running-loop test body:

```python
    async def test_start_retains_task_and_returns_queued_snapshot(self):
        from services import video_variant_index as service

        entered = threading.Event()
        release = threading.Event()

        def blocking(job_id: int, *, force: bool = False):
            entered.set()
            release.wait(timeout=2)
            return {"id": job_id, "status": "completed", "force": force}

        with patch.object(service, "run_variant_index_job", side_effect=blocking):
            queued = service.start_variant_index_job(force=True)
            self.assertEqual(queued["status"], "queued")
            self.assertTrue(entered.wait(timeout=1))
            self.assertEqual(len(service._variant_index_tasks), 1)
            release.set()
            await asyncio.gather(*tuple(service._variant_index_tasks))

        self.assertEqual(service._variant_index_tasks, set())
```

- [ ] **Step 2: Add failing rejection and escaped-failure tests**

Cover these exact cases:

- `worker_loop.submit()` raises before accepting the coroutine: inspect the mock's coroutine argument and assert `inspect.getcoroutinestate(coro) == inspect.CORO_CLOSED`, the DB job is `failed`, and the original exception is re-raised.
- An accepted concurrent future finishes with `RuntimeError("executor failed")`: the callback consumes `.result()`, removes the future, and best-effort updates a still-queued row to `failed`.
- `get_variant_group_job()` or `update_variant_group_job()` fails in the callback: `assertLogs("services.video_variant_index", level="ERROR")` proves the persistence failure is explicit and the callback does not raise.
- The first `update_variant_group_job(job_id, status="running", processed=0, total=0)` raises: `run_variant_index_job()` reaches its failed-state path instead of escaping before the `try`.

- [ ] **Step 3: Run the new service tests and confirm current behavior fails**

Run: `.venv/bin/python -m pytest backend/test_video_variant_index_service.py -q`

Expected: FAIL because the no-loop path executes inline, no strong-reference registries exist, and the initial running update is outside the exception boundary.

- [ ] **Step 4: Add registries and completion helpers**

Add these imports and module-level declarations:

```python
from concurrent.futures import Future
from functools import partial

_variant_index_tasks: set[asyncio.Task[dict[str, Any]]] = set()
_variant_index_futures: set[Future[dict[str, Any]]] = set()
_TERMINAL_JOB_STATUSES = frozenset({"completed", "failed"})
```

Implement the failure and completion boundaries:

```python
def _persist_variant_index_failure(job_id: int, exc: BaseException) -> None:
    message = str(exc) or exc.__class__.__name__
    try:
        job = get_variant_group_job(job_id)
    except Exception:
        logger.exception("Unable to read variant index job %s after background failure", job_id)
        return
    if not job:
        logger.error("Variant index job %s disappeared after background failure: %s", job_id, message)
        return
    if job.get("status") in _TERMINAL_JOB_STATUSES:
        return
    try:
        failed = update_variant_group_job(job_id, status="failed", error=message)
    except Exception:
        logger.exception("Unable to persist failure for variant index job %s", job_id)
        return
    if failed is None:
        logger.error("Failure update returned no row for variant index job %s", job_id)


def _consume_variant_index_execution(
    job_id: int,
    execution: asyncio.Task[dict[str, Any]] | Future[dict[str, Any]],
) -> None:
    try:
        execution.result()
    except BaseException as exc:
        logger.error(
            "Variant index background execution %s escaped",
            job_id,
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        _persist_variant_index_failure(job_id, exc)


def _on_variant_index_task_done(job_id: int, task: asyncio.Task[dict[str, Any]]) -> None:
    _variant_index_tasks.discard(task)
    _consume_variant_index_execution(job_id, task)


def _on_variant_index_future_done(job_id: int, future: Future[dict[str, Any]]) -> None:
    _variant_index_futures.discard(future)
    _consume_variant_index_execution(job_id, future)
```

- [ ] **Step 5: Replace inline dispatch with accepted-work ownership**

```python
def start_variant_index_job(*, force: bool = False) -> dict[str, Any]:
    job_id = add_variant_group_job("queued")
    try:
        queued = copy.deepcopy(get_variant_group_job(job_id) or {"id": job_id, "status": "queued"})
    except BaseException as exc:
        _persist_variant_index_failure(job_id, exc)
        raise

    work = asyncio.to_thread(run_variant_index_job, job_id, force=force)
    accepted = False
    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            from scheduler import worker_loop

            future = worker_loop.submit(work)
            accepted = True
            _variant_index_futures.add(future)
            future.add_done_callback(partial(_on_variant_index_future_done, job_id))
        else:
            task = loop.create_task(work)
            accepted = True
            _variant_index_tasks.add(task)
            task.add_done_callback(partial(_on_variant_index_task_done, job_id))
    except BaseException as exc:
        if not accepted:
            work.close()
        _persist_variant_index_failure(job_id, exc)
        raise
    return queued
```

The handle must enter its set before `add_done_callback()`, because a completed concurrent future invokes its callback synchronously.

- [ ] **Step 6: Move the running-state update inside `run_variant_index_job()`'s try**

Start the existing function as follows and keep the current build body unchanged inside the same `try`:

```python
def run_variant_index_job(job_id: int, *, limit: int | None = None, force: bool = False) -> dict[str, Any]:
    try:
        update_variant_group_job(job_id, status="running", processed=0, total=0)
        fingerprint = _compute_source_fingerprint() if limit is None else None
```

In its `except Exception as exc` block, wrap the failed-state write. If that write raises or returns `None`, log it and re-raise the original exception so the done callback gets one final persistence attempt.

- [ ] **Step 7: Run focused service tests**

Run: `.venv/bin/python -m pytest backend/test_video_variant_index_service.py -q`

Expected: all service tests PASS and no `coroutine was never awaited` warning appears.

- [ ] **Step 8: Commit the service boundary**

```bash
git add backend/services/video_variant_index.py backend/test_video_variant_index_service.py
git diff --cached --check
git commit -m "fix: retain variant index background jobs"
```

### Task 2: Keep the POST on a Persistent Request Loop

**Files:**
- Modify: `backend/routers/video_variant_index.py:19-22`
- Modify: `backend/test_video_variant_index_router.py:1-48`
- Modify: `backend/test_sync_route_dispatch.py:12-40`

- [ ] **Step 1: Add a failing async-handler classification**

Keep list/detail handlers in `test_db_bound_read_routes_are_sync_for_threadpool_dispatch`. Add this assertion to `test_cached_hot_read_routes_are_async_to_avoid_threadpool_queueing`:

```python
        from routers import video_variant_index

        handlers = [
            video_variant_index.create_variant_index_job,
            downloads.list_downloads,
            downloads.list_candidates,
            downloads.candidate_summary,
            favorites.get_favorites,
            logs.get_logs,
        ]
```

- [ ] **Step 2: Add the persistent-loop POST regression**

Use `fastapi.testclient.TestClient` as a context manager around an isolated `FastAPI` app. Do not use `create_router_test_client` for this test.

```python
    def test_post_returns_queued_before_background_rebuild_finishes(self):
        from concurrent.futures import ThreadPoolExecutor
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from routers.video_variant_index import router

        entered = threading.Event()
        release = threading.Event()
        finished = threading.Event()

        def blocking(_job_id: int, *, force: bool = False):
            entered.set()
            try:
                release.wait(timeout=2)
                return {"status": "completed", "force": force}
            finally:
                finished.set()

        app = FastAPI()
        app.include_router(router)
        with patch("services.video_variant_index.run_variant_index_job", side_effect=blocking):
            with TestClient(app) as client, ThreadPoolExecutor(max_workers=1) as executor:
                request = executor.submit(client.post, "/api/v1/video-variants/index/jobs")
                try:
                    response = request.result(timeout=1)
                    self.assertTrue(entered.wait(timeout=1))
                    self.assertFalse(release.is_set())
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json()["status"], "queued")
                finally:
                    release.set()
                    request.result(timeout=2)
                    self.assertTrue(finished.wait(timeout=2))
```

- [ ] **Step 3: Run the two red tests**

Run: `.venv/bin/python -m pytest backend/test_sync_route_dispatch.py backend/test_video_variant_index_router.py -q`

Expected: FAIL because `create_variant_index_job` is synchronous; the endpoint regression times out or observes inline completion.

- [ ] **Step 4: Make only the POST handler async**

```python
@router.post("/jobs")
async def create_variant_index_job(force: bool = Query(True)) -> dict[str, Any]:
    return start_variant_index_job(force=force)
```

- [ ] **Step 5: Preserve and assert all read routes**

Extend the router test to call `GET /jobs`, `GET /jobs/{job_id}`, and `GET /stats` after creating a seeded row. Assert existing status codes and response keys; do not convert these DB-bound GET handlers to async.

- [ ] **Step 6: Run route tests**

Run: `.venv/bin/python -m pytest backend/test_sync_route_dispatch.py backend/test_video_variant_index_router.py backend/test_video_variant_index_service.py -q`

Expected: all tests PASS.

- [ ] **Step 7: Commit the request-loop dispatch change**

```bash
git add backend/routers/video_variant_index.py backend/test_video_variant_index_router.py backend/test_sync_route_dispatch.py
git diff --cached --check
git commit -m "fix: dispatch variant index posts on request loop"
```

### Task 3: Exclude Emby Compatibility Routes From OpenAPI Only

**Files:**
- Modify: `backend/main.py:233-236`
- Modify: `backend/test_main_app_boundary.py`

- [ ] **Step 1: Add a failing schema uniqueness test**

```python
    def test_openapi_has_unique_first_party_operations_and_no_emby_paths(self):
        import warnings

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            app = load_main_app_without_db()
            app.openapi_schema = None
            schema = app.openapi()

        operation_ids = [
            operation["operationId"]
            for path_item in schema["paths"].values()
            for operation in path_item.values()
            if isinstance(operation, dict) and "operationId" in operation
        ]
        duplicate_warnings = [item for item in caught if "Duplicate Operation ID" in str(item.message)]

        self.assertEqual(len(operation_ids), len(set(operation_ids)))
        self.assertEqual(duplicate_warnings, [])
        self.assertIn("/api/v1/video-variants/index/jobs", schema["paths"])
        self.assertIn("/api/v1/jobs", schema["paths"])
        self.assertNotIn("/System/Info/Public", schema["paths"])
        self.assertNotIn("/emby/System/Info/Public", schema["paths"])
        self.assertNotIn("/emby", schema["paths"])
```

- [ ] **Step 2: Add a runtime preservation test**

Under `patch.object(config, "_config", {"emby_compat": {"enabled": True, "username": "javhub", "password": "secret"}})`, use `TestClient(load_main_app_without_db())` to GET `/System/Info/Public`, `/emby/System/Info/Public`, and `/emby/`. Assert all return 200. This proves root compat, prefixed compat, and prefixed discovery registrations remain live.

- [ ] **Step 3: Run the boundary test and confirm the measured failure**

Run: `.venv/bin/python -m pytest backend/test_main_app_boundary.py -q`

Expected: FAIL with duplicate operation IDs/warnings and visible Emby paths. The reviewed baseline is 40 duplicate groups and 42 duplicate-ID warnings.

- [ ] **Step 4: Change exactly three router registrations**

```python
app.include_router(emby_compat_router, include_in_schema=False)
app.include_router(emby_discovery_router, prefix="/emby", include_in_schema=False)
app.include_router(emby_compat_router, prefix="/emby", include_in_schema=False)
```

- [ ] **Step 5: Run schema and Emby protocol coverage**

Run: `.venv/bin/python -m pytest backend/test_main_app_boundary.py backend/test_emby_compat.py backend/test_emby_protocol.py backend/test_emby_media_contract.py backend/test_emby_catalog_state.py backend/test_emby_open115.py -q`

Expected: all tests PASS, with zero duplicate-operation warnings.

- [ ] **Step 6: Commit schema exclusion**

```bash
git add backend/main.py backend/test_main_app_boundary.py
git diff --cached --check
git commit -m "fix: exclude Emby compatibility routes from OpenAPI"
```

### Task 4: Full and Live Verification

**Files:**
- Verify only; no planned source changes.

- [ ] **Step 1: Run all focused tests**

Run: `.venv/bin/python -m pytest backend/test_video_variant_index_service.py backend/test_video_variant_index_router.py backend/test_sync_route_dispatch.py backend/test_main_app_boundary.py backend/test_emby_compat.py backend/test_emby_protocol.py backend/test_emby_media_contract.py backend/test_emby_catalog_state.py backend/test_emby_open115.py -q`

Expected: zero failures and no duplicate-operation warnings.

- [ ] **Step 2: Run the complete backend suite**

Run: `.venv/bin/python -m pytest backend -q`

Expected: zero failures.

- [ ] **Step 3: Verify source hygiene**

Run: `git diff --check`

Expected: exit 0.

- [ ] **Step 4: Restart only the backend through the helper**

Run: `scripts/services.sh restart backend`

Expected: backend restarts successfully.

Run: `scripts/services.sh status`

Expected: backend port `18090` is healthy and the other healthy services remain available.

- [ ] **Step 5: Exercise the live contracts**

POST `http://127.0.0.1:18090/api/v1/video-variants/index/jobs?force=true`; require an immediate `status: queued` response, then poll `/api/v1/video-variants/index/jobs/{id}` until terminal. Fetch `/openapi.json`, collect all operation IDs, and require zero duplicate groups and no `/System/Info/Public` or `/emby/System/Info/Public` paths.

- [ ] **Step 6: Review final commit scope**

Run: `git status --short`

Run: `git log -3 --oneline`

Expected: the three planned commits are present and no unrelated files were staged or committed.
