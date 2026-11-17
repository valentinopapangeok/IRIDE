import tempfile
import unittest
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from s5validation.solar_positional import run_grid


class SolarPositionalTests(unittest.TestCase):
    def test_source_and_final_grid_alignment_is_measured(self):
        try:
            import xarray as xr
        except ImportError:
            self.skipTest('xarray is optional for the solar positional replay')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'DNIin20261031_test.nc'
            xr.Dataset({'DNI': (('time', 'lat', 'lon'), np.ones((1, 2, 2), dtype=np.float32))},
                       coords={'time': [0], 'lon': [10.025, 10.075], 'lat': [44.025, 44.075]}).to_netcdf(source)
            final_path = root / 'final.tif'
            with rasterio.open(final_path, 'w', driver='GTiff', width=2, height=2, count=1,
                               dtype='float32', nodata=-9999, crs='EPSG:4326',
                               transform=from_origin(10.0, 44.1, 0.05, 0.05)) as dst:
                dst.write(np.ones((2, 2), dtype=np.float32), 1)
            result = run_grid(source, final_path, root / 'result')
            method = result['methods']['source_grid_centre']
            self.assertEqual(result['assessed_cells'], 4)
            self.assertEqual(method['below_threshold_pct'], 100.0)
            self.assertLess(method['max_m'], 1.0)


if __name__ == '__main__':
    unittest.main()
