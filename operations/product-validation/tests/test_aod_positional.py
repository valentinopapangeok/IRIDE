import unittest

import numpy as np

from s5validation.aod_positional import _summary


class AODPositionalTests(unittest.TestCase):
    def test_strict_resolution_percentage(self):
        result = _summary(np.array([999.0, 1000.0, 100.0]), 1000.0, 80.0)
        self.assertAlmostEqual(result["below_tolerance_pct"], 66.6666666667)
        self.assertEqual(result["acceptance"], "FAIL")

    def test_plan_target_pass(self):
        result = _summary(np.array([100.0, 200.0, 900.0]), 1000.0, 80.0)
        self.assertEqual(result["below_tolerance_pct"], 100.0)
        self.assertEqual(result["acceptance"], "PASS")
