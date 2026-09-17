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


class RuntimeAnalysis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import calmath_engine as ce
        cls.ce = ce
        cls.stock = ce.Firmware(ce.STOCK_BIN)
        cls.cur = ce.Firmware(ce.CURRENT_BIN)

    def test_stock_equivalent_is_identity_on_stock(self):
        for rpm, q in ((2000, 40.0), (3000, 50.0), (3500, 45.0)):
            q_eq, status, _ = self.ce.stock_equivalent_q(self.stock, self.stock, rpm, q, 4)
            self.assertAlmostEqual(q_eq, q, places=3)
            self.assertEqual(status, 'IN_OEM_AXIS')

    def test_stock_equivalent_reflects_longer_stage1_duration(self):
        q_eq = self.ce.stock_equivalent_q(self.cur, self.stock, 2250, 55.5, 4)[0]
        self.assertGreater(q_eq, 55.5)

    def test_checksum_rule_holds_on_independent_known_good_files(self):
        for path in ('diagnostic-review/reference-from-hex.analysis-only.bin',
                     'diagnostic-review/new-inputs/on/03G906021QJ.Bin',
                     'gdrive_downloads/VW_Golf___391847_DPF__EGR_chk_ok.bin'):
            with open(path, 'rb') as f:
                self.assertEqual(self.ce.block_sums(f.read()), [self.ce.CHECKSUM_TARGET] * 2, path)

    def test_oem_soi_limiter_never_clips_oem_base_soi(self):
        # premise of the SOI-limiter fix: factory intent is 'limiter above base'
        self.assertEqual(self.ce.soi_limiter_clips(self.stock), [])

    def test_stage1_soi_limiter_clips_known_points(self):
        clipped = {r for r, _, _ in self.ce.soi_limiter_clips(self.cur, self.ce.SOI_FIX_MIN_RPM)}
        self.assertTrue({2250, 2500, 4000, 4500, 5000} <= clipped)
        self.assertFalse({2000, 2750, 3000, 3250, 3500} & clipped)

    def test_soi_limiter_fix_is_minimal_and_removes_every_clip(self):
        import struct
        cells = self.ce.soi_limiter_fix_cells(self.cur, self.stock)
        self.assertEqual({c['rpm_node'] for c in cells}, {2250, 2500, 4000, 4250, 5000})
        step = 1 / 42.6666666666667
        for c in cells:
            self.assertGreater(c['new_deg'], c['old_deg'])
            self.assertGreaterEqual(c['new_deg'], c['required_base_soi_deg'] - 1e-9)
            self.assertLess(c['new_deg'] - c['required_base_soi_deg'], step)
        buf = bytearray(self.cur.data)
        for c in cells:
            struct.pack_into('>h', buf, int(c['address'], 16), c['new_raw'])
        patched = self.ce.Firmware(self.ce.CURRENT_BIN)
        patched.data, patched._c = bytes(buf), {}
        self.assertEqual(self.ce.soi_limiter_clips(patched, self.ce.SOI_FIX_MIN_RPM), [])
        # cold-cranking limiter (-10 C column, <1750 rpm) is deliberately untouched
        lim_old, lim_new = self.cur['InjCrv_phiMIMax_MAP'], patched['InjCrv_phiMIMax_MAP']
        for ix, rpm in enumerate(lim_old.x):
            if rpm < self.ce.SOI_FIX_MIN_RPM:
                self.assertEqual(lim_old.grid[ix], lim_new.grid[ix])

    def test_stage0_candidate_leaves_wot_path_untouched(self):
        out_dir = self.ce.OUT_DIR
        with tempfile.TemporaryDirectory() as d:
            self.ce.OUT_DIR = d
            try:
                plan = self.ce.build_stage0_candidate(write_bin=False)
            finally:
                self.ce.OUT_DIR = out_dir
        v = plan['verification']
        self.assertTrue(v['checksum_ok'] and v['wot_chain_gear4_unchanged'] and v['gear56_wot_columns_unchanged'])
        self.assertEqual(v['changed_bytes_outside_known_objects_and_checksums'], [])
        self.assertTrue(all(c['y'] < self.ce.STAGE0_WOT_Q_MIN_MG for c in plan['cell_changes']
                            if c['map'] == 'InjCrv_phiBasGear56_MAP'))

    def test_smoke_air_coherent_cells_lower_only_with_floors(self):
        cells, ev = self.ce.smoke_air_coherent_cells(self.cur, self.stock)
        self.assertTrue(cells)
        for c in cells:
            self.assertLessEqual(c['new_mg'], c['old_mg'] + 1e-9)
            self.assertGreaterEqual(c['new_mg'], c['floor_mg'] - 0.03)
            if c['pressure_node_hpa'] == self.ce.SMOKE_TRANSIENT_COLUMN_HPA:
                self.assertGreaterEqual(c['new_mg'], c['oem_mg'] - 0.03)
        # the already cross-validated 2000-2500 rpm WOT plateau (56.5 mg) must stay within 1.5 mg
        wot = {c['rpm_node']: c['new_mg'] for c in cells if c['pressure_node_hpa'] == self.ce.SMOKE_WOT_COLUMN_HPA}
        for rpm in (2000.0, 2250.0, 2500.0):
            self.assertGreater(wot.get(rpm, 56.5), 55.0)

    def test_smoke_air_coherent_target_lambda_and_above_oem_fuel(self):
        cells, _ = self.ce.smoke_air_coherent_cells(self.cur, self.stock)
        for c in cells:
            if c['pressure_node_hpa'] != self.ce.SMOKE_WOT_COLUMN_HPA or c['bound'] != 'lambda_target':
                continue
            lam = c['air_mg'] / (14.5 * self.ce.stock_equivalent_q(self.cur, self.stock, c['rpm_node'], c['new_mg'], 4)[0])
            self.assertAlmostEqual(lam, self.ce.SMOKE_LAMBDA_TARGET, delta=0.01)
            if 2750 <= c['rpm_node'] <= 4000:
                oem = self.ce.chain(self.stock, c['rpm_node'], 4)['q_cmd_clamp_mg']
                self.assertGreater(c['target_delivered_mg'], oem * 1.15)  # still well above OEM WOT fuel

    def test_vnext4_edge_stays_inside_oem_limiter_and_bounds(self):
        out_dir = self.ce.OUT_DIR
        with tempfile.TemporaryDirectory() as d:
            import shutil
            shutil.copy(os.path.join(out_dir, 'vcds-analysis.json'), d)
            self.ce.OUT_DIR = d
            try:
                plan = self.ce.build_vnext4_candidate(write_bin=False)
            finally:
                self.ce.OUT_DIR = out_dir
        v = plan['verification']
        self.assertTrue(v['checksum_ok'] and v['soi_limiter_unchanged'] and v['soi_edits_within_limiter_and_oem_plus_cap'])
        self.assertEqual(v['changed_bytes_outside_known_objects_and_checksums'], [])
        self.assertTrue(all(c['rpm_node'] >= 3000 for c in plan['soi_cells']))
        for e in plan['predicted_effect_gear4']:
            self.assertGreaterEqual(e['lambda_after'], 1.05, e)
            if e['rpm'] >= 3000:
                self.assertLess(e['eoi_proxy_after'], e['eoi_proxy_before'])
                self.assertGreaterEqual(e['delivered_after_mg'], (e['burned_p50_now_mg'] or 0))

    def test_vnext5_balanced_adds_no_fuel_and_hits_lambda(self):
        out_dir = self.ce.OUT_DIR
        with tempfile.TemporaryDirectory() as d:
            import shutil
            shutil.copy(os.path.join(out_dir, 'vcds-analysis.json'), d)
            self.ce.OUT_DIR = d
            try:
                plan = self.ce.build_vnext5_candidate(write_bin=False)
            finally:
                self.ce.OUT_DIR = out_dir
        self.assertTrue(plan['verification']['checksum_ok'] and plan['verification']['soi_limiter_unchanged'])
        self.assertTrue(all(c['new_mg'] <= c['old_mg'] + 1e-9 for c in plan['smoke_cells']))
        for e in plan['predicted_effect_gear4']:
            self.assertGreaterEqual(e['lambda_after'], 1.11, e)
            # before = logged runtime q, after = modelled request; <=0.5 mg is model spread, smoke cells never rise
            self.assertLessEqual(e['delivered_after_mg'], e['delivered_before_mg'] + 0.5, e)

    def test_vnext6_fuel_only_never_advances_wot_soi_beyond_current(self):
        out_dir = self.ce.OUT_DIR
        with tempfile.TemporaryDirectory() as d:
            import shutil
            shutil.copy(os.path.join(out_dir, 'vcds-analysis.json'), d)
            self.ce.OUT_DIR = d
            try:
                plan = self.ce.build_vnext6_candidate(write_bin=False)
            finally:
                self.ce.OUT_DIR = out_dir
        self.assertTrue(plan['verification']['checksum_ok'] and plan['verification']['smoke_never_raised'])
        self.assertEqual(plan['lambda_target'], self.ce.BALANCED_LAMBDA_TARGET)
        # no SOI object touched: only Stage 0 objects + smoke cells differ
        self.assertTrue(all(c['map'] == 'FlMng_qPresSmoke_MAP' for c in plan['smoke_cells']))

    def test_vnext61_gated_fuel_only_3000_4000(self):
        out_dir = self.ce.OUT_DIR
        with tempfile.TemporaryDirectory() as d:
            import shutil
            for f in ('vcds-analysis.json', 'current-analysis.json'):
                shutil.copy(os.path.join(out_dir, f), d)
            self.ce.OUT_DIR = d
            try:
                plan = self.ce.build_vnext61_candidate(write_bin=False)
            finally:
                self.ce.OUT_DIR = out_dir
        v = plan['verification']
        self.assertTrue(v['checksum_ok'] and v['torque_gate_holds_every_bin'] and v['all_other_smoke_cells_unchanged'])
        self.assertEqual(v['changed_bytes_outside_cells_and_checksums'], [])  # no Stage 0, no SOI, no 5355/1800 hPa
        self.assertTrue(all(c['rpm_node'] in (3000.0, 4000.0) and c['pressure_node_hpa'] == 2000.0 for c in plan['cells']))
        for g in plan['gate_per_bin']:
            self.assertGreaterEqual(g['delivered_new_mg'], g['burned_p95_mg'] - 1e-6 if g['burned_p95_mg'] <= g['delivered_now_mg'] else g['delivered_now_mg'] - 1e-6)
            self.assertGreaterEqual(g['delivered_new_mg'], min(g['delivered_now_mg'], g['lambda115_fuel_mg']) - 1e-6)

    def test_vcds_loader(self):
        sessions = tm.load_vcds('logs/vcds/LOG-01-011-003-008.CSV')
        self.assertEqual(len(sessions), 4)
        series, meta = sessions[3]
        self.assertEqual(meta['groups'], ['011', '003', '008'])
        self.assertEqual(meta['time'], '11:54:46')
        # first data row of that session: group C at 0.21 s, 1449 rpm, 48.8 / 327.0 / 185.4 Nm
        self.assertEqual(series['trq_smoke_nm'][0][:2], (0.21, 185.4))
        self.assertEqual(series['map_mbar'][0][:2], (0.02, 1234.2))

    def test_runtime_smoke_limit_matches_static_map(self):
        # VCDS 008 'Smoke Limitation' 309.9 Nm at 2000-2250 rpm vs inverse FMTC of the 56.5 mg smoke map value
        f, s = self.cur['FMTC_trq2qBas_MAP'], self.cur['FlMng_qPresSmoke_MAP']
        for rpm in (2000, 2250):
            inv, status = f.inverse_y(rpm, s.lookup(rpm, 2000))
            self.assertEqual(status, 'IN_RANGE')
            self.assertLess(abs(inv - 309.9), 2.5)


if __name__ == '__main__':
    unittest.main()
