import logging
import asyncio
from config import config
from database import create_download_task, update_task_status, get_download_tasks, add_log
from services.downloaders import create_downloader_client, get_downloader_config, match_remote_task
from services.notification import notification_service

logger = logging.getLogger(__name__)

class DownloaderService:
    """下载调度服务"""

    async def create_download_task(
        self,
        code: str,
        title: str,
        magnet: str,
        path: str = "",
        downloader_id: str = "",
    ) -> int:
        downloader_config = get_downloader_config(downloader_id)
        if not downloader_config:
            raise RuntimeError("未配置可用下载器")
        if not path:
            path = downloader_config.get("default_path") or config.openlist_default_path

        task_id = create_download_task(
            code,
            title,
            magnet,
            path,
            downloader_id=downloader_config.get("id"),
            downloader_name=downloader_config.get("name"),
            downloader_type=downloader_config.get("type"),
        )

        client = create_downloader_client(downloader_config)
        result = await client.add_magnet(magnet, path, title)
        if result.success:
            update_task_status(task_id, "downloading", remote_task_id=result.remote_task_id)
            add_log("INFO", f"下载任务已创建: {code} -> {downloader_config.get('name')}")

            if config.notification_enabled and config.notification_auto_download:
                try:
                    asyncio.get_running_loop().create_task(
                        notification_service.notify_auto_download(code, title, title)
                    )
                except Exception:
                    pass
        else:
            error_msg = result.message or f"{downloader_config.get('name')} API 调用失败"
            update_task_status(task_id, "failed", error_msg)
            add_log("ERROR", f"下载任务创建失败: {code} -> {error_msg}")

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

        downloader_config = get_downloader_config(db_task.get("downloader_id"))
        if not downloader_config:
            return {"task_id": task_id, "status": db_task.get('status', 'unknown')}

        remote_tasks = await create_downloader_client(downloader_config).list_tasks()
        matched = match_remote_task(remote_tasks, magnet, db_task.get("remote_task_id") or info_hash or "")

        if not matched:
            return {"task_id": task_id, "status": db_task.get('status', 'unknown')}

        status = matched.get("status") or "unknown"

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
