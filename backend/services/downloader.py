import httpx
import asyncio
from typing import Optional
from config import config
from database import create_download_task, update_task_status, get_download_tasks, add_log
from services.openlist import openlist_client
from services.notification import notification_service

class DownloaderService:
    """下载调度服务"""

    def create_download_task(self, code: str, title: str, magnet: str, path: str = "") -> str:
        """
        创建下载任务并发送到OpenList
        """
        if not path:
            path = config.openlist_default_path

        # 创建数据库记录
        task_id = create_download_task(code, title, magnet, path)

        # 发送到OpenList
        result = openlist_client.add_offline_download(path, [magnet])
        if result:
            update_task_status(task_id, "downloading")
            add_log("INFO", f"下载任务已创建: {code}")

            # 发送通知
            if config.notification_enabled and config.notification_auto_download:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(
                            notification_service.notify_auto_download(code, title, title)
                        )
                    else:
                        loop.run_until_complete(
                            notification_service.notify_auto_download(code, title, title)
                        )
                except Exception as e:
                    pass  # 通知失败不影响主流程
        else:
            update_task_status(task_id, "failed", "OpenList API 调用失败")
            add_log("ERROR", f"下载任务创建失败: {code}")

        return task_id

    def get_all_tasks(self):
        """获取所有下载任务"""
        return get_download_tasks()

    def poll_task_status(self, task_id: str) -> dict:
        """
        轮询OpenList获取任务状态
        """
        tasks = openlist_client.get_offline_tasks()
        return {"task_id": task_id, "status": "unknown"}

    def update_all_task_statuses(self):
        """
        批量更新所有进行中任务的状态
        """
        tasks = get_download_tasks()

        for task in tasks:
            if task['status'] == 'downloading':
                try:
                    self.poll_task_status(task['id'])
                except:
                    pass

downloader_service = DownloaderService()
