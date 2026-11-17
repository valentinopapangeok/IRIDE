import unittest

import numpy as np

from s5validation.cloud_positional import _summary


class CloudPositionalTests(unittest.TestCase):
    def test_strict_tolerance_percentage(self):
        result = _summary(np.array([2999.9, 3000.0, 1000.0]), 3000.0)
        self.assertAlmostEqual(result["below_tolerance_pct"], 66.6666666667)
        self.assertEqual(result["acceptance"], "FAIL")

    def test_target_pass(self):
        result = _summary(np.array([1.0, 2999.0, 2500.0]), 3000.0)
        self.assertEqual(result["below_tolerance_pct"], 100.0)
        self.assertEqual(result["acceptance"], "PASS")
