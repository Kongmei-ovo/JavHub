from __future__ import annotations

import hashlib
import io
import unittest
import zipfile
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

import httpx

from test_support.client import create_router_test_client
from test_support.postgres import TempPostgresMixin


HEX_A = "0123456789abcdef0123456789abcdef01234567"
HEX_B = "89abcdef0123456789abcdef0123456789abcdef"


def _zip_csv(csv_text: str, *, member: str = "data.csv") -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(member, csv_text.encode("utf-8"))
    return output.getvalue()


def _asset(name: str, content: bytes, url_suffix: str) -> dict:
    return {
        "name": name,
        "size": len(content),
        "digest": f"sha256:{hashlib.sha256(content).hexdigest()}",
        "browser_download_url": f"https://github.com/li-peifeng/AVdb-Only/releases/download/test/{url_suffix}",
    }


def _settings(**overrides) -> dict:
    return {
        "repository": "li-peifeng/AVdb-Only",
        "timeout": 5,
        "batch_size": 100,
        "keep_generations": 2,
        "min_source_records": 1,
        "min_searchable_records": 1,
        "min_source_ratio": 0.5,
        "max_skipped_ratio": 0.5,
        "max_asset_bytes": 1024 * 1024,
        "max_total_download_bytes": 2 * 1024 * 1024,
        "max_uncompressed_bytes": 4 * 1024 * 1024,
        **overrides,
    }


class AvdbArchiveAndCsvTests(unittest.TestCase):
    def test_old_and_new_csv_schemas_stream_rows_and_keep_rows_without_a_code(self):
        from services.avdb_sync import DownloadedAsset, iter_avdb_csv_records, validate_zip_archive

        csv_text = (
            "tid,emby,number,title,publish_date,magnet,size,website\n"
            f"1,,ABC-123,ABC-123 1080p,2026-07-01,magnet:?xt=urn:btih:{HEX_A}&amp;dn=ABC-123,3930,sehuatang\n"
            f"2,,,没有可提取番号的标题,2026-07-02,magnet:?xt=urn:btih:{HEX_B},,sehuatang\n"
        )
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "asset.zip"
            path.write_bytes(_zip_csv(csv_text))
            member, size = validate_zip_archive(path, max_uncompressed_bytes=1024 * 1024)
            stats = {}
            rows = list(iter_avdb_csv_records(
                DownloadedAsset("sehuatang", "asset.zip", path, member, size, 2),
                stats=stats,
            ))

        self.assertEqual([row["normalized_code"] for row in rows], ["ABC123", None])
        self.assertIn("&dn=ABC-123", rows[0]["magnet"])
        self.assertNotIn("&amp;", rows[0]["magnet"])
        self.assertEqual(
            stats,
            {"expected": 2, "total": 2, "valid": 2, "searchable": 1, "skipped": 0},
        )

    def test_title_fallback_handles_fc2_and_invalid_magnets_are_counted_as_skipped(self):
        from services.avdb_sync import DownloadedAsset, iter_avdb_csv_records, validate_zip_archive
        import tempfile
        from pathlib import Path

        csv_text = (
            "tid,number,title,publish_date,magnet,sub_type\n"
            f"1,,FC2-PPV-4282620 sample,2026-07-01,magnet:?xt=urn:btih:{HEX_A},\n"
            "2,ABC-999,ABC-999 bad,2026-07-01,magnet:?xt=urn:btih:not-a-hash,\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "asset.zip"
            path.write_bytes(_zip_csv(csv_text))
            member, size = validate_zip_archive(path, max_uncompressed_bytes=1024 * 1024)
            stats = {}
            rows = list(iter_avdb_csv_records(
                DownloadedAsset("x1080x", "asset.zip", path, member, size, 2),
                stats=stats,
            ))

        self.assertEqual(rows[0]["normalized_code"], "FC2PPV4282620")
        self.assertEqual(
            stats,
            {"expected": 2, "total": 2, "valid": 1, "searchable": 1, "skipped": 1},
        )

    def test_zip_slip_member_is_rejected(self):
        from services.avdb_sync import AvdbSyncError, validate_zip_archive
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unsafe.zip"
            path.write_bytes(_zip_csv("tid,number,title,magnet\n", member="../escape.csv"))
            with self.assertRaisesRegex(AvdbSyncError, "unsafe ZIP member"):
                validate_zip_archive(path, max_uncompressed_bytes=1024 * 1024)

    def test_oversized_raw_magnet_is_rejected_before_html_unescape(self):
        from services.avdb_sync import _record_from_csv

        raw_magnet = "magnet:?xt=urn:btih:" + HEX_A + ("x" * 8192)
        indexes = {"tid": 0, "number": 1, "title": 2, "magnet": 3}
        with patch("services.avdb_sync.html.unescape", side_effect=AssertionError("must not run")):
            record = _record_from_csv(
                ["1", "ABC-123", "ABC-123", raw_magnet],
                indexes,
                source="sehuatang",
            )
        self.assertIsNone(record)


class AvdbSyncServiceTests(unittest.TestCase):
    def _release_and_payloads(self):
        sehuatang = _zip_csv(
            "tid,emby,number,title,publish_date,magnet,size\n"
            f"1,,ABC-123,ABC-123 中文字幕 1080p,2026-07-01,magnet:?xt=urn:btih:{HEX_A},3930\n"
        )
        x1080x = _zip_csv(
            "tid,number,title,publish_date,magnet,size,sub_type\n"
            f"2,XYZ-987,XYZ-987,2026-07-02,magnet:?xt=urn:btih:{HEX_B},1200,\n"
        )
        assets = [
            _asset("All_sehuatang_1_test.zip", sehuatang, "sehuatang.zip"),
            _asset("All_X1080X_1_test.zip", x1080x, "x1080x.zip"),
        ]
        release = {
            "id": 101,
            "tag_name": "2026-07-13",
            "published_at": "2026-07-13T12:02:11Z",
            "assets": assets,
        }
        return release, {assets[0]["browser_download_url"]: sehuatang, assets[1]["browser_download_url"]: x1080x}

    @contextmanager
    def _lock(self):
        yield True

    def test_same_release_changed_fingerprint_downloads_and_replaces_generation(self):
        from services.avdb_sync import AvdbSyncService

        release, payloads = self._release_and_payloads()

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.host == "api.github.com":
                return httpx.Response(200, json=release, headers={"ETag": '"release-101"'})
            content = payloads[str(request.url)]
            return httpx.Response(200, content=content, headers={"Content-Length": str(len(content))})

        captured = {}

        def fake_replace(**kwargs):
            captured.update(kwargs)
            rows = {}
            stats = {}
            for source, records, counters in kwargs["assets"]:
                rows[source] = list(records)
                stats[source] = dict(counters)
            captured["rows"] = rows
            captured["stats"] = stats
            return {"generation_id": "new-gen", "record_count": 2, "source_counts": {"sehuatang": 1, "x1080x": 1}}

        client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)
        with patch("services.avdb_sync.avdb_sync_advisory_lock", self._lock), \
             patch("services.avdb_sync.get_avdb_sync_state", return_value={
                 "status": "running",
                 "current_release_id": 101,
                 "active_generation": "old-gen",
                 "asset_fingerprint": "sha256:old",
             }), \
             patch("services.avdb_sync.mark_avdb_sync_running") as running, \
             patch("services.avdb_sync.mark_avdb_sync_failed") as failed, \
             patch("services.avdb_sync.replace_avdb_generation", side_effect=fake_replace), \
             patch("services.avdb_sync.get_avdb_status", return_value={"status": "success", "current_release": "2026-07-13"}):
            result = AvdbSyncService(settings=_settings(), client=client).sync()
        client.close()

        self.assertTrue(result["changed"])
        self.assertEqual(set(captured["rows"]), {"sehuatang", "x1080x"})
        self.assertEqual(captured["rows"]["sehuatang"][0]["normalized_code"], "ABC123")
        self.assertEqual(captured["stats"]["x1080x"]["valid"], 1)
        self.assertEqual(captured["stats"]["x1080x"]["searchable"], 1)
        self.assertEqual(captured["stats"]["x1080x"]["expected"], 1)
        self.assertEqual(captured["release_id"], 101)
        self.assertTrue(captured["asset_fingerprint"].startswith("sha256:"))
        running.assert_called_once_with()
        failed.assert_not_called()

    def test_digest_mismatch_fails_without_importing(self):
        from services.avdb_sync import AvdbSyncError, AvdbSyncService

        release, payloads = self._release_and_payloads()
        release["assets"][0]["digest"] = "sha256:" + ("0" * 64)

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.host == "api.github.com":
                return httpx.Response(200, json=release)
            content = payloads[str(request.url)]
            return httpx.Response(200, content=content, headers={"Content-Length": str(len(content))})

        client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)
        with patch("services.avdb_sync.avdb_sync_advisory_lock", self._lock), \
             patch("services.avdb_sync.get_avdb_sync_state", return_value={}), \
             patch("services.avdb_sync.mark_avdb_sync_running"), \
             patch("services.avdb_sync.mark_avdb_sync_failed") as failed, \
             patch("services.avdb_sync.replace_avdb_generation") as replace:
            with self.assertRaisesRegex(AvdbSyncError, "SHA-256"):
                AvdbSyncService(settings=_settings(), client=client).sync()
        client.close()

        replace.assert_not_called()
        failed.assert_called_once()

    def test_conditional_latest_request_skips_download_on_304(self):
        from services.avdb_sync import AvdbSyncService

        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.headers["If-None-Match"], '"old-etag"')
            return httpx.Response(304)

        client = httpx.Client(transport=httpx.MockTransport(handler))
        with patch("services.avdb_sync.avdb_sync_advisory_lock", self._lock), \
             patch("services.avdb_sync.get_avdb_sync_state", return_value={
                 "status": "running", "release_etag": '"old-etag"',
             }), \
             patch("services.avdb_sync.mark_avdb_sync_running") as running, \
             patch("services.avdb_sync.mark_avdb_sync_unchanged") as unchanged, \
             patch("services.avdb_sync.replace_avdb_generation") as replace, \
             patch("services.avdb_sync.get_avdb_status", return_value={"status": "success"}):
            result = AvdbSyncService(settings=_settings(), client=client).sync()
        client.close()

        self.assertFalse(result["changed"])
        running.assert_called_once_with()
        unchanged.assert_called_once_with(etag=None, last_modified=None)
        replace.assert_not_called()

    def test_client_construction_failure_is_persisted(self):
        from services.avdb_sync import AvdbSyncService

        service = AvdbSyncService(settings=_settings())
        with patch("services.avdb_sync.avdb_sync_advisory_lock", self._lock), \
             patch("services.avdb_sync.get_avdb_sync_state", return_value={"status": "running"}), \
             patch("services.avdb_sync.mark_avdb_sync_running") as running, \
             patch("services.avdb_sync.mark_avdb_sync_failed") as failed, \
             patch.object(service, "_new_client", side_effect=RuntimeError("bad proxy")):
            with self.assertRaisesRegex(RuntimeError, "bad proxy"):
                service.sync()

        running.assert_called_once_with()
        failed.assert_called_once_with("bad proxy")

    def test_same_release_and_same_asset_fingerprint_skips_download(self):
        from services.avdb_sync import (
            AvdbSyncService,
            release_asset_fingerprint,
            select_release_assets,
        )

        release, _payloads = self._release_and_payloads()
        fingerprint = release_asset_fingerprint(select_release_assets(release))
        asset_requests = []

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.host != "api.github.com":
                asset_requests.append(str(request.url))
                return httpx.Response(500)
            return httpx.Response(200, json=release, headers={"ETag": '"same"'})

        client = httpx.Client(transport=httpx.MockTransport(handler))
        state = {
            "current_release_id": 101,
            "active_generation": "active",
            "asset_fingerprint": fingerprint,
        }
        with patch("services.avdb_sync.avdb_sync_advisory_lock", self._lock), \
             patch("services.avdb_sync.get_avdb_sync_state", return_value=state), \
             patch("services.avdb_sync.mark_avdb_sync_running"), \
             patch("services.avdb_sync.mark_avdb_sync_unchanged") as unchanged, \
             patch("services.avdb_sync.replace_avdb_generation") as replace, \
             patch("services.avdb_sync.get_avdb_status", return_value={"status": "success"}):
            result = AvdbSyncService(settings=_settings(), client=client).sync()
        client.close()

        self.assertFalse(result["changed"])
        self.assertEqual(asset_requests, [])
        unchanged.assert_called_once_with(etag='"same"', last_modified=None)
        replace.assert_not_called()

    def test_proxy_transport_failure_retries_then_falls_back_to_direct_for_assets(self):
        from services.avdb_sync import AvdbSyncService

        release, payloads = self._release_and_payloads()
        proxy_attempts = []
        direct_requests = []

        def proxy_handler(request: httpx.Request) -> httpx.Response:
            proxy_attempts.append(str(request.url))
            raise httpx.ConnectError("proxy unavailable", request=request)

        def direct_handler(request: httpx.Request) -> httpx.Response:
            direct_requests.append(str(request.url))
            if request.url.host == "api.github.com":
                return httpx.Response(200, json=release)
            content = payloads[str(request.url)]
            return httpx.Response(200, content=content, headers={"Content-Length": str(len(content))})

        proxy_client = httpx.Client(transport=httpx.MockTransport(proxy_handler))
        direct_client = httpx.Client(transport=httpx.MockTransport(direct_handler))
        service = AvdbSyncService(settings=_settings())
        clients = Mock(side_effect=[proxy_client, direct_client])

        def fake_replace(**kwargs):
            for _source, records, _stats in kwargs["assets"]:
                list(records)
            return {"generation_id": "direct-gen", "record_count": 2}

        with patch("services.avdb_sync.config", SimpleNamespace(proxy_url="http://proxy.test:8080")), \
             patch("services.avdb_sync.avdb_sync_advisory_lock", self._lock), \
             patch("services.avdb_sync.get_avdb_sync_state", return_value={}), \
             patch("services.avdb_sync.mark_avdb_sync_running"), \
             patch("services.avdb_sync.mark_avdb_sync_failed") as failed, \
             patch("services.avdb_sync.replace_avdb_generation", side_effect=fake_replace), \
             patch("services.avdb_sync.get_avdb_status", return_value={"status": "success"}), \
             patch("services.avdb_sync.time.sleep") as sleep, \
             patch.object(service, "_new_client", clients):
            result = service.sync()

        self.assertTrue(result["changed"])
        self.assertEqual(len(proxy_attempts), 3)
        self.assertEqual(len(direct_requests), 3)  # latest + both asset ZIPs
        self.assertEqual(
            clients.call_args_list,
            [call(proxy="http://proxy.test:8080"), call(proxy=None)],
        )
        self.assertEqual(sleep.call_args_list, [call(0.25), call(0.5)])
        failed.assert_not_called()

    def test_direct_latest_request_retries_transient_transport_errors(self):
        from services.avdb_sync import AvdbSyncService

        attempts = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise httpx.ReadError("transient TLS EOF", request=request)
            return httpx.Response(304)

        direct_client = httpx.Client(transport=httpx.MockTransport(handler))
        service = AvdbSyncService(settings=_settings())
        clients = Mock(return_value=direct_client)
        with patch("services.avdb_sync.config", SimpleNamespace(proxy_url="")), \
             patch("services.avdb_sync.avdb_sync_advisory_lock", self._lock), \
             patch("services.avdb_sync.get_avdb_sync_state", return_value={}), \
             patch("services.avdb_sync.mark_avdb_sync_running"), \
             patch("services.avdb_sync.mark_avdb_sync_unchanged") as unchanged, \
             patch("services.avdb_sync.get_avdb_status", return_value={"status": "success"}), \
             patch("services.avdb_sync.time.sleep") as sleep, \
             patch.object(service, "_new_client", clients):
            result = service.sync()

        self.assertFalse(result["changed"])
        self.assertEqual(attempts, 3)
        clients.assert_called_once_with(proxy=None)
        self.assertEqual(sleep.call_args_list, [call(0.25), call(0.5)])
        unchanged.assert_called_once_with(etag=None, last_modified=None)

    def test_http_status_error_does_not_retry_or_fall_back(self):
        from services.avdb_sync import AvdbSyncError, AvdbSyncService

        requests = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(str(request.url))
            return httpx.Response(502, text="bad gateway")

        proxy_client = httpx.Client(transport=httpx.MockTransport(handler))
        service = AvdbSyncService(settings=_settings())
        clients = Mock(return_value=proxy_client)
        with patch("services.avdb_sync.config", SimpleNamespace(proxy_url="http://proxy.test:8080")), \
             patch("services.avdb_sync.avdb_sync_advisory_lock", self._lock), \
             patch("services.avdb_sync.get_avdb_sync_state", return_value={}), \
             patch("services.avdb_sync.mark_avdb_sync_running"), \
             patch("services.avdb_sync.mark_avdb_sync_failed") as failed, \
             patch("services.avdb_sync.time.sleep") as sleep, \
             patch.object(service, "_new_client", clients):
            with self.assertRaisesRegex(AvdbSyncError, "failed to check"):
                service.sync()

        self.assertEqual(len(requests), 1)
        clients.assert_called_once_with(proxy="http://proxy.test:8080")
        sleep.assert_not_called()
        failed.assert_called_once()

    def test_created_clients_ignore_environment_proxies(self):
        from services.avdb_sync import AvdbSyncService

        service = AvdbSyncService(settings=_settings())
        with patch("services.avdb_sync.httpx.Client") as client:
            service._new_client(proxy="http://proxy.test:8080")
            service._new_client(proxy=None)

        self.assertTrue(all(call.kwargs["trust_env"] is False for call in client.call_args_list))
        self.assertEqual(
            [call.kwargs["proxy"] for call in client.call_args_list],
            ["http://proxy.test:8080", None],
        )

    def test_asset_transport_error_removes_partial_file_and_restarts_download(self):
        from services.avdb_sync import ReleaseAsset, _download_asset
        import tempfile
        from pathlib import Path

        content = b"complete-asset-payload"
        attempts = 0
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "asset.zip"

            class PartialFailureStream(httpx.SyncByteStream):
                def __iter__(stream_self):
                    yield content[:4]
                    self.assertTrue(destination.exists())
                    raise httpx.ReadError("TLS EOF", request=requests[-1])

            requests = []

            def handler(request: httpx.Request) -> httpx.Response:
                nonlocal attempts
                attempts += 1
                requests.append(request)
                if attempts == 1:
                    return httpx.Response(
                        200,
                        headers={"Content-Length": str(len(content))},
                        stream=PartialFailureStream(),
                    )
                self.assertFalse(destination.exists(), "partial asset must be removed before retry")
                return httpx.Response(
                    200,
                    content=content,
                    headers={"Content-Length": str(len(content))},
                )

            asset = ReleaseAsset(
                source="sehuatang",
                name="All_sehuatang_1_test.zip",
                url="https://github.com/li-peifeng/AVdb-Only/releases/download/test/asset.zip",
                size=len(content),
                sha256=hashlib.sha256(content).hexdigest(),
                expected_rows=1,
            )
            client = httpx.Client(transport=httpx.MockTransport(handler))
            with patch("services.avdb_sync._DOWNLOAD_CHUNK_SIZE", 4), \
                 patch("services.avdb_sync.time.sleep") as sleep:
                downloaded = _download_asset(
                    client,
                    asset,
                    destination,
                    max_asset_bytes=1024,
                )
            client.close()

            self.assertEqual(downloaded, len(content))
            self.assertEqual(destination.read_bytes(), content)
        self.assertEqual(attempts, 2)
        sleep.assert_called_once_with(0.25)

    def test_asset_http_status_error_is_not_retried(self):
        from services.avdb_sync import AvdbSyncError, ReleaseAsset, _download_asset
        import tempfile
        from pathlib import Path

        attempts = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            return httpx.Response(503, text="unavailable")

        asset = ReleaseAsset(
            source="x1080x",
            name="All_X1080X_1_test.zip",
            url="https://github.com/li-peifeng/AVdb-Only/releases/download/test/asset.zip",
            size=10,
            sha256="0" * 64,
            expected_rows=1,
        )
        client = httpx.Client(transport=httpx.MockTransport(handler))
        with tempfile.TemporaryDirectory() as directory, \
             patch("services.avdb_sync.time.sleep") as sleep:
            with self.assertRaisesRegex(AvdbSyncError, "failed to download"):
                _download_asset(client, asset, Path(directory) / "asset.zip", max_asset_bytes=1024)
        client.close()

        self.assertEqual(attempts, 1)
        sleep.assert_not_called()

    def test_asset_transport_retries_are_bounded_to_three_attempts(self):
        from services.avdb_sync import AvdbSyncError, ReleaseAsset, _download_asset
        import tempfile
        from pathlib import Path

        attempts = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            raise httpx.ConnectError("TLS handshake failed", request=request)

        asset = ReleaseAsset(
            source="x1080x",
            name="All_X1080X_1_test.zip",
            url="https://github.com/li-peifeng/AVdb-Only/releases/download/test/asset.zip",
            size=10,
            sha256="0" * 64,
            expected_rows=1,
        )
        client = httpx.Client(transport=httpx.MockTransport(handler))
        with tempfile.TemporaryDirectory() as directory, \
             patch("services.avdb_sync.time.sleep") as sleep:
            destination = Path(directory) / "asset.zip"
            with self.assertRaisesRegex(AvdbSyncError, "failed to download"):
                _download_asset(client, asset, destination, max_asset_bytes=1024)
            self.assertFalse(destination.exists())
        client.close()

        self.assertEqual(attempts, 3)
        self.assertEqual(sleep.call_args_list, [call(0.25), call(0.5)])

    def test_asset_digest_validation_error_is_not_retried(self):
        from services.avdb_sync import AvdbSyncError, ReleaseAsset, _download_asset
        import tempfile
        from pathlib import Path

        content = b"wrong-digest"
        attempts = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            return httpx.Response(
                200,
                content=content,
                headers={"Content-Length": str(len(content))},
            )

        asset = ReleaseAsset(
            source="sehuatang",
            name="All_sehuatang_1_test.zip",
            url="https://github.com/li-peifeng/AVdb-Only/releases/download/test/asset.zip",
            size=len(content),
            sha256="0" * 64,
            expected_rows=1,
        )
        client = httpx.Client(transport=httpx.MockTransport(handler))
        with tempfile.TemporaryDirectory() as directory, \
             patch("services.avdb_sync.time.sleep") as sleep:
            with self.assertRaisesRegex(AvdbSyncError, "SHA-256"):
                _download_asset(client, asset, Path(directory) / "asset.zip", max_asset_bytes=1024)
        client.close()

        self.assertEqual(attempts, 1)
        sleep.assert_not_called()


class AvdbSourceAndRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_source_uses_exact_normalized_code_and_deduplicates_info_hash(self):
        from sources.avdb_source import AvdbSource

        row = {
            "title": "ABC-123 中文字幕 1080p",
            "magnet": f"magnet:?xt=urn:btih:{HEX_A}",
            "info_hash": HEX_A,
            "size_text": "3930",
        }
        with patch("sources.avdb_source.search_avdb_records", return_value=[row, dict(row)]) as search:
            results = await AvdbSource(enabled=True, result_limit=10).search("abc-123")

        search.assert_called_once_with("ABC123", limit=10)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["size"], "3.84 GB")
        self.assertTrue(results[0]["subtitle"])
        self.assertEqual(results[0]["source"], "avdb")

    def test_numeric_sizes_are_mb_humanized_and_outliers_are_unknown(self):
        from sources.avdb_source import _display_size

        self.assertEqual(_display_size("512"), "512 MB")
        self.assertEqual(_display_size("3930"), "3.84 GB")
        self.assertEqual(_display_size(str(128 * 1024)), "128 GB")
        for invalid in ("0", "-1", str(128 * 1024 + 1)):
            with self.subTest(invalid=invalid):
                self.assertEqual(_display_size(invalid), "")

    def test_status_route_exposes_stable_contract(self):
        from routers.avdb import router

        status = {
            "status": "never", "available": False, "current_release": None,
            "current_generation": None, "record_count": 0, "source_counts": {},
            "last_checked_at": None, "last_started_at": None,
            "last_completed_at": None, "last_error": None,
        }
        with patch("routers.avdb.config", SimpleNamespace(avdb_enabled=True, avdb_sync_enabled=False)), \
             patch("routers.avdb.get_avdb_status", return_value=status):
            response = create_router_test_client(router).get("/api/v1/avdb/status")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["enabled"], True)
        self.assertEqual(response.json()["status"], "never")

    def test_config_pins_internal_source_identity_and_repository(self):
        from config import Config

        cfg = object.__new__(Config)
        cfg._config = {
            "sources": {
                "avdb": {
                    "enabled": "yes",
                    "sync_enabled": "true",
                    "name": "torznab",
                    "repository": "attacker/private",
                    "interval_hours": 9999,
                }
            }
        }
        normalized = cfg.avdb_source_config
        self.assertEqual(normalized["name"], "avdb")
        self.assertEqual(normalized["repository"], "li-peifeng/AVdb-Only")
        self.assertEqual(normalized["interval_hours"], 168)
        self.assertTrue(normalized["enabled"])
        self.assertTrue(normalized["sync_enabled"])

    def test_registration_adds_enabled_avdb_source(self):
        import sources
        from sources.avdb_source import AvdbSource
        from sources.registry import SourceRegistry

        cfg = SimpleNamespace(
            enabled_torznab_configs=[],
            avdb_enabled=True,
            avdb_source_config={"enabled": True, "name": "avdb", "result_limit": 20},
        )
        with patch.object(SourceRegistry, "_sources", {}), \
             patch.object(SourceRegistry, "_priority", []), \
             patch.object(sources, "config", cfg):
            sources.register_all_sources()
            self.assertIsInstance(SourceRegistry.get("avdb"), AvdbSource)


class AvdbSchedulerTests(unittest.TestCase):
    def test_scheduler_starts_interval_jobs_when_subscription_cron_is_disabled(self):
        from scheduler import tasks

        fake_scheduler = Mock()
        cfg = SimpleNamespace(scheduler_check_hour=None, scheduler_variant_index_rebuild_hour=None)
        with patch.object(tasks, "scheduler", fake_scheduler), patch.object(tasks, "config", cfg), \
             patch.object(tasks, "recover_avdb_sync_state", return_value=False) as recover, \
             patch.object(tasks, "configure_candidate_auto_process_job") as candidates, \
             patch.object(tasks, "configure_acquisition_coordinator_job") as acquisition, \
             patch.object(tasks, "configure_avdb_sync_job") as avdb:
            tasks.start_scheduler()

        candidates.assert_called_once_with()
        recover.assert_called_once_with()
        acquisition.assert_called_once_with()
        avdb.assert_called_once_with()
        fake_scheduler.start.assert_called_once_with()
        fake_scheduler.add_job.assert_not_called()

    def test_avdb_manual_job_is_always_whitelisted(self):
        from scheduler.tasks import MANUAL_JOB_IDS
        self.assertIn("avdb_sync", MANUAL_JOB_IDS)

    def test_sync_enabled_registers_interval_job(self):
        from apscheduler.triggers.interval import IntervalTrigger
        from scheduler import tasks

        fake_scheduler = Mock()
        cfg = SimpleNamespace(
            avdb_sync_enabled=True,
            avdb_source_config={"interval_hours": 6},
        )
        with patch.object(tasks, "scheduler", fake_scheduler), patch.object(tasks, "config", cfg):
            tasks.configure_avdb_sync_job()

        call = fake_scheduler.add_job.call_args
        self.assertEqual(call.kwargs["id"], "avdb_sync")
        self.assertIsInstance(call.args[1], IntervalTrigger)

    def test_recovery_does_not_change_state_while_another_worker_holds_lock(self):
        from database import avdb

        @contextmanager
        def busy_lock():
            yield False

        with patch.object(avdb, "avdb_sync_advisory_lock", busy_lock), \
             patch.object(avdb, "get_db_orig") as get_db:
            self.assertFalse(avdb.recover_interrupted_avdb_sync())
        get_db.assert_not_called()


class AvdbPostgresGenerationTests(TempPostgresMixin, unittest.TestCase):
    @staticmethod
    def _record(source: str, tid: str, code: str, info_hash: str) -> dict:
        return {
            "source": source,
            "source_tid": tid,
            "normalized_code": code,
            "number": "ABC-123",
            "title": "ABC-123",
            "magnet": f"magnet:?xt=urn:btih:{info_hash}",
            "info_hash": info_hash,
            "size_text": "1000",
            "publish_date": "2026-07-01",
        }

    def test_failed_staging_import_preserves_active_generation(self):
        from database.avdb import get_avdb_status, replace_avdb_generation, search_avdb_records

        first_assets = [
            ("sehuatang", [self._record("sehuatang", "1", "ABC123", HEX_A)], {"expected": 1, "total": 1}),
            ("x1080x", [self._record("x1080x", "2", "ABC123", HEX_B)], {"expected": 1, "total": 1}),
        ]
        first = replace_avdb_generation(
            release_id=1,
            release_tag="release-1",
            release_published_at="2026-07-01T00:00:00+00:00",
            asset_fingerprint="sha256:first",
            etag='"one"',
            last_modified=None,
            assets=first_assets,
            batch_size=100,
            keep_generations=2,
            min_source_records=1,
            min_searchable_records=1,
            min_source_ratio=0.5,
            max_skipped_ratio=0.5,
        )

        def broken_rows():
            yield self._record("x1080x", "4", "ABC123", "fedcba9876543210fedcba9876543210fedcba98")
            raise RuntimeError("broken CSV")

        with self.assertRaisesRegex(RuntimeError, "broken CSV"):
            replace_avdb_generation(
                release_id=2,
                release_tag="release-2",
                release_published_at="2026-07-02T00:00:00+00:00",
                asset_fingerprint="sha256:second",
                etag='"two"',
                last_modified=None,
                assets=[
                    ("sehuatang", [self._record("sehuatang", "3", "ABC123", HEX_A)], {"expected": 1, "total": 1}),
                    ("x1080x", broken_rows(), {"expected": 1, "total": 1}),
                ],
                batch_size=100,
                keep_generations=2,
                min_source_records=1,
                min_searchable_records=1,
                min_source_ratio=0.5,
                max_skipped_ratio=0.5,
            )

        status = get_avdb_status()
        self.assertEqual(status["current_generation"], first["generation_id"])
        self.assertEqual(status["current_release"], "release-1")
        self.assertEqual(len(search_avdb_records("ABC123", limit=10)), 2)

    def test_same_release_changed_fingerprint_can_replace_active_generation(self):
        from database.avdb import get_avdb_status, replace_avdb_generation

        def replace(fingerprint: str, tid_offset: int):
            return replace_avdb_generation(
                release_id=10,
                release_tag="same-release",
                release_published_at="2026-07-01T00:00:00+00:00",
                asset_fingerprint=fingerprint,
                etag=None,
                last_modified=None,
                assets=[
                    ("sehuatang", [self._record("sehuatang", str(tid_offset), "ABC123", f"{tid_offset:040x}")], {"expected": 1, "total": 1}),
                    ("x1080x", [self._record("x1080x", str(tid_offset + 1), "ABC123", f"{tid_offset + 1:040x}")], {"expected": 1, "total": 1}),
                ],
                batch_size=100,
                keep_generations=2,
                min_source_records=1,
                min_searchable_records=1,
                min_source_ratio=0.5,
                max_skipped_ratio=0.05,
            )

        first = replace("sha256:first", 10)
        second = replace("sha256:changed", 20)
        status = get_avdb_status()
        self.assertNotEqual(first["generation_id"], second["generation_id"])
        self.assertEqual(status["current_generation"], second["generation_id"])
        self.assertEqual(status["asset_fingerprint"], "sha256:changed")

    def test_bad_counts_and_unsearchable_assets_do_not_switch_generation(self):
        from database.avdb import get_avdb_status, replace_avdb_generation

        base_kwargs = {
            "batch_size": 100,
            "keep_generations": 2,
            "min_source_records": 1,
            "min_searchable_records": 1,
            "min_source_ratio": 0.5,
            "max_skipped_ratio": 0.05,
        }
        first = replace_avdb_generation(
            release_id=1,
            release_tag="release-1",
            release_published_at="2026-07-01T00:00:00+00:00",
            asset_fingerprint="sha256:base",
            etag=None,
            last_modified=None,
            assets=[
                ("sehuatang", [self._record("sehuatang", "1", "ABC123", HEX_A)], {"expected": 1, "total": 1}),
                ("x1080x", [self._record("x1080x", "2", "ABC123", HEX_B)], {"expected": 1, "total": 1}),
            ],
            **base_kwargs,
        )

        truncated = [
            ("sehuatang", [self._record("sehuatang", "3", "ABC123", f"{3:040x}")], {"expected": 2, "total": 1}),
            ("x1080x", [self._record("x1080x", "4", "ABC123", f"{4:040x}")], {"expected": 1, "total": 1}),
        ]
        with self.assertRaisesRegex(ValueError, "did not match filename count"):
            replace_avdb_generation(
                release_id=2,
                release_tag="release-2",
                release_published_at="2026-07-02T00:00:00+00:00",
                asset_fingerprint="sha256:truncated",
                etag=None,
                last_modified=None,
                assets=truncated,
                **base_kwargs,
            )

        unsearchable = self._record("sehuatang", "5", "", f"{5:040x}")
        unsearchable["normalized_code"] = None
        with self.assertRaisesRegex(ValueError, "searchable records"):
            replace_avdb_generation(
                release_id=2,
                release_tag="release-2",
                release_published_at="2026-07-02T00:00:00+00:00",
                asset_fingerprint="sha256:unsearchable",
                etag=None,
                last_modified=None,
                assets=[
                    ("sehuatang", [unsearchable], {"expected": 1, "total": 1}),
                    ("x1080x", [self._record("x1080x", "6", "ABC123", f"{6:040x}")], {"expected": 1, "total": 1}),
                ],
                **base_kwargs,
            )

        with self.assertRaisesRegex(ValueError, "maximum ratio"):
            replace_avdb_generation(
                release_id=2,
                release_tag="release-2",
                release_published_at="2026-07-02T00:00:00+00:00",
                asset_fingerprint="sha256:skipped",
                etag=None,
                last_modified=None,
                assets=[
                    ("sehuatang", [self._record("sehuatang", "7", "ABC123", f"{7:040x}")], {"expected": 2, "total": 2}),
                    ("x1080x", [self._record("x1080x", "8", "ABC123", f"{8:040x}")], {"expected": 1, "total": 1}),
                ],
                **base_kwargs,
            )

        self.assertEqual(get_avdb_status()["current_generation"], first["generation_id"])

    def test_startup_recovery_marks_orphaned_running_state_failed(self):
        from database.avdb import get_avdb_status, recover_interrupted_avdb_sync
        from database.base import get_db_orig

        conn = get_db_orig()
        try:
            conn.execute("UPDATE avdb_sync_state SET status = 'running' WHERE id = 1")
            conn.commit()
        finally:
            conn.close()

        self.assertTrue(recover_interrupted_avdb_sync())
        status = get_avdb_status()
        self.assertEqual(status["status"], "failed")
        self.assertIn("interrupted", status["last_error"])

    def test_valid_and_searchable_ratios_are_checked_against_active_generation(self):
        from database.avdb import get_avdb_status, replace_avdb_generation

        def records(source: str, start: int, count: int, searchable: int) -> list[dict]:
            rows = []
            for offset in range(count):
                value = start + offset
                row = self._record(source, str(value), "ABC123", f"{value:040x}")
                if offset >= searchable:
                    row["normalized_code"] = None
                rows.append(row)
            return rows

        kwargs = {
            "batch_size": 100,
            "keep_generations": 2,
            "min_source_records": 1,
            "min_searchable_records": 1,
            "min_source_ratio": 0.5,
            "max_skipped_ratio": 0.05,
        }
        first = replace_avdb_generation(
            release_id=1,
            release_tag="release-1",
            release_published_at="2026-07-01T00:00:00+00:00",
            asset_fingerprint="sha256:ratio-base",
            etag=None,
            last_modified=None,
            assets=[
                ("sehuatang", records("sehuatang", 100, 4, 4), {"expected": 4, "total": 4}),
                ("x1080x", records("x1080x", 200, 4, 4), {"expected": 4, "total": 4}),
            ],
            **kwargs,
        )

        with self.assertRaisesRegex(ValueError, "dropped from 4 to 1"):
            replace_avdb_generation(
                release_id=2,
                release_tag="release-2",
                release_published_at="2026-07-02T00:00:00+00:00",
                asset_fingerprint="sha256:valid-drop",
                etag=None,
                last_modified=None,
                assets=[
                    ("sehuatang", records("sehuatang", 300, 1, 1), {"expected": 1, "total": 1}),
                    ("x1080x", records("x1080x", 400, 1, 1), {"expected": 1, "total": 1}),
                ],
                **kwargs,
            )

        with self.assertRaisesRegex(ValueError, "searchable records dropped from 4 to 1"):
            replace_avdb_generation(
                release_id=2,
                release_tag="release-2",
                release_published_at="2026-07-02T00:00:00+00:00",
                asset_fingerprint="sha256:searchable-drop",
                etag=None,
                last_modified=None,
                assets=[
                    ("sehuatang", records("sehuatang", 500, 4, 1), {"expected": 4, "total": 4}),
                    ("x1080x", records("x1080x", 600, 4, 1), {"expected": 4, "total": 4}),
                ],
                **kwargs,
            )

        self.assertEqual(get_avdb_status()["current_generation"], first["generation_id"])


if __name__ == "__main__":
    unittest.main()
