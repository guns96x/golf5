import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

from calmath.transient_diff import characteristic_snapshot, compare_snapshots


class FakeCurve:
    name = 'ASDdc_trqLimHi_CUR'
    kind = 'CURVE'
    address = 0x100
    unit = 'Nm'
    x = [1.0, 2.0]
    values = [10.0, 20.0]


class FakeMap:
    name = 'FlMng_qDynSmoke_MAP'
    kind = 'MAP'
    address = 0x200
    unit = 'mg/stroke'
    x = [1000.0, 2000.0]
    y = [0.0, 100.0]
    grid = [[1.0, 2.0], [3.0, 4.0]]


class FakeValue:
    name = 'ASDdc_swtGearSel_C'
    kind = 'VALUE'
    address = 0x300
    unit = '-'
    value = 2.0


class TransientDiff(unittest.TestCase):
    def test_snapshot_normalizes_curve_map_and_value(self):
        c = characteristic_snapshot(FakeCurve())
        m = characteristic_snapshot(FakeMap())
        v = characteristic_snapshot(FakeValue())
        self.assertEqual(c['values'], [10.0, 20.0])
        self.assertEqual(m['values'], [1.0, 2.0, 3.0, 4.0])
        self.assertEqual(v['values'], [2.0])
        self.assertEqual(m['shape'], [2, 2])

    def test_compare_snapshots_reports_numeric_deltas(self):
        base = {'name': 'x', 'kind': 'CURVE', 'address': 1, 'unit': 'Nm', 'shape': [2],
                'axes': [[1, 2]], 'values': [10.0, 20.0]}
        same = dict(base)
        changed = dict(base, values=[12.0, 18.0])
        r_same = compare_snapshots(base, same)
        r_change = compare_snapshots(base, changed)
        self.assertTrue(r_same['identical'])
        self.assertEqual(r_same['changed_points'], 0)
        self.assertFalse(r_change['identical'])
        self.assertEqual(r_change['changed_points'], 2)
        self.assertEqual(r_change['min_delta'], -2.0)
        self.assertEqual(r_change['max_delta'], 2.0)
        self.assertEqual(r_change['max_abs_delta'], 2.0)

    def test_compare_rejects_structure_mismatch(self):
        a = {'name': 'x', 'kind': 'CURVE', 'address': 1, 'unit': 'Nm', 'shape': [2],
             'axes': [[1, 2]], 'values': [1, 2]}
        b = dict(a, shape=[3], values=[1, 2, 3])
        with self.assertRaises(ValueError):
            compare_snapshots(a, b)


if __name__ == '__main__':
    unittest.main()
