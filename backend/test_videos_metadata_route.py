from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from fastapi.routing import APIRoute
from routers.videos import get_video_metadata, router


class VideosMetadataRouteTest(unittest.IsolatedAsyncioTestCase):
    def test_metadata_route_is_registered_before_content_id_route(self):
        paths = [route.path for route in router.routes if isinstance(route, APIRoute)]

        self.assertLess(paths.index("/api/v1/videos/{content_id}/metadata"), paths.index("/api/v1/videos/{content_id}"))

    async def test_metadata_route_calls_get_video_metadata_not_get_video(self):
        client = AsyncMock()
        client.get_video_metadata.return_value = {"summary": "Metadata summary"}

        with patch("routers.videos.get_info_client", return_value=client):
            data = await get_video_metadata("MIAA-784")

        client.get_video_metadata.assert_awaited_once_with("MIAA-784")
        client.get_video.assert_not_called()
        self.assertEqual(data, {"summary": "Metadata summary"})


if __name__ == "__main__":
    unittest.main()
