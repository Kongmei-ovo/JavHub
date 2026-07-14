"""Deterministic, per-file atomic property-list writing utilities."""

from __future__ import annotations

import argparse
import importlib.util
import os
import plistlib
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import yaml


JAVINFO_LABEL = "com.kongmei.javinfoapi"
BACKEND_LABEL = "com.kongmei.javhub.backend"
FRONTEND_LABEL = "com.kongmei.javhub.frontend"
SYSTEM_PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

_CleanupFailure = tuple[str, OSError]


def _report_cleanup_failures(
    failures: list[_CleanupFailure],
    *,
    primary: BaseException | None = None,
) -> None:
    if not failures:
        return

    if primary is not None:
        for note, _ in failures:
            primary.add_note(note)
        return

    first_note, first_error = failures[0]
    first_error.add_note(first_note)
    for note, _ in failures[1:]:
        first_error.add_note(note)
    raise first_error


def _cleanup_temporary_paths(paths: list[Path]) -> list[_CleanupFailure]:
    failures: list[_CleanupFailure] = []
    for path in paths:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        except OSError as error:
            failures.append(
                (
                    "temporary plist cleanup failed for "
                    f"{path}: {type(error).__name__}: {error}",
                    error,
                )
            )
    return failures


def write_plists_atomically(
    payloads: Mapping[Path, dict[str, Any]],
    *,
    replace: Callable[[str | Path, str | Path], None] = os.replace,
) -> None:
    """Write deterministic XML plists, replacing each destination atomically.

    Serialization and parsing validation happen for every payload before any
    filesystem changes. All temporary files are then made durable before the
    first destination is replaced. A failure during replacement may leave a
    mixture of complete old and new files, but never a partially written plist.
    """

    serialized: list[tuple[Path, bytes]] = []
    for target, payload in payloads.items():
        contents = plistlib.dumps(
            payload,
            fmt=plistlib.FMT_XML,
            sort_keys=True,
        )
        serialized.append((Path(target), contents))

    for _, contents in serialized:
        plistlib.loads(contents)

    temporary_paths: list[Path] = []
    prepared: list[tuple[Path, Path]] = []

    try:
        for target, contents in serialized:
            target.parent.mkdir(parents=True, exist_ok=True)

            fd: int | None = None
            temp_name: str | None = None
            is_tracked = False
            try:
                fd, temp_name = tempfile.mkstemp(
                    prefix=f".{target.name}.",
                    suffix=".tmp",
                    dir=target.parent,
                )
                temp_path = Path(temp_name)
                temporary_paths.append(temp_path)
                is_tracked = True

                stream = os.fdopen(fd, "wb")
                fd = None
                with stream:
                    written = stream.write(contents)
                    if written != len(contents):
                        raise OSError(
                            f"short write for temporary plist {temp_path}"
                        )
                    stream.flush()
                    os.fsync(stream.fileno())

                os.chmod(temp_path, 0o644)
                prepared.append((target, temp_path))
            except BaseException as primary:
                cleanup_failures: list[_CleanupFailure] = []
                if fd is not None:
                    try:
                        os.close(fd)
                    except OSError as error:
                        cleanup_failures.append(
                            (
                                "temporary plist file descriptor cleanup "
                                f"failed for fd {fd}: "
                                f"{type(error).__name__}: {error}",
                                error,
                            )
                        )
                if temp_name is not None and not is_tracked:
                    try:
                        os.unlink(temp_name)
                    except FileNotFoundError:
                        pass
                    except OSError as error:
                        cleanup_failures.append(
                            (
                                "untracked temporary plist cleanup failed for "
                                f"{temp_name}: {type(error).__name__}: {error}",
                                error,
                            )
                        )
                _report_cleanup_failures(cleanup_failures, primary=primary)
                raise

        for target, temp_path in prepared:
            replace(temp_path, target)
    except BaseException as primary:
        cleanup_failures = _cleanup_temporary_paths(temporary_paths)
        _report_cleanup_failures(cleanup_failures, primary=primary)
        raise
    else:
        cleanup_failures = _cleanup_temporary_paths(temporary_paths)
        _report_cleanup_failures(cleanup_failures)


def normalize_config_path(config_path: str | Path) -> Path:
    return Path(config_path).expanduser().resolve(strict=False)


def load_service_config(config_path: Path) -> dict[str, Any]:
    try:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError):
        return {}
    return config if isinstance(config, dict) else {}


def bounded_worker_count(config: Mapping[str, Any]) -> int:
    try:
        worker_count = int(
            (config.get("javinfo") or {}).get("supplement_worker_count", 6)
        )
    except Exception:
        worker_count = 6
    return max(1, min(16, worker_count))


def normalized_advertise_host(env: Mapping[str, Any]) -> str:
    value = str(env.get("JAVHUB_PROXY_ADVERTISE_HOST") or "").strip()
    return value or "127.0.0.1"


def environment_value(
    env: Mapping[str, Any],
    key: str,
    default: Any,
) -> str:
    return str(env.get(key) or default)


def resolve_proxy_url(
    root_dir: Path,
    proxy: Any,
    advertise_host: str,
) -> str:
    helper_path = (
        root_dir / "backend" / "modules" / "proxy_config.py"
    ).resolve(strict=False)
    spec = importlib.util.spec_from_file_location(
        "_javhub_service_proxy_config",
        helper_path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load proxy helper from {helper_path}")
    helper_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper_module)
    effective_proxy_url = getattr(helper_module, "effective_proxy_url", None)
    if not callable(effective_proxy_url):
        raise ImportError(
            f"proxy helper {helper_path} does not define effective_proxy_url"
        )

    proxy_config = proxy if isinstance(proxy, Mapping) else {}
    return effective_proxy_url(
        proxy_config,
        advertise_host=advertise_host,
    )


def render_service_plists(
    *,
    javinfo_plist: Path,
    backend_plist: Path,
    frontend_plist: Path,
    root_dir: Path,
    javinfo_dir: Path,
    frontend_npm_bin: Path,
    config_path: str | Path,
    env: Mapping[str, Any],
) -> None:
    root_dir = root_dir.resolve(strict=False)
    javinfo_dir = javinfo_dir.resolve(strict=False)
    config_path = normalize_config_path(config_path)
    config = load_service_config(config_path)
    advertise_host = normalized_advertise_host(env)
    proxy_url = resolve_proxy_url(
        root_dir,
        config.get("proxy"),
        advertise_host,
    )

    javinfo_environment = {
        "PATH": SYSTEM_PATH,
        "SERVER_PORT": "8080",
        "SUPPLEMENT_WORKER_COUNT": str(bounded_worker_count(config)),
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
    backend_dir = root_dir / "backend"
    backend_payload = {
        "Label": BACKEND_LABEL,
        "ProgramArguments": [
            str(root_dir / ".venv" / "bin" / "uvicorn"),
            "main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "18090",
        ],
        "WorkingDirectory": str(backend_dir),
        "EnvironmentVariables": {
            "PATH": f"{root_dir}/.venv/bin:{SYSTEM_PATH}",
            "PYTHONUNBUFFERED": "1",
            "JAVHUB_CONFIG_PATH": str(config_path),
            "JAVHUB_PROXY_ADVERTISE_HOST": advertise_host,
            "JAVHUB_DB_HOST": environment_value(
                env, "JAVHUB_DB_HOST", "localhost"
            ),
            "JAVHUB_DB_PORT": environment_value(env, "JAVHUB_DB_PORT", "5432"),
            "JAVHUB_DB_USER": environment_value(
                env, "JAVHUB_DB_USER", "kongmei"
            ),
            "JAVHUB_DB_PASSWORD": environment_value(
                env, "JAVHUB_DB_PASSWORD", ""
            ),
            "JAVHUB_DB_NAME": environment_value(env, "JAVHUB_DB_NAME", "javhub"),
            "JAVHUB_CACHE_BACKEND": environment_value(
                env, "JAVHUB_CACHE_BACKEND", "redis"
            ),
            "JAVHUB_REDIS_URL": environment_value(
                env,
                "JAVHUB_REDIS_URL",
                "redis://127.0.0.1:6379/0",
            ),
            "JAVHUB_REDIS_PREFIX": environment_value(
                env, "JAVHUB_REDIS_PREFIX", "javhub-cache"
            ),
        },
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": str(backend_dir / "javhub-backend.launchd.log"),
        "StandardErrorPath": str(backend_dir / "javhub-backend.launchd.err.log"),
    }
    frontend_dir = root_dir / "frontend"
    frontend_payload = {
        "Label": FRONTEND_LABEL,
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
        "WorkingDirectory": str(frontend_dir),
        "EnvironmentVariables": {"PATH": SYSTEM_PATH},
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": str(root_dir / "javhub-frontend.launchd.log"),
        "StandardErrorPath": str(root_dir / "javhub-frontend.launchd.err.log"),
    }

    write_plists_atomically(
        {
            Path(javinfo_plist): javinfo_payload,
            Path(backend_plist): backend_payload,
            Path(frontend_plist): frontend_payload,
        }
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render JavHub LaunchAgent property lists."
    )
    parser.add_argument("--javinfo-plist", required=True, type=Path)
    parser.add_argument("--backend-plist", required=True, type=Path)
    parser.add_argument("--frontend-plist", required=True, type=Path)
    parser.add_argument("--root-dir", required=True, type=Path)
    parser.add_argument("--javinfo-dir", required=True, type=Path)
    parser.add_argument("--frontend-npm-bin", required=True, type=Path)
    parser.add_argument("--config-path", required=True, type=Path)
    arguments = parser.parse_args(argv)

    render_service_plists(
        javinfo_plist=arguments.javinfo_plist,
        backend_plist=arguments.backend_plist,
        frontend_plist=arguments.frontend_plist,
        root_dir=arguments.root_dir,
        javinfo_dir=arguments.javinfo_dir,
        frontend_npm_bin=arguments.frontend_npm_bin,
        config_path=arguments.config_path,
        env=os.environ,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
