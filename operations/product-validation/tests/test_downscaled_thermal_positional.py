import unittest

import numpy as np

from s5validation.downscaled_thermal_positional import _nearest_indices, _summary


class DownscaledThermalPositionalTests(unittest.TestCase):
    def test_footprint_summary_uses_strict_threshold(self):
        result = _summary(np.array([999.0, 1000.0, 1200.0]), 1000.0, 80.0)
        self.assertAlmostEqual(result["below_tolerance_pct"], 100.0 / 3.0)
        self.assertEqual(result["acceptance"], "FAIL")

    def test_nearest_index_handles_geographic_bins(self):
        source_lon = np.array([12.00, 12.03, 12.06])
        source_lat = np.array([42.00, 42.03, 42.06])
        indices = _nearest_indices(np.array([12.001, 12.059]), np.array([42.001, 42.059]), source_lon, source_lat, 42.0)
        self.assertEqual(indices.tolist(), [0, 2])

