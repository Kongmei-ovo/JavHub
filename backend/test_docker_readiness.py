from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_docker_readiness.py"


def _payload() -> dict:
    return {
        "status": "degraded",
        "config": {"loaded": True, "error": "", "path": "/config/config.yaml"},
        "database": {"connectable": True, "error": ""},
        "javinfo": {
            "api_url_configured": True,
            "legacy": False,
            "reachable": True,
            "error": "",
        },
        "cache": {"backend": "redis", "error": ""},
        "downloaders": {
            "default_id": "",
            "default_available": False,
            "error": "",
        },
        "sources": {"registered": 1, "available": 1, "error": ""},
        "scheduler": {
            "effective_enabled": False,
            "disabled_reason": "manual_policy",
        },
    }


def _run(payload: dict) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )


def test_readiness_validator_allows_unbound_optional_downloader():
    result = _run(_payload())

    assert result.returncode == 0, result.stderr
    assert "readiness smoke ok" in result.stdout


def test_readiness_validator_rejects_database_failure():
    payload = _payload()
    payload["database"] = {
        "connectable": False,
        "error": "connection refused",
    }

    result = _run(payload)

    assert result.returncode != 0
    assert "database.connectable" in result.stderr


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("config.loaded", False, "config.loaded"),
        ("javinfo.legacy", True, "javinfo.legacy"),
        ("cache.backend", "memory", "cache.backend"),
        ("sources.error", "registry unavailable", "sources.error"),
        ("downloaders.error", "invalid config", "downloaders.error"),
        ("scheduler.error", "scheduler unavailable", "scheduler.error"),
    ),
)
def test_readiness_validator_rejects_core_dependency_failures(
    field: str,
    value: object,
    message: str,
):
    payload = _payload()
    section, key = field.split(".", 1)
    payload[section][key] = value

    result = _run(payload)

    assert result.returncode != 0
    assert message in result.stderr


def test_readiness_validator_rejects_unexplained_degraded_status():
    payload = _payload()
    payload["downloaders"]["default_available"] = True

    result = _run(payload)

    assert result.returncode != 0
    assert "status" in result.stderr
