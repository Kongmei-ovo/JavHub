import unittest

from routers import categories


class CategoryRouteTests(unittest.TestCase):
    def test_categories_router_no_longer_exposes_stats_endpoint(self):
        paths = {route.path for route in categories.router.routes}

        self.assertIn("/api/v1/categories", paths)
        self.assertNotIn("/api/v1/categories/stats", paths)


if __name__ == "__main__":
    unittest.main()
