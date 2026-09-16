import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

from calmath.evidence_matrix import assess_hypothesis


class EvidenceMatrix(unittest.TestCase):
    def test_single_static_map_cannot_cross_validate(self):
        r = assess_hypothesis([
            {'family': 'static_calibration', 'status': 'CALCULATED', 'direction': 'supports', 'critical': False}
        ])
        self.assertEqual(r['status'], 'PROVISIONAL')
        self.assertEqual(r['independent_support_families'], 1)

    def test_two_independent_families_cross_validate(self):
        r = assess_hypothesis([
            {'family': 'runtime_torque', 'status': 'MEASURED', 'direction': 'supports', 'critical': True},
            {'family': 'vehicle_response', 'status': 'CALCULATED', 'direction': 'supports', 'critical': False},
        ])
        self.assertEqual(r['status'], 'CROSS_VALIDATED')
        self.assertEqual(r['independent_support_families'], 2)

    def test_contradicting_evidence_returns_conflict(self):
        r = assess_hypothesis([
            {'family': 'runtime_torque', 'status': 'MEASURED', 'direction': 'supports', 'critical': False},
            {'family': 'air_boost', 'status': 'MEASURED', 'direction': 'contradicts', 'critical': False},
        ])
        self.assertEqual(r['status'], 'CONFLICT')

    def test_missing_critical_evidence_forces_hold(self):
        r = assess_hypothesis([
            {'family': 'runtime_asd', 'status': 'UNKNOWN', 'direction': 'unknown', 'critical': True},
            {'family': 'static_calibration', 'status': 'CALCULATED', 'direction': 'supports', 'critical': False},
        ])
        self.assertEqual(r['status'], 'HOLD')
        self.assertIn('runtime_asd', r['missing_critical_families'])

    def test_duplicate_family_does_not_count_twice(self):
        r = assess_hypothesis([
            {'family': 'runtime_torque', 'status': 'MEASURED', 'direction': 'supports', 'critical': False},
            {'family': 'runtime_torque', 'status': 'CALCULATED', 'direction': 'supports', 'critical': False},
        ])
        self.assertEqual(r['status'], 'PROVISIONAL')
        self.assertEqual(r['independent_support_families'], 1)


if __name__ == '__main__':
    unittest.main()
