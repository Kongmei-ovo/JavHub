import logging
import asyncio
from config import config
from database import create_download_task, update_task_status, get_download_task, get_download_tasks, add_log
from services.downloaders import create_downloader_client, get_downloader_config, match_remote_task
from services.notification import notification_service
from services.open115_downloader import Open115FinalizationError, open115_downloader

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
        downloader_type = str(downloader_config.get("type") or "")
        if downloader_type == "open115":
            task_id = create_download_task(
                code,
                title,
                magnet,
                "",
                downloader_id=downloader_config.get("id"),
                downloader_name=downloader_config.get("name"),
                downloader_type="open115",
                movie_id=code,
            )
            try:
                submission = await open115_downloader.submit(code, magnet)
                update_task_status(
                    task_id,
                    "downloading",
                    remote_task_id=submission.info_hash,
                    info_hash=submission.info_hash,
                    target_folder_id=submission.folder_id,
                    open115_task_id=submission.info_hash,
                    path=submission.path,
                )
                add_log("INFO", f"115 离线任务已创建: {code}")
            except Exception as exc:
                update_task_status(task_id, "failed", str(exc))
                add_log("ERROR", f"115 离线任务创建失败: {code}")
            return task_id
        if not path:
            path = downloader_config.get("default_path") or ""

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
                except RuntimeError:
                    logger.debug("No running event loop for auto-download notification")
        else:
            error_msg = result.message or f"{downloader_config.get('name')} API 调用失败"
            update_task_status(task_id, "failed", error_msg)
            add_log("ERROR", f"下载任务创建失败: {code} -> {error_msg}")

        return task_id

    def get_all_tasks(self):
        return get_download_tasks()

    async def poll_task_status(self, task_id: int) -> dict:
        from database import get_download_task, update_task_status

        db_task = get_download_task(task_id)
        if not db_task:
            return {"task_id": task_id, "status": "unknown"}

        magnet = db_task.get('magnet', '')
        if not magnet:
            return {"task_id": task_id, "status": "unknown"}

        if db_task.get("downloader_type") == "open115":
            info_hash = (
                db_task.get("info_hash")
                or db_task.get("open115_task_id")
                or db_task.get("remote_task_id")
            )
            matched = await open115_downloader.find_task(info_hash)
            if not matched:
                return {"task_id": task_id, "status": db_task.get("status", "unknown")}
            remote_status = int(matched.get("status") or 0)
            status = {
                -1: "failed",
                0: "pending",
                1: "downloading",
                2: "completed",
            }.get(remote_status, "unknown")
            if status == "failed":
                update_task_status(task_id, "failed", "115 离线任务失败")
                return {"task_id": task_id, "status": "failed"}
            if status != "completed":
                update_task_status(task_id, status)
                return {"task_id": task_id, "status": status}

            result_file_id = str(matched.get("file_id") or "")
            if not result_file_id:
                update_task_status(task_id, "failed", "115 完成任务未返回 file_id")
                return {"task_id": task_id, "status": "failed"}
            update_task_status(task_id, "finalizing", result_file_id=result_file_id)
            try:
                await open115_downloader.finalize(
                    task_id=task_id,
                    movie_id=str(db_task.get("movie_id") or db_task.get("content_id") or ""),
                    result_file_id=result_file_id,
                )
            except Open115FinalizationError as exc:
                update_task_status(task_id, "failed", str(exc), result_file_id=result_file_id)
                return {"task_id": task_id, "status": "failed"}
            update_task_status(task_id, "completed", error_msg="", result_file_id=result_file_id)
            return {"task_id": task_id, "status": "completed"}

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

    def _sync_acquisition_session(self, task_id: int) -> None:
        """Mirror an offline task's terminal outcome onto its acquisition session.

        Failures are classified with ``classify_candidate_error`` so the waiting
        page can show a structured reason instead of a raw 115 string."""
        from database.acquisition_session import (
            get_session_by_download_task,
            update_acquisition_session,
        )

        task = get_download_task(task_id)
        if not task:
            return
        session = get_session_by_download_task(task_id)
        if not session:
            return
        status = task.get("status")
        if status == "completed":
            update_acquisition_session(session["id"], status="ready")
        elif status == "failed":
            from services.candidate_processor import classify_candidate_error

            info = classify_candidate_error(task.get("error_msg"))
            update_acquisition_session(
                session["id"],
                status="failed",
                error_code=info.get("error_category"),
                error_msg=task.get("error_msg"),
            )
        elif status in {"finalizing", "downloading"} and session.get("status") != status:
            update_acquisition_session(session["id"], status=status)

    async def update_all_task_statuses(self):
        tasks = get_download_tasks()
        for task in tasks:
            if task['status'] in {'pending', 'downloading', 'finalizing'}:
                try:
                    await self.poll_task_status(task['id'])
                except Exception as e:
                    logger.warning(f"轮询任务状态失败 task_id={task['id']}: {e}")
                try:
                    self._sync_acquisition_session(task['id'])
                except Exception as e:
                    logger.warning(f"同步获取会话失败 task_id={task['id']}: {e}")

downloader_service = DownloaderService()
