"""Unit tests for the logging→DB bridge routing policy."""
import logging
from unittest.mock import patch

from services.db_log_bridge import (
    _BridgeFilter,
    _DbLogHandler,
    _is_app_logger,
    _stored_level,
)
from database.log import _should_prune


def _record(name, level, msg="hello"):
    return logging.LogRecord(
        name=name, level=level, pathname=__file__, lineno=1, msg=msg, args=(), exc_info=None
    )


def test_stored_level_maps_to_ui_vocabulary():
    assert _stored_level(logging.DEBUG) is None
    assert _stored_level(logging.INFO) == "INFO"
    assert _stored_level(logging.WARNING) == "WARNING"
    assert _stored_level(logging.ERROR) == "ERROR"
    # CRITICAL folds into ERROR so the UI (which only knows INFO/WARNING/ERROR) shows it.
    assert _stored_level(logging.CRITICAL) == "ERROR"


def test_is_app_logger():
    assert _is_app_logger("routers.supplement")
    assert _is_app_logger("services.downloader")
    assert _is_app_logger("scheduler.tasks")
    assert _is_app_logger("main")
    assert not _is_app_logger("httpx")
    assert not _is_app_logger("uvicorn.access")
    assert not _is_app_logger("apscheduler.scheduler")


def test_bridge_filter_keeps_errors_and_our_info_drops_thirdparty_noise():
    f = _BridgeFilter()
    # our normal behaviors are visible
    assert f.filter(_record("routers.supplement", logging.INFO)) is True
    assert f.filter(_record("services.downloader", logging.INFO)) is True
    # third-party INFO is noise → dropped
    assert f.filter(_record("httpx", logging.INFO)) is False
    assert f.filter(_record("uvicorn.access", logging.INFO)) is False
    # WARNING/ERROR from ANYONE is kept (this is what fixes "看不到 error")
    assert f.filter(_record("httpx", logging.WARNING)) is True
    assert f.filter(_record("routers.x", logging.ERROR)) is True
    # debug never; the bridge never re-ingests its own plumbing
    assert f.filter(_record("routers.x", logging.DEBUG)) is False
    assert f.filter(_record("services.db_log_bridge", logging.ERROR)) is False


def test_bridge_filter_stamps_trace_id_on_request_thread():
    f = _BridgeFilter()
    rec = _record("routers.x", logging.ERROR)
    assert f.filter(rec) is True
    assert hasattr(rec, "bridge_trace_id")


def test_db_handler_routes_to_add_log_with_mapped_level_and_trace():
    handler = _DbLogHandler()
    calls = []
    with patch("database.log.add_log", lambda level, message, trace_id=None: calls.append((level, message, trace_id))):
        rec = _record("routers.x", logging.ERROR, msg="boom")
        rec.bridge_trace_id = "trace-1"
        handler.emit(rec)
    assert calls == [("ERROR", "boom", "trace-1")]


def test_db_handler_skips_below_info():
    handler = _DbLogHandler()
    calls = []
    with patch("database.log.add_log", lambda *a, **k: calls.append(a)):
        handler.emit(_record("routers.x", logging.DEBUG))
    assert calls == []


def test_db_handler_swallows_add_log_failure():
    handler = _DbLogHandler()

    def boom(*a, **k):
        raise RuntimeError("db down")

    with patch("database.log.add_log", boom):
        # must not raise — logging can never break the app
        handler.emit(_record("routers.x", logging.ERROR))


def test_should_prune_bounds():
    assert _should_prune(0) is False
    assert _should_prune(1) is True
