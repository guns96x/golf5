import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

from calmath.transient_runtime import analyze_runtime


class FakeFMTC:
    def lookup(self, rpm, torque, policy='clamp'):
        return torque / 5.0


class RuntimeTransient(unittest.TestCase):
    def test_known_asd_intervention_and_recovery(self):
        samples = [
            {'t_s': 0.0, 'rpm': 1600, 'torque_before_asd_nm': 300, 'torque_after_asd_nm': 250,
             'dynamic_smoke_mg': 0.0},
            {'t_s': 0.5, 'rpm': 1700, 'torque_before_asd_nm': 320, 'torque_after_asd_nm': 280,
             'dynamic_smoke_mg': 2.0},
            {'t_s': 1.0, 'rpm': 1800, 'torque_before_asd_nm': 320, 'torque_after_asd_nm': 310,
             'dynamic_smoke_mg': 1.0},
            {'t_s': 1.5, 'rpm': 1900, 'torque_before_asd_nm': 320, 'torque_after_asd_nm': 320,
             'dynamic_smoke_mg': 0.0},
        ]
        r = analyze_runtime(samples, FakeFMTC(), uncertainty_nm=5.0)
        self.assertEqual(r['status'], 'CALCULATED')
        self.assertEqual(r['peak_asd_deficit_nm'], 50.0)
        self.assertAlmostEqual(r['integrated_asd_deficit_nm_s'], 37.5)
        self.assertEqual(r['samples'][0]['delta_q_asd_mg'], 10.0)
        self.assertAlmostEqual(r['time_to_90pct_post_asd_torque_s'], 1.0)
        self.assertEqual(r['peak_dynamic_smoke_mg'], 2.0)

    def test_missing_runtime_channels_returns_hold(self):
        r = analyze_runtime([{'t_s': 0.0, 'rpm': 1500}], FakeFMTC(), uncertainty_nm=5.0)
        self.assertEqual(r['status'], 'HOLD')
        self.assertIn('torque_before_asd_nm', r['missing_required_channels'])
        self.assertIn('torque_after_asd_nm', r['missing_required_channels'])

    def test_dynamic_smoke_is_not_folded_into_asd_iq_delta(self):
        samples = [
            {'t_s': 0.0, 'rpm': 1800, 'torque_before_asd_nm': 300, 'torque_after_asd_nm': 300,
             'dynamic_smoke_mg': 5.0},
            {'t_s': 0.5, 'rpm': 1850, 'torque_before_asd_nm': 300, 'torque_after_asd_nm': 300,
             'dynamic_smoke_mg': 0.0},
        ]
        r = analyze_runtime(samples, FakeFMTC(), uncertainty_nm=1.0)
        self.assertEqual(r['samples'][0]['delta_q_asd_mg'], 0.0)
        self.assertEqual(r['samples'][0]['dynamic_smoke_mg'], 5.0)


if __name__ == '__main__':
    unittest.main()
