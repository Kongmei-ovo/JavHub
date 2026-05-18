from __future__ import annotations

import asyncio
import gzip
import hashlib
import os
import re
import shutil
import time
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator, Awaitable, Callable


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_STORAGE_DIR = ROOT_DIR / "data" / "javinfo_imports"
ACTIVE_STATUSES = {"pending", "uploading", "uploaded", "restoring", "stopping", "swapping", "restarting", "migrating"}
FINAL_STATUSES = {"completed", "failed", "canceled"}
PG_DUMPALL_PATTERNS = (
    re.compile(r"(?im)^\s*CREATE\s+DATABASE\b"),
    re.compile(r"(?im)^\s*\\connect\b"),
)
SQL_SAMPLE_BYTES = 262144


class JavInfoImportError(RuntimeError):
    pass


class JavInfoImportConflict(JavInfoImportError):
    pass


@dataclass(frozen=True)
class DumpFormat:
    kind: str
    compressed: bool = False


@dataclass
class CommandResult:
    returncode: int
    output: str


def _safe_filename(filename: str) -> str:
    value = Path(str(filename or "dump")).name.strip()
    return value or "dump"


def _redact_settings(settings: dict[str, Any]) -> dict[str, Any]:
    redacted = dict(settings or {})
    if redacted.get("password"):
        redacted["password"] = ""
    return redacted


def _normalize_settings(settings: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "host": "localhost",
        "port": 5432,
        "database": "r18",
        "maintenance_database": "postgres",
        "user": "kongmei",
        "password": "",
        "max_parallel_jobs": 2,
        "keep_previous_databases": 1,
    }
    normalized.update(settings or {})
    for key in ("host", "database", "maintenance_database", "user", "password"):
        normalized[key] = str(normalized.get(key) or "").strip()
    try:
        normalized["port"] = int(normalized.get("port") or 5432)
    except Exception:
        normalized["port"] = 5432
    try:
        normalized["max_parallel_jobs"] = max(1, min(int(normalized.get("max_parallel_jobs") or 2), 8))
    except Exception:
        normalized["max_parallel_jobs"] = 2
    try:
        normalized["keep_previous_databases"] = max(0, min(int(normalized.get("keep_previous_databases", 1)), 5))
    except Exception:
        normalized["keep_previous_databases"] = 1
    return normalized


def _pg_env(settings: dict[str, Any]) -> dict[str, str]:
    env = dict(os.environ)
    env["PGCONNECT_TIMEOUT"] = "10"
    password = str(settings.get("password") or "")
    if password:
        env["PGPASSWORD"] = password
    else:
        env.pop("PGPASSWORD", None)
    return env


def _pg_ident(value: str) -> str:
    return '"' + str(value).replace('"', '""') + '"'


def _pg_literal(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _connection_args(settings: dict[str, Any], database: str) -> list[str]:
    return [
        "--host",
        str(settings.get("host") or "localhost"),
        "--port",
        str(settings.get("port") or 5432),
        "--username",
        str(settings.get("user") or "kongmei"),
        "--dbname",
        database,
    ]


def build_pg_restore_command(settings: dict[str, Any], database: str, file_path: Path) -> list[str]:
    normalized = _normalize_settings(settings)
    jobs = normalized["max_parallel_jobs"]
    return [
        "pg_restore",
        *_connection_args(normalized, database),
        "--no-owner",
        "--no-privileges",
        "--exit-on-error",
        f"--jobs={jobs}",
        str(file_path),
    ]


def build_psql_command(settings: dict[str, Any], database: str, file_path: Path | None = None) -> list[str]:
    normalized = _normalize_settings(settings)
    command = [
        "psql",
        *_connection_args(normalized, database),
        "--set=ON_ERROR_STOP=1",
    ]
    if file_path is not None:
        command.extend(["--file", str(file_path)])
    return command


def _reject_pg_dumpall_sample(sample: str) -> None:
    if any(pattern.search(sample) for pattern in PG_DUMPALL_PATTERNS):
        raise ValueError("pg_dumpall style dumps with CREATE DATABASE or \\connect are not supported")


def _read_text_sample(path: Path) -> str:
    with path.open("rb") as fh:
        return fh.read(SQL_SAMPLE_BYTES).decode("utf-8", errors="ignore")


def _read_gzip_text_sample(path: Path) -> str:
    with gzip.open(path, "rb") as fh:
        return fh.read(SQL_SAMPLE_BYTES).decode("utf-8", errors="ignore")


def detect_dump_format(path: Path, filename: str = "") -> DumpFormat:
    name = (filename or path.name).lower()
    suffixes = path.suffixes
    with path.open("rb") as fh:
        header = fh.read(8)

    if header.startswith(b"PGDMP") or name.endswith((".dump", ".backup")):
        return DumpFormat("custom")
    if name.endswith(".sql.gz") or suffixes[-2:] == [".sql", ".gz"] or header.startswith(b"\x1f\x8b"):
        _reject_pg_dumpall_sample(_read_gzip_text_sample(path))
        return DumpFormat("plain_sql_gzip", compressed=True)
    if name.endswith(".sql") or header.lstrip().startswith((b"--", b"SET", b"CRE", b"\\", b"DO ")):
        _reject_pg_dumpall_sample(_read_text_sample(path))
        return DumpFormat("plain_sql")
    raise ValueError("unsupported dump format; use .dump, .backup, .sql, or .sql.gz")


async def _read_stream_output(process: asyncio.subprocess.Process) -> str:
    chunks: list[str] = []
    if not process.stdout:
        return ""
    while True:
        line = await process.stdout.readline()
        if not line:
            break
        chunks.append(line.decode("utf-8", errors="replace").rstrip())
    return "\n".join(chunks)


async def _terminate_process(process: asyncio.subprocess.Process) -> None:
    if process.returncode is not None:
        return
    process.terminate()
    try:
        await asyncio.wait_for(process.wait(), timeout=5)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()


async def _discard_task_result(task: asyncio.Task) -> None:
    with suppress(BaseException):
        _ = await task


async def _collect_process(
    process: asyncio.subprocess.Process,
    args: list[str],
    *,
    timeout: int | None,
    cancel_check: Callable[[], bool] | None,
) -> CommandResult:
    output_task = asyncio.create_task(_read_stream_output(process))
    wait_task = asyncio.create_task(process.wait())
    deadline = asyncio.get_running_loop().time() + timeout if timeout is not None else None
    try:
        while not wait_task.done():
            if cancel_check and cancel_check():
                await _terminate_process(process)
                raise asyncio.CancelledError()
            if deadline is not None and asyncio.get_running_loop().time() >= deadline:
                await _terminate_process(process)
                raise TimeoutError(f"command timed out: {args[0]}")
            wait_timeout = 0.5
            if deadline is not None:
                wait_timeout = max(0.01, min(wait_timeout, deadline - asyncio.get_running_loop().time()))
            await asyncio.wait({wait_task}, timeout=wait_timeout)
        returncode = await wait_task
        output = await output_task
        return CommandResult(returncode=returncode, output=output)
    except BaseException:
        if not wait_task.done():
            wait_task.cancel()
        if not output_task.done():
            output_task.cancel()
        await _discard_task_result(output_task)
        raise


class AsyncCommandRunner:
    async def run(
        self,
        args: list[str],
        *,
        env: dict[str, str] | None = None,
        stdin_path: Path | None = None,
        gzip_stdin: bool = False,
        timeout: int | None = None,
        log: Callable[[str], None] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> CommandResult:
        if stdin_path is not None and gzip_stdin:
            return await self._run_with_gzip_stdin(
                args,
                env=env,
                stdin_path=stdin_path,
                timeout=timeout,
                log=log,
                cancel_check=cancel_check,
            )
        stdin = asyncio.subprocess.DEVNULL
        input_handle = None
        if stdin_path is not None:
            input_handle = stdin_path.open("rb")
            stdin = input_handle
        try:
            process = await asyncio.create_subprocess_exec(
                *args,
                stdin=stdin,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
            )
            result = await _collect_process(process, args, timeout=timeout, cancel_check=cancel_check)
            output = result.output
            if output and log:
                for line in output.splitlines()[-50:]:
                    log(line)
            return result
        finally:
            if input_handle is not None:
                input_handle.close()

    async def _run_with_gzip_stdin(
        self,
        args: list[str],
        *,
        env: dict[str, str] | None,
        stdin_path: Path,
        timeout: int | None,
        log: Callable[[str], None] | None,
        cancel_check: Callable[[], bool] | None,
    ) -> CommandResult:
        process = await asyncio.create_subprocess_exec(
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env,
        )

        async def pump() -> None:
            assert process.stdin is not None
            try:
                with gzip.open(stdin_path, "rb") as fh:
                    while True:
                        chunk = await asyncio.to_thread(fh.read, 1024 * 1024)
                        if not chunk:
                            break
                        process.stdin.write(chunk)
                        await process.stdin.drain()
            finally:
                process.stdin.close()
                await process.stdin.wait_closed()

        try:
            pump_task = asyncio.create_task(pump())
            result = await _collect_process(process, args, timeout=timeout, cancel_check=cancel_check)
            await pump_task
            output = result.output
        except BaseException:
            if "pump_task" in locals() and not pump_task.done():
                pump_task.cancel()
            if "pump_task" in locals():
                await _discard_task_result(pump_task)
            raise
        if output and log:
            for line in output.splitlines()[-50:]:
                log(line)
        return result


class JavInfoImportManager:
    def __init__(
        self,
        *,
        storage_dir: Path = DEFAULT_STORAGE_DIR,
        command_runner: AsyncCommandRunner | None = None,
        service_helper: Path | None = None,
        post_import_migrator: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ):
        self.storage_dir = Path(storage_dir)
        self.command_runner = command_runner or AsyncCommandRunner()
        self.service_helper = service_helper if service_helper is not None else ROOT_DIR / "scripts" / "services.sh"
        self.post_import_migrator = post_import_migrator
        self._jobs: dict[int, dict[str, Any]] = {}
        self._next_id = 1
        self._lock = asyncio.Lock()

    def _active_job(self) -> dict[str, Any] | None:
        for job in self._jobs.values():
            if job.get("status") in ACTIVE_STATUSES:
                return job
        return None

    def create_job(
        self,
        settings: dict[str, Any],
        *,
        filename: str,
        file_size: int | None = None,
        confirm_replace: bool = False,
    ) -> dict[str, Any]:
        if not confirm_replace:
            raise ValueError("confirm_replace is required")
        active = self._active_job()
        if active:
            raise JavInfoImportConflict(f"import job {active['id']} is already active")

        self.storage_dir.mkdir(parents=True, exist_ok=True)
        job_id = self._next_id
        self._next_id += 1
        normalized = _normalize_settings(settings)
        job_dir = self.storage_dir / str(job_id)
        job_dir.mkdir(parents=True, exist_ok=True)
        job = {
            "id": job_id,
            "status": "pending",
            "stage": "pending",
            "filename": _safe_filename(filename),
            "file_size": int(file_size or 0),
            "uploaded_bytes": 0,
            "sha256": "",
            "file_path": str(job_dir / _safe_filename(filename)),
            "settings": _redact_settings(normalized),
            "_settings": normalized,
            "logs": [],
            "error": "",
            "created_at": time.time(),
            "updated_at": time.time(),
            "cancel_requested": False,
        }
        self._jobs[job_id] = job
        return self.public_job(job)

    async def save_upload(self, job_id: int, chunks: AsyncIterator[bytes]) -> dict[str, Any]:
        job = self._require_job(job_id)
        if job.get("status") not in {"pending", "uploading"}:
            raise ValueError("job is not accepting uploads")
        digest = hashlib.sha256()
        path = Path(job["file_path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        job["status"] = "uploading"
        job["stage"] = "uploading"
        job["updated_at"] = time.time()
        uploaded = 0
        try:
            with path.open("wb") as fh:
                async for chunk in chunks:
                    if job.get("cancel_requested"):
                        job["status"] = "canceled"
                        job["stage"] = "canceled"
                        raise asyncio.CancelledError()
                    if not chunk:
                        continue
                    fh.write(chunk)
                    digest.update(chunk)
                    uploaded += len(chunk)
                    job["uploaded_bytes"] = uploaded
                    job["updated_at"] = time.time()
            fmt = detect_dump_format(path, job["filename"])
            job["dump_format"] = fmt.kind
            job["sha256"] = digest.hexdigest()
            job["status"] = "uploaded"
            job["stage"] = "uploaded"
            job["updated_at"] = time.time()
            return self.public_job(job)
        except Exception as exc:
            if isinstance(exc, asyncio.CancelledError):
                raise
            job["status"] = "failed"
            job["stage"] = "failed"
            job["error"] = str(exc)
            job["updated_at"] = time.time()
            raise

    async def preflight(self, settings: dict[str, Any], *, expected_size: int = 0) -> dict[str, Any]:
        normalized = _normalize_settings(settings)
        checks: dict[str, Any] = {
            "tools": {
                "pg_restore": bool(shutil.which("pg_restore")),
                "psql": bool(shutil.which("psql")),
                "gzip": bool(shutil.which("gzip")),
            },
            "database": {"ok": False, "can_create_database": False, "error": ""},
            "disk": {"ok": False, "free_bytes": 0, "required_bytes": int(expected_size or 0)},
        }
        free = shutil.disk_usage(self.storage_dir.parent if self.storage_dir.exists() else ROOT_DIR).free
        checks["disk"]["free_bytes"] = free
        checks["disk"]["ok"] = free > max(int(expected_size or 0) * 2, 1024 * 1024 * 1024)

        if all(checks["tools"].values()):
            result = await self.command_runner.run(
                [
                    "psql",
                    *_connection_args(normalized, normalized["maintenance_database"]),
                    "--tuples-only",
                    "--no-align",
                    "--command",
                    "SELECT rolsuper OR rolcreatedb FROM pg_roles WHERE rolname = current_user",
                ],
                env=_pg_env(normalized),
                timeout=15,
            )
            checks["database"]["ok"] = result.returncode == 0
            checks["database"]["can_create_database"] = "t" in result.output.lower().split()
            if result.returncode != 0:
                checks["database"]["error"] = result.output[-1000:]

        ok = all(checks["tools"].values()) and checks["database"]["ok"] and checks["disk"]["ok"]
        return {"ok": ok, "checks": checks}

    async def restore_job(self, job_id: int) -> dict[str, Any]:
        async with self._lock:
            job = self._require_job(job_id)
            if job.get("status") != "uploaded":
                return self.public_job(job)
            try:
                await self._restore_uploaded_job(job)
                job["status"] = "completed"
                job["stage"] = "completed"
                job["updated_at"] = time.time()
            except asyncio.CancelledError:
                job["status"] = "canceled"
                job["stage"] = "canceled"
                job["updated_at"] = time.time()
            except Exception as exc:
                job["status"] = "failed"
                job["stage"] = "failed"
                job["error"] = str(exc)
                job["updated_at"] = time.time()
            return self.public_job(job)

    async def cancel_job(self, job_id: int) -> dict[str, Any]:
        job = self._require_job(job_id)
        job["cancel_requested"] = True
        if job.get("status") in {"pending", "uploading", "uploaded"}:
            job["status"] = "canceled"
            job["stage"] = "canceled"
            job["updated_at"] = time.time()
        return self.public_job(job)

    def get_job(self, job_id: int) -> dict[str, Any] | None:
        job = self._jobs.get(job_id)
        return self.public_job(job) if job else None

    def list_jobs(self, limit: int = 20) -> list[dict[str, Any]]:
        jobs = sorted(self._jobs.values(), key=lambda item: item.get("created_at", 0), reverse=True)
        return [self.public_job(job) for job in jobs[: max(1, min(int(limit or 20), 100))]]

    def _require_job(self, job_id: int) -> dict[str, Any]:
        job = self._jobs.get(int(job_id))
        if not job:
            raise KeyError(f"import job {job_id} not found")
        return job

    def public_job(self, job: dict[str, Any]) -> dict[str, Any]:
        public = {k: v for k, v in job.items() if not k.startswith("_") and k != "cancel_requested"}
        public["logs"] = list(public.get("logs") or [])[-100:]
        return public

    def _log(self, job: dict[str, Any], message: str) -> None:
        if not message:
            return
        job.setdefault("logs", []).append(str(message)[-2000:])
        job["updated_at"] = time.time()

    async def _restore_uploaded_job(self, job: dict[str, Any]) -> None:
        settings = job["_settings"]
        file_path = Path(job["file_path"])
        fmt = detect_dump_format(file_path, job["filename"])
        target_db = settings["database"]
        staging_db = f"{target_db}_import_{job['id']}"
        can_stage = await self._can_create_database(settings)
        service_stopped = False

        try:
            if can_stage:
                self._raise_if_canceled(job)
                job["stage"] = "restoring"
                job["status"] = "restoring"
                await self._sql(job, settings, settings["maintenance_database"], f"DROP DATABASE IF EXISTS {_pg_ident(staging_db)}")
                await self._sql(job, settings, settings["maintenance_database"], f"CREATE DATABASE {_pg_ident(staging_db)}")
                await self._restore_to_database(job, fmt, staging_db)

                self._raise_if_canceled(job)
                job["stage"] = "stopping"
                await self._service("stop", job)
                service_stopped = True
                job["stage"] = "swapping"
                backup_db = f"{target_db}_before_import_{time.strftime('%Y%m%d%H%M%S')}"
                await self._sql(job, settings, settings["maintenance_database"], _terminate_db_sql(target_db))
                await self._sql(job, settings, settings["maintenance_database"], f"ALTER DATABASE {_pg_ident(target_db)} RENAME TO {_pg_ident(backup_db)}")
                await self._sql(job, settings, settings["maintenance_database"], f"ALTER DATABASE {_pg_ident(staging_db)} RENAME TO {_pg_ident(target_db)}")
                await self._cleanup_old_backups(settings, target_db, int(settings.get("keep_previous_databases", 1)))
                job["stage"] = "restarting"
                await self._service("restart", job)
            else:
                self._log(job, "database user cannot create databases; restoring directly into target database")
                job["stage"] = "stopping"
                await self._service("stop", job)
                service_stopped = True
                self._raise_if_canceled(job)
                job["stage"] = "restoring"
                job["status"] = "restoring"
                await self._reset_target_database(job, settings, target_db)
                await self._restore_to_database(job, fmt, target_db)
                job["stage"] = "restarting"
                await self._service("restart", job)
        except BaseException:
            if service_stopped:
                job["stage"] = "restarting"
                try:
                    await self._service("restart", job)
                    self._log(job, "javinfo service restarted after interrupted import")
                except Exception as restart_exc:
                    self._log(job, f"failed to restart javinfo after interrupted import: {restart_exc}")
            raise
        job["stage"] = "migrating"
        job["status"] = "migrating"
        await self._run_post_import_migrations(job)

    async def _restore_to_database(self, job: dict[str, Any], fmt: DumpFormat, database: str) -> None:
        settings = job["_settings"]
        file_path = Path(job["file_path"])
        if fmt.kind == "custom":
            command = build_pg_restore_command(settings, database, file_path)
            result = await self.command_runner.run(
                command,
                env=_pg_env(settings),
                timeout=None,
                log=lambda line: self._log(job, line),
                cancel_check=lambda: bool(job.get("cancel_requested")),
            )
        elif fmt.kind == "plain_sql":
            command = build_psql_command(settings, database, file_path)
            result = await self.command_runner.run(
                command,
                env=_pg_env(settings),
                timeout=None,
                log=lambda line: self._log(job, line),
                cancel_check=lambda: bool(job.get("cancel_requested")),
            )
        elif fmt.kind == "plain_sql_gzip":
            command = build_psql_command(settings, database, None)
            result = await self.command_runner.run(
                command,
                env=_pg_env(settings),
                stdin_path=file_path,
                gzip_stdin=True,
                timeout=None,
                log=lambda line: self._log(job, line),
                cancel_check=lambda: bool(job.get("cancel_requested")),
            )
        else:
            raise ValueError(f"unsupported dump format: {fmt.kind}")
        if result.returncode != 0:
            raise JavInfoImportError(result.output[-2000:] or f"{command[0]} failed")

    async def _sql(self, job: dict[str, Any] | None, settings: dict[str, Any], database: str, sql: str) -> None:
        result = await self.command_runner.run(
            [
                "psql",
                *_connection_args(settings, database),
                "--set=ON_ERROR_STOP=1",
                "--command",
                sql,
            ],
            env=_pg_env(settings),
            timeout=60,
            cancel_check=(lambda: bool(job and job.get("cancel_requested"))),
        )
        if result.returncode != 0:
            raise JavInfoImportError(result.output[-2000:] or "psql failed")

    async def _reset_target_database(self, job: dict[str, Any], settings: dict[str, Any], database: str) -> None:
        await self._sql(
            job,
            settings,
            database,
            "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public",
        )

    def _raise_if_canceled(self, job: dict[str, Any]) -> None:
        if job.get("cancel_requested"):
            raise asyncio.CancelledError()

    async def _can_create_database(self, settings: dict[str, Any]) -> bool:
        result = await self.command_runner.run(
            [
                "psql",
                *_connection_args(settings, settings["maintenance_database"]),
                "--tuples-only",
                "--no-align",
                "--command",
                "SELECT rolsuper OR rolcreatedb FROM pg_roles WHERE rolname = current_user",
            ],
            env=_pg_env(settings),
            timeout=15,
        )
        return result.returncode == 0 and "t" in result.output.lower().split()

    async def _service(self, action: str, job: dict[str, Any]) -> None:
        if not self.service_helper or not Path(self.service_helper).exists():
            self._log(job, f"service helper not found; skipped javinfo {action}")
            return
        result = await self.command_runner.run([str(self.service_helper), action, "javinfo"], timeout=120)
        if result.returncode != 0:
            raise JavInfoImportError(result.output[-2000:] or f"failed to {action} javinfo")

    async def _run_post_import_migrations(self, job: dict[str, Any]) -> None:
        self._raise_if_canceled(job)
        self._log(job, "running JavInfoApi migrations")
        if self.post_import_migrator is not None:
            await self.post_import_migrator(job)
            self._log(job, "JavInfoApi migrations completed")
            return

        from modules.info_client import get_info_client

        client = get_info_client()
        last_error: Exception | None = None
        for attempt in range(1, 11):
            self._raise_if_canceled(job)
            try:
                await client.run_migrations()
                self._log(job, "JavInfoApi migrations completed")
                return
            except Exception as exc:
                last_error = exc
                if attempt == 10:
                    break
                self._log(job, f"JavInfoApi migration attempt {attempt} failed; retrying")
                await asyncio.sleep(min(attempt, 5))
        raise JavInfoImportError(f"JavInfoApi migrations failed: {last_error}")

    async def _cleanup_old_backups(self, settings: dict[str, Any], target_db: str, keep: int) -> None:
        keep = max(0, int(keep or 0))
        sql = (
            "SELECT datname FROM pg_database "
            f"WHERE datname LIKE {_pg_literal(target_db + '_before_import_%')} "
            "ORDER BY datname DESC"
        )
        result = await self.command_runner.run(
            [
                "psql",
                *_connection_args(settings, settings["maintenance_database"]),
                "--tuples-only",
                "--no-align",
                "--command",
                sql,
            ],
            env=_pg_env(settings),
            timeout=30,
        )
        if result.returncode != 0:
            return
        backups = [line.strip() for line in result.output.splitlines() if line.strip()]
        for db_name in backups[keep:]:
            await self._sql(None, settings, settings["maintenance_database"], f"DROP DATABASE IF EXISTS {_pg_ident(db_name)}")


def _terminate_db_sql(database: str) -> str:
    return (
        "SELECT pg_terminate_backend(pid) "
        "FROM pg_stat_activity "
        f"WHERE datname = {_pg_literal(database)} AND pid <> pg_backend_pid()"
    )


_default_manager: JavInfoImportManager | None = None


def get_import_manager() -> JavInfoImportManager:
    global _default_manager
    if _default_manager is None:
        _default_manager = JavInfoImportManager()
    return _default_manager
