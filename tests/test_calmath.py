"""Known-answer tests for tools/calmath. Run: python -m unittest discover -s tests"""
import math
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
os.chdir(ROOT)

from calmath import a2l, physics as ph, telemetry as tm  # noqa: E402


class Physics(unittest.TestCase):
    def test_fuel_flow(self):
        # 60 mg/stroke at 3000 rpm, 4 cyl: 100 injections/s -> 6 g/s -> 21.6 kg/h
        self.assertAlmostEqual(ph.injections_per_s(3000), 100.0)
        self.assertAlmostEqual(ph.fuel_flow_g_s(60, 3000), 6.0)
        self.assertAlmostEqual(ph.fuel_flow_kg_h(60, 3000), 21.6)

    def test_air_per_stroke(self):
        self.assertAlmostEqual(ph.air_mg_stroke(100.0, 3000), 1000.0)

    def test_lambda(self):
        self.assertAlmostEqual(ph.lambda_from(1000, 50, 14.5), 1000 / 725)
        self.assertAlmostEqual(ph.q_max_for_lambda(1000, 1000 / 725, 14.5), 50)
        with self.assertRaises(ValueError):
            ph.lambda_from(1000, 0, 14.5)

    def test_power_units(self):
        self.assertAlmostEqual(ph.power_w(100, 1000), 100 * 2 * math.pi * 1000 / 60)
        self.assertAlmostEqual(ph.w_to_ps(735.49875), 1.0)
        self.assertAlmostEqual(ph.w_to_hp(745.69987), 1.0)

    def test_bmep(self):
        self.assertAlmostEqual(ph.bmep_bar(300, 1.896e-3), 4 * math.pi * 300 / 1.896e-3 / 1e5)
        self.assertTrue(15 < ph.bmep_bar(300, 1.896e-3) < 25)

    def test_fuel_torque_roundtrip(self):
        t = ph.torque_from_fuel_nm(50, 42.8e6, 0.40)
        self.assertAlmostEqual(t, 4 * 50e-6 * 42.8e6 * 0.40 / (4 * math.pi))
        self.assertAlmostEqual(ph.q_from_torque_mg(t, 42.8e6, 0.40), 50)

    def test_injection_time(self):
        self.assertAlmostEqual(ph.injection_ms(30, 2000), 2.5)

    def test_road_load_known_answer(self):
        p = dict(mass_kg=1000, inertia_engine_kgm2=0, inertia_wheels_kgm2=0, wheel_radius_m=0.3, crr=0,
                 rho_air=1.2, cda_m2=0, grade_rad=0, eta_driveline=1.0)
        # v = 0.01*3000 = 30 m/s, a = 0.01*100 = 1 m/s2 -> F = 1000 N, P = 30 kW, omega = 314.16 rad/s
        t = ph.road_load_engine_torque_nm(3000, 100, 0.01, p)
        self.assertAlmostEqual(t, 30000 / ph.rpm_to_rad_s(3000))

    def test_road_load_terms(self):
        base = dict(mass_kg=1400, inertia_engine_kgm2=0.2, inertia_wheels_kgm2=3.0, wheel_radius_m=0.31, crr=0.01,
                    rho_air=1.2, cda_m2=0.7, grade_rad=0, eta_driveline=0.93)
        t0 = ph.road_load_engine_torque_nm(3000, 150, 0.01, base)
        up = dict(base, grade_rad=math.atan(0.01))
        self.assertGreater(ph.road_load_engine_torque_nm(3000, 150, 0.01, up), t0)
        lossy = dict(base, eta_driveline=0.85)
        self.assertGreater(ph.road_load_engine_torque_nm(3000, 150, 0.01, lossy), t0)


class Interpolation(unittest.TestCase):
    def test_interp_clamp_extrap(self):
        x, v = [0, 10, 20], [0, 10, 30]
        self.assertEqual(a2l._interp(x, v, 5, 'clamp'), 5)
        self.assertEqual(a2l._interp(x, v, 25, 'clamp'), 30)
        self.assertEqual(a2l._interp(x, v, 25, 'extrapolate'), 40)
        self.assertEqual(a2l._interp(x, v, -5, 'extrapolate'), 0)  # extrapolation only above the axis

    def test_rat_func_linear(self):
        db = a2l.db()
        db['compu']['__test'] = {'type': 'RAT_FUNC', 'unit': 'x', 'coeffs': [0, 100, 0, 0, 0, 1]}
        self.assertAlmostEqual(a2l.to_phys(5650, '__test'), 56.5)


BIN = open(os.path.join(ROOT, '03G906021QJ_stage1_full_power_dpf_egr_off.bin'), 'rb').read()


class A2LDecoding(unittest.TestCase):
    """Integration: values independently established by the deep-audit and Audit v3."""

    def test_smoke_map(self):
        s = a2l.load('FlMng_qPresSmoke_MAP', BIN)
        self.assertEqual(s.address, 0x1D6490)
        self.assertEqual((len(s.x), len(s.y)), (16, 12))
        self.assertAlmostEqual(s.lookup(2000, 2000), 56.5)
        self.assertEqual(s.axes[1]['input'], 'FlMng_pIATCorr_mp')

    def test_fmtc_axis_end(self):
        f = a2l.load('FMTC_trq2qBas_MAP', BIN)
        self.assertEqual(f.y[-1], 336.0)
        self.assertGreater(f.lookup(2000, 400, 'extrapolate'), f.lookup(2000, 400, 'clamp'))

    def test_fmtc_inverse(self):
        f = a2l.load('FMTC_trq2qBas_MAP', BIN)
        q = f.lookup(2500, 250.0)
        trq, status = f.inverse_y(2500, q)
        self.assertEqual(status, 'IN_RANGE')
        self.assertAlmostEqual(trq, 250.0, places=6)
        self.assertEqual(f.inverse_y(2500, 500)[1], 'ABOVE_AXIS')

    def test_gear_maps_identical_in_current_bin(self):
        a, b = a2l.load('InjCrv_phiBasGear34_MAP', BIN), a2l.load('InjCrv_phiBasGear56_MAP', BIN)
        self.assertEqual(a.grid, b.grid)


class Telemetry(unittest.TestCase):
    def test_obd_decode(self):
        self.assertEqual(tm.decode_obd('410C1B34'), ('010C', 1741.0))
        self.assertEqual(tm.decode_obd('410BE9'), ('010B', 2330.0))
        self.assertEqual(tm.decode_obd('411012FD'), ('0110', 48.61))
        self.assertEqual(tm.decode_obd('410D3C'), ('010D', 60.0))
        self.assertIsNone(tm.decode_obd('7F0112'))

    def test_time_alignment_uses_latency(self):
        rows = ['event_seq,timestamp_utc_ms,mono_ns,pid,request,value,unit,raw,latency_ms,status',
                '1,10000,0,010C,010C,1000,RPM,x,200,VALID',
                '2,10500,0,0110,0110,50,g/s,x,100,VALID']
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 'Event_RAW_test.csv')
            with open(p, 'w', encoding='utf-8') as f:
                f.write('\n'.join(rows))
            s, _ = tm.load_events(p)
        # sample times: 10000-100 = 9900 (t0) and 10500-50 = 10450 -> 0.55 s apart
        self.assertEqual(s['rpm'][0][0], 0.0)
        self.assertAlmostEqual(s['maf_g_s'][0][0], 0.55)
        self.assertAlmostEqual(s['rpm'][0][2], 0.1)

    def test_local_derivative_exact_on_quadratic(self):
        seg = [(t / 4, 1000 + 200 * (t / 4) + 10 * (t / 4) ** 2, 0) for t in range(0, 41)]
        fit, d = tm.local_poly_derivative(seg, 5.0, 3.0)
        self.assertAlmostEqual(fit, 1000 + 1000 + 250, places=6)
        self.assertAlmostEqual(d, 200 + 20 * 5, places=6)

    def test_segmentation_and_gear(self):
        series = {'rpm': [(t * 0.5, 1500 + 60 * t, 0.1) for t in range(40)],
                  'map_mbar': [(t * 0.5, 2300, 0.1) for t in range(40)],
                  'speed_kmh': [(t * 2.0 + 0.25, 0.0357 * (1500 + 60 * (t * 4 + 0.5)), 0.1) for t in range(10)]}
        segs = tm.wot_segments(series, baro=1005)
        self.assertEqual(len(segs), 1)
        g = tm.gear_ratio(series, segs[0])
        self.assertAlmostEqual(g['kmh_per_rpm'], 0.0357, places=4)
        self.assertEqual(tm.classify_gear(g['kmh_per_rpm']), 4)


if __name__ == '__main__':
    unittest.main()
