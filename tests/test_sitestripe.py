import copy
import json
from pathlib import Path
import sys
import unittest

SITE = Path(__file__).resolve().parents[1] / 'site'
sys.path.insert(0, str(SITE))
import build
from affiliate_links import validate_sitestripe_url, product_affiliate_url
from import_sitestripe import prepare_import


class SiteStripeTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((SITE / 'products.json').read_text())
        self.product = copy.deepcopy(self.data['products'][0])
        self.product.update(asin='B0ZZZZZZZZ', name='Import validation fixture', approved=True,
                            sitestripe_url='https://www.amazon.com/dp/B0ZZZZZZZZ?tag=kitchenfi0fde-20&linkCode=ll1&linkId=fixture',
                            variant='Fixture variant', seller='Fixture seller', verified_at='2026-11-07',
                            source_url='https://example.com/specifications', content_rights='original-editorial-graphic',
                            editorial_reason='Test fixture only, never an import entry')

    def test_preserves_long_link_in_pages_and_feed_helper(self):
        p = self.product
        self.assertEqual(product_affiliate_url(p, 'kitchenfi0fde-20'), p['sitestripe_url'])
        self.assertIn('linkId=fixture', build.buy(p, 'kitchenfi0fde-20'))

    def test_rejects_wrong_tag_asin_and_destination(self):
        u = self.product['sitestripe_url']
        for bad in (u.replace('kitchenfi0fde-20','other-20'), u.replace('B0ZZZZZZZZ','B0YYYYYYYY'),
                    u.replace('www.amazon.com','www.amazon.com.evil.example'), 'https://amzn.to/example',
                    u+'&tag=other-20'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_sitestripe_url(bad, 'B0ZZZZZZZZ', 'kitchenfi0fde-20')

    def test_valid_batch_preserves_existing_and_original_graphics(self):
        before = copy.deepcopy(self.data)
        result = prepare_import(self.data, [self.product])
        self.assertEqual(self.data, before)
        self.assertEqual(result['products'][:-1], self.data['products'])
        self.assertTrue(result['products'][-1]['graphic_only'])
        sample = {'products': [result['products'][-1]], 'subcategories': {}, 'gift_guides': {}, 'comparisons': {}}
        build.hide_unphotographed(sample, lambda _: False)
        self.assertEqual(len(sample['products']),1)

    def test_invalid_batch_never_changes_source(self):
        before = copy.deepcopy(self.data)
        for entries in ([self.product,self.product], [dict(self.product, approved=False)],
                        [dict(self.product, seller='')], [dict(self.product, asin=self.data['products'][0]['asin'])]):
            with self.subTest(entries=len(entries)), self.assertRaises(ValueError):
                prepare_import(self.data,entries)
            self.assertEqual(self.data,before)


if __name__ == '__main__':
    unittest.main()
