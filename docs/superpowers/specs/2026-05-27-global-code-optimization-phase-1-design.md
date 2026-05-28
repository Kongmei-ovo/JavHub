# Global Code Optimization Phase 1 Design

## Context

JavHub is healthy enough to optimize from a clean baseline:

- `scripts/services.sh status` reports JavInfoApi, backend, and frontend healthy.
- The working tree was clean before this design document was created.
- `PYTHONPATH=backend .venv/bin/python -m pytest -q` passed with 417 tests, 16 subtests, and 31 warnings.
- `frontend npm test` passed with 265 tests.
- `frontend npm run build` passed.

The current codebase has several broad optimization opportunities, but a single
unbounded cleanup would be hard to verify. Phase 1 focuses on low-risk,
cross-cutting maintainability and developer-experience improvements that make
future performance and feature work easier.

## Goals

Phase 1 should improve the whole repository without changing product behavior:

1. Make the common backend test entry point work from the repository root without
   requiring developers to remember `PYTHONPATH=backend`.
2. Reduce noisy backend test warnings caused by deprecated `TestClient(app)`
   usage by introducing and adopting a shared test client helper.
3. Replace inventory scheduler `print(...)` debug output with standard module
   logging so service logs are structured consistently.
4. Split the largest backend database initializer into named, domain-oriented
   helper functions while preserving initialization order and side effects.
5. Extract a small, behavior-preserving frontend helper from one large page when
   the extraction can be covered by existing or focused tests.

## Non-Goals

Phase 1 will not:

- Redesign UI screens or change copy, layout, or navigation.
- Change API response shapes, route paths, scheduler semantics, database schemas,
  or cache behavior except where existing initialization code is moved into
  smaller functions.
- Optimize JavInfoApi, external services, or deployment infrastructure.
- Remove all warnings in the repository. Dependency-level warnings that require
  package upgrades or upstream behavior changes may remain.
- Split every large Vue or Python file. Phase 1 creates the pattern and handles
  the safest high-signal slices.

## Approach

### Development Entry Points

Add root-level pytest configuration so backend modules and backend tests resolve
the same way whether tests run from the repository root, CI, or `backend/`.
The README and CI can keep their current commands if desired, but the root
command should no longer fail during collection when `PYTHONPATH` is omitted.

### Backend Test Client Helper

Create a small backend test support helper that builds FastAPI test clients using
the current httpx transport style instead of the deprecated app shortcut. Convert
route tests that instantiate `TestClient(app)` directly to the helper. Keep the
helper inside `backend/test_support` so production code has no new dependency on
test utilities.

### Inventory Scheduler Logging

Replace `print(...)` calls in `backend/scheduler/inventory_tasks.py` with a
module logger. Preserve message content and exception visibility, but route it
through `logging.getLogger(__name__)`. Use `logger.exception(...)` in exception
handlers where stack traces are useful for operations.

### Database Initializer Decomposition

Split `backend/database/base.py:init_db` into private helpers grouped by domain,
for example download tasks, subscriptions/logs, inventory snapshots, missing
videos, and candidate-related state. The public `init_db()` function remains the
single entry point and calls helpers in the current order. This is a structural
refactor only: SQL text, indexes, migrations, and commit behavior remain
equivalent.

### Frontend Helper Extraction

Extract translation-provider presentation helpers from
`frontend/src/views/TranslationJobs.vue` into
`frontend/src/utils/translationProviders.js`. The extracted helpers should cover
provider labeling, provider order labeling, provider key normalization, and
first-network-provider selection. Add focused Node tests in
`frontend/src/utils/translationProviders.test.js`. Avoid component reshaping in
this phase.

## Data Flow And Behavior

Runtime data flow should not change. The backend should still initialize the
same database tables and indexes on startup. Inventory jobs should still update
job state, progress, missing videos, and download candidates the same way. The
frontend should still call the same APIs and render the same views.

The only intentional flow changes are development-time flows:

- Root test execution should resolve backend imports without manual environment
  variables.
- Route tests should obtain clients through one helper instead of each test
  directly choosing a deprecated client construction style.
- Operational logs emitted by inventory jobs should use the application logging
  stack instead of raw stdout prints.

## Error Handling

Existing error handling must be preserved. Refactors should not swallow
exceptions or convert failures to successful states. Inventory job exception
handlers should continue to mark jobs as failed and reset progress where they do
today. Logger conversions should use exception-aware logging in broad exception
blocks so stack traces remain available.

## Testing And Verification

Phase 1 is complete only when fresh verification proves all of the following:

- `scripts/services.sh status` reports JavInfoApi, backend, and frontend healthy.
- `.venv/bin/python -m pytest -q` from the repository root passes without
  `PYTHONPATH=backend`.
- `PYTHONPATH=backend .venv/bin/python -m pytest -q` still passes to protect the
  existing documented workflow.
- `npm test` from `frontend/` passes.
- `npm run build` from `frontend/` passes.
- `frontend/src/utils/translationProviders.test.js` covers provider labeling,
  provider order labeling, provider key normalization, and first network
  provider selection.
- A search for direct `print(...)` calls in `backend/scheduler/inventory_tasks.py`
  returns no matches.

## Risks

- Changing pytest import behavior can hide import-order assumptions. Mitigate by
  running both the new root command and the existing documented command.
- Replacing `TestClient(app)` in many tests can be noisy. Mitigate by starting
  with a small helper and converting only direct route client construction sites.
- Splitting `init_db()` can accidentally reorder migrations. Mitigate by keeping
  SQL blocks intact and preserving call order exactly.
- Frontend extraction can drift into UI refactoring. Mitigate by limiting it to
  translation-provider presentation helpers and direct tests.
