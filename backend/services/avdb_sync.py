"""Secure full-release synchronization for the AVDB public magnet index."""
from __future__ import annotations

import base64
import binascii
import csv
import hashlib
import html
import json
import logging
import re
import stat
import tempfile
import time
import zipfile
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Iterator
from urllib.parse import parse_qsl, urlsplit

import httpx

from config import config
from database.avdb import (
    avdb_sync_advisory_lock,
    get_avdb_status,
    get_avdb_sync_state,
    mark_avdb_sync_failed,
    mark_avdb_sync_running,
    mark_avdb_sync_unchanged,
    replace_avdb_generation,
)
from modules.code_matcher import extract_code, normalize_code


logger = logging.getLogger(__name__)

_GITHUB_API_VERSION = "2022-11-28"
_DOWNLOAD_CHUNK_SIZE = 1024 * 1024
_LATEST_TRANSPORT_ATTEMPTS = 3
_ASSET_TRANSPORT_ATTEMPTS = 3
_TRANSPORT_RETRY_BASE_SECONDS = 0.25
_CSV_FIELD_LIMIT = 4 * 1024 * 1024
_REQUIRED_CSV_COLUMNS = {"tid", "number", "title", "magnet"}
_HEX_INFO_HASH_RE = re.compile(r"^[0-9a-fA-F]{40}$")
_BASE32_INFO_HASH_RE = re.compile(r"^[A-Z2-7]{32}$", re.IGNORECASE)
_SHA256_RE = re.compile(r"^sha256:([0-9a-fA-F]{64})$")
_ASSET_NAME_RE = re.compile(
    r"^All_(sehuatang|x1080x)_(\d+)(?:_|\.zip$)",
    re.IGNORECASE,
)
_FC2_TITLE_RE = re.compile(
    r"(?<![A-Z0-9])(FC2[-_.\s]*PPV[-_.\s]*\d{4,})(?![A-Z0-9])",
    re.IGNORECASE,
)

csv.field_size_limit(_CSV_FIELD_LIMIT)


class AvdbSyncError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReleaseAsset:
    source: str
    name: str
    url: str
    size: int
    sha256: str
    expected_rows: int


@dataclass(frozen=True)
class DownloadedAsset:
    source: str
    name: str
    path: Path
    csv_member: str
    uncompressed_size: int
    expected_rows: int


def _parse_release_timestamp(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        raise AvdbSyncError("GitHub release is missing published_at")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AvdbSyncError("GitHub release published_at is invalid") from exc
    if parsed.tzinfo is None:
        raise AvdbSyncError("GitHub release published_at must include a timezone")
    return parsed.isoformat()


def _asset_from_payload(payload: dict[str, Any], *, source: str) -> ReleaseAsset:
    name = str(payload.get("name") or "").strip()
    name_match = _ASSET_NAME_RE.match(name)
    if not name_match or name_match.group(1).lower() != source:
        raise AvdbSyncError(f"AVDB asset {name or source} has an invalid filename")
    expected_rows = int(name_match.group(2))
    if expected_rows <= 0:
        raise AvdbSyncError(f"AVDB asset {name} has an invalid row count")
    url = str(payload.get("browser_download_url") or "").strip()
    parsed_url = urlsplit(url)
    if parsed_url.scheme != "https" or parsed_url.hostname != "github.com":
        raise AvdbSyncError(f"AVDB asset {name or source} has an unexpected download URL")
    try:
        size = int(payload.get("size") or 0)
    except (TypeError, ValueError) as exc:
        raise AvdbSyncError(f"AVDB asset {name or source} has an invalid size") from exc
    digest_match = _SHA256_RE.fullmatch(str(payload.get("digest") or "").strip())
    if not digest_match:
        raise AvdbSyncError(f"AVDB asset {name or source} is missing a SHA-256 digest")
    return ReleaseAsset(
        source=source,
        name=name,
        url=url,
        size=size,
        sha256=digest_match.group(1).lower(),
        expected_rows=expected_rows,
    )


def select_release_assets(release: dict[str, Any]) -> list[ReleaseAsset]:
    candidates = release.get("assets")
    if not isinstance(candidates, list):
        raise AvdbSyncError("GitHub release assets are missing")
    selected: list[ReleaseAsset] = []
    for source in ("sehuatang", "x1080x"):
        matches = [
            item
            for item in candidates
            if isinstance(item, dict)
            and str(item.get("name") or "").lower().startswith("all_")
            and str(item.get("name") or "").lower().endswith(".zip")
            and source in str(item.get("name") or "").lower()
        ]
        if len(matches) != 1:
            raise AvdbSyncError(f"expected exactly one All_{source} ZIP asset")
        selected.append(_asset_from_payload(matches[0], source=source))
    return selected


def release_asset_fingerprint(assets: Iterable[ReleaseAsset]) -> str:
    """Stable identity for the exact pair of release assets, excluding URLs."""
    manifest = [
        {
            "source": asset.source,
            "name": asset.name,
            "size": asset.size,
            "sha256": asset.sha256,
        }
        for asset in sorted(assets, key=lambda item: item.source)
    ]
    encoded = json.dumps(manifest, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _safe_zip_member_name(name: str) -> bool:
    normalized = str(name or "").replace("\\", "/")
    path = PurePosixPath(normalized)
    return bool(
        normalized
        and not normalized.startswith("/")
        and not re.match(r"^[A-Za-z]:", normalized)
        and ".." not in path.parts
    )


def validate_zip_archive(path: Path, *, max_uncompressed_bytes: int) -> tuple[str, int]:
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as exc:
        raise AvdbSyncError(f"invalid AVDB ZIP archive: {path.name}") from exc
    with archive:
        csv_members: list[zipfile.ZipInfo] = []
        total = 0
        for member in archive.infolist():
            if not _safe_zip_member_name(member.filename):
                raise AvdbSyncError(f"unsafe ZIP member path: {member.filename}")
            mode = member.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise AvdbSyncError(f"ZIP symlink is not allowed: {member.filename}")
            if member.flag_bits & 0x1:
                raise AvdbSyncError(f"encrypted ZIP member is not allowed: {member.filename}")
            if member.is_dir():
                continue
            total += int(member.file_size)
            if total > max_uncompressed_bytes:
                raise AvdbSyncError("AVDB ZIP exceeds the uncompressed size limit")
            if member.filename.lower().endswith(".csv"):
                csv_members.append(member)
        if len(csv_members) != 1:
            raise AvdbSyncError("each AVDB ZIP must contain exactly one CSV file")
        return csv_members[0].filename, total


def extract_info_hash(magnet: str | None) -> str | None:
    value = str(magnet or "").strip()
    parsed = urlsplit(value)
    if parsed.scheme.lower() != "magnet":
        return None
    for key, item in parse_qsl(parsed.query, keep_blank_values=False):
        if key.lower() != "xt" or not item.lower().startswith("urn:btih:"):
            continue
        digest = item.rsplit(":", 1)[-1].strip()
        if _HEX_INFO_HASH_RE.fullmatch(digest):
            return digest.lower()
        if _BASE32_INFO_HASH_RE.fullmatch(digest):
            try:
                decoded = base64.b32decode(digest.upper())
            except (binascii.Error, ValueError):
                continue
            return decoded.hex()
    return None


def _fallback_code_from_title(title: str) -> str:
    fc2_match = _FC2_TITLE_RE.search(title)
    if fc2_match:
        return normalize_code(fc2_match.group(1))
    return normalize_code(extract_code(title))


def _normalized_row_code(number: str, title: str) -> str:
    candidate = normalize_code(number)
    if candidate and any(ch.isalpha() for ch in candidate) and any(ch.isdigit() for ch in candidate):
        return candidate
    return _fallback_code_from_title(title)


def _record_from_csv(values: list[str], indexes: dict[str, int], *, source: str) -> dict[str, Any] | None:
    def get(name: str) -> str:
        index = indexes.get(name)
        if index is None or index >= len(values):
            return ""
        return str(values[index] or "").strip()

    title = get("title")[:4000]
    raw_magnet = get("magnet")
    if len(raw_magnet) > 8192:
        return None
    magnet = html.unescape(raw_magnet).strip()
    number = get("number")[:200]
    source_tid = get("tid")[:200]
    normalized_code = _normalized_row_code(number, title)
    info_hash = extract_info_hash(magnet)
    if not source_tid or not title or not info_hash or len(magnet) > 8192:
        return None
    return {
        "source": source,
        "source_tid": source_tid,
        "normalized_code": normalized_code or None,
        "number": number or None,
        "title": title,
        "magnet": magnet,
        "info_hash": info_hash,
        "size_text": get("size")[:100] or None,
        "publish_date": get("publish_date")[:100] or None,
    }


def iter_avdb_csv_records(
    asset: DownloadedAsset,
    *,
    stats: dict[str, int] | None = None,
) -> Iterator[dict[str, Any]]:
    counters = stats if stats is not None else {}
    counters.update(
        {
            "expected": asset.expected_rows,
            "total": 0,
            "valid": 0,
            "searchable": 0,
            "skipped": 0,
        }
    )
    try:
        archive = zipfile.ZipFile(asset.path)
        with archive, archive.open(asset.csv_member, "r") as binary:
            import io

            with io.TextIOWrapper(binary, encoding="utf-8-sig", newline="") as text:
                reader = csv.reader(text, strict=True)
                try:
                    header = next(reader)
                except StopIteration as exc:
                    raise AvdbSyncError(f"AVDB CSV is empty: {asset.name}") from exc
                normalized_header = [str(item or "").strip().lower() for item in header]
                if len(set(normalized_header)) != len(normalized_header):
                    raise AvdbSyncError(f"AVDB CSV has duplicate columns: {asset.name}")
                missing = _REQUIRED_CSV_COLUMNS.difference(normalized_header)
                if missing:
                    raise AvdbSyncError(
                        f"AVDB CSV {asset.name} is missing columns: {', '.join(sorted(missing))}"
                    )
                indexes = {name: index for index, name in enumerate(normalized_header)}
                for values in reader:
                    counters["total"] += 1
                    record = _record_from_csv(values, indexes, source=asset.source)
                    if record is not None:
                        counters["valid"] += 1
                        if record.get("normalized_code"):
                            counters["searchable"] += 1
                        yield record
                    else:
                        counters["skipped"] += 1
    except UnicodeDecodeError as exc:
        raise AvdbSyncError(f"AVDB CSV is not valid UTF-8: {asset.name}") from exc
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile, csv.Error) as exc:
        raise AvdbSyncError(f"failed to read AVDB CSV: {asset.name}") from exc


def _download_asset(
    client: httpx.Client,
    asset: ReleaseAsset,
    destination: Path,
    *,
    max_asset_bytes: int,
) -> int:
    if asset.size <= 0 or asset.size > max_asset_bytes:
        raise AvdbSyncError(f"AVDB asset {asset.name} exceeds the download size limit")
    for attempt in range(_ASSET_TRANSPORT_ATTEMPTS):
        digest = hashlib.sha256()
        downloaded = 0
        try:
            with client.stream(
                "GET",
                asset.url,
                headers={"Accept": "application/octet-stream", "Accept-Encoding": "identity"},
            ) as response:
                response.raise_for_status()
                content_length = response.headers.get("content-length")
                if content_length:
                    try:
                        declared = int(content_length)
                    except ValueError as exc:
                        raise AvdbSyncError(
                            f"AVDB asset {asset.name} has an invalid Content-Length"
                        ) from exc
                    if declared > max_asset_bytes:
                        raise AvdbSyncError(
                            f"AVDB asset {asset.name} exceeds the download size limit"
                        )
                with destination.open("xb") as output:
                    for chunk in response.iter_bytes(chunk_size=_DOWNLOAD_CHUNK_SIZE):
                        if not chunk:
                            continue
                        downloaded += len(chunk)
                        if downloaded > max_asset_bytes or downloaded > asset.size:
                            raise AvdbSyncError(
                                f"AVDB asset {asset.name} exceeded its declared size"
                            )
                        digest.update(chunk)
                        output.write(chunk)
        except httpx.TransportError as exc:
            destination.unlink(missing_ok=True)
            if attempt + 1 >= _ASSET_TRANSPORT_ATTEMPTS:
                raise AvdbSyncError(f"failed to download AVDB asset {asset.name}") from exc
            time.sleep(_TRANSPORT_RETRY_BASE_SECONDS * (attempt + 1))
            continue
        except httpx.HTTPError as exc:
            raise AvdbSyncError(f"failed to download AVDB asset {asset.name}") from exc

        if downloaded != asset.size:
            raise AvdbSyncError(f"AVDB asset {asset.name} size did not match GitHub metadata")
        if digest.hexdigest() != asset.sha256:
            raise AvdbSyncError(f"AVDB asset {asset.name} failed SHA-256 verification")
        return downloaded
    raise RuntimeError("unreachable AVDB asset retry state")


def _request_latest_release(
    client: httpx.Client,
    url: str,
    *,
    headers: dict[str, str],
) -> httpx.Response:
    """Retry only transient transport failures; HTTP responses are definitive."""
    for attempt in range(_LATEST_TRANSPORT_ATTEMPTS):
        try:
            response = client.get(url, headers=headers)
        except httpx.TransportError:
            if attempt + 1 >= _LATEST_TRANSPORT_ATTEMPTS:
                raise
            time.sleep(_TRANSPORT_RETRY_BASE_SECONDS * (attempt + 1))
            continue
        if response.status_code != 304:
            response.raise_for_status()
        return response
    raise RuntimeError("unreachable AVDB latest release retry state")


class AvdbSyncService:
    def __init__(self, *, settings: dict[str, Any] | None = None, client: httpx.Client | None = None):
        self.settings = dict(settings or config.avdb_source_config)
        self.client = client

    def _latest_url(self) -> str:
        # repository is normalized by Config to the one audited upstream.
        repository = str(self.settings.get("repository") or "li-peifeng/AVdb-Only")
        if repository != "li-peifeng/AVdb-Only":
            raise AvdbSyncError("unsupported AVDB repository")
        return f"https://api.github.com/repos/{repository}/releases/latest"

    def _new_client(self, *, proxy: str | None) -> httpx.Client:
        return httpx.Client(
            timeout=httpx.Timeout(float(self.settings.get("timeout") or 60)),
            follow_redirects=True,
            proxy=proxy,
            trust_env=False,
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": _GITHUB_API_VERSION,
                "User-Agent": "JavHub-AVDB-Sync",
            },
        )

    def sync(self) -> dict[str, Any]:
        with avdb_sync_advisory_lock() as acquired:
            if not acquired:
                return {**get_avdb_status(), "changed": False, "busy": True}
            state = get_avdb_sync_state()
            mark_avdb_sync_running()
            try:
                with ExitStack() as clients:
                    proxy_url = None
                    if self.client is not None:
                        client = self.client
                    else:
                        proxy_url = config.proxy_url.strip() or None
                        client = clients.enter_context(self._new_client(proxy=proxy_url))
                    headers: dict[str, str] = {}
                    if state.get("release_etag"):
                        headers["If-None-Match"] = str(state["release_etag"])
                    if state.get("release_last_modified"):
                        headers["If-Modified-Since"] = str(state["release_last_modified"])
                    try:
                        response = _request_latest_release(
                            client,
                            self._latest_url(),
                            headers=headers,
                        )
                    except httpx.TransportError as exc:
                        if self.client is None and proxy_url:
                            logger.warning(
                                "AVDB GitHub request failed through configured proxy; retrying directly"
                            )
                            client = clients.enter_context(self._new_client(proxy=None))
                            try:
                                response = _request_latest_release(
                                    client,
                                    self._latest_url(),
                                    headers=headers,
                                )
                            except httpx.HTTPError as direct_exc:
                                raise AvdbSyncError(
                                    "failed to check the AVDB GitHub release"
                                ) from direct_exc
                        else:
                            raise AvdbSyncError(
                                "failed to check the AVDB GitHub release"
                            ) from exc
                    except httpx.HTTPError as exc:
                        raise AvdbSyncError("failed to check the AVDB GitHub release") from exc
                    if response.status_code == 304:
                        mark_avdb_sync_unchanged(etag=None, last_modified=None)
                        return {**get_avdb_status(), "changed": False, "busy": False}
                    release = response.json()
                    if not isinstance(release, dict):
                        raise AvdbSyncError("GitHub latest release response is invalid")
                    try:
                        release_id = int(release.get("id") or 0)
                    except (TypeError, ValueError) as exc:
                        raise AvdbSyncError("GitHub release id is invalid") from exc
                    release_tag = str(release.get("tag_name") or "").strip()
                    release_published_at = _parse_release_timestamp(release.get("published_at"))
                    if release_id <= 0 or not release_tag:
                        raise AvdbSyncError("GitHub release identity is incomplete")
                    etag = response.headers.get("etag")
                    last_modified = response.headers.get("last-modified")
                    active_release_id = int(state.get("current_release_id") or 0)
                    if active_release_id > release_id:
                        raise AvdbSyncError("GitHub returned an older AVDB release than the active generation")

                    assets = select_release_assets(release)
                    asset_fingerprint = release_asset_fingerprint(assets)
                    if (
                        active_release_id == release_id
                        and state.get("active_generation")
                        and state.get("asset_fingerprint") == asset_fingerprint
                    ):
                        mark_avdb_sync_unchanged(etag=etag, last_modified=last_modified)
                        return {**get_avdb_status(), "changed": False, "busy": False}
                    max_asset_bytes = int(self.settings.get("max_asset_bytes") or 0)
                    max_total_download = int(self.settings.get("max_total_download_bytes") or 0)
                    max_uncompressed = int(self.settings.get("max_uncompressed_bytes") or 0)
                    if sum(asset.size for asset in assets) > max_total_download:
                        raise AvdbSyncError("AVDB release exceeds the total download size limit")

                    with tempfile.TemporaryDirectory(prefix="javhub-avdb-") as temp_dir:
                        downloaded_assets: list[DownloadedAsset] = []
                        total_downloaded = 0
                        total_uncompressed = 0
                        for index, asset in enumerate(assets):
                            destination = Path(temp_dir) / f"asset-{index}.zip"
                            total_downloaded += _download_asset(
                                client,
                                asset,
                                destination,
                                max_asset_bytes=max_asset_bytes,
                            )
                            if total_downloaded > max_total_download:
                                raise AvdbSyncError("AVDB release exceeds the total download size limit")
                            csv_member, archive_size = validate_zip_archive(
                                destination,
                                max_uncompressed_bytes=max_uncompressed - total_uncompressed,
                            )
                            total_uncompressed += archive_size
                            downloaded_assets.append(
                                DownloadedAsset(
                                    source=asset.source,
                                    name=asset.name,
                                    path=destination,
                                    csv_member=csv_member,
                                    uncompressed_size=archive_size,
                                    expected_rows=asset.expected_rows,
                                )
                            )

                        streams: list[tuple[str, Iterable[dict[str, Any]], dict[str, int]]] = []
                        for asset in downloaded_assets:
                            stats: dict[str, int] = {"expected": asset.expected_rows}
                            streams.append(
                                (asset.source, iter_avdb_csv_records(asset, stats=stats), stats)
                            )
                        imported = replace_avdb_generation(
                            release_id=release_id,
                            release_tag=release_tag,
                            release_published_at=release_published_at,
                            asset_fingerprint=asset_fingerprint,
                            etag=etag,
                            last_modified=last_modified,
                            assets=streams,
                            batch_size=int(self.settings.get("batch_size") or 1000),
                            keep_generations=int(self.settings.get("keep_generations") or 2),
                            min_source_records=int(self.settings.get("min_source_records") or 1000),
                            min_searchable_records=int(
                                self.settings.get("min_searchable_records") or 1000
                            ),
                            min_source_ratio=float(self.settings.get("min_source_ratio") or 0.5),
                            max_skipped_ratio=float(
                                self.settings.get("max_skipped_ratio")
                                if self.settings.get("max_skipped_ratio") is not None
                                else 0.05
                            ),
                        )
                    return {**get_avdb_status(), **imported, "changed": True, "busy": False}
            except Exception as exc:
                try:
                    mark_avdb_sync_failed(str(exc) or exc.__class__.__name__)
                except Exception:
                    logger.exception("Failed to persist AVDB sync failure state")
                raise


def sync_avdb_release() -> dict[str, Any]:
    return AvdbSyncService().sync()
