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
