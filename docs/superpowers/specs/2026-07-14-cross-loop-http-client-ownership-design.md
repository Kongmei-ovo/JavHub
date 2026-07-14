# Cross-Loop HTTP Client Ownership Design

**Date:** 2026-07-14

## Context

JavHub intentionally has two long-lived asyncio event loops: the FastAPI request loop and `scheduler.worker_loop`. Two global HTTP clients are used from both:

- `Open115Client` owns one `httpx.AsyncClient` plus asyncio locks created at process scope. A real backend log records polling failure with `is bound to a different event loop`, after which downloader polling catches the error and leaves the task unchanged.
- `InfoClient` detects loop changes but overwrites its single `AsyncClient` without closing the previous pool. Alternating request/background calls create abandoned connection pools, while shutdown closes only the latest one.

## Goals

- Reuse one owned `AsyncClient` per live event loop, never across loops.
- Drain normal in-flight uses and close every owned client on its owning loop during application shutdown.
- Preserve a process-wide Open115 request interval and token-refresh exclusion without loop-bound locks.
- Keep injected HTTP test doubles supported and caller-owned.
- Ensure downloader polling can advance a task submitted on the request loop when polling runs on the worker loop.

## Non-Goals

- Move all FastAPI traffic onto the worker loop.
- Change Open115 authentication, download-state, retry, or API payload semantics.
- Change JavInfo endpoint methods or response decoding.
- Hide polling failures; existing warnings remain for genuine remote failures.

## Design

### Shared loop-owned client pool

Add `backend/modules/loop_client_pool.py` with a focused generic `LoopClientPool`. It accepts an async-client factory and owns a thread-safe mapping from `asyncio.AbstractEventLoop` to client. The pool exposes an async `lease()` context manager rather than handing out untracked clients.

Entering a lease reads the running loop, returns that loop's open client, or creates one under a short `threading.Lock`. It never returns a client created for another loop. The same lock increments a process-wide active-lease count and clears an idle `threading.Event`; lease exit decrements the count and sets the event in `finally` when the count reaches zero. Client creation and accounting happen without an `await` while the lock is held. A regular mapping is used rather than weak references because shutdown must retain every client until it is explicitly closed.

The pool has a terminal `OPEN -> CLOSING -> CLOSED` lifecycle. `close_all()` atomically changes `OPEN` to `CLOSING`, so new leases are rejected instead of creating clients behind the shutdown snapshot. It waits for the idle event through one bounded `asyncio.to_thread()` call; that worker never owns a lock and exits at the deadline even if its awaiting task is canceled. The pool then schedules every client close on the client's recorded owner loop and reports the underlying task's actual completion through a loop-neutral concurrent future. Both same-loop and remote-loop closes have a bounded observation timeout.

Mappings are removed only after their client closes or is already closed. A timeout, cancellation, stopped owner loop, or `aclose()` failure leaves that entry retained for a later `close_all()` retry, while the pool remains closed to new leases. Concurrent close callers share one thread-safe in-flight close future backed by a strongly referenced internal leader task; canceling any waiter does not cancel the leader.

Each owner-loop task created for `aclose()` is strongly retained together with a separate concurrent completion future. The close leader observes that completion only until the configured deadline, requests cancellation of the owner task on timeout, and returns without pretending cancellation has completed. The retained attempt's done callback consumes the actual task outcome and removes the client only on success. A subsequent `close_all()` observes an existing attempt instead of starting a second `aclose()` for the same client. Once the mapping is empty the state becomes `CLOSED`; repeated close calls are harmless. This pool never silently reopens after shutdown.

### InfoClient integration

`InfoClient` replaces `_client` and `_client_loop` with a `LoopClientPool[httpx.AsyncClient]`. Each request helper holds a lease for the complete buffered request or stream context. `close()` delegates to `close_all()`.

The existing singleton, dynamic `api_url`, timeout defaults, request mapping, and `reset_info_client()` contract remain intact. A client is reused for A-B-A loop access as A1, B1, A1 rather than A1, B1, A2.

### Open115 integration

An `Open115Client` created without an injected `http_client` uses `LoopClientPool`, and `_request()` holds one lease through the HTTP request. An injected client remains a single caller-owned object and is never closed by `Open115Client`, preserving current test and embedding behavior. Injection is explicitly limited to loop-agnostic test doubles or clients whose caller guarantees single-loop use; cross-loop ownership of a real injected client remains the caller's responsibility.

The loop-bound throttle and refresh locks are replaced with cancellation-safe process-wide coordination:

- Request-slot reservation holds a `threading.Lock` only long enough to reserve the next monotonic start time, then releases it and performs any delay with `asyncio.sleep()`. No worker thread sleeps while holding a lock, and all loops observe one rate limit. Cancellation may leave an unused reserved slot but cannot stall later callers.
- Token refresh uses a process-wide single-flight record protected by a short `threading.Lock`. The leader performs refresh on its own loop after releasing the lock and completes a shared `concurrent.futures.Future`; followers use a shielded loop-local wrapper of that future. Follower cancellation affects only that follower. Leader success, failure, or cancellation always publishes an outcome and clears the in-flight record in `finally`, so no thread can acquire and orphan a lock after its coroutine has gone away.

Other shared dictionaries retain their existing semantics; no mutable loop-bound primitives remain on the singleton.

### Shutdown

The existing `main.shutdown_event()` calls to `InfoClient.close()` and `Open115Client.close()` remain the single client shutdown boundary. Uvicorn has already drained request handlers, and `stop_scheduler()` continues to wait for scheduled jobs. Extend scheduler shutdown to snapshot its tracked manual job threads and join them up to one shared bounded deadline before closing clients, logging any thread still alive. New pool leases are rejected once closing starts, so an untracked late fire-and-forget task fails promptly instead of recreating a transport. The persistent worker loop must remain running until both client pools have submitted and awaited their owner-loop closes.

## Error Handling

- Client creation failure does not cache a partial entry.
- Closing one client cannot prevent attempts to close the remaining clients; failures are retained and logged with loop identity.
- Lease accounting, close leadership, and refresh single-flight state are released or completed in `finally` blocks. No `threading.Lock` is held across an `await`.
- A client found closed is replaced only for its own loop.
- New leases fail once shutdown starts; an active lease gets the drain window before forced close.
- Genuine Open115 request errors continue mapping to `Open115Error`; loop-affinity failures are eliminated rather than swallowed.

## Tests

Add deterministic unit coverage for `LoopClientPool` using two persistent event loops in separate threads:

- A-B-A access creates exactly two clients and reuses A's client;
- concurrent first access on one loop creates one client;
- close waits for an active lease and rejects a new lease once closing begins;
- `close_all()` executes each close coroutine on its recorded owner loop;
- a stopped owner loop, hanging/raising `aclose()`, and cancellation retain failed entries without blocking other closes;
- a cancellation-resistant timed-out close remains single-instance and is consumed when it eventually finishes;
- a later close retries retained entries, while successful repeated close is harmless.

Add InfoClient tests with an instrumented AsyncClient factory proving two clients are retained and both close.

Add Open115 tests proving:

- owned transports are distinct per loop;
- injected test doubles remain usable and untouched, while cross-loop production coverage exercises the owned pooled path;
- cross-loop throttling respects one global interval;
- concurrent refreshes serialize across loops without consuming waiting executor threads;
- canceling a refresh follower or leader does not deadlock the next refresh;
- a submit-on-request-loop then poll-on-worker-loop flow does not raise loop-affinity errors and advances the mocked remote task state.

## Verification

- Run the new pool, InfoClient, Open115, downloader, scheduler, and acquisition tests.
- Search backend logs after an actual 115 submission/poll cycle for loop-affinity errors.
- Restart the backend and verify shutdown completes without pending-client warnings.
- Run the complete backend suite and compare open file/socket counts across repeated request/background alternation.

## Success Criteria

- No owned AsyncClient or asyncio lock is used from a foreign event loop.
- A 115 task submitted through the API can be finalized by the scheduled coordinator.
- InfoClient creates at most one live client per event loop and closes every normally reachable client at shutdown; unavailable owner loops remain visible as logged, retryable close failures rather than being forgotten.
- Existing request payloads, authentication behavior, and test-double ownership remain compatible.
