"""Deferred Emby playback descriptions and final source selection."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

from services.emby_mapper import seconds_to_ticks

PlaybackKind = Literal["open115", "online"]


def _container_of(name: str) -> str:
    lowered = str(name or "").lower()
    return lowered.rsplit(".", 1)[-1] if "." in lowered else "mp4"


def _media_source_dto(resource: dict, item_id: str, token: str = "") -> dict:
    source_id = f"open115:{resource['id']}"
    container = str(
        resource.get("extension") or _container_of(resource.get("name"))
    ).lower().lstrip(".")
    stream_url = (
        f"/Videos/{item_id}/stream.{container}"
        f"?MediaSourceId={source_id}&Static=true"
    )
    if token:
        stream_url += f"&api_key={token}"
    source = {
        "Id": source_id,
        "Protocol": "Http",
        "Container": container,
        "Size": int(resource.get("size") or 0),
        "Name": resource.get("name") or "",
        "Path": stream_url,
        "IsRemote": True,
        "SupportsDirectPlay": True,
        "SupportsDirectStream": True,
        "SupportsTranscoding": container not in {"mp4", "webm"},
        "Type": "Default",
        "RunTimeTicks": seconds_to_ticks(resource.get("duration")),
        "RequiresOpening": False,
        "RequiresClosing": False,
        "SupportsProbing": False,
        "DirectStreamUrl": stream_url,
        "MediaStreams": [
            {
                "Codec": "unknown",
                "Type": "Video",
                "Index": 0,
                "IsDefault": True,
                "IsForced": False,
                "IsExternal": False,
                "DisplayTitle": container.upper() or "Video",
            }
        ],
        "RequiredHttpHeaders": {},
    }
    if source["SupportsTranscoding"]:
        hls_url = (
            f"/Videos/{item_id}/stream.m3u8"
            f"?MediaSourceId={source_id}&mode=hls&Static=true"
        )
        if token:
            hls_url += f"&api_key={token}"
        source["TranscodingUrl"] = hls_url
        source["TranscodingContainer"] = "m3u8"
        source["TranscodingSubProtocol"] = "hls"
    return source


def _online_media_source_dto(item_id: str, token: str = "") -> dict:
    stream_url = (
        f"/Videos/{item_id}/stream.m3u8"
        "?MediaSourceId=online:auto&Static=true"
    )
    if token:
        stream_url += f"&api_key={token}"
    return {
        "Id": "online:auto",
        "Protocol": "Http",
        "Container": "m3u8",
        "Name": "在线源（按播放请求检测）",
        "Path": stream_url,
        "IsRemote": True,
        "SupportsDirectPlay": True,
        "SupportsDirectStream": True,
        "SupportsTranscoding": False,
        "Type": "Default",
        "RequiresOpening": False,
        "RequiresClosing": False,
        "DirectStreamUrl": stream_url,
        "MediaStreams": [
            {
                "Codec": "h264",
                "Type": "Video",
                "Index": 0,
                "IsDefault": True,
                "IsForced": False,
                "IsExternal": False,
                "DisplayTitle": "Deferred Online HLS",
            }
        ],
        "RequiredHttpHeaders": {},
    }


@dataclass(frozen=True)
class PlaybackSelection:
    kind: PlaybackKind
    resource: dict | None = None


class EmbyPlaybackBroker:
    """Keep catalog reads separate from source selection and resolution."""

    @staticmethod
    def describe(item_id: str, token: str, resources: list[dict]) -> list[dict]:
        ready_videos = [
            resource
            for resource in resources
            if resource.get("resource_type") == "video"
            and resource.get("status") == "ready"
        ]
        ready_videos.sort(
            key=lambda resource: (
                not bool(resource.get("is_default")),
                -int(resource.get("size") or 0),
            )
        )
        sources = [
            _media_source_dto(resource, item_id, token=token)
            for resource in ready_videos
        ]
        sources.append(_online_media_source_dto(item_id, token=token))
        return sources

    @staticmethod
    def select(
        item_id: str,
        media_source_id: str,
        *,
        get_resource: Callable[[int], dict | None],
        list_resources: Callable[[str], list[dict]],
    ) -> PlaybackSelection | None:
        if media_source_id == "online:auto":
            return PlaybackSelection(kind="online")

        resource = None
        if media_source_id.startswith("open115:"):
            try:
                resource_id = int(media_source_id.split(":", 1)[1])
            except ValueError:
                return None
            resource = get_resource(resource_id)
        elif not media_source_id:
            resources = [
                item
                for item in list_resources(item_id)
                if item.get("resource_type") == "video"
                and item.get("status") == "ready"
            ]
            resource = next(
                (item for item in resources if item.get("is_default")),
                resources[0] if resources else None,
            )
            if resource is None:
                return PlaybackSelection(kind="online")

        if not resource or str(resource.get("movie_id")) != item_id:
            return None
        return PlaybackSelection(kind="open115", resource=resource)

    @staticmethod
    def probe_media_type(extension: str) -> str:
        extension = str(extension or "").lower().lstrip(".")
        if extension in {"m3u8", "m3u"}:
            return "application/vnd.apple.mpegurl"
        if extension == "mp4":
            return "video/mp4"
        if extension == "webm":
            return "video/webm"
        if extension == "mkv":
            return "video/x-matroska"
        return "application/octet-stream"


emby_playback_broker = EmbyPlaybackBroker()
