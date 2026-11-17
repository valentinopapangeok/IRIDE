import unittest

import numpy as np

from s5validation.methane_positional import _summary


class MethanePositionalTests(unittest.TestCase):
    def test_strict_declared_resolution_percentage(self):
        result = _summary(np.array([3499.0, 3500.0, 100.0]), 3500.0, 80.0)
        self.assertAlmostEqual(result["below_tolerance_pct"], 66.6666666667)
        self.assertEqual(result["acceptance"], "FAIL")

    def test_passes_plan_target(self):
        result = _summary(np.array([100.0, 200.0, 3400.0]), 3500.0, 80.0)
        self.assertEqual(result["below_tolerance_pct"], 100.0)
        self.assertEqual(result["acceptance"], "PASS")
