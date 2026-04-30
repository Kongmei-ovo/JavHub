"""订阅数据库层"""
from database.base import get_db_orig


def add_subscription(actress_id: int, actress_name: str, auto_download: bool = False) -> int:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO subscriptions (actress_id, actress_name, auto_download, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
        (actress_id, actress_name, auto_download)
    )
    conn.commit()
    sub_id = cursor.lastrowid
    conn.close()
    return sub_id


def get_subscriptions() -> list:
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM subscriptions ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_subscription(subscription_id: int):
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM subscriptions WHERE id = ?", (subscription_id,))
    conn.commit()
    conn.close()


def is_subscribed(actress_id: int) -> bool:
    """检查某演员是否已订阅"""
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM subscriptions WHERE actress_id = ?", (actress_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None


def toggle_subscription(actress_id: int, actress_name: str, auto_download: bool = False) -> dict:
    """切换订阅状态，返回 {subscribed: bool, id: int}"""
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM subscriptions WHERE actress_id = ?", (actress_id,))
    row = cursor.fetchone()
    if row:
        cursor.execute("DELETE FROM subscriptions WHERE id = ?", (row["id"],))
        conn.commit()
        conn.close()
        return {"subscribed": False, "id": row["id"]}
    else:
        cursor.execute(
            "INSERT INTO subscriptions (actress_id, actress_name, auto_download, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            (actress_id, actress_name, auto_download)
        )
        conn.commit()
        sub_id = cursor.lastrowid
        conn.close()
        return {"subscribed": True, "id": sub_id}


def update_last_check(subscription_id: int, last_found: str = ""):
    """更新订阅的最后检查时间"""
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE subscriptions SET last_check = CURRENT_TIMESTAMP, last_found = ? WHERE id = ?",
        (last_found, subscription_id)
    )
    conn.commit()
    conn.close()


def get_subscription_by_actress(actress_id: int) -> dict | None:
    """根据 actress_id 获取订阅"""
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM subscriptions WHERE actress_id = ?", (actress_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_subscription(subscription_id: int, **kwargs):
    """更新订阅字段"""
    allowed = {"enabled", "auto_download"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [subscription_id]
    conn = get_db_orig()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE subscriptions SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()
