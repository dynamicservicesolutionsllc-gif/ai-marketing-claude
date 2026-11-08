import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "site"))
import build

DATA = json.loads((Path(build.__file__).parent / "products.json").read_text(encoding="utf-8"))


def by_asin(data, asin):
    return next(p for p in data["products"] if p["asin"] == asin)


class ComparisonDataTests(unittest.TestCase):
    def errors(self, data):
        return build.load(data)[1]

    def test_catalog_is_valid(self):
        self.assertEqual(self.errors(copy.deepcopy(DATA)), [])

    def test_alternatives_need_four_products_with_five_facts(self):
        data = copy.deepcopy(DATA)
        p = by_asin(data, "B0CJZW65R3")
        p["alternatives"] = p["alternatives"][:3]
        self.assertTrue(any("exactly 4" in e for e in self.errors(data)))
        data = copy.deepcopy(DATA)
        by_asin(data, "B0CJZW65R3")["alternatives"][0]["facts"].pop()
        self.assertTrue(any("exactly 5 verified facts" in e for e in self.errors(data)))

    def test_alternative_cannot_be_self_or_unknown(self):
        data = copy.deepcopy(DATA)
        by_asin(data, "B0CJZW65R3")["alternatives"][0]["asin"] = "B0CJZW65R3"
        self.assertTrue(any("different catalog product" in e for e in self.errors(data)))

    def test_no_price_claims_in_facts(self):
        data = copy.deepcopy(DATA)
        by_asin(data, "B0CJZW65R3")["comparison_facts"][0] = "Only $20."
        self.assertTrue(any("price claims" in e for e in self.errors(data)))

    def test_accessories_render_in_their_own_section(self):
        data = copy.deepcopy(DATA)
        products = data["products"]
        fryer = by_asin(data, "B0C33CHG99")
        html = build.render_pick(data, fryer, products)
        self.assertIn("<h2>Air fryer accessories</h2>", html)
        self.assertIn('data-pl="accessories"', html)

    def test_comparison_section_renders_facts(self):
        data = copy.deepcopy(DATA)
        html = build.render_pick(data, by_asin(data, "B0CJZW65R3"), data["products"])
        self.assertIn("Compare similar products", html)
        self.assertIn("Featured product: key facts", html)
        self.assertEqual(html.count("<h3>Key facts</h3>"), 4)

    def test_ledger_products_can_be_alternatives_but_unknown_asins_cannot(self):
        data = copy.deepcopy(DATA)
        fryer = by_asin(data, "B0C33CHG99")
        self.assertEqual(self.errors(data), [])  # alternatives point at approved ledger entries
        fryer["alternatives"][0]["asin"] = "B0ZZZZZZZZ"
        self.assertTrue(any("different catalog product" in e for e in self.errors(data)))

    def test_ledger_imports_keep_comparison_fields(self):
        import import_sitestripe
        ledger = json.loads((Path(build.__file__).parent / "imports" / "sitestripe.json").read_text(encoding="utf-8"))
        merged = import_sitestripe.prepare_import(copy.deepcopy(DATA), ledger)
        ninja = by_asin(merged, "B0CS3V8M9H")
        self.assertEqual(len(ninja["alternatives"]), 4)
        self.assertEqual(len(ninja["comparison_facts"]), 5)
        html = build.render_pick(merged, by_asin(merged, "B0C33CHG99"), merged["products"])
        self.assertEqual(html.count("<h3>Key facts</h3>"), 4)


if __name__ == "__main__":
    unittest.main()
