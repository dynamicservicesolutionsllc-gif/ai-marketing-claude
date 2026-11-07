import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('discovery', Path(__file__).resolve().parents[1] / 'site/discover_products.py')
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)


class DiscoveryTests(unittest.TestCase):
    def test_search_contract_and_failure(self):
        with patch.object(d, 'post_json', return_value={'searchResult': {'items': []}}) as request:
            self.assertEqual(d.search_products('token', 'tag', 'kitchen', 20), [])
            payload = request.call_args.args[1]
            self.assertEqual(payload['keywords'], 'kitchen')
            self.assertEqual(payload['itemCount'], 10)
            self.assertNotIn('maxResults', payload)
        with patch.object(d, 'post_json', return_value={'errors': [{'code': 'Denied'}]}):
            with self.assertRaises(RuntimeError):
                d.search_products('token', 'tag', 'kitchen')

    def test_queue_deduplicates_and_preserves_catalog(self):
        with tempfile.TemporaryDirectory() as tmp:
            catalog = Path(tmp) / 'products.json'
            report = Path(tmp) / 'queue.json'
            catalog.write_text(json.dumps({'site': {'associate_tag': 'test-20'}, 'products': [{'asin': 'B000000001'}]}))
            before = catalog.read_bytes()
            results = [{'asin': a, 'title': 'API title must not persist', 'source': 'kitchen', 'rank': n} for n, a in enumerate(['B000000001', 'B000000002', 'B000000002'])]
            with patch.object(d, 'PRODUCTS_FILE', catalog), patch.object(d, 'log_msg'), patch.object(d, 'get_access_token', return_value='token'), patch.object(d, 'search_products', return_value=results), patch.object(d.time, 'sleep'), patch.dict(os.environ, {'AMAZON_CREATORS_CLIENT_ID': 'test', 'AMAZON_CREATORS_CLIENT_SECRET': 'test', 'KFF_DISCOVERY_REPORT': str(report)}):
                self.assertEqual(d.main(), 0)
                self.assertEqual(d.main(), 0)
            self.assertEqual(catalog.read_bytes(), before)
            self.assertEqual([x['asin'] for x in json.loads(report.read_text())['candidates']], ['B000000002'])
            self.assertNotIn('API title', report.read_text())


if __name__ == '__main__':
    unittest.main()
