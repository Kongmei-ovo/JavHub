from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse
from xml.etree import ElementTree

import httpx

from models.video import MagnetInfo


class TorznabSource:
    """Torznab/Newznab-compatible magnet source."""

    def __init__(
        self,
        name: str = "torznab",
        base_url: str = "",
        api_key: str = "",
        indexer: str = "all",
        categories: str = "",
        limit: int = 20,
        timeout: int = 15,
        enabled: bool = False,
    ):
        self.name = name
        self.base_url = base_url.strip().rstrip("/")
        self.api_key = api_key.strip()
        self.indexer = (indexer or "all").strip() or "all"
        self.categories = categories.strip()
        self.limit = limit
        self.timeout = timeout
        self.enabled = enabled

    def is_implemented(self) -> bool:
        return bool(self.enabled and self.base_url and self.api_key)

    async def search(self, keyword: str) -> list[MagnetInfo]:
        keyword = str(keyword or "").strip()
        if not self.is_implemented() or not keyword:
            return []

        params: dict[str, Any] = {
            "t": "search",
            "q": keyword,
            "limit": self.limit,
        }
        if self.categories:
            params["cat"] = self.categories

        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(
                    self._api_url(),
                    params=params,
                    headers={"X-Api-Key": self.api_key},
                )
                response.raise_for_status()
            return self._parse_results(response.text)
        except (httpx.HTTPError, ElementTree.ParseError, ValueError, TypeError):
            return []

    async def get_detail(self, content_id: str) -> dict | None:
        return None

    async def get_actress_videos(self, actress_name: str) -> list:
        return []

    def _api_url(self) -> str:
        if "{indexer}" in self.base_url:
            return self.base_url.format(indexer=self.indexer)

        parsed = urlparse(self.base_url)
        path = parsed.path.rstrip("/").lower()
        if path.endswith("/api") or path.endswith("/newznab"):
            return self.base_url

        if self.indexer.isdigit():
            return f"{self.base_url}/api/v1/indexer/{self.indexer}/newznab"
        return f"{self.base_url}/api/v2.0/indexers/{self.indexer}/results/torznab/api"

    def _parse_results(self, text: str) -> list[MagnetInfo]:
        root = ElementTree.fromstring(text)
        if _local_name(root.tag) == "error":
            return []
        if any(_local_name(child.tag) == "error" for child in root.iter()):
            return []

        results = []
        for item in (node for node in root.iter() if _local_name(node.tag) == "item"):
            parsed = self._parse_item(item)
            if parsed:
                results.append(parsed)
        return results

    def _parse_item(self, item: ElementTree.Element) -> MagnetInfo | None:
        attrs = _torznab_attrs(item)
        title = _child_text(item, "title") or ""
        enclosure = _first_child(item, "enclosure")
        enclosure_url = _attr(enclosure, "url") if enclosure is not None else ""
        link_text = _child_text(item, "link")
        guid_text = _child_text(item, "guid")

        magnet = _first_present(
            attrs.get("magneturl"),
            attrs.get("magneturi"),
            enclosure_url if _is_magnet(enclosure_url) else "",
            link_text if _is_magnet(link_text) else "",
            guid_text if _is_magnet(guid_text) else "",
        )

        download_url = _first_present(
            enclosure_url if _is_http(enclosure_url) else "",
            link_text if _is_http(link_text) else "",
            guid_text if _is_http(guid_text) else "",
        )
        if not magnet and not download_url:
            return None

        size_value = _first_present(
            attrs.get("size"),
            _attr(enclosure, "length") if enclosure is not None else "",
        )
        seeders = _to_int(_first_present(attrs.get("seeders"), attrs.get("seeds")))
        leechers = _to_int(attrs.get("leechers"))
        peers = _to_int(attrs.get("peers"))
        info_hash = _first_present(attrs.get("infohash"), attrs.get("info_hash"))
        resolution, quality, hd = _quality_flags(title)

        result = {
            "magnet": magnet,
            "title": title,
            "size": _display_size(size_value),
            "quality": quality,
            "resolution": resolution,
            "hd": hd,
            "subtitle": _has_subtitle(title),
            "source": self.name,
        }
        if download_url:
            result["download_url"] = download_url
            result["torrent_url"] = download_url
        if seeders is not None:
            result["seeders"] = seeders
        if leechers is not None:
            result["leechers"] = leechers
        if peers is not None:
            result["peers"] = peers
        if info_hash:
            result["info_hash"] = info_hash
        return result


def _local_name(value: str) -> str:
    return value.rsplit("}", 1)[-1].lower()


def _attr(element: ElementTree.Element | None, name: str) -> str:
    if element is None:
        return ""
    wanted = name.lower()
    for key, value in element.attrib.items():
        if _local_name(key) == wanted:
            return str(value or "").strip()
    return ""


def _first_child(element: ElementTree.Element, name: str) -> ElementTree.Element | None:
    wanted = name.lower()
    for child in element:
        if _local_name(child.tag) == wanted:
            return child
    return None


def _child_text(element: ElementTree.Element, name: str) -> str:
    child = _first_child(element, name)
    return str(child.text or "").strip() if child is not None else ""


def _torznab_attrs(item: ElementTree.Element) -> dict[str, str]:
    attrs = {}
    for child in item:
        if _local_name(child.tag) not in {"attr", "attribute"}:
            continue
        name = _attr(child, "name").lower().replace("-", "_")
        value = _attr(child, "value")
        if name and value:
            attrs[name] = value
    return attrs


def _first_present(*values: str | None) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _is_magnet(value: str | None) -> bool:
    return str(value or "").strip().lower().startswith("magnet:")


def _is_http(value: str | None) -> bool:
    text = str(value or "").strip().lower()
    return text.startswith("http://") or text.startswith("https://")


def _to_int(value: str | None) -> int | None:
    try:
        return int(str(value or "").strip())
    except ValueError:
        return None


def _display_size(value: str | None) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if not re.fullmatch(r"\d+", text):
        return text

    bytes_value = int(text)
    units = (("TB", 1024**4), ("GB", 1024**3), ("MB", 1024**2), ("KB", 1024), ("B", 1))
    for unit, factor in units:
        if bytes_value >= factor or unit == "B":
            return f"{bytes_value / factor:.1f}{unit}"
    return ""


def _quality_flags(title: str) -> tuple[str | None, str | None, bool]:
    lowered = title.lower()
    resolution = None
    if "2160" in lowered or "4k" in lowered:
        resolution = "2160p"
    elif "1080" in lowered:
        resolution = "1080p"
    elif "720" in lowered:
        resolution = "720p"

    hd = bool(resolution) or any(token in lowered for token in (" hd", ".hd", "_hd", "fhd", "uhd", "bluray", "web-dl"))
    quality = "4K" if resolution == "2160p" else "HD" if hd else None
    return resolution, quality, hd


def _has_subtitle(title: str) -> bool:
    lowered = title.lower()
    return any(token in lowered for token in ("字幕", "subtitle", "subtitles", " sub", ".sub", "_sub", "chs", "cht", "zh"))
