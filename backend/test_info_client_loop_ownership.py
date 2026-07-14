import asyncio
import threading
import unittest

import httpx

from modules.info_client import InfoClient


class LoopThread:
    def __init__(self, name: str) -> None:
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, name=name, daemon=True)
        self.thread.start()

    def run(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result(timeout=2)

    def stop(self) -> None:
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(timeout=2)
        self.loop.close()


class RecordingInfoHTTPClient:
    def __init__(self) -> None:
        self.created_loop = asyncio.get_running_loop()
        self.request_loops = []
        self.closed_loop = None
        self.is_closed = False

    async def get(self, _url, **_kwargs):
        self.request_loops.append(asyncio.get_running_loop())
        return httpx.Response(200, json={"status": "ok"})

    async def aclose(self) -> None:
        self.closed_loop = asyncio.get_running_loop()
        self.is_closed = True


class InfoClientLoopOwnershipTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.loops = [LoopThread("info-a"), LoopThread("info-b")]

    def tearDown(self) -> None:
        for loop in self.loops:
            loop.stop()

    async def test_reuses_clients_per_loop_and_closes_each_on_its_owner(self):
        clients = []

        def factory():
            client = RecordingInfoHTTPClient()
            clients.append(client)
            return client

        info = InfoClient(api_url="http://javinfo.test", client_factory=factory)
        self.loops[0].run(info._get("/status"))
        self.loops[1].run(info._get("/status"))
        self.loops[0].run(info._get("/status"))

        self.assertEqual(len(clients), 2)
        self.assertEqual(len(clients[0].request_loops), 2)
        self.assertEqual(len(clients[1].request_loops), 1)

        await info.close()

        self.assertTrue(all(client.is_closed for client in clients))
        self.assertTrue(all(client.closed_loop is client.created_loop for client in clients))


if __name__ == "__main__":
    unittest.main()
