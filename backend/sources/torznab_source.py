from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse
from xml.etree import ElementTree

import httpx

from models.video import MagnetInfo
from services.secret_redactor import redact_sensitive_text, sanitize_source_item_uris


class TorznabSearchError(RuntimeError):
    """A sanitized Torznab failure safe for registry/API observability."""


class TorznabSource:
    """Torznab/Newznab-compatible magnet source."""

    def __init__(
        self,
        kind: str = "prowlarr",
        name: str = "torznab",
        base_url: str = "",
        api_key: str = "",
        indexer: str = "all",
        categories: str = "",
        limit: int = 20,
        timeout: int = 15,
        enabled: bool = False,
    ):
        normalized_kind = str(kind or "prowlarr").strip().casefold()
        self.kind = (
            normalized_kind
            if normalized_kind in {"prowlarr", "jackett", "torznab"}
            else "prowlarr"
        )
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
        headers: dict[str, str] = {}
        if self.kind == "prowlarr":
            headers["X-Api-Key"] = self.api_key
        else:
            params["apikey"] = self.api_key

        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(
                    self._api_url(),
                    params=params,
                    headers=headers,
                )
                response.raise_for_status()
            return self._parse_results(response.text)
        except TorznabSearchError:
            raise
        except Exception as exc:
            raise TorznabSearchError(
                _safe_failure_message(exc, self.api_key)
            ) from None

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

        if self.kind == "prowlarr" and self.indexer.isdigit():
            return f"{self.base_url}/api/v1/indexer/{self.indexer}/newznab"
        return f"{self.base_url}/api/v2.0/indexers/{self.indexer}/results/torznab/api"

    def _parse_results(self, text: str) -> list[MagnetInfo]:
        root = ElementTree.fromstring(text)
        error = next(
            (node for node in root.iter() if _local_name(node.tag) == "error"),
            None,
        )
        if error is not None:
            code = _attr(error, "code")
            description = _first_present(
                _attr(error, "description"),
                str(error.text or "").strip(),
            )
            detail = ": ".join(part for part in (code, description) if part)
            message = "Torznab response error"
            if detail:
                message = f"{message}: {detail}"
            raise TorznabSearchError(
                redact_sensitive_text(message, secrets=(self.api_key,))
            )

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
        sanitized = sanitize_source_item_uris(result, secrets=(self.api_key,))
        if sanitized is not None:
            return sanitized

        fallback_magnet = _safe_info_hash_magnet(info_hash)
        if not fallback_magnet:
            return None
        result["magnet"] = fallback_magnet
        result.pop("download_url", None)
        result.pop("torrent_url", None)
        return sanitize_source_item_uris(result, secrets=(self.api_key,))


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


def _safe_info_hash_magnet(value: str | None) -> str:
    info_hash = str(value or "").strip()
    if re.fullmatch(r"[0-9a-fA-F]{40}", info_hash) or re.fullmatch(
        r"[A-Z2-7a-z2-7]{32}", info_hash
    ):
        return f"magnet:?xt=urn:btih:{info_hash}"
    return ""


def _safe_failure_message(exc: Exception, api_key: str) -> str:
    if isinstance(exc, ElementTree.ParseError):
        prefix = "Torznab XML parse failed"
    elif isinstance(exc, httpx.TimeoutException):
        prefix = "Torznab HTTP timeout"
    elif isinstance(exc, httpx.HTTPError):
        prefix = f"Torznab HTTP request failed ({type(exc).__name__})"
    else:
        prefix = f"Torznab search failed ({type(exc).__name__})"
    detail = redact_sensitive_text(exc, secrets=(api_key,))
    return f"{prefix}: {detail}" if detail else prefix
