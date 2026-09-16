import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

from calmath.injection_selector import selector_components, blend_duration, invert_blended_duration


class FakeMap:
    def __init__(self, y, scale, offset=0.0):
        self.y = list(y)
        self.scale = scale
        self.offset = offset

    def lookup(self, rpm, q, y_policy='clamp'):
        if q <= self.y[0]:
            qq = self.y[0]
        elif q >= self.y[-1]:
            qq = self.y[-1]
        else:
            qq = q
        return self.offset + self.scale * qq


class InjectionSelector(unittest.TestCase):
    def test_selector_components_boundaries(self):
        self.assertEqual(selector_components(0.0, 5), (0, 0, 0.0))
        self.assertEqual(selector_components(0.5, 5), (0, 1, 0.5))
        lo, hi, w = selector_components(0.97, 5)
        self.assertEqual((lo, hi), (0, 1))
        self.assertAlmostEqual(w, 0.97)
        self.assertEqual(selector_components(1.0, 5), (1, 1, 0.0))
        self.assertEqual(selector_components(9.0, 5), (4, 4, 0.0))

    def test_blend_duration_respects_each_maps_axis_clamp(self):
        maps = [FakeMap([0, 55], 0.5), FakeMap([0, 60], 0.6)]
        d = blend_duration(maps, 3500, 58, 0.5)
        self.assertAlmostEqual(d, (27.5 + 34.8) / 2)

    def test_inverse_recovers_in_range_equivalent_iq(self):
        maps = [FakeMap([0, 55], 0.5), FakeMap([0, 60], 0.6)]
        target = blend_duration(maps, 3500, 50.0, 0.5)
        q, status = invert_blended_duration(maps, 3500, target, 0.5)
        self.assertEqual(status, 'IN_RANGE')
        self.assertAlmostEqual(q, 50.0, places=6)

    def test_inverse_reports_above_axis_instead_of_extrapolating(self):
        maps = [FakeMap([0, 55], 0.5), FakeMap([0, 60], 0.6)]
        q, status = invert_blended_duration(maps, 3500, 99.0, 0.5)
        self.assertEqual(status, 'ABOVE_AXIS')
        self.assertEqual(q, 60.0)

    def test_non_monotone_surface_rejected(self):
        class BadMap(FakeMap):
            def lookup(self, rpm, q, y_policy='clamp'):
                return -q
        with self.assertRaises(ValueError):
            invert_blended_duration([BadMap([0, 60], 1.0)], 3000, -10.0, 0.0)


if __name__ == '__main__':
    unittest.main()
