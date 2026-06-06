from __future__ import annotations

import unittest

from fastapi import Query

from routers._query import qv


class QueryValueHelperTest(unittest.TestCase):
    def test_qv_returns_plain_values(self):
        self.assertEqual(qv("avbase"), "avbase")
        self.assertEqual(qv(20), 20)

    def test_qv_unwraps_fastapi_query_defaults(self):
        self.assertEqual(qv(Query("avbase")), "avbase")
        self.assertEqual(qv(Query(20, ge=1, le=100)), 20)

    def test_qv_preserves_none(self):
        self.assertIsNone(qv(None))
        self.assertIsNone(qv(Query(None)))
