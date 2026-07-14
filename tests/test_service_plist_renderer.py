import os
import plistlib
import stat
import subprocess
import sys
import types
from pathlib import Path
from typing import get_type_hints

import pytest

import scripts.render_service_plists as renderer
from scripts.render_service_plists import write_plists_atomically


def _write_plist(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        plistlib.dumps(payload, fmt=plistlib.FMT_XML, sort_keys=True)
    )


def _snapshot(path: Path) -> tuple[bytes, dict]:
    contents = path.read_bytes()
    return contents, plistlib.loads(contents)


def _assert_no_temp_files(directory: Path) -> None:
    assert list(directory.glob(".*.tmp")) == []


def _install_proxy_helper(root_dir: Path) -> None:
    repository_root = Path(__file__).resolve().parents[1]
    source = repository_root / "backend" / "modules" / "proxy_config.py"
    destination = root_dir / "backend" / "modules" / "proxy_config.py"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source.read_bytes())


def test_write_plists_is_deterministic_round_trippable_and_world_readable(tmp_path):
    target = tmp_path / "LaunchAgents" / "example.plist"
    payload = {
        "Enabled": True,
        "Label": "com.example.a&b<c",
        "ProgramArguments": ["/bin/echo", "fish & chips < tacos"],
    }

    write_plists_atomically({target: payload})
    first_contents = target.read_bytes()
    write_plists_atomically({target: payload})

    assert target.read_bytes() == first_contents
    assert plistlib.loads(first_contents) == payload
    assert stat.S_IMODE(target.stat().st_mode) == 0o644


def test_serialization_failure_leaves_all_existing_targets_unchanged(tmp_path):
    first = tmp_path / "first.plist"
    second = tmp_path / "second.plist"
    _write_plist(first, {"Label": "old.first", "Enabled": False})
    _write_plist(second, {"Label": "old.second", "Enabled": True})
    old_first = _snapshot(first)
    old_second = _snapshot(second)
    replace_calls = []

    with pytest.raises(TypeError):
        write_plists_atomically(
            {
                first: {"Label": "new.first"},
                second: {"Label": "new.second", "Invalid": object()},
            },
            replace=lambda source, destination: replace_calls.append(
                (source, destination)
            ),
        )

    assert _snapshot(first) == old_first
    assert _snapshot(second) == old_second
    assert replace_calls == []
    _assert_no_temp_files(tmp_path)


def test_second_mkstemp_failure_cleans_temps_without_replacing_targets(
    tmp_path, monkeypatch
):
    first = tmp_path / "first.plist"
    second = tmp_path / "second.plist"
    _write_plist(first, {"Label": "old.first"})
    _write_plist(second, {"Label": "old.second"})
    old_first = _snapshot(first)
    old_second = _snapshot(second)
    real_mkstemp = renderer.tempfile.mkstemp
    mkstemp_calls = 0
    replace_calls = []

    def fail_second_mkstemp(*args, **kwargs):
        nonlocal mkstemp_calls
        mkstemp_calls += 1
        if mkstemp_calls == 2:
            raise OSError("injected mkstemp failure")
        return real_mkstemp(*args, **kwargs)

    monkeypatch.setattr(renderer.tempfile, "mkstemp", fail_second_mkstemp)

    with pytest.raises(OSError, match="injected mkstemp failure"):
        write_plists_atomically(
            {
                first: {"Label": "new.first"},
                second: {"Label": "new.second"},
            },
            replace=lambda source, destination: replace_calls.append(
                (source, destination)
            ),
        )

    assert _snapshot(first) == old_first
    assert _snapshot(second) == old_second
    assert replace_calls == []
    _assert_no_temp_files(tmp_path)


def test_second_replace_failure_leaves_only_complete_old_or_new_plists(tmp_path):
    first = tmp_path / "first.plist"
    second = tmp_path / "second.plist"
    _write_plist(first, {"Label": "old.first", "Enabled": False})
    _write_plist(second, {"Label": "old.second", "Enabled": False})
    old_second = _snapshot(second)
    new_first = {"Label": "new.first", "Enabled": True}
    new_second = {"Label": "new.second", "Enabled": True}
    replace_calls = 0

    def fail_second_replace(source, destination):
        nonlocal replace_calls
        replace_calls += 1
        if replace_calls == 2:
            raise OSError("injected replace failure")
        os.replace(source, destination)

    with pytest.raises(OSError, match="injected replace failure"):
        write_plists_atomically(
            {first: new_first, second: new_second}, replace=fail_second_replace
        )

    expected_first = plistlib.dumps(
        new_first, fmt=plistlib.FMT_XML, sort_keys=True
    )
    assert first.read_bytes() == expected_first
    assert plistlib.loads(first.read_bytes()) == new_first
    assert _snapshot(second) == old_second
    _assert_no_temp_files(tmp_path)


def test_fsync_failure_cleans_all_temps_before_any_replace(tmp_path, monkeypatch):
    first = tmp_path / "first.plist"
    second = tmp_path / "second.plist"
    _write_plist(first, {"Label": "old.first"})
    _write_plist(second, {"Label": "old.second"})
    old_first = _snapshot(first)
    old_second = _snapshot(second)
    real_fsync = renderer.os.fsync
    fsync_calls = 0
    replace_calls = []

    def fail_second_fsync(fd):
        nonlocal fsync_calls
        fsync_calls += 1
        if fsync_calls == 2:
            raise OSError("injected fsync failure")
        real_fsync(fd)

    monkeypatch.setattr(renderer.os, "fsync", fail_second_fsync)

    with pytest.raises(OSError, match="injected fsync failure"):
        write_plists_atomically(
            {
                first: {"Label": "new.first"},
                second: {"Label": "new.second"},
            },
            replace=lambda source, destination: replace_calls.append(
                (source, destination)
            ),
        )

    assert _snapshot(first) == old_first
    assert _snapshot(second) == old_second
    assert replace_calls == []
    _assert_no_temp_files(tmp_path)


def test_cleanup_failure_preserves_primary_error_and_attempts_every_temp(
    tmp_path, monkeypatch
):
    first = tmp_path / "first.plist"
    second = tmp_path / "second.plist"
    _write_plist(first, {"Label": "old.first"})
    _write_plist(second, {"Label": "old.second"})
    old_first = _snapshot(first)
    old_second = _snapshot(second)
    real_fsync = renderer.os.fsync
    real_unlink = renderer.Path.unlink
    fsync_calls = 0
    cleanup_attempts = []
    replace_calls = []

    def fail_second_fsync(fd):
        nonlocal fsync_calls
        fsync_calls += 1
        if fsync_calls == 2:
            raise OSError("injected fsync failure")
        real_fsync(fd)

    def fail_first_temp_unlink(path, *args, **kwargs):
        if path.name.startswith(".") and path.name.endswith(".tmp"):
            cleanup_attempts.append(path)
            if len(cleanup_attempts) == 1:
                raise OSError("injected temp cleanup failure")
        return real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(renderer.os, "fsync", fail_second_fsync)
    monkeypatch.setattr(renderer.Path, "unlink", fail_first_temp_unlink)

    with pytest.raises(OSError, match="injected fsync failure") as error:
        write_plists_atomically(
            {
                first: {"Label": "new.first"},
                second: {"Label": "new.second"},
            },
            replace=lambda source, destination: replace_calls.append(
                (source, destination)
            ),
        )

    notes = "\n".join(getattr(error.value, "__notes__", ()))
    assert "injected temp cleanup failure" in notes
    assert len(cleanup_attempts) == 2
    assert str(cleanup_attempts[0]) in notes
    assert set(tmp_path.glob(".*.tmp")) == {cleanup_attempts[0]}
    assert not cleanup_attempts[1].exists()
    assert _snapshot(first) == old_first
    assert _snapshot(second) == old_second
    assert replace_calls == []

    real_unlink(cleanup_attempts[0])


def _read_rendered_plists(
    javinfo_plist: Path,
    backend_plist: Path,
    frontend_plist: Path,
) -> tuple[dict, dict, dict]:
    return tuple(
        plistlib.loads(path.read_bytes())
        for path in (javinfo_plist, backend_plist, frontend_plist)
    )


def _render_from_config_text(
    tmp_path: Path,
    config_text: str,
    *,
    env: dict[str, str] | None = None,
) -> tuple[dict, dict, dict]:
    root_dir = tmp_path / "project"
    _install_proxy_helper(root_dir)
    javinfo_dir = tmp_path / "javinfo"
    config_path = tmp_path / "config.yaml"
    config_path.write_text(config_text, encoding="utf-8")
    javinfo_plist = tmp_path / "plists" / "javinfo.plist"
    backend_plist = tmp_path / "plists" / "backend.plist"
    frontend_plist = tmp_path / "plists" / "frontend.plist"

    renderer.render_service_plists(
        javinfo_plist=javinfo_plist,
        backend_plist=backend_plist,
        frontend_plist=frontend_plist,
        root_dir=root_dir,
        javinfo_dir=javinfo_dir,
        frontend_npm_bin=tmp_path / "node" / "npm",
        config_path=config_path,
        env=env or {},
    )

    return _read_rendered_plists(
        javinfo_plist,
        backend_plist,
        frontend_plist,
    )


def test_render_service_plists_round_trips_complete_payloads_and_modes(tmp_path):
    root_dir = tmp_path / 'Project & <root> "quoted"'
    javinfo_dir = tmp_path / 'JavInfo & <api> "quoted"'
    frontend_npm_bin = tmp_path / 'Node & <bin> "quoted"' / "npm"
    config_path = root_dir / 'config & <prod> "quoted".yaml'
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        """\
proxy:
  enabled: true
  mode: vless
  singbox_port: 18888
javinfo:
  supplement_worker_count: 99
""",
        encoding="utf-8",
    )
    env = {
        "JAVHUB_PROXY_ADVERTISE_HOST": "  proxy.example.test  ",
        "JAVHUB_DB_HOST": 'db & <host> "quoted"',
        "JAVHUB_DB_PORT": "6543",
        "JAVHUB_DB_USER": 'user & <name> "quoted"',
        "JAVHUB_DB_PASSWORD": 'password & <secret> "quoted"',
        "JAVHUB_DB_NAME": 'database & <name> "quoted"',
        "JAVHUB_CACHE_BACKEND": "redis",
        "JAVHUB_REDIS_URL": 'redis://cache.test:6379/0?x=1&y=<two>&q="quoted"',
        "JAVHUB_REDIS_PREFIX": 'prefix & <cache> "quoted"',
    }
    javinfo_plist = tmp_path / "LaunchAgents" / "javinfo.plist"
    backend_plist = tmp_path / "LaunchAgents" / "backend.plist"
    frontend_plist = tmp_path / "LaunchAgents" / "frontend.plist"
    _install_proxy_helper(root_dir)

    renderer.render_service_plists(
        javinfo_plist=javinfo_plist,
        backend_plist=backend_plist,
        frontend_plist=frontend_plist,
        root_dir=root_dir,
        javinfo_dir=javinfo_dir,
        frontend_npm_bin=frontend_npm_bin,
        config_path=config_path,
        env=env,
    )

    resolved_root = root_dir.resolve(strict=False)
    resolved_javinfo = javinfo_dir.resolve(strict=False)
    resolved_config = config_path.resolve(strict=False)
    expected_javinfo = {
        "Label": "com.kongmei.javinfoapi",
        "ProgramArguments": [str(resolved_javinfo / "JavInfoApi")],
        "WorkingDirectory": str(resolved_javinfo),
        "EnvironmentVariables": {
            "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
            "SERVER_PORT": "8080",
            "SUPPLEMENT_WORKER_COUNT": "16",
            "JAVINFO_SOURCE_PROXY_URL": "socks5://proxy.example.test:18888",
        },
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": str(resolved_javinfo / "javinfoapi.launchd.log"),
        "StandardErrorPath": str(
            resolved_javinfo / "javinfoapi.launchd.err.log"
        ),
    }
    expected_backend = {
        "Label": "com.kongmei.javhub.backend",
        "ProgramArguments": [
            str(resolved_root / ".venv" / "bin" / "uvicorn"),
            "main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "18090",
        ],
        "WorkingDirectory": str(resolved_root / "backend"),
        "EnvironmentVariables": {
            "PATH": (
                f"{resolved_root}/.venv/bin:"
                "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
            ),
            "PYTHONUNBUFFERED": "1",
            "JAVHUB_CONFIG_PATH": str(resolved_config),
            "JAVHUB_PROXY_ADVERTISE_HOST": "proxy.example.test",
            "JAVHUB_DB_HOST": env["JAVHUB_DB_HOST"],
            "JAVHUB_DB_PORT": env["JAVHUB_DB_PORT"],
            "JAVHUB_DB_USER": env["JAVHUB_DB_USER"],
            "JAVHUB_DB_PASSWORD": env["JAVHUB_DB_PASSWORD"],
            "JAVHUB_DB_NAME": env["JAVHUB_DB_NAME"],
            "JAVHUB_CACHE_BACKEND": env["JAVHUB_CACHE_BACKEND"],
            "JAVHUB_REDIS_URL": env["JAVHUB_REDIS_URL"],
            "JAVHUB_REDIS_PREFIX": env["JAVHUB_REDIS_PREFIX"],
        },
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": str(
            resolved_root / "backend" / "javhub-backend.launchd.log"
        ),
        "StandardErrorPath": str(
            resolved_root / "backend" / "javhub-backend.launchd.err.log"
        ),
    }
    expected_frontend = {
        "Label": "com.kongmei.javhub.frontend",
        "ProgramArguments": [
            str(frontend_npm_bin),
            "run",
            "preview",
            "--",
            "--host",
            "0.0.0.0",
            "--port",
            "5174",
        ],
        "WorkingDirectory": str(resolved_root / "frontend"),
        "EnvironmentVariables": {
            "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
        },
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": str(resolved_root / "javhub-frontend.launchd.log"),
        "StandardErrorPath": str(
            resolved_root / "javhub-frontend.launchd.err.log"
        ),
    }

    assert _read_rendered_plists(
        javinfo_plist,
        backend_plist,
        frontend_plist,
    ) == (expected_javinfo, expected_backend, expected_frontend)
    for path in (javinfo_plist, backend_plist, frontend_plist):
        assert stat.S_IMODE(path.stat().st_mode) == 0o644


def test_render_service_plists_config_path_annotation_accepts_str_and_path():
    annotations = get_type_hints(renderer.render_service_plists)

    assert annotations["config_path"] == str | Path


@pytest.mark.parametrize(
    ("proxy_yaml", "expected_url"),
    [
        (
            "enabled: false\nmode: vless\nsingbox_port: 18888",
            None,
        ),
        (
            "enabled: true\nmode: http\n"
            "http_url: '  http://primary.example:8080/path  '\n"
            "https_url: https://fallback.example:8443",
            "http://primary.example:8080/path",
        ),
        (
            "enabled: true\nmode: http\nhttp_url: '   '\n"
            "https_url: '  https://fallback.example:8443/path  '",
            "https://fallback.example:8443/path",
        ),
        (
            "enabled: true\nmode: vless\nsingbox_port: bad",
            "socks5://proxy.internal:17890",
        ),
        (
            "enabled: true\nmode: vless\nsingbox_port: 0",
            "socks5://proxy.internal:17890",
        ),
        (
            "enabled: true\nmode: vless\nsingbox_port: -1",
            "socks5://proxy.internal:17890",
        ),
        (
            "enabled: true\nmode: vless\nsingbox_port: 65536",
            "socks5://proxy.internal:17890",
        ),
        (
            "enabled: true\nmode: vless\nsingbox_port: true",
            "socks5://proxy.internal:17890",
        ),
        (
            "enabled: true\nmode: vless\nsingbox_port: ''",
            "socks5://proxy.internal:17890",
        ),
        (
            "enabled: true\nmode: vless\nsingbox_port: null",
            "socks5://proxy.internal:17890",
        ),
        (
            "enabled: true\nmode: http\nhttp_url: ''\nhttps_url: ''",
            None,
        ),
    ],
    ids=[
        "disabled",
        "http",
        "blank-http-falls-back-to-https",
        "vless-bad-port",
        "vless-zero-port",
        "vless-negative-port",
        "vless-too-large-port",
        "vless-bool-port",
        "vless-blank-port",
        "vless-null-port",
        "enabled-without-url",
    ],
)
def test_render_service_plists_normalizes_proxy_modes_and_ports(
    tmp_path,
    proxy_yaml,
    expected_url,
):
    javinfo, backend, _ = _render_from_config_text(
        tmp_path,
        f"proxy:\n  {proxy_yaml.replace(chr(10), chr(10) + '  ')}\n",
        env={"JAVHUB_PROXY_ADVERTISE_HOST": "  proxy.internal  "},
    )

    javinfo_env = javinfo["EnvironmentVariables"]
    if expected_url is None:
        assert "JAVINFO_SOURCE_PROXY_URL" not in javinfo_env
    else:
        assert javinfo_env["JAVINFO_SOURCE_PROXY_URL"] == expected_url
    assert (
        backend["EnvironmentVariables"]["JAVHUB_PROXY_ADVERTISE_HOST"]
        == "proxy.internal"
    )


@pytest.mark.parametrize(
    "config_text",
    [
        "proxy: [unterminated\n",
        "- proxy\n- javinfo\n",
    ],
    ids=["invalid-yaml", "non-dict-yaml"],
)
def test_render_service_plists_treats_invalid_or_non_dict_yaml_as_empty(
    tmp_path,
    config_text,
):
    javinfo, _, _ = _render_from_config_text(tmp_path, config_text)

    assert javinfo["EnvironmentVariables"] == {
        "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        "SERVER_PORT": "8080",
        "SUPPLEMENT_WORKER_COUNT": "6",
    }


def test_missing_config_path_renders_default_service_values(tmp_path):
    javinfo_plist = tmp_path / "javinfo.plist"
    backend_plist = tmp_path / "backend.plist"
    frontend_plist = tmp_path / "frontend.plist"
    root_dir = tmp_path / "project"
    _install_proxy_helper(root_dir)

    renderer.render_service_plists(
        javinfo_plist=javinfo_plist,
        backend_plist=backend_plist,
        frontend_plist=frontend_plist,
        root_dir=root_dir,
        javinfo_dir=tmp_path / "javinfo",
        frontend_npm_bin=tmp_path / "npm",
        config_path=tmp_path / "missing.yaml",
        env={},
    )

    javinfo, _, _ = _read_rendered_plists(
        javinfo_plist, backend_plist, frontend_plist
    )
    assert javinfo["EnvironmentVariables"]["SUPPLEMENT_WORKER_COUNT"] == "6"
    assert "JAVINFO_SOURCE_PROXY_URL" not in javinfo["EnvironmentVariables"]


def test_unreadable_config_path_renders_defaults(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("javinfo:\n  supplement_worker_count: 12\n")
    real_read_text = renderer.Path.read_text

    def fail_config_read(path, *args, **kwargs):
        if path == config_path:
            raise PermissionError("injected unreadable config")
        return real_read_text(path, *args, **kwargs)

    monkeypatch.setattr(renderer.Path, "read_text", fail_config_read)
    javinfo, _, _ = _render_from_config_text(tmp_path, "{}\n")

    assert javinfo["EnvironmentVariables"]["SUPPLEMENT_WORKER_COUNT"] == "6"


def test_unexpected_yaml_failure_propagates_without_replacing_targets(
    tmp_path, monkeypatch
):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("{}\n", encoding="utf-8")
    destinations = [tmp_path / name for name in ("javinfo.plist", "backend.plist", "frontend.plist")]
    snapshots = []
    for index, destination in enumerate(destinations):
        _write_plist(destination, {"old": index})
        snapshots.append(destination.read_bytes())

    def fail_unexpectedly(_text):
        raise RuntimeError("injected yaml internals failure")

    monkeypatch.setattr(renderer.yaml, "safe_load", fail_unexpectedly)

    with pytest.raises(RuntimeError, match="injected yaml internals failure"):
        renderer.render_service_plists(
            javinfo_plist=destinations[0],
            backend_plist=destinations[1],
            frontend_plist=destinations[2],
            root_dir=tmp_path / "project",
            javinfo_dir=tmp_path / "javinfo",
            frontend_npm_bin=tmp_path / "npm",
            config_path=config_path,
            env={},
        )

    assert [path.read_bytes() for path in destinations] == snapshots


@pytest.mark.parametrize(
    ("javinfo_yaml", "expected_workers"),
    [
        ("{}", "6"),
        ("javinfo:\n  supplement_worker_count: bad", "6"),
        ("javinfo:\n  supplement_worker_count: 0", "1"),
        ("javinfo:\n  supplement_worker_count: 99", "16"),
    ],
    ids=["missing", "bad", "minimum", "maximum"],
)
def test_render_service_plists_bounds_worker_count(
    tmp_path,
    javinfo_yaml,
    expected_workers,
):
    javinfo, _, _ = _render_from_config_text(tmp_path, f"{javinfo_yaml}\n")

    assert (
        javinfo["EnvironmentVariables"]["SUPPLEMENT_WORKER_COUNT"]
        == expected_workers
    )


def test_vless_proxy_ignores_stale_http_fields(tmp_path):
    javinfo, _, _ = _render_from_config_text(
        tmp_path,
        """\
proxy:
  enabled: true
  mode: vless
  singbox_port: 19000
  http_url: http://stale.example:8080
  https_url: https://stale.example:8443
""",
        env={"JAVHUB_PROXY_ADVERTISE_HOST": "vless.example"},
    )
    assert (
        javinfo["EnvironmentVariables"]["JAVINFO_SOURCE_PROXY_URL"]
        == "socks5://vless.example:19000"
    )


def test_proxy_helper_is_loaded_from_root_without_sys_path_or_cache_leakage(
    tmp_path, monkeypatch
):
    repository_root = Path(__file__).resolve().parents[1]
    isolated_root = tmp_path / "isolated-project"
    helper_path = isolated_root / "backend" / "modules" / "proxy_config.py"
    helper_path.parent.mkdir(parents=True)
    helper_path.write_bytes(
        (repository_root / "backend" / "modules" / "proxy_config.py").read_bytes()
    )
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "proxy:\n  enabled: true\n  mode: vless\n  singbox_port: 19001\n",
        encoding="utf-8",
    )
    fake_module = types.ModuleType("modules.proxy_config")
    fake_module.effective_proxy_url = lambda *_args, **_kwargs: "malicious://cached"
    monkeypatch.setitem(sys.modules, "modules.proxy_config", fake_module)
    original_sys_path = list(sys.path)
    javinfo_plist = tmp_path / "javinfo.plist"
    backend_plist = tmp_path / "backend.plist"
    frontend_plist = tmp_path / "frontend.plist"

    renderer.render_service_plists(
        javinfo_plist=javinfo_plist,
        backend_plist=backend_plist,
        frontend_plist=frontend_plist,
        root_dir=isolated_root,
        javinfo_dir=tmp_path / "javinfo",
        frontend_npm_bin=tmp_path / "npm",
        config_path=config_path,
        env={"JAVHUB_PROXY_ADVERTISE_HOST": "isolated.example"},
    )

    javinfo, _, _ = _read_rendered_plists(
        javinfo_plist, backend_plist, frontend_plist
    )
    assert (
        javinfo["EnvironmentVariables"]["JAVINFO_SOURCE_PROXY_URL"]
        == "socks5://isolated.example:19001"
    )
    assert sys.path == original_sys_path


def test_relative_config_path_is_read_from_renderer_cwd_and_injected_absolute(
    tmp_path,
    monkeypatch,
):
    outside = tmp_path / "outside"
    outside.mkdir()
    config_path = outside / "custom.yaml"
    config_path.write_text(
        """\
proxy:
  enabled: true
  mode: vless
  singbox_port: 18889
javinfo:
  supplement_worker_count: 7
""",
        encoding="utf-8",
    )
    monkeypatch.chdir(outside)
    root_dir = tmp_path / "project"
    _install_proxy_helper(root_dir)
    javinfo_plist = tmp_path / "javinfo.plist"
    backend_plist = tmp_path / "backend.plist"
    frontend_plist = tmp_path / "frontend.plist"

    renderer.render_service_plists(
        javinfo_plist=javinfo_plist,
        backend_plist=backend_plist,
        frontend_plist=frontend_plist,
        root_dir=root_dir,
        javinfo_dir=tmp_path / "javinfo",
        frontend_npm_bin=tmp_path / "npm",
        config_path="custom.yaml",
        env={"JAVHUB_PROXY_ADVERTISE_HOST": "  outside.example  "},
    )

    javinfo, backend, _ = _read_rendered_plists(
        javinfo_plist,
        backend_plist,
        frontend_plist,
    )
    assert javinfo["EnvironmentVariables"]["SUPPLEMENT_WORKER_COUNT"] == "7"
    assert (
        javinfo["EnvironmentVariables"]["JAVINFO_SOURCE_PROXY_URL"]
        == "socks5://outside.example:18889"
    )
    assert backend["EnvironmentVariables"]["JAVHUB_CONFIG_PATH"] == str(
        config_path.resolve(strict=False)
    )
    assert (
        backend["EnvironmentVariables"]["JAVHUB_PROXY_ADVERTISE_HOST"]
        == "outside.example"
    )


def test_tilde_config_path_is_read_and_injected_from_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    config_path = home / "custom.yaml"
    config_path.write_text("javinfo:\n  supplement_worker_count: 9\n", encoding="utf-8")
    monkeypatch.setenv("HOME", str(home))
    javinfo_plist = tmp_path / "javinfo.plist"
    backend_plist = tmp_path / "backend.plist"
    frontend_plist = tmp_path / "frontend.plist"
    root_dir = tmp_path / "project"
    _install_proxy_helper(root_dir)

    renderer.render_service_plists(
        javinfo_plist=javinfo_plist,
        backend_plist=backend_plist,
        frontend_plist=frontend_plist,
        root_dir=root_dir,
        javinfo_dir=tmp_path / "javinfo",
        frontend_npm_bin=tmp_path / "npm",
        config_path="~/custom.yaml",
        env={},
    )

    javinfo, backend, _ = _read_rendered_plists(
        javinfo_plist, backend_plist, frontend_plist
    )
    assert javinfo["EnvironmentVariables"]["SUPPLEMENT_WORKER_COUNT"] == "9"
    assert backend["EnvironmentVariables"]["JAVHUB_CONFIG_PATH"] == str(config_path)


def test_empty_environment_uses_complete_backend_defaults_and_vless_host(tmp_path):
    blank_env = {
        key: ""
        for key in (
            "JAVHUB_PROXY_ADVERTISE_HOST",
            "JAVHUB_DB_HOST",
            "JAVHUB_DB_PORT",
            "JAVHUB_DB_USER",
            "JAVHUB_DB_PASSWORD",
            "JAVHUB_DB_NAME",
            "JAVHUB_CACHE_BACKEND",
            "JAVHUB_REDIS_URL",
            "JAVHUB_REDIS_PREFIX",
        )
    }
    javinfo, backend, _ = _render_from_config_text(
        tmp_path,
        "proxy:\n  enabled: true\n  mode: vless\n  singbox_port: 18888\n",
        env=blank_env,
    )
    root_dir = (tmp_path / "project").resolve(strict=False)
    config_path = (tmp_path / "config.yaml").resolve(strict=False)

    assert (
        javinfo["EnvironmentVariables"]["JAVINFO_SOURCE_PROXY_URL"]
        == "socks5://127.0.0.1:18888"
    )
    assert backend["EnvironmentVariables"] == {
        "PATH": f"{root_dir}/.venv/bin:{renderer.SYSTEM_PATH}",
        "PYTHONUNBUFFERED": "1",
        "JAVHUB_CONFIG_PATH": str(config_path),
        "JAVHUB_PROXY_ADVERTISE_HOST": "127.0.0.1",
        "JAVHUB_DB_HOST": "localhost",
        "JAVHUB_DB_PORT": "5432",
        "JAVHUB_DB_USER": "kongmei",
        "JAVHUB_DB_PASSWORD": "",
        "JAVHUB_DB_NAME": "javhub",
        "JAVHUB_CACHE_BACKEND": "redis",
        "JAVHUB_REDIS_URL": "redis://127.0.0.1:6379/0",
        "JAVHUB_REDIS_PREFIX": "javhub-cache",
    }


def test_main_requires_all_cli_arguments():
    complete = [
        "--javinfo-plist", "javinfo.plist",
        "--backend-plist", "backend.plist",
        "--frontend-plist", "frontend.plist",
        "--root-dir", "project",
        "--javinfo-dir", "javinfo",
        "--frontend-npm-bin", "npm",
        "--config-path", "config.yaml",
    ]
    for index in range(0, len(complete), 2):
        incomplete = complete[:index] + complete[index + 2 :]
        with pytest.raises(SystemExit) as error:
            renderer.main(incomplete)
        assert error.value.code == 2


def test_main_renders_all_three_cli_destinations(tmp_path, monkeypatch):
    root_dir = tmp_path / "cli-project"
    _install_proxy_helper(root_dir)
    javinfo_dir = tmp_path / "cli-javinfo"
    frontend_npm_bin = tmp_path / "cli-node" / "npm"
    config_path = tmp_path / "cli-config.yaml"
    config_path.write_text(
        "javinfo:\n  supplement_worker_count: 11\n",
        encoding="utf-8",
    )
    javinfo_plist = tmp_path / "cli-plists" / "javinfo.plist"
    backend_plist = tmp_path / "cli-plists" / "backend.plist"
    frontend_plist = tmp_path / "cli-plists" / "frontend.plist"
    monkeypatch.setenv("JAVHUB_PROXY_ADVERTISE_HOST", "  cli.example  ")

    result = renderer.main(
        [
            "--javinfo-plist",
            str(javinfo_plist),
            "--backend-plist",
            str(backend_plist),
            "--frontend-plist",
            str(frontend_plist),
            "--root-dir",
            str(root_dir),
            "--javinfo-dir",
            str(javinfo_dir),
            "--frontend-npm-bin",
            str(frontend_npm_bin),
            "--config-path",
            str(config_path),
        ]
    )

    javinfo, backend, frontend = _read_rendered_plists(
        javinfo_plist,
        backend_plist,
        frontend_plist,
    )
    assert result == 0
    assert javinfo["Label"] == "com.kongmei.javinfoapi"
    assert javinfo["ProgramArguments"] == [
        str(javinfo_dir.resolve(strict=False) / "JavInfoApi")
    ]
    assert javinfo["EnvironmentVariables"]["SUPPLEMENT_WORKER_COUNT"] == "11"
    assert backend["Label"] == "com.kongmei.javhub.backend"
    assert backend["WorkingDirectory"] == str(
        root_dir.resolve(strict=False) / "backend"
    )
    assert backend["EnvironmentVariables"]["JAVHUB_CONFIG_PATH"] == str(
        config_path.resolve(strict=False)
    )
    assert frontend["Label"] == "com.kongmei.javhub.frontend"
    assert frontend["ProgramArguments"][0] == str(frontend_npm_bin)


def test_script_entrypoint_works_outside_repo_without_pythonpath(tmp_path):
    repository_root = Path(__file__).resolve().parents[1]
    script_path = repository_root / "scripts" / "render_service_plists.py"
    outside = tmp_path / "outside"
    outside.mkdir()
    config_path = tmp_path / "cli-config.yaml"
    config_path.write_text(
        "proxy:\n  enabled: true\n  mode: vless\n  singbox_port: 18892\n",
        encoding="utf-8",
    )
    javinfo_plist = tmp_path / "plists" / "javinfo.plist"
    backend_plist = tmp_path / "plists" / "backend.plist"
    frontend_plist = tmp_path / "plists" / "frontend.plist"
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.update(
        {
            "PYTHONNOUSERSITE": "1",
            "JAVHUB_PROXY_ADVERTISE_HOST": "  cli-isolated.example  ",
            "JAVHUB_DB_PASSWORD": "cli & <password>",
        }
    )

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--javinfo-plist", str(javinfo_plist),
            "--backend-plist", str(backend_plist),
            "--frontend-plist", str(frontend_plist),
            "--root-dir", str(repository_root),
            "--javinfo-dir", str(tmp_path / "javinfo"),
            "--frontend-npm-bin", str(tmp_path / "npm"),
            "--config-path", str(config_path),
        ],
        cwd=outside,
        env=env,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    javinfo, backend, frontend = _read_rendered_plists(
        javinfo_plist, backend_plist, frontend_plist
    )
    assert (
        javinfo["EnvironmentVariables"]["JAVINFO_SOURCE_PROXY_URL"]
        == "socks5://cli-isolated.example:18892"
    )
    assert backend["EnvironmentVariables"]["JAVHUB_PROXY_ADVERTISE_HOST"] == "cli-isolated.example"
    assert backend["EnvironmentVariables"]["JAVHUB_DB_PASSWORD"] == "cli & <password>"
    assert backend["EnvironmentVariables"]["JAVHUB_CONFIG_PATH"] == str(config_path)
    assert frontend["Label"] == renderer.FRONTEND_LABEL
