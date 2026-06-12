"""ItemId-native 115 offline download orchestration."""
from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

from database import upsert_movie_resource
from services.open115 import Open115File, open115_client

VIDEO_EXTENSIONS = {
    "mp4", "mkv", "avi", "wmv", "ts", "m2ts", "iso", "webm", "mov", "m4v",
}
SUBTITLE_EXTENSIONS = {"srt", "ass", "ssa", "vtt", "sub"}


class Open115FinalizationError(RuntimeError):
    pass


@dataclass(frozen=True)
class Open115Submission:
    info_hash: str
    folder_id: str
    path: str


def encode_movie_directory(movie_id: str) -> str:
    raw = str(movie_id or "").encode("utf-8")
    if not raw:
        raise ValueError("movie_id is required")
    return "v1_" + base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_movie_directory(directory: str) -> str:
    encoded = str(directory or "")
    if not encoded.startswith("v1_"):
        raise ValueError("unsupported movie directory encoding")
    payload = encoded[3:]
    padding = "=" * (-len(payload) % 4)
    return base64.urlsafe_b64decode(payload + padding).decode("utf-8")


def _normalized_extension(file: Open115File) -> str:
    return str(file.extension or PurePosixPath(file.name).suffix).lower().lstrip(".")


def _stem(name: str) -> str:
    return PurePosixPath(name).stem.lower().strip()


def _matching_video_id(subtitle: Open115File, videos: list[tuple[Open115File, int]]) -> int | None:
    subtitle_stem = _stem(subtitle.name)
    matches = []
    for video, resource_id in videos:
        video_stem = _stem(video.name)
        if subtitle_stem == video_stem or subtitle_stem.startswith(
            (f"{video_stem}.", f"{video_stem}-", f"{video_stem}_")
        ):
            matches.append((len(video_stem), resource_id))
    if matches:
        return max(matches)[1]
    return videos[0][1] if videos else None


class Open115DownloaderClient:
    def __init__(self, client: Any = open115_client):
        self.client = client

    async def submit(self, movie_id: str, magnet: str) -> Open115Submission:
        target_path = f"{self.client.root_path.rstrip('/')}/{encode_movie_directory(movie_id)}"
        folder_id = await self.client.ensure_folder_path(target_path)
        hashes = await self.client.add_offline_task([magnet], folder_id)
        return Open115Submission(
            info_hash=str(hashes[0]),
            folder_id=str(folder_id),
            path=target_path,
        )

    async def find_task(self, info_hash: str) -> dict[str, Any] | None:
        wanted = str(info_hash or "").strip().lower()
        if not wanted:
            return None
        page = 1
        while True:
            result = await self.client.list_offline_tasks(page)
            tasks = result.get("tasks") or []
            for task in tasks:
                if str(task.get("info_hash") or "").lower() == wanted:
                    return task
            page_count = max(1, int(result.get("page_count") or 1))
            if page >= page_count:
                return None
            page += 1

    async def finalize(
        self,
        *,
        task_id: int,
        movie_id: str,
        result_file_id: str,
    ) -> dict[str, int]:
        files = [item async for item in self.client.walk_files(result_file_id)]
        videos = sorted(
            [item for item in files if _normalized_extension(item) in VIDEO_EXTENSIONS],
            key=lambda item: (-item.size, item.file_id),
        )
        subtitles = [
            item for item in files if _normalized_extension(item) in SUBTITLE_EXTENSIONS
        ]
        registered_videos: list[tuple[Open115File, int]] = []
        ready_count = 0
        for video in videos:
            ready = bool(video.pick_code)
            resource_id, _created = upsert_movie_resource(
                movie_id=movie_id,
                provider="open115",
                remote_file_id=video.file_id,
                parent_id=video.parent_id,
                pick_code=video.pick_code,
                name=video.name,
                extension=_normalized_extension(video),
                size=video.size,
                duration=video.duration,
                resource_type="video",
                status="ready" if ready else "missing",
                is_default=ready and ready_count == 0,
                download_task_id=task_id,
            )
            if ready:
                ready_count += 1
            registered_videos.append((video, resource_id))

        for subtitle in subtitles:
            upsert_movie_resource(
                movie_id=movie_id,
                provider="open115",
                remote_file_id=subtitle.file_id,
                parent_id=subtitle.parent_id,
                pick_code=subtitle.pick_code,
                name=subtitle.name,
                extension=_normalized_extension(subtitle),
                size=subtitle.size,
                duration=0,
                resource_type="subtitle",
                status="ready" if subtitle.pick_code else "missing",
                is_default=False,
                download_task_id=task_id,
                related_resource_id=_matching_video_id(subtitle, registered_videos),
            )

        if ready_count == 0:
            raise Open115FinalizationError("115 离线任务没有产生可播放视频")
        return {
            "video_count": len(videos),
            "ready_video_count": ready_count,
            "subtitle_count": len(subtitles),
        }


open115_downloader = Open115DownloaderClient()
