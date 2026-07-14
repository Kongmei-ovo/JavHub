# Operational Contract Cleanup Design

**Date:** 2026-07-14

## Context

Two remaining operational contracts are misleading:

1. `POST /api/v1/video-variants/index/jobs` is a synchronous FastAPI handler. Starlette runs it in a worker thread, `start_variant_index_job()` finds no event loop, and performs the full rebuild inline before returning the supposedly queued job.
2. Emby compatibility routers are mounted at root and `/emby` with multi-method routes included in OpenAPI. `/openapi.json` currently contains 40 duplicate operation-ID groups and emits repeated FastAPI warnings. These compatibility routes are consumed by Emby clients, not generated OpenAPI clients.

## Goals

- Make variant-index job creation return a queued record without waiting for the rebuild.
- Retain a strong reference to every in-process background execution until completion.
- Keep job status/result/error persistence unchanged.
- Produce an OpenAPI schema with unique operation IDs and no compatibility-route warning flood.
- Preserve all root and `/emby` HTTP behavior for media clients.

## Non-Goals

- Redesign variant grouping or add a distributed job queue.
- Change scheduler-triggered variant rebuild behavior.
- Remove or rename any Emby compatibility endpoint.
- Document the Emby protocol through JavHub's OpenAPI schema.

## Design

### Non-blocking variant job creation

Change `routers/video_variant_index.py::create_variant_index_job` to `async def`. It will call the existing service from a running request loop, allowing the service to schedule work and return immediately.

`start_variant_index_job()` will always enqueue rather than execute inline:

- With a running loop, create `asyncio.to_thread(run_variant_index_job, ...)` as a task.
- Without a running loop, submit that coroutine to `scheduler.worker_loop`. The concurrent future is retained internally and is never returned through the service or HTTP contract.

The service captures a detached copy of the newly inserted `queued` record before handing work to either loop and always returns that snapshot. This prevents a fast worker from racing the POST response to `running` or `completed`.

Module-level sets retain live asyncio tasks and concurrent futures. Done callbacks consume outcomes, remove completed work, and handle unexpected wrapper/executor failures that escaped `run_variant_index_job()`. Move the initial `running` update inside that function's `try`; its normal exception path attempts to persist `failed`, while the done callback makes one final best-effort `failed` update for a still-nonterminal job. A persistence outage is logged even if it makes a terminal write impossible.

If task creation or worker-loop submission fails, the service closes any coroutine that was not accepted, marks the queued job failed when the job store is writable, and re-raises. Otherwise the endpoint returns the captured queued snapshot immediately and clients continue polling the existing GET job route.

### Emby schema exclusion

Set `include_in_schema=False` on exactly the three existing registrations in `backend/main.py`: root `emby_compat_router`, `/emby` `emby_discovery_router`, and `/emby` `emby_compat_router`. This changes schema visibility only; FastAPI still registers and serves every route.

First-party `/api/v1` routers remain documented. No custom operation-ID generator is introduced because the compatibility protocol does not need generated SDK metadata.

## Error Handling

- Failure to enqueue updates the newly created variant job to failed before returning/raising, rather than leaving it permanently queued.
- Unexpected task/future exceptions are logged with job id, consumed by the done callback, and trigger a best-effort failed-state write when normal job handling did not reach a terminal state.
- Cancellation of an HTTP request after the queued response does not cancel the rebuild.
- A coroutine rejected before scheduling is explicitly closed, preventing `coroutine was never awaited` warnings.
- OpenAPI generation remains a normal request and should emit no duplicate-operation warnings.

## Tests

Variant endpoint tests will use a persistent `TestClient` context or one long-lived async client loop. They will block `run_variant_index_job` on a threading event, issue the POST, assert the queued response arrives before release, then release the worker before closing the client. This avoids the assembled test helper's per-request loop teardown masking production behavior. Additional tests cover:

- async-loop and no-running-loop enqueue paths;
- the response remains the original queued snapshot even if the worker advances immediately;
- strong-reference cleanup after completion;
- enqueue rejection closes the unscheduled coroutine and persists failed state;
- failed rebuild and unexpected wrapper failure persist failed job state when the job store is available;
- existing GET list/detail/stats routes remain compatible.

OpenAPI tests will assemble the real application without lifespan and assert:

- operation IDs are globally unique;
- representative first-party paths remain in the schema;
- representative root and `/emby` compatibility paths are absent from the schema;
- the same compatibility paths still respond through the ASGI app;
- generating the schema emits no duplicate-operation warnings.

## Verification

- Run variant service/router, Emby protocol/media, and app-boundary tests.
- Time a live variant-index POST and verify it returns before the job becomes terminal.
- Fetch `/openapi.json`, count duplicate operation IDs, and require zero.
- Inspect backend stderr after schema generation for duplicate-operation warnings.
- Run the full backend suite and restart/status checks.

## Success Criteria

- Variant job POST latency is independent of rebuild duration.
- Every enqueued execution remains referenced until it finishes and leaves a terminal job record whenever the job store is writable; persistence failures are explicit logs, not silently orphaned work.
- OpenAPI has zero duplicate operation-ID groups.
- Emby root and `/emby` compatibility behavior is unchanged despite schema exclusion.
