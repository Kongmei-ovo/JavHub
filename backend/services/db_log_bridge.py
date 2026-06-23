"""Bridge Python's standard ``logging`` into the aggregated ``logs`` table.

The 运行日志 page is meant to be a single aggregation of "what the system is
doing". Historically only a handful of explicit ``add_log()`` calls wrote there,
so real errors/exceptions (which go through ``logging``) never showed up — that's
why the ERROR level looked empty.

This installs a non-blocking bridge so standard logging flows into the table:

* WARNING / ERROR / CRITICAL / unhandled exceptions from **any** logger → stored
  (this is what fixes "看不到 error").
* INFO from **our own** modules (routers/services/scheduler/…) → stored, so
  normal behaviors are visible too.
* INFO/DEBUG from third-party libs (httpx/uvicorn.access/apscheduler/…) → dropped,
  so the aggregation isn't flooded with request noise.

Writes happen on a background ``QueueListener`` thread (the request thread only
enqueues), records are redacted before storage, and any failure is swallowed —
logging must never add latency to or break a request.
"""
from __future__ import annotations

import atexit
import logging
import logging.handlers
import queue
import threading

# Top-level package names whose INFO is worth aggregating. Anything else only
# contributes at WARNING and above. Kept in sync with backend packages that use
# logging.getLogger(__name__).
_APP_LOGGER_HEADS = frozenset({
    "routers", "services", "scheduler", "database", "middlewares",
    "modules", "sources", "translations", "config", "models",
    "telegram_bot", "main", "__main__",
})

# Cap a single stored message so a giant traceback can't bloat a row.
_MAX_MESSAGE_CHARS = 8000

_listener: logging.handlers.QueueListener | None = None


def _is_app_logger(name: str) -> bool:
    return (name or "").split(".", 1)[0] in _APP_LOGGER_HEADS


def _stored_level(levelno: int) -> str | None:
    """Map a Python level to the INFO/WARNING/ERROR vocabulary the UI knows."""
    if levelno >= logging.ERROR:      # ERROR + CRITICAL
        return "ERROR"
    if levelno >= logging.WARNING:
        return "WARNING"
    if levelno >= logging.INFO:
        return "INFO"
    return None


class _BridgeFilter(logging.Filter):
    """Decide what reaches the DB and stamp the request's trace id while we're
    still on the request thread (the listener thread has no trace context)."""

    def filter(self, record: logging.LogRecord) -> bool:
        level = record.levelno
        if level < logging.INFO:
            return False
        if level < logging.WARNING and not _is_app_logger(record.name):
            return False
        # Never re-ingest the bridge's own plumbing (defensive against loops).
        if record.name.startswith("services.db_log_bridge"):
            return False
        try:
            from middlewares.trace import get_trace_id
            record.bridge_trace_id = get_trace_id()
        except Exception:
            record.bridge_trace_id = None
        return True


class _DbLogHandler(logging.Handler):
    """Runs on the QueueListener thread; persists each record into ``logs``."""

    _guard = threading.local()

    def emit(self, record: logging.LogRecord) -> None:
        if getattr(self._guard, "active", False):
            return
        self._guard.active = True
        try:
            stored = _stored_level(record.levelno)
            if stored is None:
                return
            # The QueueHandler already formatted msg (incl. any traceback) and
            # redacted it, so getMessage() is the final text.
            message = record.getMessage()
            if len(message) > _MAX_MESSAGE_CHARS:
                message = message[:_MAX_MESSAGE_CHARS] + "…(truncated)"
            from database.log import add_log
            add_log(stored, message, trace_id=getattr(record, "bridge_trace_id", None))
        except Exception:
            # Logging must never break the app — drop on any failure.
            pass
        finally:
            self._guard.active = False


def install_db_log_bridge() -> None:
    """Idempotently attach the logging→DB bridge to the root logger."""
    global _listener
    if _listener is not None:
        return

    log_queue: queue.SimpleQueue = queue.SimpleQueue()
    queue_handler = logging.handlers.QueueHandler(log_queue)
    # Format upfront on the request thread so the listener stores the final,
    # redacted message (with traceback for exc records). %(message)s + the
    # default Formatter behavior appends the exception text when present.
    queue_handler.setFormatter(logging.Formatter("%(message)s"))
    queue_handler.addFilter(_BridgeFilter())
    try:
        # Redact tokens/signed URLs before they are stored, same as stdout.
        from services.log_redaction import SensitiveDataFilter
        queue_handler.addFilter(SensitiveDataFilter())
    except Exception:
        pass

    listener = logging.handlers.QueueListener(
        log_queue, _DbLogHandler(), respect_handler_level=False
    )
    listener.start()
    logging.getLogger().addHandler(queue_handler)

    _listener = listener
    atexit.register(_shutdown_db_log_bridge)


def _shutdown_db_log_bridge() -> None:
    global _listener
    if _listener is not None:
        try:
            _listener.stop()
        except Exception:
            pass
        _listener = None
