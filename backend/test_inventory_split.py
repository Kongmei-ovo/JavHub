from __future__ import annotations

import unittest
from unittest.mock import patch


class InventorySplitTest(unittest.TestCase):
    def test_inventory_routes_are_split_across_domain_routers(self):
        from routers import inventory, inventory_actors, inventory_jobs, inventory_mapping

        route_sources = {}
        for source_name, router in {
            "inventory": inventory.router,
            "inventory_actors": inventory_actors.router,
            "inventory_jobs": inventory_jobs.router,
            "inventory_mapping": inventory_mapping.router,
        }.items():
            for route in router.routes:
                route_sources[route.path] = source_name

        self.assertEqual(route_sources["/api/inventory/jobs/trigger"], "inventory_jobs")
        self.assertEqual(route_sources["/api/inventory/pipeline/run"], "inventory_jobs")
        self.assertEqual(route_sources["/api/inventory/jobs"], "inventory_jobs")
        self.assertEqual(route_sources["/api/inventory/actors"], "inventory_actors")
        self.assertEqual(route_sources["/api/inventory/actors/{actress_id}"], "inventory_actors")
        self.assertEqual(route_sources["/api/inventory/actor-mappings"], "inventory_mapping")
        self.assertEqual(route_sources["/api/inventory/actor-mappings/confirm"], "inventory_mapping")
        self.assertEqual(route_sources["/api/inventory/snapshots/latest"], "inventory")
        self.assertEqual(route_sources["/api/inventory/missing"], "inventory")

    def test_main_mounts_all_inventory_routers_without_changing_paths(self):
        import importlib
        import sys

        sys.modules.pop("main", None)
        with patch("database.init_db"):
            main = importlib.import_module("main")

        paths = {
            route.path
            for route in main.app.routes
            if getattr(route, "path", "").startswith("/api/inventory")
        }

        self.assertIn("/api/inventory/jobs/trigger", paths)
        self.assertIn("/api/inventory/pipeline/run", paths)
        self.assertIn("/api/inventory/jobs", paths)
        self.assertIn("/api/inventory/jobs/{job_id}", paths)
        self.assertIn("/api/inventory/actors", paths)
        self.assertIn("/api/inventory/actors/{actress_id}", paths)
        self.assertIn("/api/inventory/actors/{actress_id}/emby-videos", paths)
        self.assertIn("/api/inventory/actor-mappings", paths)
        self.assertIn("/api/inventory/actor-mappings/confirm", paths)
        self.assertIn("/api/inventory/snapshots/latest", paths)
        self.assertIn("/api/inventory/missing", paths)


if __name__ == "__main__":
    unittest.main()
