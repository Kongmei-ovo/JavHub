import logging
import asyncio
import re
import urllib.parse
from config import config
from database import create_download_task, update_task_status, get_download_task, get_download_tasks, add_log
from services.downloaders import create_downloader_client, get_downloader_config, match_remote_task
from services.notification import notification_service
from services.open115_downloader import (
    Open115FinalizationError,
    Open115NotReadyError,
    open115_downloader,
)

logger = logging.getLogger(__name__)

OPEN115_NATIVE_NAME = "115 Open（原生）"


def _offline_link_title(url: str) -> str:
    """Best-effort display title for a raw cloud-download link: the magnet's
    ``dn`` name, then an ed2k/http basename, then the bare hash/url."""
    match = re.search(r"[?&]dn=([^&]+)", url)
    if match:
        try:
            name = urllib.parse.unquote_plus(match.group(1)).strip()
            if name:
                return name[:120]
        except Exception:
            pass
    ed2k = re.match(r"ed2k://\|file\|([^|]+)\|", url, re.IGNORECASE)
    if ed2k:
        return urllib.parse.unquote(ed2k.group(1)).strip()[:120] or url[:120]
    if url.lower().startswith(("http://", "https://")):
        tail = url.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]
        if tail:
            return urllib.parse.unquote(tail)[:120]
    return url[:120]

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

    async def create_open115_offline_tasks(self, urls: list[str], cid: str) -> dict:
        """Add raw magnet/url links to 115 offline, landing them in ``cid`` (the
        folder the user is browsing), and register each accepted link as a
        tracked ``kind="offline"`` download task so the coordinator polls it to
        completion. These have no movie semantics — completion skips finalize."""
        from services.open115 import Open115Error, open115_client

        cid = str(cid or "0")
        added: list[dict] = []
        skipped: list[dict] = []
        for raw in urls:
            url = str(raw or "").strip()
            if not url:
                continue
            title = _offline_link_title(url)
            try:
                hashes = await open115_client.add_offline_task([url], cid)
            except Open115Error as exc:
                skipped.append({"url": url, "reason": exc.api_message})
                continue
            info_hash = str(hashes[0])
            task_id = create_download_task(
                info_hash,
                title,
                url,
                "",
                downloader_id="open115",
                downloader_name=OPEN115_NATIVE_NAME,
                downloader_type="open115",
                movie_id=info_hash,
                info_hash=info_hash,
                target_folder_id=cid,
                open115_task_id=info_hash,
                kind="offline",
            )
            update_task_status(task_id, "downloading", remote_task_id=info_hash)
            added.append({"info_hash": info_hash, "title": title, "task_id": task_id})
            add_log("INFO", f"115 离线任务已添加: {title}")
        return {"added": added, "skipped": skipped}

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
            # Raw 115 offline adds (kind="offline") just land files in the user's
            # chosen folder — they have no movie identity. Completing them must NOT
            # run the movie finalize (which would pollute movie_resources and fail
            # on non-AV content). This is the fix for raw adds "never finishing".
            if db_task.get("kind") == "offline":
                update_task_status(
                    task_id, "completed", error_msg="", result_file_id=result_file_id or None
                )
                return {"task_id": task_id, "status": "completed"}

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
            except Open115NotReadyError:
                # Videos are there but 115 hasn't assigned pick codes yet; stay in
                # "finalizing" so the next coordinator pass retries instead of
                # false-failing a good download.
                update_task_status(task_id, "finalizing", result_file_id=result_file_id)
                return {"task_id": task_id, "status": "finalizing"}
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
