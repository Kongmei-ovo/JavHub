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


class ApiLoadScriptTests(unittest.TestCase):
    def test_help_documents_scenarios_and_endpoint_groups(self):
        result = run_node("--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--scenario <default|cold|warm|hot>", result.stdout)
        self.assertIn("--endpoint-group <default|inventory>", result.stdout)

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

    def test_inventory_endpoint_group_uses_inventory_read_endpoints(self):
        config = parse_args("--endpoint-group", "inventory")

        self.assertEqual(config["endpointGroup"], "inventory")
        self.assertEqual(
            config["endpoints"],
            [
                "/api/inventory/snapshots/latest",
                "/api/inventory/jobs",
                "/api/inventory/actors?page=1&page_size=20",
                "/api/inventory/actor-mappings/summary",
                "/api/inventory/missing",
                "/api/inventory/exempt",
                "/api/inventory/aliases",
            ],
        )

    def test_rejects_unknown_scenario(self):
        result = run_node("--scenario", "boiling", "--help")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid --scenario value: boiling", result.stderr)


if __name__ == "__main__":
    unittest.main()
