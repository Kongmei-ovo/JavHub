from __future__ import annotations

import unittest

from fastapi import HTTPException

from test_support.postgres import TempPostgresMixin


class CandidateSwapMagnetTest(TempPostgresMixin, unittest.IsolatedAsyncioTestCase):
    async def test_candidate_detail_exposes_magnet_alternatives(self):
        from database import upsert_download_candidate
        from database.download_candidate import update_download_candidate_magnet_alternatives
        from routers.downloads import get_candidate

        candidate = upsert_download_candidate(
            content_id="SIVR-438",
            title="Title",
            source="inventory",
            magnet="magnet:?xt=urn:btih:first",
            magnet_source="javdb",
        )
        alternatives = [
            {"magnet": "magnet:?xt=urn:btih:first", "source": "javdb", "title": "First", "score": {"total": 20}},
            {"magnet": "magnet:?xt=urn:btih:second", "source": "javbus", "title": "Second", "score": {"total": 19}},
        ]
        update_download_candidate_magnet_alternatives(candidate["id"], alternatives)

        result = get_candidate(candidate["id"])

        self.assertEqual(result["data"]["magnet_alternatives"], alternatives)

    async def test_swap_magnet_promotes_alternative_and_resets_status(self):
        from database import get_download_candidate, list_download_candidate_events, set_download_candidate_status, upsert_download_candidate
        from database.download_candidate import update_download_candidate_magnet_alternatives
        from routers.downloads import SwapCandidateMagnetRequest, swap_candidate_magnet

        candidate = upsert_download_candidate(
            content_id="SIVR-438",
            title="Title",
            source="inventory",
            magnet="magnet:?xt=urn:btih:first",
            magnet_source="javdb",
        )
        set_download_candidate_status(candidate["id"], "failed", download_task_id=44, error_msg="bad magnet")
        update_download_candidate_magnet_alternatives(
            candidate["id"],
            [
                {"magnet": "magnet:?xt=urn:btih:first", "source": "javdb", "title": "First", "score": {"total": 20}},
                {"magnet": "magnet:?xt=urn:btih:second", "source": "javbus", "title": "Second", "score": {"total": 19}},
            ],
        )

        result = await swap_candidate_magnet(candidate["id"], SwapCandidateMagnetRequest(alt_index=1))

        updated = get_download_candidate(candidate["id"])
        self.assertEqual(result["status"], "ok")
        self.assertEqual(updated["status"], "candidate")
        self.assertEqual(updated["magnet"], "magnet:?xt=urn:btih:second")
        self.assertEqual(updated["magnet_source"], "javbus")
        self.assertIsNone(updated["error_msg"])
        self.assertEqual(updated["magnet_alternatives"][0]["magnet"], "magnet:?xt=urn:btih:second")
        self.assertEqual(updated["magnet_alternatives"][1]["magnet"], "magnet:?xt=urn:btih:first")
        self.assertEqual(list_download_candidate_events(candidate["id"])[0]["action"], "magnet_swapped")

    async def test_swap_magnet_rejects_bad_alt_index(self):
        from database import upsert_download_candidate
        from database.download_candidate import update_download_candidate_magnet_alternatives
        from routers.downloads import SwapCandidateMagnetRequest, swap_candidate_magnet

        candidate = upsert_download_candidate(
            content_id="SIVR-438",
            source="inventory",
            magnet="magnet:?xt=urn:btih:first",
        )
        update_download_candidate_magnet_alternatives(
            candidate["id"],
            [{"magnet": "magnet:?xt=urn:btih:first", "source": "javdb", "title": "First", "score": {"total": 20}}],
        )

        with self.assertRaises(HTTPException) as raised:
            await swap_candidate_magnet(candidate["id"], SwapCandidateMagnetRequest(alt_index=3))

        self.assertEqual(raised.exception.status_code, 400)
