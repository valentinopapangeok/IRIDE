import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from s5validation.downloads import inventory_campaign
from s5validation.pipeline import discover
from test_downloads import FakeStorage


class PipelineInputTests(unittest.TestCase):
    def test_inventory_accepts_product_list(self):
        storage = FakeStorage()
        storage.add('ar_delivery/', 'IRIDE-S_S5-02-01_20261005_V1.tif')
        storage.add('ar_delivery/', 'IRIDE-S_S5-02-02_20261005_V1.tif')
        config = {'campaign': {'start': '2026-10-01T00:00:00+00:00', 'end': '2027-01-01T00:00:00+00:00'},
                  'delivery': {'prefix': 'ar_delivery/'},
                  'products': {'S5-02-01': {}, 'S5-02-02': {}}}
        items, errors = inventory_campaign(storage, config, products=['S5-02-02'])
        self.assertFalse(errors)
        self.assertEqual({item['product'] for item in items}, {'S5-02-02'})

    def test_manifest_discovery_accepts_product_list(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = root / 'deliveries.json'
            manifest.write_text(json.dumps([
                {'product': 'S5-02-01', 'delivery_id': 'a', 'revision': 'v1', 'uri': 'a.tif', 'acquired_at': '2026-10-05T00:00:00+00:00'},
                {'product': 'S5-02-02', 'delivery_id': 'b', 'revision': 'v1', 'uri': 'b.tif', 'acquired_at': '2026-10-05T00:00:00+00:00'}]), encoding='utf-8')
            config = {'delivery': {'mode': 'manifest', 'manifest': str(manifest)}, 'products': {'S5-02-01': {}, 'S5-02-02': {}}}
            found = discover(config, root, products=['S5-02-02'])
            self.assertEqual([item.product for item in found], ['S5-02-02'])


if __name__ == '__main__':
    unittest.main()
