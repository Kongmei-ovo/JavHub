import logging
import asyncio
from typing import Optional
from config import config
from database import create_download_task, update_task_status, get_download_tasks, add_log
from services.openlist import openlist_client
from services.notification import notification_service

logger = logging.getLogger(__name__)

class DownloaderService:
    """下载调度服务"""

    async def create_download_task(self, code: str, title: str, magnet: str, path: str = "") -> str:
        if not path:
            path = config.openlist_default_path

        task_id = create_download_task(code, title, magnet, path)

        result = await openlist_client.add_offline_download(path, [magnet])
        if result:
            update_task_status(task_id, "downloading")
            add_log("INFO", f"下载任务已创建: {code}")

            if config.notification_enabled and config.notification_auto_download:
                try:
                    asyncio.get_running_loop().create_task(
                        notification_service.notify_auto_download(code, title, title)
                    )
                except Exception:
                    pass
        else:
            update_task_status(task_id, "failed", "OpenList API 调用失败")
            add_log("ERROR", f"下载任务创建失败: {code}")

        return task_id

    def get_all_tasks(self):
        return get_download_tasks()

    async def poll_task_status(self, task_id: int) -> dict:
        from database import get_download_tasks, update_task_status

        db_tasks = get_download_tasks(limit=500)
        db_task = next((t for t in db_tasks if t['id'] == task_id), None)
        if not db_task:
            return {"task_id": task_id, "status": "unknown"}

        magnet = db_task.get('magnet', '')
        if not magnet:
            return {"task_id": task_id, "status": "unknown"}

        import re
        hash_match = re.search(r'btih:([a-fA-F0-9]{40}|[a-zA-Z0-9]{32})', magnet)
        info_hash = hash_match.group(1).lower() if hash_match else None

        openlist_tasks = await openlist_client.get_offline_tasks()

        matched = None
        if info_hash:
            matched = next(
                (t for t in openlist_tasks if t.get('hash', '').lower() == info_hash),
                None
            )

        if not matched:
            return {"task_id": task_id, "status": db_task.get('status', 'unknown')}

        state = matched.get('state', -1)
        if state == 2:
            status = 'completed'
        elif state == 7:
            status = 'failed'
        elif state in (0, 1):
            status = 'downloading'
        else:
            status = 'unknown'

        update_task_status(task_id, status)
        return {"task_id": task_id, "status": status}

    async def update_all_task_statuses(self):
        tasks = get_download_tasks()
        for task in tasks:
            if task['status'] == 'downloading':
                try:
                    await self.poll_task_status(task['id'])
                except Exception as e:
                    logger.warning(f"轮询任务状态失败 task_id={task['id']}: {e}")

downloader_service = DownloaderService()
