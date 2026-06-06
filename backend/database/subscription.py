"""订阅数据库层"""
import json
import time
from datetime import datetime
from typing import Any

from database.base import get_db


VALID_SUBSCRIPTION_SCOPES = {"actress", "maker", "series", "label"}


def _ensure_subscription_schema() -> None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS scope TEXT DEFAULT 'actress'")
        cursor.execute("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS target_id BIGINT")
        cursor.execute("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS target_label TEXT")
        cursor.execute("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS cadence_minutes INT DEFAULT 1440")
        cursor.execute("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS cooldown_until TIMESTAMPTZ NULL")
        cursor.execute("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS last_seen_codes JSONB DEFAULT '[]'")
        cursor.execute("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS last_run_at TIMESTAMPTZ NULL")
        cursor.execute("UPDATE subscriptions SET scope = 'actress' WHERE scope IS NULL OR scope = ''")
        cursor.execute(
            """
            UPDATE subscriptions
            SET target_id = actress_id
            WHERE scope = 'actress' AND target_id IS NULL AND actress_id IS NOT NULL
            """
        )
        cursor.execute(
            """
            UPDATE subscriptions
            SET target_label = actress_name
            WHERE scope = 'actress' AND (target_label IS NULL OR target_label = '')
            """
        )


def _normalize_last_seen_codes(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item]
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return []
        if isinstance(decoded, list):
            return [str(item) for item in decoded if item]
    return []


def _normalize_subscription_row(row: Any) -> dict:
    data = dict(row)
    scope = str(data.get("scope") or "actress").strip() or "actress"
    data["scope"] = scope if scope in VALID_SUBSCRIPTION_SCOPES else "actress"
    if data.get("target_id") is None and data["scope"] == "actress":
        data["target_id"] = data.get("actress_id")
    if not data.get("target_label") and data["scope"] == "actress":
        data["target_label"] = data.get("actress_name")
    cadence_value = data.get("cadence_minutes")
    data["cadence_minutes"] = int(cadence_value) if cadence_value is not None else 1440
    data["last_seen_codes"] = _normalize_last_seen_codes(data.get("last_seen_codes"))
    return data


def _bump_subscriptions_generation() -> None:
    try:
        from services.cache import set_data_generation

        set_data_generation("subscriptions", time.time_ns())
    except Exception:
        pass


def _normalize_scope_fields(
    actress_id: int | None,
    actress_name: str | None,
    scope: str,
    target_id: int | None,
    target_label: str | None,
) -> tuple[int | None, str, str, int, str]:
    scope = str(scope or "actress").strip().lower()
    if scope not in VALID_SUBSCRIPTION_SCOPES:
        raise ValueError(f"invalid subscription scope: {scope}")

    if scope == "actress":
        resolved_target_id = target_id if target_id is not None else actress_id
        resolved_target_label = target_label or actress_name
        if resolved_target_id is None or not resolved_target_label:
            raise ValueError("actress subscription requires actress_id and actress_name")
        return (
            int(resolved_target_id),
            str(resolved_target_label),
            scope,
            int(resolved_target_id),
            str(resolved_target_label),
        )

    if target_id is None or not target_label:
        raise ValueError(f"{scope} subscription requires target_id and target_label")
    return None, str(target_label), scope, int(target_id), str(target_label)


def add_subscription(
    actress_id: int | None = None,
    actress_name: str | None = None,
    auto_download: bool = False,
    *,
    scope: str = "actress",
    target_id: int | None = None,
    target_label: str | None = None,
) -> int:
    _ensure_subscription_schema()
    actress_id, actress_name, scope, target_id, target_label = _normalize_scope_fields(
        actress_id,
        actress_name,
        scope,
        target_id,
        target_label,
    )
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO subscriptions (
                actress_id, actress_name, scope, target_id, target_label,
                auto_download, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (actress_id, actress_name, scope, target_id, target_label, auto_download)
        )
        sub_id = cursor.lastrowid
    _bump_subscriptions_generation()
    return sub_id


def get_subscriptions() -> list:
    _ensure_subscription_schema()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM subscriptions ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [_normalize_subscription_row(row) for row in rows]


def cleanup_legacy_subscriptions() -> int:
    """删除旧的停用订阅记录，避免前端详情页把历史行误判为订阅。"""
    _ensure_subscription_schema()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM subscriptions WHERE COALESCE(enabled, 1) = 0")
        removed = cursor.rowcount
    if removed:
        _bump_subscriptions_generation()
    return removed


def delete_subscription(subscription_id: int):
    _ensure_subscription_schema()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM subscriptions WHERE id = ?", (subscription_id,))
        changed = cursor.rowcount
    if changed:
        _bump_subscriptions_generation()


def is_subscribed(actress_id: int) -> bool:
    """检查某演员是否已订阅（enabled=1）"""
    _ensure_subscription_schema()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM subscriptions WHERE scope = 'actress' AND actress_id = ? AND enabled = 1",
            (actress_id,),
        )
        return cursor.fetchone() is not None


def toggle_subscription(actress_id: int, actress_name: str, auto_download: bool = False) -> dict:
    """切换订阅状态，返回 {subscribed: bool, id: int}"""
    _ensure_subscription_schema()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, enabled FROM subscriptions WHERE scope = 'actress' AND actress_id = ?",
            (actress_id,),
        )
        row = cursor.fetchone()
        if row:
            if row["enabled"]:
                cursor.execute("DELETE FROM subscriptions WHERE id = ?", (row["id"],))
                result = {"subscribed": False, "id": row["id"]}
                changed = True
            else:
                cursor.execute("UPDATE subscriptions SET enabled = 1 WHERE id = ?", (row["id"],))
                result = {"subscribed": True, "id": row["id"]}
                changed = True
        else:
            cursor.execute(
                """
                INSERT INTO subscriptions (
                    actress_id, actress_name, scope, target_id, target_label,
                    auto_download, enabled, created_at
                )
                VALUES (?, ?, 'actress', ?, ?, ?, 1, CURRENT_TIMESTAMP)
                """,
                (actress_id, actress_name, actress_id, actress_name, auto_download)
            )
            result = {"subscribed": True, "id": cursor.lastrowid}
            changed = True
    if changed:
        _bump_subscriptions_generation()
    return result


def update_last_check(
    subscription_id: int,
    last_found: str = "",
    *,
    last_seen_codes: list[str] | None = None,
    last_run_at: datetime | str | None = None,
    cooldown_until: datetime | str | None = None,
):
    """更新订阅的最后检查时间"""
    _ensure_subscription_schema()
    set_parts = [
        "last_check = CURRENT_TIMESTAMP",
        "last_found = ?",
        "last_run_at = COALESCE(?, CURRENT_TIMESTAMP)",
        "cooldown_until = ?",
    ]
    values: list[Any] = [last_found, last_run_at, cooldown_until]
    if last_seen_codes is not None:
        set_parts.append("last_seen_codes = ?::jsonb")
        values.append(json.dumps(last_seen_codes[:500], ensure_ascii=False))
    values.append(subscription_id)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE subscriptions SET {', '.join(set_parts)} WHERE id = ?",
            values,
        )
        changed = cursor.rowcount
    if changed:
        _bump_subscriptions_generation()


def set_subscription_cooldown(
    subscription_id: int,
    cooldown_until: datetime | str,
    *,
    last_run_at: datetime | str | None = None,
):
    _ensure_subscription_schema()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE subscriptions
            SET cooldown_until = ?,
                last_run_at = COALESCE(?, CURRENT_TIMESTAMP)
            WHERE id = ?
            """,
            (cooldown_until, last_run_at, subscription_id),
        )
        changed = cursor.rowcount
    if changed:
        _bump_subscriptions_generation()


def get_subscription_by_actress(actress_id: int) -> dict | None:
    """根据 actress_id 获取订阅"""
    _ensure_subscription_schema()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM subscriptions WHERE scope = 'actress' AND actress_id = ?",
            (actress_id,),
        )
        row = cursor.fetchone()
        return _normalize_subscription_row(row) if row else None


def update_subscription(subscription_id: int, **kwargs):
    """更新订阅字段"""
    _ensure_subscription_schema()
    allowed = {"enabled", "auto_download", "cadence_minutes"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    if "cadence_minutes" in fields:
        fields["cadence_minutes"] = max(0, int(fields["cadence_minutes"]))
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [subscription_id]
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE subscriptions SET {set_clause} WHERE id = ?", values)
        changed = cursor.rowcount
    if changed:
        _bump_subscriptions_generation()
