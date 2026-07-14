# LaunchAgent Configuration Boundaries Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render all three LaunchAgent plists through structured, deterministic Python code while propagating one absolute config path and one shared effective proxy URL.

**Architecture:** A dependency-free proxy normalizer becomes the single source of truth for `Config.proxy_url` and service rendering. A standalone plist renderer builds typed dictionaries, serializes every payload before touching disk, and atomically replaces each destination; `services.sh` keeps lifecycle and change-detection ownership.

**Tech Stack:** Python 3, `plistlib`, PyYAML, pathlib, pytest, Bash, macOS `plutil`/LaunchAgents.

---

## Execution Constraints

- The implementation depends on the current uncommitted project state. Do not create a clean worktree from `HEAD` unless that worktree first receives the current tracked and untracked baseline; otherwise required Phase 1/AVDB files are absent.
- The commit blocks below define logical boundaries. In the current dirty checkout, never execute a broad `git add` for a file that was already modified at plan start. Stage only exact new hunks after inspecting `git diff --cached`, or leave that checkpoint uncommitted.
- Use `scripts/services.sh` for every real service action.
- Do not run `ensure`, restart services, or write real LaunchAgents during unit-test tasks. Runtime service checks belong only to Task 5.

## File Map

- Create `backend/modules/proxy_config.py`: pure effective-proxy normalization.
- Create `backend/test_proxy_config.py`: table-driven proxy contract tests.
- Modify `backend/config.py:712-719`: delegate `Config.proxy_url` to the shared helper.
- Create `scripts/render_service_plists.py`: structured plist builders, config loading, serialization, and per-file atomic replacement.
- Create `tests/test_service_plist_renderer.py`: cross-platform renderer and failure-boundary tests.
- Modify `scripts/services.sh:61-279`: remove XML/YAML shell helpers and call the renderer from `write_plists()`.
- Modify `tests/test_services.py:77-173,3145-3212`: retain macOS integration coverage using parsed plists.

### Task 1: Shared Effective Proxy Contract

**Files:**
- Create: `backend/modules/proxy_config.py`
- Create: `backend/test_proxy_config.py`
- Modify: `backend/config.py:694-719`
- Test: `backend/test_config.py:12-20`

- [ ] **Step 1: Write the failing pure-function tests**

```python
from __future__ import annotations

import unittest

from modules.proxy_config import effective_proxy_url


class EffectiveProxyURLTest(unittest.TestCase):
    def test_disabled_and_http_modes(self):
        self.assertEqual(effective_proxy_url({"enabled": False}), "")
        self.assertEqual(
            effective_proxy_url({"enabled": True, "http_url": "http://proxy", "https_url": "https://fallback"}),
            "http://proxy",
        )
        self.assertEqual(
            effective_proxy_url({"enabled": True, "http_url": "", "https_url": "https://fallback"}),
            "https://fallback",
        )
        self.assertEqual(
            effective_proxy_url({"enabled": True, "http_url": "   ", "https_url": "https://fallback"}),
            "https://fallback",
        )

    def test_vless_uses_one_bounded_port_contract(self):
        cases = {
            1080: "socks5://javhub:1080",
            "17891": "socks5://javhub:17891",
            None: "socks5://javhub:17890",
            "": "socks5://javhub:17890",
            "bad": "socks5://javhub:17890",
            0: "socks5://javhub:17890",
            -1: "socks5://javhub:17890",
            65536: "socks5://javhub:17890",
        }
        for port, expected in cases.items():
            with self.subTest(port=port):
                self.assertEqual(
                    effective_proxy_url(
                        {"enabled": True, "mode": "vless", "singbox_port": port},
                        advertise_host=" javhub ",
                    ),
                    expected,
                )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test and confirm the missing module**

Run: `.venv/bin/python -m pytest backend/test_proxy_config.py -q`

Expected: FAIL during collection with `ModuleNotFoundError: No module named 'modules.proxy_config'`.

- [ ] **Step 3: Implement the dependency-free normalizer**

```python
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

DEFAULT_VLESS_PORT = 17890


def _vless_port(value: Any) -> int:
    if isinstance(value, bool):
        return DEFAULT_VLESS_PORT
    try:
        port = int(str(value).strip())
    except (TypeError, ValueError):
        return DEFAULT_VLESS_PORT
    return port if 1 <= port <= 65535 else DEFAULT_VLESS_PORT


def effective_proxy_url(
    proxy: Mapping[str, Any] | None,
    *,
    advertise_host: str | None = None,
) -> str:
    settings = proxy if isinstance(proxy, Mapping) else {}
    if not settings.get("enabled"):
        return ""
    if settings.get("mode") == "vless":
        host = str(advertise_host or "").strip() or "127.0.0.1"
        return f"socks5://{host}:{_vless_port(settings.get('singbox_port'))}"
    http_url = str(settings.get("http_url") or "").strip()
    https_url = str(settings.get("https_url") or "").strip()
    return http_url or https_url
```

- [ ] **Step 4: Make `Config.proxy_url` delegate to the helper and extend its regression test**

Add `from modules.proxy_config import effective_proxy_url` near the imports, then replace the property body with:

```python
    @property
    def proxy_url(self) -> str:
        return effective_proxy_url(
            self.proxy,
            advertise_host=os.environ.get("JAVHUB_PROXY_ADVERTISE_HOST"),
        )
```

Extend `backend/test_config.py` with:

```python
    def test_vless_proxy_invalid_ports_use_the_shared_default(self):
        from config import Config

        cfg = Config.__new__(Config)
        for port in ("bad", 0, 65536):
            with self.subTest(port=port):
                cfg._config = {"proxy": {"enabled": True, "mode": "vless", "singbox_port": port}}
                self.assertEqual(cfg.proxy_url, "socks5://127.0.0.1:17890")
```

- [ ] **Step 5: Run focused tests**

Run: `.venv/bin/python -m pytest backend/test_proxy_config.py backend/test_config.py -q`

Expected: PASS with no failures.

- [ ] **Step 6: Commit the shared contract in the isolated worktree**

```bash
git add backend/modules/proxy_config.py backend/test_proxy_config.py backend/config.py backend/test_config.py
git diff --cached --check
git commit -m "fix: share effective proxy normalization"
```

### Task 2: Deterministic Per-File Atomic Plist Writer

**Files:**
- Create: `scripts/render_service_plists.py`
- Create: `tests/test_service_plist_renderer.py`

- [ ] **Step 1: Write failing serialization and failure-boundary tests**

```python
from __future__ import annotations

import plistlib
from pathlib import Path

import pytest

from scripts.render_service_plists import write_plists_atomically


def test_writer_is_deterministic_and_uses_0644(tmp_path: Path):
    target = tmp_path / "service.plist"
    payload = {"WorkingDirectory": "/tmp/a&b", "KeepAlive": True, "Label": "example"}

    write_plists_atomically({target: payload})
    first = target.read_bytes()
    write_plists_atomically({target: payload})

    assert target.read_bytes() == first
    assert plistlib.loads(first) == payload
    assert target.stat().st_mode & 0o777 == 0o644


def test_serialization_failure_leaves_every_destination_unchanged(tmp_path: Path):
    first = tmp_path / "first.plist"
    second = tmp_path / "second.plist"
    first.write_bytes(plistlib.dumps({"old": 1}))
    second.write_bytes(plistlib.dumps({"old": 2}))

    with pytest.raises(TypeError):
        write_plists_atomically({first: {"new": 1}, second: {"invalid": object()}})

    assert plistlib.loads(first.read_bytes()) == {"old": 1}
    assert plistlib.loads(second.read_bytes()) == {"old": 2}


def test_second_replace_failure_leaves_only_complete_plists(tmp_path: Path):
    first = tmp_path / "first.plist"
    second = tmp_path / "second.plist"
    first.write_bytes(plistlib.dumps({"old": 1}))
    second.write_bytes(plistlib.dumps({"old": 2}))
    calls = 0

    def fail_second(source: str | Path, destination: str | Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("replace failed")
        Path(source).replace(destination)

    with pytest.raises(OSError, match="replace failed"):
        write_plists_atomically(
            {first: {"new": 1}, second: {"new": 2}},
            replace=fail_second,
        )

    assert plistlib.loads(first.read_bytes()) == {"new": 1}
    assert plistlib.loads(second.read_bytes()) == {"old": 2}
```

Also add this second-temp failure case:

```python
def test_temp_write_failure_precedes_every_replace(tmp_path: Path, monkeypatch):
    from scripts import render_service_plists as renderer

    first = tmp_path / "first.plist"
    second = tmp_path / "second.plist"
    first_before = plistlib.dumps({"old": 1})
    second_before = plistlib.dumps({"old": 2})
    first.write_bytes(first_before)
    second.write_bytes(second_before)
    real_mkstemp = renderer.tempfile.mkstemp
    calls = 0
    replacements = []

    def fail_second_temp(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("temp write failed")
        return real_mkstemp(*args, **kwargs)

    monkeypatch.setattr(renderer.tempfile, "mkstemp", fail_second_temp)
    with pytest.raises(OSError, match="temp write failed"):
        renderer.write_plists_atomically(
            {first: {"new": 1}, second: {"new": 2}},
            replace=lambda source, destination: replacements.append((source, destination)),
        )

    assert replacements == []
    assert first.read_bytes() == first_before
    assert second.read_bytes() == second_before
    assert list(tmp_path.glob(".*.tmp")) == []
```

- [ ] **Step 2: Run the tests and confirm the renderer is missing**

Run: `.venv/bin/python -m pytest tests/test_service_plist_renderer.py -q`

Expected: FAIL during collection because `scripts.render_service_plists` does not exist.

- [ ] **Step 3: Implement serialize-first, temp-first, replace-last writing**

```python
from __future__ import annotations

import os
import plistlib
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


def write_plists_atomically(
    payloads: Mapping[Path, dict[str, Any]],
    *,
    replace: Callable[[str | Path, str | Path], None] = os.replace,
) -> None:
    serialized = [
        (Path(destination), plistlib.dumps(payload, fmt=plistlib.FMT_XML, sort_keys=True))
        for destination, payload in payloads.items()
    ]
    for _destination, content in serialized:
        plistlib.loads(content)

    temporary_paths: list[tuple[Path, Path]] = []
    try:
        for destination, content in serialized:
            destination.parent.mkdir(parents=True, exist_ok=True)
            fd, raw_temporary = tempfile.mkstemp(
                prefix=f".{destination.name}.",
                suffix=".tmp",
                dir=destination.parent,
            )
            temporary = Path(raw_temporary)
            with os.fdopen(fd, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            temporary.chmod(0o644)
            temporary_paths.append((temporary, destination))

        for temporary, destination in temporary_paths:
            replace(temporary, destination)
    finally:
        for temporary, _destination in temporary_paths:
            temporary.unlink(missing_ok=True)
```

- [ ] **Step 4: Run the writer tests**

Run: `.venv/bin/python -m pytest tests/test_service_plist_renderer.py -q`

Expected: 3 tests PASS.

- [ ] **Step 5: Commit the atomic writer**

```bash
git add scripts/render_service_plists.py tests/test_service_plist_renderer.py
git diff --cached --check
git commit -m "feat: add atomic plist writer"
```

### Task 3: Build Exact JavInfo, Backend, and Frontend Payloads

**Files:**
- Modify: `scripts/render_service_plists.py`
- Modify: `tests/test_service_plist_renderer.py`

- [ ] **Step 1: Add failing structured-payload tests**

Add tests that call `render_service_plists()` with temporary paths and assert parsed dictionaries, not XML strings:

```python
def test_renderer_preserves_dynamic_values_and_complete_service_shape(tmp_path, monkeypatch):
    config_path = tmp_path / "relative config & value.yaml"
    config_path.write_text(
        "javinfo:\n  supplement_worker_count: 99\n"
        "proxy:\n  enabled: true\n  mode: vless\n  singbox_port: 18888\n",
        encoding="utf-8",
    )
    outputs = [tmp_path / name for name in ("javinfo.plist", "backend.plist", "frontend.plist")]
    env = {
        "JAVHUB_DB_PASSWORD": "p&<word>",
        "JAVHUB_REDIS_URL": "redis://host/0?a=1&b=<two>",
        "JAVHUB_REDIS_PREFIX": "prefix<&>",
        "JAVHUB_PROXY_ADVERTISE_HOST": "proxy-host",
    }

    render_service_plists(
        javinfo_plist=outputs[0],
        backend_plist=outputs[1],
        frontend_plist=outputs[2],
        root_dir=tmp_path / "repo & root",
        javinfo_dir=tmp_path / "JavInfo <Api>",
        frontend_npm_bin=tmp_path / "bin & npm",
        config_path=config_path,
        env=env,
    )

    javinfo, backend, frontend = [plistlib.loads(path.read_bytes()) for path in outputs]
    assert javinfo["EnvironmentVariables"]["SUPPLEMENT_WORKER_COUNT"] == "16"
    assert javinfo["EnvironmentVariables"]["JAVINFO_SOURCE_PROXY_URL"] == "socks5://proxy-host:18888"
    assert backend["EnvironmentVariables"]["JAVHUB_CONFIG_PATH"] == str(config_path.resolve())
    assert backend["EnvironmentVariables"]["JAVHUB_PROXY_ADVERTISE_HOST"] == "proxy-host"
    assert backend["EnvironmentVariables"]["JAVHUB_DB_PASSWORD"] == "p&<word>"
    assert backend["EnvironmentVariables"]["JAVHUB_REDIS_URL"] == "redis://host/0?a=1&b=<two>"
    assert backend["RunAtLoad"] is True and backend["KeepAlive"] is True
    assert frontend["ProgramArguments"] == [str(tmp_path / "bin & npm"), "run", "preview", "--", "--host", "0.0.0.0", "--port", "5174"]
```

Add a parameterized test for invalid YAML, disabled/HTTP proxy modes, worker values, and VLESS ports `"bad"`, `0`, and `65536`. Add a cwd test that passes `Path("custom.yaml")`, changes to a directory outside the repository with `monkeypatch.chdir()`, and asserts the same resolved absolute path is both read and injected.

- [ ] **Step 2: Run only the new payload tests**

Run: `.venv/bin/python -m pytest tests/test_service_plist_renderer.py -q`

Expected: FAIL because `render_service_plists` is not defined.

- [ ] **Step 3: Add the renderer input model and normalization helpers**

```python
import argparse
import importlib.util

import yaml

JAVINFO_LABEL = "com.kongmei.javinfoapi"
BACKEND_LABEL = "com.kongmei.javhub.backend"
FRONTEND_LABEL = "com.kongmei.javhub.frontend"
SYSTEM_PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"


def normalize_config_path(value: str | Path) -> Path:
    path = Path(value).expanduser()
    return path.resolve(strict=False)


def load_service_config(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, UnicodeError, yaml.YAMLError):
        return {}
    return value if isinstance(value, dict) else {}


def bounded_worker_count(config_data: Mapping[str, Any]) -> int:
    try:
        value = int((config_data.get("javinfo") or {}).get("supplement_worker_count", 6))
    except (AttributeError, TypeError, ValueError):
        value = 6
    return max(1, min(16, value))


def resolve_proxy_url(root_dir: Path, proxy: Any, advertise_host: str) -> str:
    helper_path = (root_dir / "backend/modules/proxy_config.py").resolve(strict=False)
    spec = importlib.util.spec_from_file_location("_javhub_service_proxy_config", helper_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load proxy helper from {helper_path}")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    effective_proxy_url = getattr(helper, "effective_proxy_url", None)
    if not callable(effective_proxy_url):
        raise ImportError(f"proxy helper {helper_path} does not define effective_proxy_url")

    return effective_proxy_url(
        proxy if isinstance(proxy, Mapping) else {},
        advertise_host=advertise_host,
    )


def normalized_advertise_host(env: Mapping[str, str]) -> str:
    return str(env.get("JAVHUB_PROXY_ADVERTISE_HOST") or "").strip() or "127.0.0.1"


def environment_value(env: Mapping[str, str], key: str, default: str) -> str:
    return str(env.get(key) or default)
```

- [ ] **Step 4: Implement the three complete payload builders**

Use the exact existing labels, arguments, directories, ports, flags, and log paths. The public function must have this signature and call `write_plists_atomically(payloads)`:

```python
def render_service_plists(
    *,
    javinfo_plist: Path,
    backend_plist: Path,
    frontend_plist: Path,
    root_dir: Path,
    javinfo_dir: Path,
    frontend_npm_bin: Path,
    config_path: str | Path,
    env: Mapping[str, str],
) -> None:
    root_dir = Path(root_dir).resolve(strict=False)
    javinfo_dir = Path(javinfo_dir).resolve(strict=False)
    effective_config_path = normalize_config_path(config_path)
    config_data = load_service_config(effective_config_path)
    advertise_host = normalized_advertise_host(env)
    proxy_url = resolve_proxy_url(root_dir, config_data.get("proxy"), advertise_host)

    javinfo_environment = {
        "PATH": SYSTEM_PATH,
        "SERVER_PORT": "8080",
        "SUPPLEMENT_WORKER_COUNT": str(bounded_worker_count(config_data)),
    }
    if proxy_url:
        javinfo_environment["JAVINFO_SOURCE_PROXY_URL"] = proxy_url

    javinfo_payload = {
        "Label": JAVINFO_LABEL,
        "ProgramArguments": [str(javinfo_dir / "JavInfoApi")],
        "WorkingDirectory": str(javinfo_dir),
        "EnvironmentVariables": javinfo_environment,
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": str(javinfo_dir / "javinfoapi.launchd.log"),
        "StandardErrorPath": str(javinfo_dir / "javinfoapi.launchd.err.log"),
    }
    backend_payload = {
        "Label": BACKEND_LABEL,
        "ProgramArguments": [str(root_dir / ".venv/bin/uvicorn"), "main:app", "--host", "0.0.0.0", "--port", "18090"],
        "WorkingDirectory": str(root_dir / "backend"),
        "EnvironmentVariables": {
            "PATH": f"{root_dir}/.venv/bin:{SYSTEM_PATH}",
            "PYTHONUNBUFFERED": "1",
            "JAVHUB_CONFIG_PATH": str(effective_config_path),
            "JAVHUB_PROXY_ADVERTISE_HOST": normalized_advertise_host(env),
            "JAVHUB_DB_HOST": environment_value(env, "JAVHUB_DB_HOST", "localhost"),
            "JAVHUB_DB_PORT": environment_value(env, "JAVHUB_DB_PORT", "5432"),
            "JAVHUB_DB_USER": environment_value(env, "JAVHUB_DB_USER", "kongmei"),
            "JAVHUB_DB_PASSWORD": environment_value(env, "JAVHUB_DB_PASSWORD", ""),
            "JAVHUB_DB_NAME": environment_value(env, "JAVHUB_DB_NAME", "javhub"),
            "JAVHUB_CACHE_BACKEND": environment_value(env, "JAVHUB_CACHE_BACKEND", "redis"),
            "JAVHUB_REDIS_URL": environment_value(env, "JAVHUB_REDIS_URL", "redis://127.0.0.1:6379/0"),
            "JAVHUB_REDIS_PREFIX": environment_value(env, "JAVHUB_REDIS_PREFIX", "javhub-cache"),
        },
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": str(root_dir / "backend/javhub-backend.launchd.log"),
        "StandardErrorPath": str(root_dir / "backend/javhub-backend.launchd.err.log"),
    }
    frontend_payload = {
        "Label": FRONTEND_LABEL,
        "ProgramArguments": [str(frontend_npm_bin), "run", "preview", "--", "--host", "0.0.0.0", "--port", "5174"],
        "WorkingDirectory": str(root_dir / "frontend"),
        "EnvironmentVariables": {"PATH": SYSTEM_PATH},
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": str(root_dir / "javhub-frontend.launchd.log"),
        "StandardErrorPath": str(root_dir / "javhub-frontend.launchd.err.log"),
    }
    write_plists_atomically({
        Path(javinfo_plist): javinfo_payload,
        Path(backend_plist): backend_payload,
        Path(frontend_plist): frontend_payload,
    })
```

- [ ] **Step 5: Add an exact CLI and run its tests**

The CLI must require `--javinfo-plist`, `--backend-plist`, `--frontend-plist`, `--root-dir`, `--javinfo-dir`, `--frontend-npm-bin`, and `--config-path`:

```python
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--javinfo-plist", type=Path, required=True)
    parser.add_argument("--backend-plist", type=Path, required=True)
    parser.add_argument("--frontend-plist", type=Path, required=True)
    parser.add_argument("--root-dir", type=Path, required=True)
    parser.add_argument("--javinfo-dir", type=Path, required=True)
    parser.add_argument("--frontend-npm-bin", type=Path, required=True)
    parser.add_argument("--config-path", required=True)
    args = parser.parse_args(argv)
    render_service_plists(
        javinfo_plist=args.javinfo_plist,
        backend_plist=args.backend_plist,
        frontend_plist=args.frontend_plist,
        root_dir=args.root_dir,
        javinfo_dir=args.javinfo_dir,
        frontend_npm_bin=args.frontend_npm_bin,
        config_path=args.config_path,
        env=os.environ,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Run: `.venv/bin/python -m pytest tests/test_service_plist_renderer.py -q`

Expected: all renderer tests PASS.

- [ ] **Step 6: Commit the complete renderer**

```bash
git add scripts/render_service_plists.py tests/test_service_plist_renderer.py
git diff --cached --check
git commit -m "feat: render structured service plists"
```

### Task 4: Replace Shell Heredocs Without Changing Lifecycle Behavior

**Files:**
- Modify: `scripts/services.sh:61-279`
- Modify: `tests/test_services.py:77-173,3145-3212`

- [ ] **Step 1: Convert existing service integration assertions to parsed dictionaries**

Import `plistlib` in `tests/test_services.py`. Replace XML substring checks with assertions such as:

```python
payload = plistlib.loads(javinfo_plist.read_bytes())
assert payload["EnvironmentVariables"]["JAVINFO_SOURCE_PROXY_URL"] == "http://127.0.0.1:1082"
```

Add one integration test that sets `JAVHUB_CONFIG_PATH`, `JAVHUB_PROXY_ADVERTISE_HOST`, `JAVHUB_DB_PASSWORD`, and `NPM_BIN`, runs `render-plists`, parses all three outputs, and asserts the absolute config path, identical backend/JavInfo advertise host, metacharacter password, resolved npm path, labels, ports, and lifecycle flags.

Add an `ensure` failure test that makes the backend plist destination a directory, stubs `launchctl` to record calls, and asserts renderer failure exits nonzero without `bootstrap`, `bootout`, or `kickstart`.

- [ ] **Step 2: Run the integration tests against the old shell renderer**

Run: `.venv/bin/python -m pytest tests/test_services.py -q`

Expected: at least the backend config-path/metacharacter assertion FAILS; on non-macOS the file is explicitly skipped.

- [ ] **Step 3: Replace the heredoc body with one renderer invocation**

Delete `xml_escape()`, `javinfo_source_proxy_url()`, and `javinfo_worker_count()`. Preserve the pre-render snapshots and post-render `plutil`/`cmp` blocks. In `write_plists()`, invoke:

```bash
  "${PYTHON_BIN}" "${ROOT_DIR}/scripts/render_service_plists.py" \
    --javinfo-plist "${JAVINFO_PLIST}" \
    --backend-plist "${BACKEND_PLIST}" \
    --frontend-plist "${FRONTEND_PLIST}" \
    --root-dir "${ROOT_DIR}" \
    --javinfo-dir "${JAVINFO_DIR}" \
    --frontend-npm-bin "${FRONTEND_NPM_BIN}" \
    --config-path "${JAVHUB_CONFIG_PATH:-${ROOT_DIR}/config.yaml}"
```

- [ ] **Step 4: Run syntax, renderer, config, and integration tests**

Run: `bash -n scripts/services.sh`

Expected: exit 0.

Run: `.venv/bin/python -m pytest backend/test_proxy_config.py backend/test_config.py tests/test_service_plist_renderer.py tests/test_services.py -q`

Expected: all applicable tests PASS; macOS service tests are not skipped on the development machine.

- [ ] **Step 5: Commit shell integration**

```bash
git add scripts/services.sh tests/test_services.py
git diff --cached --check
git commit -m "fix: render launchagents from shared config"
```

### Task 5: Full and Live Verification

**Files:**
- Verify only; no planned source changes.

- [ ] **Step 1: Run static and focused verification from repository root**

```bash
.venv/bin/python -m py_compile backend/modules/proxy_config.py scripts/render_service_plists.py
bash -n scripts/services.sh
.venv/bin/python -m pytest backend/test_proxy_config.py backend/test_config.py tests/test_service_plist_renderer.py tests/test_services.py -q
git diff --check
```

Expected: every command exits 0, with zero test failures.

- [ ] **Step 2: Run the complete Python suite**

Run: `.venv/bin/python -m pytest -q`

Expected: zero failures.

- [ ] **Step 3: Install/update services through the project helper**

Run: `scripts/services.sh ensure`

Expected: renderer and `plutil` succeed; only semantically changed LaunchAgents restart.

Run: `scripts/services.sh status`

Expected: JavInfo `8080`, backend `18090`, and frontend `5174` report healthy.

- [ ] **Step 4: Validate installed plists and idempotence**

```bash
plutil -lint "$HOME/Library/LaunchAgents/com.kongmei.javinfoapi.plist" "$HOME/Library/LaunchAgents/com.kongmei.javhub.backend.plist" "$HOME/Library/LaunchAgents/com.kongmei.javhub.frontend.plist"
scripts/services.sh ensure
scripts/services.sh status
```

Expected: all plists lint clean; the second `ensure` leaves healthy process IDs unchanged.

- [ ] **Step 5: Review final scope before integration**

Run: `git status --short`

Run: `git diff --check`

Run: `git log -4 --oneline`

Expected: only planned files differ from the plan's starting point, no whitespace errors exist, and the three task commits are present.
