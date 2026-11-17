import tempfile
import unittest
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from s5validation.precipitation_positional import run_grid


class PrecipitationPositionalTests(unittest.TestCase):
    def test_last_write_geometry_reports_conforming_percentage(self):
        try:
            import pandas as pd
        except ImportError:
            self.skipTest('pandas is optional for the precipitation positional replay')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pd.DataFrame({'time': ['2026-10-07 20:05:00'], 'latitude': [44.025], 'longitude': [10.025], 'rr': [1.0]}).to_csv(root / 'data.csv', index=False)
            pd.DataFrame({'latitude': [44.075], 'longitude': [10.025], 'rr': [1.0]}).to_csv(root / 'W_IT-HSAF-ROME,SATELLITE,h40B_C_LIIB_202610072000_PINFCI.csv', index=False)
            final = root / 'final.tif'
            with rasterio.open(final, 'w', driver='GTiff', width=2, height=2, count=1, dtype='float32', nodata=-999,
                               crs='EPSG:4326', transform=from_origin(10.0, 44.1, 0.05, 0.05)) as dst:
                dst.write(np.ones((2, 2), dtype='float32'), 1)
            result = run_grid(root, final, root / 'result', '2026-10-07T20', tolerance_m=4000)
            self.assertEqual(result['assessed_cells'], 2)
            self.assertEqual(result['assignment_distance_m']['below_tolerance_pct'], 100.0)
            self.assertEqual(result['source_counts']['radar'], 1)
            self.assertEqual(result['source_counts']['H40'], 1)


if __name__ == '__main__':
    unittest.main()
