"""Regression tests for automatically generated static HTML repairs."""
import importlib.util
import os
import pathlib
import tempfile
import unittest
from unittest.mock import patch

FILE = pathlib.Path(__file__).resolve().parents[1] / "site" / "auto_repair.py"
spec = importlib.util.spec_from_file_location("kff_auto_repair", FILE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class SafeRepairTests(unittest.TestCase):
    def run_fix(self, content):
        with tempfile.TemporaryDirectory() as td:
            path = pathlib.Path(td) / "index.html"
            path.write_text(content, encoding="utf-8")
            with patch.dict(os.environ, {"KFF_REPAIR_DRY_RUN": "0"}):
                changes, status = module.repair(path)
            return changes, status, path.read_text(encoding="utf-8")

    def test_uses_existing_heading_only(self):
        original = "<html><head></head><body><h1>Compact Kitchen Appliances for Small Apartments</h1></body></html>"
        changes, status, result = self.run_fix(original)
        self.assertEqual(status, "modified")
        self.assertIn("missing-title-from-existing-h1", changes)
        self.assertIn('<title>Compact Kitchen Appliances for Small Apartments</title>', result)
        self.assertIn('name="description"', result)

    def test_no_fabricated_affiliate_link(self):
        original = "<html><head><title>Kitchen</title></head><body><h1>Kitchen</h1><p>Buy now</p></body></html>"
        changes, status, result = self.run_fix(original)
        self.assertEqual(changes, [])
        self.assertEqual(status, "no-safe-change")
        self.assertEqual(result, original)

    def test_adds_disclosure_only_for_known_tag(self):
        original = ('<html><head><title>Kitchen</title></head><body><h1>Kitchen</h1>'
                    '<a href="https://www.amazon.com/dp/B0DHD15DZ1?tag=kitchenfi0fde-20">View</a></body></html>')
        changes, status, result = self.run_fix(original)
        self.assertIn("missing-associate-disclosure", changes)
        self.assertIn("As an Amazon Associate I earn from qualifying purchases.", result)

    def test_does_not_guess_unknown_tracking_id(self):
        original = ('<html><head><title>Kitchen</title></head><body><h1>Kitchen</h1>'
                    '<a href="https://www.amazon.com/dp/B0DHD15DZ1?tag=unverified-20">View</a></body></html>')
        changes, status, result = self.run_fix(original)
        self.assertNotIn("missing-associate-disclosure", changes)
        self.assertEqual(result, original)

if __name__ == "__main__":
    unittest.main()
