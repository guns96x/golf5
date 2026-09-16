import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

from calmath.boost_transient import analyze_boost_transient


class BoostTransient(unittest.TestCase):
    def test_step_response_metrics(self):
        samples = [
            {'t_s': 0.0, 'boost_requested_mbar': 1200, 'map_actual_mbar': 1100, 'n75_pct': 50},
            {'t_s': 0.5, 'boost_requested_mbar': 2200, 'map_actual_mbar': 1400, 'n75_pct': 98},
            {'t_s': 1.0, 'boost_requested_mbar': 2200, 'map_actual_mbar': 1900, 'n75_pct': 96},
            {'t_s': 1.5, 'boost_requested_mbar': 2200, 'map_actual_mbar': 2100, 'n75_pct': 70},
            {'t_s': 2.0, 'boost_requested_mbar': 2200, 'map_actual_mbar': 2200, 'n75_pct': 60},
        ]
        r = analyze_boost_transient(samples)
        self.assertEqual(r['status'], 'CALCULATED')
        self.assertEqual(r['peak_positive_error_mbar'], 800.0)
        self.assertEqual(r['peak_negative_error_mbar'], 0.0)
        self.assertAlmostEqual(r['time_to_90pct_step_s'], 1.0)
        self.assertEqual(r['peak_dmap_dt_mbar_s'], 1000.0)
        self.assertAlmostEqual(r['actuator_saturation_fraction'], 0.4)
        self.assertAlmostEqual(r['signed_error_area_mbar_s'], 625.0)

    def test_missing_runtime_request_returns_hold(self):
        r = analyze_boost_transient([
            {'t_s': 0.0, 'map_actual_mbar': 1100, 'n75_pct': 50},
            {'t_s': 1.0, 'map_actual_mbar': 1500, 'n75_pct': 70},
        ])
        self.assertEqual(r['status'], 'HOLD')
        self.assertIn('boost_requested_mbar', r['missing_required_channels'])

    def test_non_monotonic_time_is_rejected(self):
        with self.assertRaises(ValueError):
            analyze_boost_transient([
                {'t_s': 1.0, 'boost_requested_mbar': 2000, 'map_actual_mbar': 1500},
                {'t_s': 0.5, 'boost_requested_mbar': 2000, 'map_actual_mbar': 1600},
            ])


if __name__ == '__main__':
    unittest.main()
