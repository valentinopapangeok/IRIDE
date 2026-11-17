import io
import tempfile
import unittest
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from s5validation.snow_positional import run_grid


class SnowPositionalTests(unittest.TestCase):
    def test_olci_grid_geometry_is_explicitly_grid_only(self):
        try:
            import xarray as xr
        except ImportError:
            self.skipTest('xarray is optional for the OLCI positional replay')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            nc = io.BytesIO()
            xr.Dataset(coords={'longitude': (('y', 'x'), np.array([[10.025, 10.075], [10.025, 10.075]])),
                               'latitude': (('y', 'x'), np.array([[44.075, 44.075], [44.025, 44.025]]))}).to_netcdf(nc, engine='h5netcdf')
            archive = root / 'S3A_OL_2_LFR____20261005T100000_20261005T100300_20261005T120000.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('geo_coordinates.nc', nc.getvalue())
                z.writestr('lqsf.nc', b'placeholder')
            final = root / 'final.tif'
            with rasterio.open(final, 'w', driver='GTiff', width=2, height=2, count=1, dtype='uint8', nodata=255,
                               crs='EPSG:4326', transform=from_origin(10.0, 44.1, 0.05, 0.05)) as dst:
                dst.write(np.ones((2, 2), dtype=np.uint8), 1)
            result = run_grid(root, final, root / 'result')
            self.assertEqual(result['grid_status'], 'MEASURED_LINEAGE')
            self.assertEqual(result['scene_count'], 1)
            self.assertEqual(result['assessed_final_cells'], 4)


if __name__ == '__main__':
    unittest.main()
