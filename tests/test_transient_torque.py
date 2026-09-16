import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

from calmath.transient_torque import torque_delta, iq_delta, integrated_deficit, intervention_status


class FakeFMTC:
    def lookup(self, rpm, torque, policy='clamp'):
        return float(torque) / 5.0


class TransientTorqueMath(unittest.TestCase):
    def test_torque_delta_positive_when_intervention_removes_torque(self):
        self.assertEqual(torque_delta(340.0, 292.0), 48.0)

    def test_torque_delta_negative_when_intervention_adds_torque(self):
        self.assertEqual(torque_delta(280.0, 300.0), -20.0)

    def test_iq_delta_maps_torque_intervention_to_iq(self):
        result = iq_delta(FakeFMTC(), 1800.0, 340.0, 290.0)
        self.assertEqual(result['q_before_mg'], 68.0)
        self.assertEqual(result['q_after_mg'], 58.0)
        self.assertEqual(result['delta_q_mg'], 10.0)
        self.assertEqual(result['fmtc_policy'], 'clamp')

    def test_integrated_deficit_uses_trapezoid_rule(self):
        samples = [
            {'t_s': 0.0, 'delta_nm': 0.0},
            {'t_s': 0.5, 'delta_nm': 40.0},
            {'t_s': 1.0, 'delta_nm': 20.0},
            {'t_s': 1.5, 'delta_nm': 0.0},
        ]
        result = integrated_deficit(samples)
        self.assertAlmostEqual(result['nm_s'], 30.0)
        self.assertEqual(result['peak_deficit_nm'], 40.0)
        self.assertEqual(result['duration_s'], 1.5)

    def test_integrated_deficit_rejects_non_monotonic_time(self):
        with self.assertRaises(ValueError):
            integrated_deficit([
                {'t_s': 1.0, 'delta_nm': 10.0},
                {'t_s': 0.5, 'delta_nm': 20.0},
            ])

    def test_intervention_status_requires_exceeding_uncertainty(self):
        self.assertEqual(intervention_status(25.0, 10.0), 'CALCULATED')
        self.assertEqual(intervention_status(10.0, 10.0), 'WITHIN_UNCERTAINTY')
        self.assertEqual(intervention_status(-9.0, 10.0), 'WITHIN_UNCERTAINTY')


if __name__ == '__main__':
    unittest.main()
