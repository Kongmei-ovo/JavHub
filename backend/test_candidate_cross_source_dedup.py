"""Cross-source dedup: same number across inventory/subscription/supplement
must not download twice."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from test_support.postgres import TempPostgresMixin


class CrossSourceDedupTest(TempPostgresMixin, unittest.IsolatedAsyncioTestCase):
    async def test_completeness_lookup_includes_global_and_other_actress_candidates(self):
        from database import upsert_download_candidate
        from database.download_candidate import list_download_candidate_states_by_actress

        other_actress = upsert_download_candidate(
            content_id="SIVR-438",
            dvd_id="SIVR-438",
            actress_id=202,
            source="subscription",
        )
        acquisition = upsert_download_candidate(
            content_id="JUR-418",
            actress_id=None,
            source="acquisition",
        )
        upsert_download_candidate(
            content_id="UNRELATED-1",
            actress_id=303,
            source="subscription",
        )

        rows = list_download_candidate_states_by_actress(
            101,
            {"sivr_438", "jur-418"},
        )

        self.assertEqual(
            {row["id"] for row in rows},
            {other_actress["id"], acquisition["id"]},
        )

    async def test_second_source_skips_when_sibling_already_sent(self):
        from database import set_download_candidate_status, upsert_download_candidate
        from services.candidate_processor import process_candidate

        sent = upsert_download_candidate(
            content_id="SIVR-438",
            dvd_id="SIVR-438",
            source="inventory",
        )
        set_download_candidate_status(sent["id"], "sent", download_task_id=42)

        sibling = upsert_download_candidate(
            content_id="sivr438",
            dvd_id="SIVR-438",
            source="subscription",
            status="candidate",
            magnet="magnet:?xt=urn:btih:abc",
        )

        with patch(
            "services.candidate_processor.downloader_service.create_download_task",
            new=AsyncMock(side_effect=AssertionError("must not send a duplicate")),
        ):
            result = await process_candidate(sibling["id"], policy="auto", operator="system")

        self.assertEqual(result["action"], "skipped_duplicate")
        self.assertEqual(result["sibling_id"], sent["id"])

    async def test_normalize_compares_ignoring_separators_and_case(self):
        from database import set_download_candidate_status, upsert_download_candidate
        from services.candidate_processor import process_candidate

        sent = upsert_download_candidate(
            content_id="SIVR-438",
            dvd_id="SIVR-438",
            source="inventory",
        )
        set_download_candidate_status(sent["id"], "completed", download_task_id=42)

        sibling = upsert_download_candidate(
            content_id="sivr_438",
            dvd_id="sivr 438",
            source="supplement",
            status="candidate",
            magnet="magnet:?xt=urn:btih:abc",
        )

        result = await process_candidate(sibling["id"], policy="auto", operator="system")

        self.assertEqual(result["action"], "skipped_duplicate")

    async def test_dedup_does_not_block_distinct_codes(self):
        from database import set_download_candidate_status, upsert_download_candidate
        from services.candidate_processor import process_candidate

        sent = upsert_download_candidate(
            content_id="SIVR-438",
            dvd_id="SIVR-438",
            source="inventory",
        )
        set_download_candidate_status(sent["id"], "sent", download_task_id=42)

        target = upsert_download_candidate(
            content_id="SIVR-439",
            dvd_id="SIVR-439",
            source="subscription",
            status="candidate",
            magnet="magnet:?xt=urn:btih:def",
        )

        with patch(
            "services.candidate_processor.downloader_service.create_download_task",
            new=AsyncMock(return_value=99),
        ) as create_mock, patch(
            "services.candidate_processor.get_download_task",
            return_value={"id": 99, "status": "downloading"},
        ):
            result = await process_candidate(target["id"], policy="auto", operator="system")

        self.assertEqual(result["action"], "sent")
        create_mock.assert_awaited_once()


class LockShiftTest(TempPostgresMixin, unittest.IsolatedAsyncioTestCase):
    async def test_process_candidates_returns_busy_when_lock_held(self):
        from services import candidate_processor
        from services.candidate_processor import process_candidates

        acquired = candidate_processor._PROCESSING_LOCK.acquire(blocking=False)
        self.assertTrue(acquired)
        try:
            result = await process_candidates(
                filters={"status": "candidate"},
                policy="auto",
                operator="manual",
            )
        finally:
            candidate_processor._PROCESSING_LOCK.release()

        self.assertEqual(result["status"], "busy")


if __name__ == "__main__":
    unittest.main()
