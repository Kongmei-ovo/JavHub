from __future__ import annotations

import unittest

from services import supplement_autopilot


class FakeClient:
    def __init__(self, fail: bool = False, existing: bool = False):
        self.fail = fail
        self.existing = existing
        self.posts: list[tuple[str, dict | None]] = []

    async def proxy_post(self, path: str, json_body=None, params=None):
        self.posts.append((path, params))
        if self.fail:
            raise RuntimeError("upstream down")
        return {"job_id": 42, "status": "queued", "existing": self.existing}


class SupplementAutopilotTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        supplement_autopilot.reset_attempt_cache()

    async def test_creates_filmography_job(self):
        client = FakeClient()
        result = await supplement_autopilot.ensure_actress_supplement(1020504, client=client)
        self.assertEqual(result["action"], "job_created")
        self.assertEqual(len(client.posts), 1)
        path, params = client.posts[0]
        self.assertEqual(path, "/api/v1/supplement/actresses/1020504/filmography/jobs")
        self.assertEqual(params, {"source": "avbase"})

    async def test_ttl_dedupes_repeat_calls(self):
        client = FakeClient()
        first = await supplement_autopilot.ensure_actress_supplement(7, client=client)
        second = await supplement_autopilot.ensure_actress_supplement(7, client=client)
        self.assertEqual(first["action"], "job_created")
        self.assertEqual(second["action"], "skipped_recent")
        self.assertEqual(len(client.posts), 1)

    async def test_force_bypasses_ttl(self):
        client = FakeClient()
        await supplement_autopilot.ensure_actress_supplement(7, client=client)
        result = await supplement_autopilot.ensure_actress_supplement(7, client=client, force=True)
        self.assertEqual(result["action"], "job_created")
        self.assertEqual(len(client.posts), 2)

    async def test_failure_releases_ttl_claim(self):
        failing = FakeClient(fail=True)
        result = await supplement_autopilot.ensure_actress_supplement(7, client=failing)
        self.assertEqual(result["action"], "job_failed")
        working = FakeClient()
        retry = await supplement_autopilot.ensure_actress_supplement(7, client=working)
        self.assertEqual(retry["action"], "job_created")

    async def test_existing_job_reported(self):
        client = FakeClient(existing=True)
        result = await supplement_autopilot.ensure_actress_supplement(7, client=client)
        self.assertEqual(result["action"], "job_exists")

    async def test_invalid_actress_id_skipped(self):
        client = FakeClient()
        result = await supplement_autopilot.ensure_actress_supplement(0, client=client)
        self.assertEqual(result["action"], "skipped_invalid")
        self.assertEqual(client.posts, [])


if __name__ == "__main__":
    unittest.main()
