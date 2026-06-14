"""Image field selection shared by Emby DTOs and image routes."""
from __future__ import annotations

import hashlib
from typing import Any

DMM_ACTRESS_AVATAR_BASE = (
    "https://awsimgsrc.dmm.co.jp/pics_dig/mono/actjpgs/"
)


def image_tag(url: str) -> str:
    """Return a stable cache tag that changes when the selected image changes."""
    value = str(url or "").strip()
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16] if value else ""


def movie_primary_image_url(metadata: dict | None) -> str:
    """Use the same cover as JavHub movie cards, with detail art as fallback."""
    metadata = metadata or {}
    return str(
        metadata.get("jacket_thumb_url")
        or metadata.get("jacket_full_url")
        or ""
    ).strip()


def movie_backdrop_image_urls(metadata: dict | None) -> list[str]:
    """Return only genuine landscape/detail images, never the primary cover."""
    metadata = metadata or {}
    raw_images: Any = (
        metadata.get("sample_image_urls")
        or metadata.get("sample_images")
        or []
    )
    if isinstance(raw_images, (str, dict)):
        raw_images = [raw_images]

    images: list[str] = []
    seen: set[str] = set()
    if isinstance(raw_images, list):
        for image in raw_images:
            if isinstance(image, dict):
                value = (
                    image.get("url")
                    or image.get("image_url")
                    or image.get("full_url")
                    or ""
                )
            else:
                value = image
            url = str(value or "").strip()
            if url and url not in seen:
                images.append(url)
                seen.add(url)

    if images:
        return images
    backdrop = str(metadata.get("backdrop_url") or "").strip()
    return [backdrop] if backdrop else []


def actress_image_url(item: dict | None) -> str:
    """Resolve JavInfo's absolute URLs and legacy DMM avatar filenames."""
    item = item or {}
    raw = str(
        item.get("image_url")
        or item.get("avatar_url")
        or item.get("javinfo_avatar_url")
        or ""
    ).strip()
    if not raw:
        return ""
    if raw.lower().startswith(("http://", "https://")):
        return raw

    path = raw.lstrip("/")
    if path.startswith("pics_dig/"):
        return f"https://awsimgsrc.dmm.co.jp/{path}"
    if path.startswith("mono/actjpgs/"):
        return f"https://awsimgsrc.dmm.co.jp/pics_dig/{path}"
    return f"{DMM_ACTRESS_AVATAR_BASE}{path}"
