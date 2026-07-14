# Runtime and Test Boundary Fixes Design

**Date:** 2026-07-14

## Context

The current backend and frontend baselines are broadly healthy, but review found five reproducible boundary defects:

1. Importing `backend/main.py` installs the database log bridge immediately. Backend tests import the assembled application, so intentional test errors can be written to the development `logs` table.
2. `load_main_app_without_db()` caches the first imported `main.app`. Tests that change `config.frontend_origin` therefore reuse stale CORS middleware and depend on execution order.
3. `/health/readiness` imports `_candidate_schedule_state` from the retired `routers.operations` module. It reports that missing module as the scheduler's disabled reason even while scheduler jobs are running.
4. The upload-completion restore task repeats cache invalidation already owned by `JavInfoImportManager`, and an exception escaping the detached task becomes `Task exception was never retrieved`.
5. `scripts/api_load_test.mjs` still exercises retired operations and inventory routes, making healthy smoke runs fail with HTTP 404 responses.

These are separate symptoms of the same class of issue: side effects and operational contracts remain attached to boundaries that were changed or retired.

## Goals

- Keep database-backed logging active for a real backend process without enabling it merely by importing the application in tests.
- Make assembled-application tests observe the configuration active for each test and remain independent of test order.
- Derive scheduler readiness from the current scheduler module and preserve the existing manual-policy semantics.
- Ensure detached JavInfo restore tasks contain and log failures and perform post-import work once.
- Make both built-in load-test endpoint groups contain only current, read-only routes.
- Add regression tests that fail for each confirmed defect before changing production behavior.

## Non-Goals

- Introduce a FastAPI application factory or restructure all import-time application assembly.
- Redesign scheduler policy, job registration, import workflows, or the System Monitor UI.
- Change AVDB behavior or absorb the existing uncommitted AVDB/UI work into this repair.
- Treat every historical test name or domain label containing `inventory` as a retired route bug.
- Expand the load script into an authentication or write-load harness.

## Design

### 1. Application lifecycle and assembled-app test isolation

`backend/main.py` will continue to assemble the FastAPI application at module import, including the existing database initialization call. The database log bridge installation will move from module scope into `startup_event()`. Uvicorn's lifespan startup will therefore enable production log aggregation, while a test that only imports `main.app` will not start a listener or write application logs to the development database. Installation remains idempotent through the existing bridge implementation.

`backend/test_support/client.py::load_main_app_without_db()` will still patch `database.init_db`, but it will import `main` when absent and reload it when already cached. Each call will return a newly assembled app whose CORS middleware reads the current `config.frontend_origin`. The helper will not run FastAPI lifespan events, which is intentional for these route-contract tests.

Regression coverage will prove both boundaries: importing through the helper does not call `install_db_log_bridge`, and two consecutive helper calls with different configured origins produce CORS responses for their respective origins. The CORS test must pass in the previously failing predecessor order as well as by itself.

### 2. Scheduler readiness from the current owner

`backend/routers/health.py::_scheduler_summary()` will import `candidate_auto_process_schedule_state` from `scheduler.tasks`, the module that currently owns the scheduler. It will normalize that state into the existing readiness fields:

- `enabled`: whether the candidate automation job is registered;
- `running`: whether candidate processing is currently active;
- `next_run_time`: the next scheduled execution when available;
- `policy`: the normalized automation policy;
- `effective_enabled`: true only when policy is not `manual` and the schedule is enabled;
- `disabled_reason`: `manual_policy`, `schedule_disabled`, a real scheduler error, or an empty string.

Manual policy is an expected state, not a readiness failure. If reading scheduler state raises, the summary will include the exception text in both `error` and `disabled_reason`; the existing readiness degradation check will then correctly mark the response degraded. This retains the contract formerly implemented in the removed operations router without restoring that router or creating a new cross-router dependency.

Tests will cover manual policy, enabled automatic policy, disabled automatic policy, and scheduler-state exceptions. The runtime check will confirm that readiness no longer mentions `routers.operations` and that `/api/v1/scheduler/jobs` remains consistent with the scheduler summary.

### 3. JavInfo restore task ownership and failure containment

`backend/routers/javinfo_imports.py::_restore_after_upload()` will remain the detached task entry point. It will await `manager.restore_job(job_id)` inside a broad exception boundary and log unexpected failures with the job id and traceback. Because this function is the final owner of the task result, it will not re-raise after logging.

The router-level `cache.purge_all()` call will be removed. Successful restore already runs `JavInfoImportManager._invalidate_javhub_caches()` after post-import migrations, where cache purge and client reset are tracked in the import job log. The router will retain the successful variant-index rebuild trigger because the manager does not own that follow-up. Failure to enqueue the optional variant-index rebuild will be logged, but will not retroactively change a completed database restore into a failed one.

Regression tests will call the task entry point directly. They will verify that manager exceptions are logged and contained, a completed restore enqueues one variant-index rebuild, a non-completed restore does not enqueue it, and the router does not issue a second cache purge.

### 4. Current load-test endpoint contracts

The default endpoint list will replace `/api/v1/operations/overview` with `/health/readiness`. The retired `inventory` endpoint group will be replaced by an `operations` group matching the read-only calls used by the current System Monitor:

- `/health/readiness`
- `/api/v1/downloads/candidates/summary`
- `/api/v1/scheduler/jobs`
- `/api/v1/cache/stats`
- `/api/v1/logs/summary?since_minutes=1440`

Help text and parser tests will expose only `default|operations`. The script will continue to reject unknown groups rather than silently mapping the retired name. This makes stale invocations fail at argument parsing with a useful error and prevents false 404-heavy performance reports.

Tests will assert the exact group names and endpoint lists. A short smoke run against the managed backend on port `18090` will verify zero failures attributable to retired routes.

## Error Handling

- Application import stays free of the persistent DB log side effect; startup failures still follow the existing service logging behavior.
- Scheduler inspection errors remain visible in readiness as `error`, rather than being disguised as an ordinary disabled schedule.
- Expected manual or disabled scheduling remains non-exceptional and does not by itself degrade readiness.
- Detached restore failures are logged once with traceback and consumed at the task boundary.
- Optional variant-index enqueue failure is observable but does not invalidate a completed restore.
- The load-test CLI rejects the retired endpoint-group name before issuing requests.

## Test and Verification Strategy

Each production change follows a separate red-green cycle:

1. Add an assembled-app regression that exposes stale CORS state and import-time bridge installation, run it to observe the expected failure, then change lifecycle/helper behavior.
2. Add direct scheduler-summary tests that expose the retired import and error-shape defect, run them red, then replace the dependency.
3. Add direct restore-task tests that expose escaping exceptions and duplicate purge, run them red, then contain the task and remove duplicate ownership.
4. Change load-script tests first to require `operations` and current routes, run them red, then update the script.

After targeted tests pass, run:

- the complete backend pytest suite;
- the complete frontend `npm run check` suite and production build included by that command;
- `git diff --check` and dependency integrity checks;
- `scripts/services.sh restart backend`, followed by service status;
- live `/health/readiness` and scheduler endpoint requests;
- default and operations load-test smoke runs;
- a before/after development-log id check around pytest to prove test exceptions no longer enter the live log table;
- a System Monitor browser check to confirm scheduler status renders without the retired-module error.

## Rollout and Compatibility

The service helper remains the only process-management interface. Only the backend needs restarting for these Python changes. No database migration, configuration migration, or frontend deployment is required.

The only deliberate CLI compatibility break is removal of `--endpoint-group inventory`, whose entire route set has already been retired. Callers must use `--endpoint-group operations` or explicit `--endpoint` values.

## Success Criteria

- Full backend tests pass independently of order, including the Emby CORS contract.
- Running backend tests does not add intentional test exceptions to the live `logs` table.
- A real backend startup installs the DB log bridge and runtime errors remain available to the logs API.
- `/health/readiness` contains no `routers.operations` error and accurately represents scheduler policy/state; genuine scheduler inspection errors degrade readiness.
- Restore background exceptions do not produce an unhandled-task warning, and successful imports purge JavHub caches once.
- Default and operations load-test smoke runs contain no stale-route 404 failures.
- Existing AVDB/UI work remains preserved and outside the repair commit set.
