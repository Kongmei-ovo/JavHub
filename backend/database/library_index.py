"""云盘文件索引数据库层。

约束（与 services/storage_resolver.py 共同遵守）：
- content_id 是对外稳定 Id 的唯一来源（未来 Emby 兼容层的 ItemId 基础）。
- 本表只存引用（backend + path + ref_payload）；直链严禁入库。
"""
from __future__ import annotations

import time
from typing import Optional

from database.base import get_db

VALID_MATCH_STATUSES = ("matched", "unmatched", "manual", "ignored")
# 自动扫描不允许覆盖的人工状态
PROTECTED_MATCH_STATUSES = ("manual", "ignored")


def _bump_library_generation() -> None:
    try:
        from services.cache import set_data_generation

        set_data_generation("library_files", time.time_ns())
    except Exception:
        pass


def upsert_library_file(
    backend: str,
    path: str,
    name: str,
    size: int = 0,
    modified_at: str | None = None,
    content_id: str | None = None,
    match_status: str = "unmatched",
    ref_payload: str | None = None,
) -> int:
    """新增或刷新一条文件记录。

    已存在且 match_status 为 manual/ignored 的行只刷新 size/modified/last_seen，
    不覆盖人工匹配结果。重新出现的软删除行会复活。
    返回 (行 id, 是否新建)。
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, match_status FROM library_files WHERE backend = ? AND path = ?",
            (backend, path),
        )
        row = cursor.fetchone()
        if row is None:
            cursor.execute(
                """
                INSERT INTO library_files (
                    backend, path, name, size, modified_at, content_id, match_status,
                    ref_payload, first_seen_at, last_seen_at, deleted_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, NULL)
                """,
                (backend, path, name, size, modified_at, content_id, match_status, ref_payload),
            )
            _bump_library_generation()
            return cursor.lastrowid, True
        existing = dict(row)
        if existing["match_status"] in PROTECTED_MATCH_STATUSES:
            cursor.execute(
                """
                UPDATE library_files
                SET name = ?, size = ?, modified_at = ?,
                    last_seen_at = CURRENT_TIMESTAMP, deleted_at = NULL
                WHERE id = ?
                """,
                (name, size, modified_at, existing["id"]),
            )
        else:
            cursor.execute(
                """
                UPDATE library_files
                SET name = ?, size = ?, modified_at = ?, content_id = ?, match_status = ?,
                    ref_payload = ?, last_seen_at = CURRENT_TIMESTAMP, deleted_at = NULL
                WHERE id = ?
                """,
                (name, size, modified_at, content_id, match_status, ref_payload, existing["id"]),
            )
        _bump_library_generation()
        return existing["id"], False


def mark_files_deleted(backend: str, seen_paths: set[str], prefix: str | None = None) -> int:
    """对扫描中未出现的行打软删除标。返回打标数量。

    prefix 非空时只影响该目录前缀下的行（增量扫描用）。
    """
    with get_db() as conn:
        cursor = conn.cursor()
        params: list = [backend]
        prefix_clause = ""
        if prefix:
            prefix_clause = " AND path LIKE ?"
            params.append(prefix.rstrip("/") + "/%")
        cursor.execute(
            f"SELECT id, path FROM library_files WHERE backend = ? AND deleted_at IS NULL{prefix_clause}",
            params,
        )
        rows = [dict(r) for r in cursor.fetchall()]
        missing_ids = [r["id"] for r in rows if r["path"] not in seen_paths]
        for file_id in missing_ids:
            cursor.execute(
                "UPDATE library_files SET deleted_at = CURRENT_TIMESTAMP WHERE id = ?",
                (file_id,),
            )
        if missing_ids:
            _bump_library_generation()
        return len(missing_ids)


def get_library_file(file_id: int) -> Optional[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM library_files WHERE id = ?", (file_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_library_files_by_content_id(content_id: str) -> list[dict]:
    """按番号取未删除文件，size 降序（多版本时首选最大文件）。"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM library_files
            WHERE content_id = ? AND deleted_at IS NULL
              AND match_status IN ('matched', 'manual')
            ORDER BY size DESC, id ASC
            """,
            (content_id,),
        )
        return [dict(row) for row in cursor.fetchall()]


def list_library_files_page(
    status: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[dict], int]:
    """分页列表（未删除）。返回 (rows, total)。"""
    where = ["deleted_at IS NULL"]
    params: list = []
    if status:
        where.append("match_status = ?")
        params.append(status)
    if search:
        where.append("(name ILIKE ? OR path ILIKE ? OR content_id ILIKE ?)")
        like = f"%{search}%"
        params.extend([like, like, like])
    where_sql = " AND ".join(where)
    offset = max(page - 1, 0) * page_size
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) AS total FROM library_files WHERE {where_sql}", params)
        total = dict(cursor.fetchone())["total"]
        cursor.execute(
            f"""
            SELECT * FROM library_files WHERE {where_sql}
            ORDER BY last_seen_at DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            params + [page_size, offset],
        )
        return [dict(row) for row in cursor.fetchall()], total


def list_matched_library_files(limit: int | None = None) -> list[dict]:
    """全部已匹配且未删除的行（snapshot 适配器 / Emby 兼容层用）。"""
    with get_db() as conn:
        cursor = conn.cursor()
        sql = """
            SELECT * FROM library_files
            WHERE deleted_at IS NULL AND match_status IN ('matched', 'manual')
              AND content_id IS NOT NULL
            ORDER BY first_seen_at DESC, id DESC
        """
        params: tuple = ()
        if limit:
            sql += " LIMIT ?"
            params = (limit,)
        cursor.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]


def set_file_match(file_id: int, content_id: str, status: str = "manual") -> bool:
    if status not in VALID_MATCH_STATUSES:
        raise ValueError(f"invalid match_status: {status}")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE library_files SET content_id = ?, match_status = ? WHERE id = ?",
            (content_id, status, file_id),
        )
        changed = cursor.rowcount > 0
        if changed:
            _bump_library_generation()
        return changed


def ignore_file(file_id: int) -> bool:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE library_files SET match_status = 'ignored', content_id = NULL WHERE id = ?",
            (file_id,),
        )
        changed = cursor.rowcount > 0
        if changed:
            _bump_library_generation()
        return changed


def library_summary() -> dict:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT match_status, COUNT(*) AS cnt
            FROM library_files WHERE deleted_at IS NULL
            GROUP BY match_status
            """
        )
        by_status = {dict(r)["match_status"]: dict(r)["cnt"] for r in cursor.fetchall()}
        cursor.execute(
            "SELECT COUNT(DISTINCT content_id) AS cnt FROM library_files "
            "WHERE deleted_at IS NULL AND content_id IS NOT NULL AND match_status IN ('matched', 'manual')"
        )
        distinct_titles = dict(cursor.fetchone())["cnt"]
    total = sum(by_status.values())
    return {
        "total_files": total,
        "matched": by_status.get("matched", 0) + by_status.get("manual", 0),
        "unmatched": by_status.get("unmatched", 0),
        "ignored": by_status.get("ignored", 0),
        "distinct_titles": distinct_titles,
    }


# ── scan runs ────────────────────────────────────────────────────


def create_scan_run(mode: str, root_path: str | None = None) -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO library_scan_runs (mode, root_path, status, started_at)
            VALUES (?, ?, 'running', CURRENT_TIMESTAMP)
            """,
            (mode, root_path),
        )
        return cursor.lastrowid


def update_scan_run(
    run_id: int,
    status: str | None = None,
    files_seen: int | None = None,
    files_added: int | None = None,
    files_removed: int | None = None,
    files_matched: int | None = None,
    error: str | None = None,
) -> None:
    fields = []
    params: list = []
    for column, value in (
        ("status", status),
        ("files_seen", files_seen),
        ("files_added", files_added),
        ("files_removed", files_removed),
        ("files_matched", files_matched),
        ("error", error),
    ):
        if value is not None:
            fields.append(f"{column} = ?")
            params.append(value)
    if status in ("done", "failed"):
        fields.append("finished_at = CURRENT_TIMESTAMP")
    if not fields:
        return
    params.append(run_id)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE library_scan_runs SET {', '.join(fields)} WHERE id = ?",
            params,
        )


def get_latest_scan_run() -> Optional[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM library_scan_runs ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None


def is_scan_running() -> bool:
    run = get_latest_scan_run()
    return bool(run and run.get("status") == "running")
