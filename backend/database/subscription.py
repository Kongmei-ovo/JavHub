"""订阅数据库层"""
import time

from database.base import get_db


def _bump_subscriptions_generation() -> None:
    try:
        from services.cache import set_data_generation

        set_data_generation("subscriptions", time.time_ns())
    except Exception:
        pass


def add_subscription(actress_id: int, actress_name: str, auto_download: bool = False) -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO subscriptions (actress_id, actress_name, auto_download, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            (actress_id, actress_name, auto_download)
        )
        sub_id = cursor.lastrowid
    _bump_subscriptions_generation()
    return sub_id


def get_subscriptions() -> list:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM subscriptions ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def cleanup_legacy_subscriptions() -> int:
    """删除旧的停用订阅记录，避免前端详情页把历史行误判为订阅。"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM subscriptions WHERE COALESCE(enabled, 1) = 0")
        removed = cursor.rowcount
    if removed:
        _bump_subscriptions_generation()
    return removed


def delete_subscription(subscription_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM subscriptions WHERE id = ?", (subscription_id,))
        changed = cursor.rowcount
    if changed:
        _bump_subscriptions_generation()


def is_subscribed(actress_id: int) -> bool:
    """检查某演员是否已订阅（enabled=1）"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM subscriptions WHERE actress_id = ? AND enabled = 1", (actress_id,))
        return cursor.fetchone() is not None


def toggle_subscription(actress_id: int, actress_name: str, auto_download: bool = False) -> dict:
    """切换订阅状态，返回 {subscribed: bool, id: int}"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, enabled FROM subscriptions WHERE actress_id = ?", (actress_id,))
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
                "INSERT INTO subscriptions (actress_id, actress_name, auto_download, enabled, created_at) VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)",
                (actress_id, actress_name, auto_download)
            )
            result = {"subscribed": True, "id": cursor.lastrowid}
            changed = True
    if changed:
        _bump_subscriptions_generation()
    return result


def update_last_check(subscription_id: int, last_found: str = ""):
    """更新订阅的最后检查时间"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE subscriptions SET last_check = CURRENT_TIMESTAMP, last_found = ? WHERE id = ?",
            (last_found, subscription_id)
        )
        changed = cursor.rowcount
    if changed:
        _bump_subscriptions_generation()


def get_subscription_by_actress(actress_id: int) -> dict | None:
    """根据 actress_id 获取订阅"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM subscriptions WHERE actress_id = ?", (actress_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_subscription(subscription_id: int, **kwargs):
    """更新订阅字段"""
    allowed = {"enabled", "auto_download"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [subscription_id]
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE subscriptions SET {set_clause} WHERE id = ?", values)
        changed = cursor.rowcount
    if changed:
        _bump_subscriptions_generation()
