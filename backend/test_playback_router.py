"""Playback progress route tests."""
from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch


class ProgressEndpointTests(unittest.TestCase):
    def test_put_progress_validates_source(self):
        from fastapi import HTTPException

        from routers.playback import ProgressRequest, put_progress

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(put_progress("ABC-123", ProgressRequest(source="emby", position_seconds=1)))
        self.assertEqual(ctx.exception.status_code, 400)

    def test_put_progress_saves(self):
        from routers.playback import ProgressRequest, put_progress

        with patch("routers.playback.save_progress", return_value={"content_id": "ABC-123"}) as mock_save:
            asyncio.run(put_progress("ABC-123", ProgressRequest(
                source="library", position_seconds=120, duration_seconds=7200,
            )))
        mock_save.assert_called_once_with("ABC-123", "library", 120, 7200)


if __name__ == "__main__":
    unittest.main()
