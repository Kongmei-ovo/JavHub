import json
import subprocess
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_node(*args):
    return subprocess.run(
        ["node", "scripts/api_load_test.mjs", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def parse_args(*args):
    code = textwrap.dedent(
        """
        import { pathToFileURL } from "node:url";

        const parserArgs = JSON.parse(process.argv[1]);
        const mod = await import(pathToFileURL("scripts/api_load_test.mjs"));
        if (typeof mod.parseArgs !== "function") {
          throw new Error("parseArgs export missing");
        }
        const config = mod.parseArgs(parserArgs);
        process.stdout.write(JSON.stringify(config));
        """
    )
    result = subprocess.run(
        ["node", "--input-type=module", "-e", code, json.dumps(list(args))],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr or result.stdout)
    return json.loads(result.stdout)


def endpoint_group_names():
    code = textwrap.dedent(
        """
        import { pathToFileURL } from "node:url";

        const mod = await import(pathToFileURL("scripts/api_load_test.mjs"));
        if (!mod.ENDPOINT_GROUPS) {
          throw new Error("ENDPOINT_GROUPS export missing");
        }
        process.stdout.write(JSON.stringify(Object.keys(mod.ENDPOINT_GROUPS)));
        """
    )
    result = subprocess.run(
        ["node", "--input-type=module", "-e", code],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr or result.stdout)
    return json.loads(result.stdout)


class ApiLoadScriptTests(unittest.TestCase):
    def test_help_documents_scenarios_and_endpoint_groups(self):
        result = run_node("--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--scenario <default|cold|warm|hot>", result.stdout)
        self.assertIn("--endpoint-group <default|operations>", result.stdout)

    def test_cold_scenario_implies_purge(self):
        config = parse_args("--scenario", "cold")

        self.assertEqual(config["scenario"], "cold")
        self.assertTrue(config["purge"])
        self.assertFalse(config["warmup"])

    def test_warm_scenario_enables_preflight_warmup_pass(self):
        config = parse_args("--scenario", "warm")

        self.assertEqual(config["scenario"], "warm")
        self.assertFalse(config["purge"])
        self.assertTrue(config["warmup"])

    def test_hot_scenario_keeps_existing_cache(self):
        config = parse_args("--scenario", "hot", "--purge")

        self.assertEqual(config["scenario"], "hot")
        self.assertFalse(config["purge"])
        self.assertFalse(config["warmup"])

    def test_default_endpoint_group_uses_readiness_not_retired_overview(self):
        config = parse_args()

        self.assertEqual(
            config["endpoints"],
            [
                "/health",
                "/api/v1/cache/stats",
                "/api/v1/videos?page=1&page_size=20&include_total=false",
                "/api/v1/videos/search?page=1&page_size=20&include_total=false",
                "/api/v1/actresses?page=1&page_size=20",
                "/api/v1/actors?page=1&page_size=20",
                "/api/v1/directors?page=1&page_size=20",
                "/api/v1/authors?page=1&page_size=20",
                "/api/v1/categories",
                "/api/v1/makers?page=1&page_size=20",
                "/api/v1/labels?page=1&page_size=20",
                "/api/v1/series?page=1&page_size=20",
                "/health/readiness",
            ],
        )

    def test_builtin_endpoint_group_names_are_exact(self):
        self.assertEqual(endpoint_group_names(), ["default", "operations"])

    def test_operations_endpoint_group_matches_system_monitor_reads(self):
        config = parse_args("--endpoint-group", "operations")

        self.assertEqual(config["endpointGroup"], "operations")
        self.assertEqual(
            config["endpoints"],
            [
                "/health/readiness",
                "/api/v1/downloads/candidates/summary",
                "/api/v1/scheduler/jobs",
                "/api/v1/cache/stats",
                "/api/v1/logs/summary?since_minutes=1440",
            ],
        )

    def test_rejects_retired_inventory_endpoint_group(self):
        result = run_node("--endpoint-group", "inventory", "--help")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid --endpoint-group value: inventory", result.stderr)

    def test_rejects_unknown_scenario(self):
        result = run_node("--scenario", "boiling", "--help")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid --scenario value: boiling", result.stderr)


if __name__ == "__main__":
    unittest.main()
