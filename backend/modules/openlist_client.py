from __future__ import annotations
from typing import Optional

class OpenListClient:
    """OpenList (115) API 客户端"""

    def __init__(self, api_url: str, username: str, password: str, default_path: str):
        self.api_url = api_url.rstrip("/")
        self.username = username
        self.password = password
        self.default_path = default_path

    async def add_offline_download(self, magnet: str, path: Optional[str] = None) -> str:
        """添加离线下载，返回任务ID"""
        # TODO: 实现 OpenList API 调用
        return "mock_task_id"

    async def get_task_status(self, task_id: str) -> dict:
        """获取任务状态"""
        return {"status": "pending"}

    async def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        return True

_openlist_client: Optional[OpenListClient] = None

def get_openlist_client() -> OpenListClient:
    global _openlist_client
    if _openlist_client is None:
        from config import config
        openlist_config = config.openlist
        _openlist_client = OpenListClient(
            api_url=openlist_config.get("api_url", ""),
            username=openlist_config.get("username", ""),
            password=openlist_config.get("password", ""),
            default_path=openlist_config.get("default_path", "/115/AV"),
        )
    return _openlist_client