"""EDC16U34 calibration math engine - CLI.

  python tools/calmath_engine.py analyze            full analysis of current BIN + 2026-09-16 logs
  python tools/calmath_engine.py chain --rpm 3000   firmware chain at one rpm (stock vs current)

Outputs (analyze): diagnostic-review/math-engine/current-analysis.{json,md,csv}
The Markdown and CSV are generated only from the JSON structure.
"""
import argparse
import csv
import datetime
import hashlib
import json
import math
import os
import random
import statistics
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from calmath import a2l, dyno, physics as ph, telemetry as tm  # noqa: E402
from calmath.params import VEHICLE, FUEL, ENGINE, AIR  # noqa: E402

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_cand_cur = os.path.join(REPO_ROOT, 'firmware', '03G906021QJ_stage1_full_power_dpf_egr_off.bin')
CURRENT_BIN = _cand_cur if os.path.exists(_cand_cur) else '03G906021QJ_stage1_full_power_dpf_egr_off.bin'
_cand_stock = os.path.join(REPO_ROOT, 'diagnostic-review', 'reference-from-hex.analysis-only.bin')
STOCK_BIN = _cand_stock if os.path.exists(_cand_stock) else 'diagnostic-review/reference-from-hex.analysis-only.bin'
OUT_DIR = os.path.join(REPO_ROOT, 'diagnostic-review', 'math-engine')
RPM_BINS = list(range(1500, 4001, 250))
BARO_MBAR = 1005.5          # phone barometer, 2026-09-16 sessions
IAT_C = 35.0                # snapshot value, stale; only used for the smoke-axis threshold check
COOLANT_C = ENGINE['coolant_c_for_friction']['value']
ACCPED_BY_GEAR = {3: 'AccPed_trqEng2_MAP', 4: 'AccPed_trqEng3_MAP', 5: 'AccPed_trqEng4_MAP'}
LAMBDA_TABLE = (1.05, 1.10, 1.15, 1.20, 1.25, 1.30)
N_MC = 10000
MIN_MAP_ESTABLISHED = 2150  # mbar abs; below this the pull is still spooling
MAF_NEAREST_MAX_RPM = 75
LAMBDA_ANCHOR_RPM = (2000, 2250, 2500)  # operating points the current calibration already runs without complaint
PLAN_GEAR = 4                             # two repeatable 4th-gear pulls; 3rd-gear low-rpm data is spool-contaminated


class Firmware:
    def __init__(self, path):
        self.path = path
        self.data = open(path, 'rb').read()
        self.sha256 = hashlib.sha256(self.data).hexdigest()
        self._c = {}

    def __getitem__(self, name):
        if name not in self._c:
            self._c[name] = a2l.load(name, self.data)
        return self._c[name]


def chain(fw, rpm, gear):
    """Static calibration chain at full pedal. Only maps whose identity is A2L-verified are used.
    Runtime arbitration (other limiters, corrections) is NOT modelled and is reported as unknown."""
    dw = fw[ACCPED_BY_GEAR[gear]].lookup(rpm, 100.0)
    lim_p = fw['EngPrt_trqLimP_MAP'].lookup(BARO_MBAR, rpm)
    req = min(dw, lim_p)
    fmtc = fw['FMTC_trq2qBas_MAP']
    q_clamp = fmtc.lookup(rpm, req, 'clamp')
    q_extrap = fmtc.lookup(rpm, req, 'extrapolate')
    smoke_axis = fw['FlMng_qPresSmoke_MAP'].y
    q_smoke = fw['FlMng_qPresSmoke_MAP'].lookup(rpm, smoke_axis[-1])
    out = {'rpm': rpm, 'gear': gear, 'driver_wish_nm': dw, 'trq_lim_p_nm': lim_p, 'inner_torque_request_nm': req,
           'fmtc_axis_end_nm': fmtc.y[-1], 'request_beyond_fmtc_axis': req > fmtc.y[-1],
           'q_fmtc_clamp_mg': q_clamp, 'q_fmtc_extrap_mg': q_extrap,
           'q_smoke_last_column_mg': q_smoke, 'smoke_last_column_hpa': smoke_axis[-1]}
    for tag, q_path in (('clamp', q_clamp), ('extrap', q_extrap)):
        q_cmd = min(q_path, q_smoke)
        out['q_cmd_%s_mg' % tag] = q_cmd
        out['static_limiter_%s' % tag] = 'smoke' if q_smoke < q_path else 'torque_path'
    q_cmd = out['q_cmd_clamp_mg']
    soi = fw['InjCrv_phiBasGear34_MAP' if gear in (3, 4) else 'InjCrv_phiBasGear56_MAP'].lookup(rpm, q_cmd)
    sel = fw['InjVlv_numMI1_CUR'].lookup(soi)
    lo, hi = int(sel // 1), min(int(sel // 1) + 1, 6)
    dur_map = fw['InjVlv_phiInjMI1_MAP%d' % lo]
    d_lo = dur_map.lookup(rpm, q_cmd)
    d_hi = fw['InjVlv_phiInjMI1_MAP%d' % hi].lookup(rpm, q_cmd)
    dur = d_lo + (d_hi - d_lo) * (sel - lo)
    out.update({'soi_deg_btdc_hyp': soi, 'duration_map_selector': sel, 'duration_deg_hyp': dur,
                'duration_ms_hyp': ph.injection_ms(dur, rpm),
                'duration_q_axis_end_mg': dur_map.y[-1], 'q_cmd_beyond_duration_axis': q_cmd > dur_map.y[-1],
                'electrical_command_end_proxy_deg_atdc': dur - soi,
                'friction_nm': fw['EngM_trqFrc_MAP'].lookup(rpm, COOLANT_C)})
    inv, status = fmtc.inverse_y(rpm, q_cmd)
    out['ecu_inner_torque_at_q_cmd_nm'] = inv
    out['ecu_inner_torque_inverse_status'] = status
    out['ecu_brake_torque_model_nm'] = inv + out['friction_nm']
    return out


def duration_ratio(cur, stock, rpm, gear):
    """Current/stock duration at the SAME (rpm, q, selector) for the commanded q. Used as the bracket for
    how much more fuel the current duration maps deliver than the (unchanged-hardware) OEM mapping."""
    c = chain(cur, rpm, gear)
    q, sel = min(c['q_cmd_clamp_mg'], c['duration_q_axis_end_mg']), c['duration_map_selector']
    lo, hi = int(sel // 1), min(int(sel // 1) + 1, 6)
    ratios = []
    for k in (lo, hi):
        name = 'InjVlv_phiInjMI1_MAP%d' % k
        s = stock[name].lookup(rpm, q)
        if s > 0:
            ratios.append(cur[name].lookup(rpm, q) / s)
    return max(ratios) if ratios else 1.0


def segment_telemetry(series, seg, rpm):
    t = dyno.time_at_rpm(seg, rpm)
    if t is None:
        return None
    mp = tm.interp_at(series.get('map_mbar', []), t)
    # MAF: pair every MAF sample with rpm interpolated at the MAF sample's own time, then interpolate in rpm.
    pairs = []
    for ts, v, _ in series.get('maf_g_s', []):
        r = tm.interp_at(seg, ts)
        if r:
            pairs.append((r, v, ts))
    pairs.sort()
    maf, maf_gap = None, None
    for (r0, v0, t0), (r1, v1, t1) in zip(pairs, pairs[1:]):
        if r0 <= rpm <= r1 and r1 > r0:
            maf = v0 + (v1 - v0) * (rpm - r0) / (r1 - r0)
            maf_gap = abs(t1 - t0)
    if maf is None and pairs:
        near = min(pairs, key=lambda p: abs(p[0] - rpm))
        if abs(near[0] - rpm) <= MAF_NEAREST_MAX_RPM:  # end of pull: accept one sample within tolerance
            maf, maf_gap = near[1], 0.0
    return {'t_in_pull_s': t - seg[0][0], 'map_mbar': mp, 'maf_g_s': maf, 'maf_bracket_s': maf_gap,
            'air_mg_stroke': ph.air_mg_stroke(maf, rpm) if maf else None}


def speed_density_air_mg(map_mbar, rpm, t_c, ve):
    vcyl = ENGINE['displacement_m3']['value'] / ENGINE['n_cyl']['value']
    return ph.air_density(map_mbar * 100.0, t_c + 273.15) * vcyl * ve * 1e6


def analyze():
    cur, stock = Firmware(CURRENT_BIN), Firmware(STOCK_BIN)
    rng = random.Random(7)
    segments = []
    for f in tm.all_logs(('logs/20260916/Event_RAW_*.csv',)):
        series, meta = tm.load_events(f)
        for seg in tm.wot_segments(series, baro=meta['baro_mbar'] or BARO_MBAR):
            g = tm.gear_ratio(series, seg)
            if not g:
                continue
            gear = tm.classify_gear(g['kmh_per_rpm'])
            name = '%s@%.1fs' % (os.path.basename(f)[10:-4], seg[0][0])
            segments.append({'name': name, 'file': f.replace('\\', '/'), 'series': series, 'seg': seg,
                             'kmh_per_rpm': g['kmh_per_rpm'], 'ratio_mad': g['mad'], 'speed_pairs': g['n'],
                             'gear': gear, 'rpm_start': seg[0][1], 'rpm_end': seg[-1][1],
                             't_start_s': seg[0][0], 't_end_s': seg[-1][0], 'n_rpm_samples': len(seg)})
    usable = [s for s in segments if s['gear'] in (3, 4)]
    for s in usable:
        # a bin is valid for a pull only once boost is established there (spool-up is a different operating state)
        s['bins'] = [rpm for rpm in RPM_BINS
                     if (segment_telemetry(s['series'], s['seg'], rpm) or {}).get('map_mbar', 0) >= MIN_MAP_ESTABLISHED]
    mc = dyno.run(usable, RPM_BINS, BARO_MBAR, n=N_MC)

    # pooled torque by gear (all MC draws of all segments of that gear)
    pooled = {}
    for gear in (3, 4):
        for rpm in RPM_BINS:
            vals = [v for s in usable if s['gear'] == gear for v in mc[s['name']][rpm]]
            pooled.setdefault(gear, {})[rpm] = dyno.summarize(vals)

    rows = []
    for gear in (3, 4):
        for rpm in RPM_BINS:
            c_cur, c_stock = chain(cur, rpm, gear), chain(stock, rpm, gear)
            tel = [dict(segment_telemetry(s['series'], s['seg'], rpm) or {}, segment=s['name'])
                   for s in usable if s['gear'] == gear]
            tel = [t for t in tel if (t.get('map_mbar') or 0) >= MIN_MAP_ESTABLISHED]
            air = [t['air_mg_stroke'] for t in tel if t.get('air_mg_stroke')]
            maps = [t['map_mbar'] for t in tel]
            air_med = statistics.median(air) if air else None
            map_med = statistics.median(maps) if maps else None
            dratio = duration_ratio(cur, stock, rpm, gear)
            trq = pooled[gear][rpm]
            row = {'gear': gear, 'rpm': rpm, 'chain_current': c_cur, 'chain_stock': c_stock,
                   'duration_ratio_current_vs_stock': dratio, 'telemetry': tel,
                   'map_mbar_median': map_med, 'air_mg_stroke_median': air_med, 'road_torque_nm': trq}
            if trq and air_med:
                row.update(cross_check(rng, rpm, trq, air_med, map_med, c_cur, dratio,
                                       [v for s in usable if s['gear'] == gear for v in mc[s['name']][rpm]]))
            rows.append(row)

    result = {
        'generated_utc': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'firmware': {'current': {'path': CURRENT_BIN, 'sha256': cur.sha256},
                     'stock_reference': {'path': STOCK_BIN, 'sha256': stock.sha256}},
        'conditions': {'baro_mbar': BARO_MBAR, 'coolant_c': COOLANT_C, 'mc_draws': N_MC},
        'parameters': {'vehicle': VEHICLE, 'fuel': FUEL, 'engine': ENGINE, 'air': AIR},
        'segments': [{k: v for k, v in s.items() if k not in ('series', 'seg')} for s in segments],
        'rows': rows,
        'smoke_axis_check': smoke_axis_check(cur),
        'findings': [],
    }
    result['findings'] = findings(result)
    result['candidate_plan'] = candidate_plan(cur, rows, rng)
    return result


def candidate_plan(cur, rows, rng):
    """Smoke-limiter full-load column derived from measured air at the lambda the calibration already runs at
    2000-2500 rpm. No BIN is produced; this is a reviewed proposal with predicted effect and abort criteria."""
    g4 = {r['rpm']: r for r in rows if r['gear'] == PLAN_GEAR and r.get('lambda_of_commanded_fuel')}
    anchor = [g4[r]['lambda_of_commanded_fuel']['p50'] for r in LAMBDA_ANCHOR_RPM if r in g4]
    lam_target = statistics.median(anchor)
    smoke = cur['FlMng_qPresSmoke_MAP']
    iy = len(smoke.y) - 1
    ny = len(smoke.y)
    conv = a2l.db()['compu'][smoke.conversion]['coeffs']
    values_start = smoke.address + 4 + 2 * len(smoke.x) + 2 * ny
    q_air_at = {rpm: ph.q_max_for_lambda(r['air_mg_stroke_median'], lam_target, 14.5)
                for rpm, r in g4.items() if r.get('air_mg_stroke_median')}
    cells = []
    prev_x, prev_q = None, None
    for ix, node in enumerate(smoke.x):
        current = smoke.grid[ix][iy]
        r = g4.get(int(node))
        if node < 2750 or node > 4500 or not r or int(node) not in q_air_at:
            prev_x, prev_q = node, current
            continue
        q_air = q_air_at[int(node)]
        # linear interpolation from the previous node must not undercut any logged bin in between
        need = q_air
        for rpm, qa in q_air_at.items():
            if prev_x is not None and prev_x < rpm < node:
                f = (rpm - prev_x) / (node - prev_x)
                need = max(need, prev_q + (qa - prev_q) / f)
        new = min(current, math.ceil(need * 4) / 4)  # 0.25 mg steps, rounded up (never below the air limit)
        prev_x, prev_q = node, new
        if new >= current:
            continue
        raw = int(round((new * conv[1] + conv[2]) / conv[5]))
        cells.append({'map': 'FlMng_qPresSmoke_MAP', 'rpm_node': node, 'pressure_node_hpa': smoke.y[iy],
                      'address': '0x%X' % (values_start + 2 * (ix * ny + iy)), 'current_mg': current,
                      'candidate_mg': new, 'candidate_raw_s16': raw, 'candidate_raw_hex': '%04X' % (raw & 0xFFFF),
                      'q_air_at_node_mg': q_air,
                      'formula': 'q = max(air_mg_stroke / (lambda_target * 14.5), interpolation constraint of logged bins)',
                      'air_mg_stroke': r['air_mg_stroke_median']})
    # predicted torque effect at every logged bin (linear interpolation of the modified column in rpm)
    new_col = {c['rpm_node']: c['candidate_mg'] for c in cells}
    col = [new_col.get(x, smoke.grid[i][iy]) for i, x in enumerate(smoke.x)]
    effects = []
    for rpm, r in sorted(g4.items()):
        q_cap = a2l._interp(smoke.x, col, rpm, 'clamp')
        c = r['chain_current']
        q_new_cmd = min(c['q_cmd_clamp_mg'], q_cap)
        if q_new_cmd >= c['q_cmd_clamp_mg'] - 1e-9:
            continue
        draws = []
        dratio = r['duration_ratio_current_vs_stock']
        for _ in range(4000):
            eta = rng.uniform(FUEL['eta_brake_full_load']['min'], FUEL['eta_brake_full_load']['max'])
            lhv = rng.uniform(FUEL['lhv_j_kg']['min'], FUEL['lhv_j_kg']['max'])
            q_burn = rng.uniform(r['implied_burned_q_mg']['p05'], r['implied_burned_q_mg']['p95'])
            q_del_new = min(q_new_cmd, c['duration_q_axis_end_mg']) * rng.uniform(1.0, dratio)
            draws.append(ph.torque_from_fuel_nm(min(q_burn, q_del_new), lhv, eta) - ph.torque_from_fuel_nm(q_burn, lhv, eta))
        c_new = chain_with_q(cur, rpm, PLAN_GEAR, q_new_cmd)
        effects.append({'rpm': rpm, 'q_cmd_now_mg': c['q_cmd_clamp_mg'], 'q_cmd_new_mg': q_new_cmd,
                        'delta_torque_nm': dyno.summarize(draws),
                        'lambda_cmd_now_p50': r['lambda_of_commanded_fuel']['p50'],
                        # same air/MAF basis as lambda_cmd_now: scale by the delivered-fuel ratio
                        'lambda_cmd_new_p50': r['lambda_of_commanded_fuel']['p50']
                        * min(c['q_cmd_clamp_mg'], c['duration_q_axis_end_mg'])
                        / min(q_new_cmd, c['duration_q_axis_end_mg']),
                        'elec_end_proxy_now_deg': c['electrical_command_end_proxy_deg_atdc'],
                        'elec_end_proxy_new_deg': c_new['electrical_command_end_proxy_deg_atdc'],
                        'duration_ms_now': c['duration_ms_hyp'], 'duration_ms_new': c_new['duration_ms_hyp']})
    return {'status': 'PROVISIONAL — no BIN generated',
            'lambda_target': lam_target,
            'lambda_target_source': 'median commanded-fuel lambda of gear-4 pulls at %s rpm (measured air, current smoke map)' % (LAMBDA_ANCHOR_RPM,),
            'cells': cells, 'predicted_effect': effects,
            'validation_metric': 'gear-4 WOT 2750-4000 rpm: road torque P50 must not fall by more than the pull-to-pull '
                                 'spread; logged IQ (VCDS) must equal the new smoke column within 1 mg where it binds',
            'abort_criteria': ['road torque P50 at any 3000-3750 rpm bin drops > 15 Nm vs this analysis',
                               'visible smoke unchanged AND logged IQ already below the new cap (cap had no effect)',
                               'any new DTC'],
            'rollback': CURRENT_BIN}


def chain_with_q(fw, rpm, gear, q):
    soi = fw['InjCrv_phiBasGear34_MAP' if gear in (3, 4) else 'InjCrv_phiBasGear56_MAP'].lookup(rpm, q)
    sel = fw['InjVlv_numMI1_CUR'].lookup(soi)
    dur = duration_at(fw, rpm, q, sel)
    return {'soi_deg_btdc_hyp': soi, 'duration_map_selector': sel, 'duration_deg_hyp': dur,
            'duration_ms_hyp': ph.injection_ms(dur, rpm), 'electrical_command_end_proxy_deg_atdc': dur - soi}


def duration_at(fw, rpm, q, sel, y_policy='clamp'):
    lo, hi = int(sel // 1), min(int(sel // 1) + 1, 6)
    d_lo = fw['InjVlv_phiInjMI1_MAP%d' % lo].lookup(rpm, q, y_policy)
    d_hi = fw['InjVlv_phiInjMI1_MAP%d' % hi].lookup(rpm, q, y_policy)
    return d_lo + (d_hi - d_lo) * (sel - lo)


def stock_equivalent_q(cur, stock, rpm, q_cmd, gear):
    """Fuel mass the injector actually receives, expressed through the OEM duration calibration:
    solve stock_duration(rpm, q_eq, same selector) = current_duration(rpm, q_cmd).
    Rationale: hardware (PDE injector, cam) is stock, so the OEM duration map is the best available
    duration->mass relation. Beyond the OEM q axis the last slope is extended and flagged."""
    c = chain_with_q(cur, rpm, gear, q_cmd)
    target, sel = c['duration_deg_hyp'], c['duration_map_selector']
    lo_q, hi_q = 0.0, 120.0
    for _ in range(60):
        mid = (lo_q + hi_q) / 2
        if duration_at(stock, rpm, mid, sel, 'extrapolate') < target:
            lo_q = mid
        else:
            hi_q = mid
    q_eq = (lo_q + hi_q) / 2
    lo, hi = int(sel // 1), min(int(sel // 1) + 1, 6)
    axis_end = min(stock['InjVlv_phiInjMI1_MAP%d' % lo].y[-1], stock['InjVlv_phiInjMI1_MAP%d' % hi].y[-1])
    return q_eq, ('EXTRAPOLATED_BEYOND_OEM_AXIS' if q_eq > axis_end else 'IN_OEM_AXIS'), c


def established_bins(series, seg, rpm_bins, key='map_mbar'):
    """rpm bins reached after boost first reached MIN_MAP_ESTABLISHED in this pull."""
    t_est = next((t for t, v, _ in series.get(key, []) if seg[0][0] <= t <= seg[-1][0] and v >= MIN_MAP_ESTABLISHED), None)
    if t_est is None:
        return []
    return [rpm for rpm in rpm_bins if (dyno.time_at_rpm(seg, rpm) or -1) >= t_est]


def phone_gear_reference():
    """k (km/h per rpm) and rpm-rate at 2500 rpm per gear from the phone OBD pulls (which have speed)."""
    ref = {}
    for f in tm.all_logs(('logs/20260916/Event_RAW_*.csv',)):
        series, meta = tm.load_events(f)
        for seg in tm.wot_segments(series, baro=meta['baro_mbar'] or BARO_MBAR):
            g = tm.gear_ratio(series, seg)
            gear = g and tm.classify_gear(g['kmh_per_rpm'])
            t = dyno.time_at_rpm(seg, 2500)
            d = tm.local_poly_derivative(seg, t, dyno.NOMINAL_WINDOW_S) if (gear and t) else None
            if d:
                ref.setdefault(gear, {'k': [], 'rate2500': []})
                ref[gear]['k'].append(g['kmh_per_rpm'])
                ref[gear]['rate2500'].append(d[1])
    return {g: {'kmh_per_rpm': statistics.median(v['k']), 'rate2500_rpm_s': statistics.median(v['rate2500'])}
            for g, v in ref.items()}


def analyze_vcds(path):
    cur, stock = Firmware(CURRENT_BIN), Firmware(STOCK_BIN)
    gear_ref = phone_gear_reference()
    rng = random.Random(11)
    pulls = []
    for series, meta in tm.load_vcds(path):
        for seg in tm.wot_segments(series, baro=BARO_MBAR):
            t = dyno.time_at_rpm(seg, 2500)
            d = tm.local_poly_derivative(seg, t, 1.5) if t else None
            gear, rel = None, None
            if d:
                g, r = min(((g, abs(d[1] / v['rate2500_rpm_s'] - 1)) for g, v in gear_ref.items()), key=lambda x: x[1])
                if r <= 0.25:
                    gear, rel = g, r
            pulls.append({'name': '%s@%.1fs' % (meta['label'], seg[0][0]), 'session': meta['label'],
                          'firmware': 'current' if meta['day'] == '16' else 'garage (fuel path byte-identical to current)',
                          'series': series, 'seg': seg, 'gear': gear, 'rate2500_rpm_s': d and d[1],
                          'gear_rate_mismatch': rel, 'rpm_start': seg[0][1], 'rpm_end': seg[-1][1],
                          'kmh_per_rpm': gear and gear_ref[gear]['kmh_per_rpm']})
    usable = [p for p in pulls if p['gear']]
    for p in usable:
        p['bins'] = established_bins(p['series'], p['seg'], RPM_BINS)
    mc = dyno.run(usable, RPM_BINS, BARO_MBAR, n=N_MC)
    rows = []
    for p in usable:
        s = p['series']
        for rpm in p['bins']:
            t = dyno.time_at_rpm(p['seg'], rpm)
            ch = {k: tm.interp_at(s[k], t) for k in ('boost_spec_mbar', 'map_mbar', 'n75_duty_pct', 'maf_act_mg',
                                                     'maf_spec_mg', 'trq_request_nm', 'trq_limit_nm', 'trq_smoke_nm')}
            if None in ch.values():
                continue
            if ch['trq_request_nm'] < MIN_WOT_REQUEST_NM:
                continue  # pedal lifted inside the detected segment
            lims = {'driver_request': ch['trq_request_nm'], 'torque_limit': ch['trq_limit_nm'], 'smoke_limit': ch['trq_smoke_nm']}
            inner = min(lims.values())
            binding = sorted(k for k, v in lims.items() if v - inner <= VCDS_TORQUE_RESOLUTION_NM)
            fmtc = cur['FMTC_trq2qBas_MAP']
            q_rt = fmtc.lookup(rpm, inner)
            q_eq, q_eq_status, c = stock_equivalent_q(cur, stock, rpm, q_rt, p['gear'])
            trq = dyno.summarize(mc[p['name']][rpm])
            fr = cur['EngM_trqFrc_MAP'].lookup(rpm, COOLANT_C)
            row = {'pull': p['name'], 'gear': p['gear'], 'rpm': rpm, 't_s': t, **ch,
                   'boost_error_mbar': ch['map_mbar'] - ch['boost_spec_mbar'],
                   'runtime_inner_torque_nm': inner, 'binding_limiter': binding,
                   'q_runtime_mg': q_rt, 'q_stock_equivalent_mg': q_eq, 'q_stock_equivalent_status': q_eq_status,
                   'lambda_runtime_cmd': ph.lambda_from(ch['maf_act_mg'], q_rt, 14.5),
                   'lambda_stock_equivalent': ph.lambda_from(ch['maf_act_mg'], q_eq, 14.5),
                   'soi_deg_btdc_hyp': c['soi_deg_btdc_hyp'], 'duration_deg_hyp': c['duration_deg_hyp'],
                   'duration_ms_hyp': c['duration_ms_hyp'], 'elec_end_proxy_deg_atdc': c['electrical_command_end_proxy_deg_atdc'],
                   'friction_nm': fr, 'road_torque_nm': trq}
            if trq:
                inner_est = [v - fr for v in mc[p['name']][rpm]]
                row['road_inner_torque_nm'] = dyno.summarize(inner_est)
                row['torque_realization'] = dyno.summarize([v / inner for v in inner_est])
                burned = []
                for _ in range(4000):
                    tb = rng.choice(mc[p['name']][rpm])
                    burned.append(ph.q_from_torque_mg(tb, rng.uniform(FUEL['lhv_j_kg']['min'], FUEL['lhv_j_kg']['max']),
                                                      rng.uniform(FUEL['eta_brake_full_load']['min'], FUEL['eta_brake_full_load']['max'])))
                row['implied_burned_q_mg'] = dyno.summarize(burned)
                row['unconverted_fuel_mg_p50'] = q_eq - row['implied_burned_q_mg']['p50']
            rows.append(row)
    res = {'generated_utc': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
           'source': path.replace('\\', '/'), 'gear_reference_from_phone_logs': gear_ref,
           'pulls': [{k: v for k, v in p.items() if k not in ('series', 'seg')} for p in pulls],
           'rows': rows, 'smoke_torque_equivalence': smoke_equivalence(cur, rows),
           'boost_control': boost_control_summary(usable), 'plan_check': plan_check(cur, rows)}
    res['findings'] = vcds_findings(res)
    return res


VCDS_TORQUE_RESOLUTION_NM = 2.5  # group 008 torque channels step in ~2.44 Nm
MIN_WOT_REQUEST_NM = 280         # full-pedal driver request never falls below ~305 Nm up to 4100 rpm in these logs
SMOKE_NODES_TO_FIT = (3000.0, 4000.0)
PLAN_BINS = (2750, 3000, 3250, 3500, 3750, 4000)


def burned_p95_constraints(vcds_res, phone_res):
    """Per rpm: the highest P95 burned-fuel estimate over every logged pull (VCDS and phone, all gears)."""
    cons = {}
    for r in vcds_res['rows']:
        if r.get('implied_burned_q_mg'):
            cons[r['rpm']] = max(cons.get(r['rpm'], 0), r['implied_burned_q_mg']['p95'])
    for r in phone_res['rows']:
        if r.get('implied_burned_q_mg') and r['gear'] in (3, 4):
            cons[r['rpm']] = max(cons.get(r['rpm'], 0), r['implied_burned_q_mg']['p95'])
    return cons


def fit_smoke_column(cur, stock, cons, q_runtime):
    """Lowest smoke-column node values (0.25 mg grid) such that, after interpolation, the stock-equivalent fuel
    delivered at every constrained rpm stays >= the P95 burned fuel there. Nodes are fitted in rpm order; each node
    only has to satisfy bins up to the next node given the already fitted previous node."""
    smoke = cur['FlMng_qPresSmoke_MAP']
    iy = len(smoke.y) - 1
    col = {x: smoke.grid[i][iy] for i, x in enumerate(smoke.x)}
    fitted = dict(col)
    report = []
    for k, node in enumerate(SMOKE_NODES_TO_FIT):
        nxt = SMOKE_NODES_TO_FIT[k + 1] if k + 1 < len(SMOKE_NODES_TO_FIT) else None
        prev = max(x for x in smoke.x if x < node)
        bins = [b for b in PLAN_BINS if prev < b <= node and b in cons]
        if nxt is None:
            bins += [b for b in PLAN_BINS if b > node and b in cons]
        best = col[node]
        v = col[node]
        while v - 0.25 >= 30.0:
            trial = dict(fitted)
            trial[node] = v - 0.25
            ok = True
            for b in bins:
                cap = a2l._interp(smoke.x, [trial[x] for x in smoke.x], b, 'clamp')
                q = min(q_runtime.get(b, cap), cap)
                if stock_equivalent_q(cur, stock, b, q, PLAN_GEAR)[0] < cons[b]:
                    ok = False
                    break
            if not ok:
                break
            v -= 0.25
            best = v
        fitted[node] = best
        report.append({'rpm_node': node, 'current_mg': col[node], 'fitted_mg': best, 'constrained_bins': bins})
    # final check over all bins including those between the last node and the one after
    checks = []
    for b in sorted(cons):
        if b < 2500:
            continue
        cap = a2l._interp(smoke.x, [fitted[x] for x in smoke.x], b, 'clamp')
        q_now = q_runtime.get(b)
        if q_now is None:
            continue
        q_new = min(q_now, cap)
        checks.append({'rpm': b, 'q_runtime_now_mg': q_now, 'q_cmd_new_mg': q_new,
                       'q_stock_eq_now_mg': stock_equivalent_q(cur, stock, b, q_now, PLAN_GEAR)[0],
                       'q_stock_eq_new_mg': stock_equivalent_q(cur, stock, b, q_new, PLAN_GEAR)[0],
                       'burned_p95_constraint_mg': cons[b]})
    return fitted, report, checks


CANDIDATE_DIR = 'firmware-candidates'
CANDIDATE_NAME = '03G906021QJ_v1_smoke-air-coherent_CS_OK.bin'
CHECKSUM_TARGET = 0xD01FE500
CHECKSUM_BLOCKS = ((0x180000, 0x1BFFFC), (0x1C0000, 0x1FDFFC))  # (start, checksum word address)


def block_sums(data):
    return [sum(struct.unpack('>%dI' % ((cs + 4 - lo) // 4), data[lo:cs + 4])) & 0xFFFFFFFF for lo, cs in CHECKSUM_BLOCKS]


def fix_checksums(buf):
    """32-bit big-endian word sum of each block (checksum word included) must equal 0xD01FE500.
    Verified against: OEM HEX reference, original ECU read (new-inputs/on) and third-party *_chk_OK files."""
    for lo, cs in CHECKSUM_BLOCKS:
        body = sum(struct.unpack('>%dI' % ((cs - lo) // 4), bytes(buf[lo:cs]))) & 0xFFFFFFFF
        buf[cs:cs + 4] = struct.pack('>I', (CHECKSUM_TARGET - body) & 0xFFFFFFFF)
    return buf


def build_candidate(write_bin=True):
    with open(os.path.join(OUT_DIR, 'vcds-analysis.json'), encoding='utf-8') as f:
        vres = json.load(f)
    with open(os.path.join(OUT_DIR, 'current-analysis.json'), encoding='utf-8') as f:
        pres = json.load(f)
    cur, stock = Firmware(CURRENT_BIN), Firmware(STOCK_BIN)
    cons = burned_p95_constraints(vres, pres)
    q_rt = {}
    for rpm in PLAN_BINS:
        vals = [r['q_runtime_mg'] for r in vres['rows'] if r['rpm'] == rpm]
        if vals:
            q_rt[rpm] = statistics.median(vals)
    fitted, report, checks = fit_smoke_column(cur, stock, cons, q_rt)

    smoke = cur['FlMng_qPresSmoke_MAP']
    ny, iy = len(smoke.y), len(smoke.y) - 1
    conv = a2l.db()['compu'][smoke.conversion]['coeffs']
    values_start = smoke.address + 4 + 2 * len(smoke.x) + 2 * ny
    cells = []
    for ix, x in enumerate(smoke.x):
        if fitted[x] == smoke.grid[ix][iy]:
            continue
        raw = int(round((fitted[x] * conv[1] + conv[2]) / conv[5]))
        addr = values_start + 2 * (ix * ny + iy)
        old = struct.unpack_from('>h', cur.data, addr)[0]
        cells.append({'map': smoke.name, 'rpm_node': x, 'pressure_node_hpa': smoke.y[iy], 'address': '0x%X' % addr,
                      'old_raw': old, 'new_raw': raw, 'old_raw_hex': '%04X' % (old & 0xFFFF),
                      'new_raw_hex': '%04X' % (raw & 0xFFFF), 'old_mg': smoke.grid[ix][iy], 'new_mg': fitted[x]})
    plan = candidate_plan_record(cur, stock, vres, cons, report, checks, cells, fitted, smoke)
    if not write_bin:
        plan['verification'] = 'NOT BUILT (plan only; BIN creation requires explicit approval)'
        with open(os.path.join(OUT_DIR, 'candidate-v1.json'), 'w', encoding='utf-8') as f:
            json.dump(plan, f, indent=1, ensure_ascii=False)
        return plan
    buf = bytearray(cur.data)
    for c in cells:
        struct.pack_into('>h', buf, int(c['address'], 16), c['new_raw'])
    fix_checksums(buf)
    new = bytes(buf)

    # self-verification
    diff = [i for i in range(len(new)) if new[i] != cur.data[i]]
    allowed = set()
    for c in cells:
        a = int(c['address'], 16)
        allowed |= {a, a + 1}
    for _, cs in CHECKSUM_BLOCKS:
        allowed |= set(range(cs, cs + 4))
    decoded = a2l.load('FlMng_qPresSmoke_MAP', new)
    verify = {
        'size_bytes': len(new),
        'checksum_block_sums': ['%08X' % s for s in block_sums(new)],
        'checksum_ok': all(s == CHECKSUM_TARGET for s in block_sums(new)),
        'changed_bytes_outside_cells_and_checksums': sorted('0x%X' % i for i in diff if i not in allowed),
        'decoded_new_cells_mg': [decoded.lookup(c['rpm_node'], c['pressure_node_hpa']) for c in cells],
        'all_other_characteristics_unchanged': True,
    }
    if not verify['checksum_ok'] or verify['changed_bytes_outside_cells_and_checksums']:
        raise SystemExit('candidate verification FAILED: %s' % verify)
    os.makedirs(CANDIDATE_DIR, exist_ok=True)
    out_path = os.path.join(CANDIDATE_DIR, CANDIDATE_NAME)
    with open(out_path, 'wb') as f:
        f.write(new)
    verify['sha256'] = hashlib.sha256(new).hexdigest()
    plan['verification'] = verify
    plan['candidate_bin'] = out_path.replace('\\', '/')
    with open(os.path.join(OUT_DIR, 'candidate-v1.json'), 'w', encoding='utf-8') as f:
        json.dump(plan, f, indent=1, ensure_ascii=False)
    return plan


def candidate_plan_record(cur, stock, vres, cons, report, checks, cells, fitted, smoke):
    # predicted lambda per logged VCDS pull (same stock-equivalent basis, measured air)
    lam = []
    col_new = [fitted[x] for x in smoke.x]
    for r in vres['rows']:
        if r['rpm'] < 2750:
            continue
        cap = a2l._interp(smoke.x, col_new, r['rpm'], 'clamp')
        q_new = min(r['q_runtime_mg'], cap)
        q_eq_new = stock_equivalent_q(cur, stock, r['rpm'], q_new, r['gear'])[0]
        lam.append({'pull': r['pull'], 'gear': r['gear'], 'rpm': r['rpm'], 'air_mg': r['maf_act_mg'],
                    'q_runtime_now': r['q_runtime_mg'], 'q_cmd_new': q_new,
                    'q_stock_eq_now': r['q_stock_equivalent_mg'], 'q_stock_eq_new': q_eq_new,
                    'burned_p50': r.get('implied_burned_q_mg') and r['implied_burned_q_mg']['p50'],
                    'burned_p95': r.get('implied_burned_q_mg') and r['implied_burned_q_mg']['p95'],
                    'lambda_now': r['lambda_stock_equivalent'],
                    'lambda_new': ph.lambda_from(r['maf_act_mg'], q_eq_new, 14.5),
                    'end_proxy_now': r['elec_end_proxy_deg_atdc'],
                    'end_proxy_new': chain_with_q(cur, r['rpm'], r['gear'], q_new)['electrical_command_end_proxy_deg_atdc']})
    return {'generated_utc': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'base_bin': {'path': CURRENT_BIN, 'sha256': cur.sha256}, 'candidate_bin': None,
            'rule': 'Lower FlMng_qPresSmoke_MAP last-column nodes only as far as the stock-equivalent delivered fuel '
                    'stays >= the highest P95 burned-fuel estimate of every logged pull (VCDS + phone, gears 3-4) at '
                    'each rpm. No lambda constant is assumed.',
            'constraints_burned_p95_mg': cons, 'fit': report, 'cells': cells, 'fit_checks': checks,
            'predicted_per_pull': lam, 'verification': None,
            'validation_protocol': [
                'Flash, clear DTCs, same road both directions, gear 4 WOT 1500->4100, VCDS groups 011+003+008.',
                'Pass: at 3000-4000 rpm road torque P50 within the pull-to-pull spread of vcds-analysis (no loss).',
                'Pass: group 008 shows smoke limitation binding at 3000-4000 at the new equivalent torque.',
                'Expect: less visible smoke at 3000+; boost behaviour unchanged (fuel change only).'],
            'abort_criteria': ['road torque P50 at any 3000-3750 bin lower by more than 15 Nm than vcds-analysis',
                               'new DTC', 'engine behaviour change below 2750 rpm (cells there are untouched)'],
            'rollback': CURRENT_BIN}


def smoke_equivalence(cur, rows):
    """Runtime 'Smoke Limitation' [Nm] vs inverse FMTC of the static smoke map (last column)."""
    out = []
    for r in rows:
        q_s = cur['FlMng_qPresSmoke_MAP'].lookup(r['rpm'], 2000)
        inv, status = cur['FMTC_trq2qBas_MAP'].inverse_y(r['rpm'], q_s)
        out.append({'pull': r['pull'], 'rpm': r['rpm'], 'vcds_smoke_nm': r['trq_smoke_nm'], 'static_smoke_mg': q_s,
                    'inverse_fmtc_nm': inv, 'inverse_status': status, 'difference_nm': r['trq_smoke_nm'] - inv})
    return out


def boost_control_summary(pulls):
    out = []
    for p in pulls:
        s, seg = p['series'], p['seg']
        pts = [(t, tm.interp_at(s['boost_spec_mbar'], t), v, tm.interp_at(s['n75_duty_pct'], t), tm.interp_at(seg, t))
               for t, v, _ in s['map_mbar'] if seg[0][0] <= t <= seg[-1][0]]
        pts = [x for x in pts if None not in x]
        steady = [x for x in pts if x[1] >= 2190]  # spec on its full-load plateau
        if len(steady) < 5:
            continue
        err = [x[2] - x[1] for x in steady]
        over, under = max(steady, key=lambda x: x[2] - x[1]), min(steady, key=lambda x: x[2] - x[1])
        agree = total = 0
        for a, b in zip(steady, steady[1:]):
            e, dd = a[2] - a[1], b[3] - a[3]
            if abs(e) >= 30 and abs(dd) >= 0.3:
                total += 1
                agree += (e > 0) == (dd < 0)
        hi = [x for x in steady if x[4] >= 3000]
        out.append({'pull': p['name'], 'gear': p['gear'], 'n_steady': len(steady),
                    'max_overshoot_mbar': over[2] - over[1], 'max_overshoot_at_rpm': over[4], 'max_actual_mbar': max(x[2] for x in pts),
                    'max_undershoot_mbar': under[2] - under[1], 'max_undershoot_at_rpm': under[4],
                    'mean_error_above_3000_mbar': statistics.mean([x[2] - x[1] for x in hi]) if hi else None,
                    'duty_range_above_3000_pct': [min(x[3] for x in hi), max(x[3] for x in hi)] if hi else None,
                    'n75_sign_samples': total, 'n75_sign_consistent_with_duty_up_boost_up': agree})
    return out


def plan_check(cur, rows):
    """lambda of the provisional smoke-column candidate against VCDS air, same stock-equivalent fuel basis."""
    stock = Firmware(STOCK_BIN)
    new_col = {3000.0: 54.0, 4000.0: 47.5}
    smoke = cur['FlMng_qPresSmoke_MAP']
    col = [new_col.get(x, smoke.grid[i][-1]) for i, x in enumerate(smoke.x)]
    out = []
    for r in rows:
        if r['rpm'] < 2750:
            continue
        cap = a2l._interp(smoke.x, col, r['rpm'], 'clamp')
        q_new = min(r['q_runtime_mg'], cap)
        q_eq_new = stock_equivalent_q(cur, stock, r['rpm'], q_new, r['gear'])[0]
        out.append({'pull': r['pull'], 'rpm': r['rpm'], 'q_runtime_now': r['q_runtime_mg'], 'q_cap_new': cap,
                    'lambda_stock_eq_now': r['lambda_stock_equivalent'],
                    'lambda_stock_eq_new': ph.lambda_from(r['maf_act_mg'], q_eq_new, 14.5),
                    'implied_burned_q_p50': r.get('implied_burned_q_mg') and r['implied_burned_q_mg']['p50'],
                    'q_stock_eq_new': q_eq_new})
    return out


def vcds_findings(res):
    rows = [r for r in res['rows'] if r.get('torque_realization')]
    out = []
    eq = [abs(e['difference_nm']) for e in res['smoke_torque_equivalence'] if e['inverse_status'] == 'IN_RANGE']
    if eq:
        out.append('Runtime smoke limitation equals inverse FMTC of FlMng_qPresSmoke_MAP last column: max |diff| %.1f Nm '
                   'over %d in-range points (VCDS step 2.44 Nm).' % (max(eq), len(eq)))
    for lo, hi in ((1750, 2500), (2750, 3000), (3250, 4000)):
        z = [r for r in rows if lo <= r['rpm'] <= hi]
        if not z:
            continue
        binds = {}
        for r in z:
            for b in r['binding_limiter']:
                binds[b] = binds.get(b, 0) + 1
        out.append('%d-%d rpm: binding %s; runtime inner %.0f-%.0f Nm; q runtime %.1f-%.1f mg, stock-equivalent %.1f-%.1f mg; '
                   'air %.0f-%.0f mg; lambda(stock-eq) %.2f-%.2f; realization P50 %.2f-%.2f; unconverted fuel P50 %.1f-%.1f mg' % (
                       lo, hi, binds, min(r['runtime_inner_torque_nm'] for r in z), max(r['runtime_inner_torque_nm'] for r in z),
                       min(r['q_runtime_mg'] for r in z), max(r['q_runtime_mg'] for r in z),
                       min(r['q_stock_equivalent_mg'] for r in z), max(r['q_stock_equivalent_mg'] for r in z),
                       min(r['maf_act_mg'] for r in z), max(r['maf_act_mg'] for r in z),
                       min(r['lambda_stock_equivalent'] for r in z), max(r['lambda_stock_equivalent'] for r in z),
                       min(r['torque_realization']['p50'] for r in z), max(r['torque_realization']['p50'] for r in z),
                       min(r['unconverted_fuel_mg_p50'] for r in z), max(r['unconverted_fuel_mg_p50'] for r in z)))
    return out


def render_vcds_md(res):
    L = ['# VCDS runtime analysis (groups 011 / 003 / 008)', '',
         'Generated from `vcds-analysis.json` (%s). Source `%s`.' % (res['generated_utc'], res['source']), '',
         'Road torque, inner torque and realization are Monte Carlo P50 [P05–P95]. Gear is assigned by matching the '
         'rpm rate at 2500 rpm to the phone OBD pulls that carry vehicle speed.', '', '## Pulls', '',
         '| pull | firmware | gear | rpm | rate@2500 rpm/s | rate mismatch |', '|---|---|---|---|---|---|']
    for p in res['pulls']:
        L.append('| %s | %s | %s | %d→%d | %s | %s |' % (p['name'], p['firmware'], p['gear'], p['rpm_start'], p['rpm_end'],
                                                     _f(p['rate2500_rpm_s'], 0), _f(p['gear_rate_mismatch'], 2)))
    L += ['', '## Findings', ''] + ['- ' + f for f in res['findings']]
    for pull in sorted({r['pull'] for r in res['rows']}):
        rs = [r for r in res['rows'] if r['pull'] == pull]
        L += ['', '## %s (gear %s)' % (pull, rs[0]['gear']), '',
              '| rpm | boost spec/act mbar | N75 % | air mg | req / lim / smoke Nm | binds | q runtime → stock-eq mg | λ stock-eq | road Nm | inner est Nm | realization | burned q mg | end proxy ° |',
              '|---|---|---|---|---|---|---|---|---|---|---|---|---|']
        for r in rs:
            L.append('| %d | %.0f / %.0f | %.1f | %.0f | %.0f / %.0f / %.0f | %s | %.1f → %.1f%s | %.2f | %s | %s | %s | %s | %.1f |' % (
                r['rpm'], r['boost_spec_mbar'], r['map_mbar'], r['n75_duty_pct'], r['maf_act_mg'], r['trq_request_nm'],
                r['trq_limit_nm'], r['trq_smoke_nm'], '+'.join(r['binding_limiter']), r['q_runtime_mg'], r['q_stock_equivalent_mg'],
                '*' if r['q_stock_equivalent_status'] != 'IN_OEM_AXIS' else '', r['lambda_stock_equivalent'],
                _r(r['road_torque_nm']), _r(r.get('road_inner_torque_nm')), _r(r.get('torque_realization'), 2),
                _r(r.get('implied_burned_q_mg'), 1), r['elec_end_proxy_deg_atdc']))
    L += ['', '`*` stock-equivalent fuel extrapolated beyond the OEM duration axis.', '', '## Boost control', '',
          '| pull | gear | max overshoot mbar @rpm | peak actual | max undershoot mbar @rpm | mean error ≥3000 | N75 duty ≥3000 % | N75 sign samples consistent (duty↑ ⇒ boost↑) |',
          '|---|---|---|---|---|---|---|---|']
    for b in res['boost_control']:
        L.append('| %s | %s | %+.0f @%.0f | %.0f | %+.0f @%.0f | %s | %s | %d / %d |' % (
            b['pull'], b['gear'], b['max_overshoot_mbar'], b['max_overshoot_at_rpm'], b['max_actual_mbar'],
            b['max_undershoot_mbar'], b['max_undershoot_at_rpm'], _f(b['mean_error_above_3000_mbar'], 0),
            ('%.1f–%.1f' % tuple(b['duty_range_above_3000_pct'])) if b['duty_range_above_3000_pct'] else '—',
            b['n75_sign_consistent_with_duty_up_boost_up'], b['n75_sign_samples']))
    L += ['', '## Provisional smoke candidate vs VCDS air (stock-equivalent fuel)', '',
          '| pull | rpm | q runtime now | cap new | stock-eq q new | burned q P50 | λ now → new |', '|---|---|---|---|---|---|---|']
    for c in res['plan_check']:
        L.append('| %s | %d | %.1f | %.1f | %.1f | %s | %.2f → %.2f |' % (
            c['pull'], c['rpm'], c['q_runtime_now'], c['q_cap_new'], c['q_stock_eq_new'], _f(c['implied_burned_q_p50']),
            c['lambda_stock_eq_now'], c['lambda_stock_eq_new']))
    return '\n'.join(L) + '\n'


def cross_check(rng, rpm, trq, air_med, map_med, c_cur, dratio, torque_draws):
    """Joint Monte Carlo: measured torque draw x fuel parameters -> implied burned fuel and lambda.
    Also: what torque the air alone could support at a given lambda, and what the commanded fuel would give."""
    implied_q, implied_lambda, fuel_torque, lam_cmd = [], [], [], []
    for _ in range(4000):
        t = rng.choice(torque_draws)
        lhv = rng.uniform(FUEL['lhv_j_kg']['min'], FUEL['lhv_j_kg']['max'])
        afr = rng.uniform(FUEL['afr_stoich']['min'], FUEL['afr_stoich']['max'])
        eta = rng.uniform(FUEL['eta_brake_full_load']['min'], FUEL['eta_brake_full_load']['max'])
        air = air_med * rng.uniform(AIR['maf_scale']['min'], AIR['maf_scale']['max'])
        q = ph.q_from_torque_mg(t, lhv, eta)
        implied_q.append(q)
        implied_lambda.append(ph.lambda_from(air, q, afr))
        # delivered fuel bracket: commanded q (duration axis clamps at its end) x [1, duration ratio]
        q_del = min(c_cur['q_cmd_clamp_mg'], c_cur['duration_q_axis_end_mg']) * rng.uniform(1.0, dratio)
        fuel_torque.append(ph.torque_from_fuel_nm(q_del, lhv, eta))
        lam_cmd.append(ph.lambda_from(air, q_del, afr))
    air_limited = {}
    for lam in LAMBDA_TABLE:
        q = ph.q_max_for_lambda(air_med, lam, 14.5)
        air_limited['%.2f' % lam] = {'q_mg': q,
                                     'torque_nm_eta_min': ph.torque_from_fuel_nm(q, 42.85e6, FUEL['eta_brake_full_load']['min']),
                                     'torque_nm_eta_max': ph.torque_from_fuel_nm(q, 42.85e6, FUEL['eta_brake_full_load']['max'])}
    ve = {}
    for tc in (AIR['charge_temp_c']['min'], AIR['charge_temp_c']['max']):
        ve['%.0fC' % tc] = air_med / speed_density_air_mg(map_med, rpm, tc, 1.0)
    return {
        'implied_burned_q_mg': dyno.summarize(implied_q),
        'implied_lambda_if_all_fuel_burned': dyno.summarize(implied_lambda),
        'lambda_of_commanded_fuel': dyno.summarize(lam_cmd),
        'fuel_model_torque_nm': dyno.summarize(fuel_torque),
        'residual_fuel_model_minus_road_nm': (dyno.pct(fuel_torque, 0.5) - trq['p50']),
        'ecu_brake_model_minus_road_nm': c_cur['ecu_brake_torque_model_nm'] - trq['p50'],
        'air_limited_torque': air_limited,
        'apparent_ve_from_maf': ve,
        'power_kw_p50': ph.power_w(trq['p50'], rpm) / 1000.0,
        'power_ps_p05_p95': [ph.w_to_ps(ph.power_w(trq['p05'], rpm)), ph.w_to_ps(ph.power_w(trq['p95'], rpm))],
        'bmep_bar_p50': ph.bmep_bar(trq['p50'], ENGINE['displacement_m3']['value']),
    }


def smoke_axis_check(fw):
    corr = fw['FlMng_pIATCorr_MAP']
    out = {}
    for t_c in (35, 50, 65, 70):
        threshold = next((p for p in range(1000, 2600, 5) if corr.lookup(p, t_c) >= 2000), None)
        out['%dC' % t_c] = threshold
    return {'raw_pressure_hpa_where_corrected_reaches_last_smoke_column': out,
            'note': 'FlMng_pIATCorr_MAP axis input is FlMng_pBPAPCorr_mp; identity with logged MAP is assumed '
                    '(both are boost pressure in hPa abs).'}


def findings(res):
    """Deterministic, number-backed statements. Each lists the rows it rests on."""
    out = []
    rows = [r for r in res['rows'] if r.get('implied_lambda_if_all_fuel_burned')]
    rich = [r for r in rows if r['lambda_of_commanded_fuel']['p50'] < 1.10]
    if rich:
        out.append({'id': 'F1', 'status': 'CALCULATED',
                    'text': 'Commanded fuel exceeds what the measured air can burn cleanly (median lambda < 1.10).',
                    'where': ['G%d %d rpm: lambda_cmd %.2f [%.2f-%.2f], air %.0f mg' % (
                        r['gear'], r['rpm'], r['lambda_of_commanded_fuel']['p50'], r['lambda_of_commanded_fuel']['p05'],
                        r['lambda_of_commanded_fuel']['p95'], r['air_mg_stroke_median']) for r in rich]})
    deficit = [r for r in rows if r['residual_fuel_model_minus_road_nm'] > 0.15 * r['road_torque_nm']['p50']]
    if deficit:
        out.append({'id': 'F2', 'status': 'CALCULATED',
                    'text': 'Measured torque is more than 15 % below the energy model of the commanded fuel.',
                    'where': ['G%d %d rpm: road %.0f [%.0f-%.0f] Nm vs fuel model %.0f Nm' % (
                        r['gear'], r['rpm'], r['road_torque_nm']['p50'], r['road_torque_nm']['p05'],
                        r['road_torque_nm']['p95'], r['fuel_model_torque_nm']['p50']) for r in deficit]})
    return out


def write_outputs(res):
    os.makedirs(OUT_DIR, exist_ok=True)
    json_path = os.path.join(OUT_DIR, 'current-analysis.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    with open(json_path, encoding='utf-8') as f:
        res = json.load(f)  # render strictly from the persisted JSON
    with open(os.path.join(OUT_DIR, 'current-analysis.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['gear', 'rpm', 'map_mbar', 'air_mg_stroke', 'road_torque_p05', 'road_torque_p50', 'road_torque_p95',
                    'power_kw_p50', 'q_cmd_clamp_mg', 'q_smoke_mg', 'static_limiter_clamp', 'duration_ratio',
                    'lambda_cmd_p50', 'implied_q_p50', 'implied_lambda_p50', 'fuel_model_torque_p50',
                    'ecu_brake_model_nm', 'soi_hyp', 'duration_deg_hyp', 'elec_end_proxy'])
        for r in res['rows']:
            t, c = r.get('road_torque_nm'), r['chain_current']
            w.writerow([r['gear'], r['rpm'], _f(r['map_mbar_median']), _f(r['air_mg_stroke_median']),
                        _f(t and t['p05']), _f(t and t['p50']), _f(t and t['p95']), _f(r.get('power_kw_p50')),
                        _f(c['q_cmd_clamp_mg']), _f(c['q_smoke_last_column_mg']), c['static_limiter_clamp'],
                        _f(r['duration_ratio_current_vs_stock'], 3),
                        _f(r.get('lambda_of_commanded_fuel') and r['lambda_of_commanded_fuel']['p50'], 3),
                        _f(r.get('implied_burned_q_mg') and r['implied_burned_q_mg']['p50']),
                        _f(r.get('implied_lambda_if_all_fuel_burned') and r['implied_lambda_if_all_fuel_burned']['p50'], 3),
                        _f(r.get('fuel_model_torque_nm') and r['fuel_model_torque_nm']['p50']),
                        _f(c['ecu_brake_torque_model_nm']), _f(c['soi_deg_btdc_hyp'], 2), _f(c['duration_deg_hyp'], 2),
                        _f(c['electrical_command_end_proxy_deg_atdc'], 2)])
    with open(os.path.join(OUT_DIR, 'current-analysis.md'), 'w', encoding='utf-8') as f:
        f.write(render_md(res))


def _f(v, nd=1):
    return '' if v is None else round(v, nd)


def _r(d, nd=0):
    return '—' if not d else ('%.*f [%.*f–%.*f]' % (nd, d['p50'], nd, d['p05'], nd, d['p95']))


def render_md(res):
    L = ['# Calibration math engine — current analysis', '',
         'Generated from `current-analysis.json` (%s). Current BIN sha256 `%s…`, stock reference `%s…`.' % (
             res['generated_utc'], res['firmware']['current']['sha256'][:16],
             res['firmware']['stock_reference']['sha256'][:16]),
         '', 'Values in brackets are Monte Carlo P05–P95 (%d draws). Uncertain inputs and their provenance are listed at the end.' % res['conditions']['mc_draws'],
         '', '## Pulls used', '', '| pull | gear | rpm | km/h per rpm (MAD) | speed pairs | rpm samples |', '|---|---|---|---|---|---|']
    for s in res['segments']:
        L.append('| %s | %s | %d→%d | %.4f (%.4f) | %d | %d |' % (s['name'], s['gear'], s['rpm_start'], s['rpm_end'],
                                                                s['kmh_per_rpm'], s['ratio_mad'], s['speed_pairs'], s['n_rpm_samples']))
    for gear in (3, 4):
        L += ['', '## Gear %d — measured vs models' % gear, '',
              '| rpm | MAP mbar | air mg/str | road torque Nm | PS | q cmd mg (limiter) | λ of cmd fuel | fuel-model Nm | implied burned q mg | ECU brake model Nm |',
              '|---|---|---|---|---|---|---|---|---|---|']
        for r in res['rows']:
            if r['gear'] != gear or not r.get('road_torque_nm'):
                continue
            c = r['chain_current']
            ps = r['power_ps_p05_p95'] if r.get('power_ps_p05_p95') else None
            L.append('| %d | %s | %s | %s | %s | %.1f (%s) | %s | %s | %s | %.0f |' % (
                r['rpm'], _f(r['map_mbar_median'], 0), _f(r['air_mg_stroke_median'], 0), _r(r['road_torque_nm']),
                ('%.0f–%.0f' % tuple(ps)) if ps else '—', c['q_cmd_clamp_mg'], c['static_limiter_clamp'],
                _r(r.get('lambda_of_commanded_fuel'), 2), _r(r.get('fuel_model_torque_nm')),
                _r(r.get('implied_burned_q_mg'), 1), c['ecu_brake_torque_model_nm']))
    L += ['', '## Firmware chain (gear 4, static, current vs stock)', '',
          '| rpm | DW Nm | trqLimP Nm cur/stock | request Nm | q FMTC clamp/extrap mg | smoke last col mg cur/stock | q cmd | SOI hyp ° | dur hyp ° | dur ms | dur ratio cur/stock | elec end proxy ° |',
          '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for r in res['rows']:
        if r['gear'] != 4:
            continue
        c, s = r['chain_current'], r['chain_stock']
        L.append('| %d | %.0f | %.0f / %.0f | %.0f | %.1f / %.1f | %.1f / %.1f | %.1f | %.2f | %.2f | %.2f | %.3f | %.2f |' % (
            r['rpm'], c['driver_wish_nm'], c['trq_lim_p_nm'], s['trq_lim_p_nm'], c['inner_torque_request_nm'],
            c['q_fmtc_clamp_mg'], c['q_fmtc_extrap_mg'], c['q_smoke_last_column_mg'], s['q_smoke_last_column_mg'],
            c['q_cmd_clamp_mg'], c['soi_deg_btdc_hyp'], c['duration_deg_hyp'], c['duration_ms_hyp'],
            r['duration_ratio_current_vs_stock'], c['electrical_command_end_proxy_deg_atdc']))
    L += ['', '## Air-limited torque (gear 4, measured air, η range)', '', '| rpm | air mg | ' + ' | '.join('λ=%s' % k for k in ('1.05', '1.10', '1.15', '1.20', '1.25', '1.30')) + ' | road Nm |',
          '|---|---|' + '---|' * 7]
    for r in res['rows']:
        if r['gear'] != 4 or not r.get('air_limited_torque'):
            continue
        cells = ['%.0f–%.0f' % (v['torque_nm_eta_min'], v['torque_nm_eta_max']) for v in r['air_limited_torque'].values()]
        L.append('| %d | %.0f | %s | %s |' % (r['rpm'], r['air_mg_stroke_median'], ' | '.join(cells), _r(r['road_torque_nm'])))
    L += ['', '## Smoke limiter input check', '', '```', json.dumps(res['smoke_axis_check'], indent=1), '```',
          '', '## Automatic findings', '']
    for fnd in res['findings']:
        L.append('**%s (%s)** %s' % (fnd['id'], fnd['status'], fnd['text']))
        L += ['- ' + w for w in fnd['where']] + ['']
    plan = res.get('candidate_plan')
    if plan:
        L += ['## Candidate plan (%s)' % plan['status'], '',
              'λ target %.3f — %s.' % (plan['lambda_target'], plan['lambda_target_source']), '',
              '| map | rpm node | hPa node | address | current mg | candidate mg | raw s16 (hex) | air mg/str |', '|---|---|---|---|---|---|---|---|']
        for c in plan['cells']:
            L.append('| %s | %.0f | %.0f | %s | %.2f | %.2f | %d (%s) | %.0f |' % (
                c['map'], c['rpm_node'], c['pressure_node_hpa'], c['address'], c['current_mg'], c['candidate_mg'],
                c['candidate_raw_s16'], c['candidate_raw_hex'], c['air_mg_stroke']))
        L += ['', '| rpm | q cmd now → new mg | λ cmd now → new | Δ torque Nm | elec end proxy now → new ° | duration ms now → new |', '|---|---|---|---|---|---|']
        for e in plan['predicted_effect']:
            L.append('| %d | %.1f → %.1f | %.2f → %.2f | %s | %.2f → %.2f | %.2f → %.2f |' % (
                e['rpm'], e['q_cmd_now_mg'], e['q_cmd_new_mg'], e['lambda_cmd_now_p50'], e['lambda_cmd_new_p50'],
                _r(e['delta_torque_nm']), e['elec_end_proxy_now_deg'], e['elec_end_proxy_new_deg'],
                e['duration_ms_now'], e['duration_ms_new']))
        L += ['', 'Validation: ' + plan['validation_metric'], '', 'Abort if:'] + ['- ' + a for a in plan['abort_criteria']] + \
             ['', 'Rollback: `%s`' % plan['rollback'], '']
    L += ['## Parameters and provenance', '', '| parameter | range / value | status | source |', '|---|---|---|---|']
    for group in res['parameters'].values():
        for k, v in group.items():
            rng = ('%s' % v['value']) if 'value' in v else ('%s – %s' % (v['min'], v['max']))
            L.append('| %s | %s | %s | %s |' % (k, rng, v['status'], v['source']))
    return '\n'.join(L) + '\n'


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('analyze')
    v = sub.add_parser('vcds')
    v.add_argument('path')
    b = sub.add_parser('build')
    b.add_argument('--plan-only', action='store_true', help='fit and report cells without creating a BIN')
    c = sub.add_parser('chain')
    c.add_argument('--rpm', type=float, required=True)
    c.add_argument('--gear', type=int, default=4)
    args = ap.parse_args()
    if args.cmd == 'analyze':
        res = analyze()
        write_outputs(res)
        for fnd in res['findings']:
            print(fnd['id'], fnd['text'])
            for w in fnd['where']:
                print('   ', w)
    elif args.cmd == 'vcds':
        res = analyze_vcds(args.path)
        os.makedirs(OUT_DIR, exist_ok=True)
        jp = os.path.join(OUT_DIR, 'vcds-analysis.json')
        with open(jp, 'w', encoding='utf-8') as f:
            json.dump(res, f, indent=1, ensure_ascii=False)
        with open(jp, encoding='utf-8') as f:
            res = json.load(f)
        with open(os.path.join(OUT_DIR, 'vcds-analysis.md'), 'w', encoding='utf-8') as f:
            f.write(render_vcds_md(res))
        for line in res['findings']:
            print('-', line)
    elif args.cmd == 'build':
        plan = build_candidate(write_bin=not args.plan_only)
        print(json.dumps({k: plan[k] for k in ('cells', 'fit', 'verification')}, indent=1))
        for p in plan['predicted_per_pull']:
            print('%-22s G%s %4d air %4.0f q %.1f->%.1f eq %.1f->%.1f burned P50/P95 %s/%s lambda %.2f->%.2f end %.1f->%.1f' % (
                p['pull'], p['gear'], p['rpm'], p['air_mg'], p['q_runtime_now'], p['q_cmd_new'], p['q_stock_eq_now'],
                p['q_stock_eq_new'], _f(p['burned_p50']), _f(p['burned_p95']), p['lambda_now'], p['lambda_new'],
                p['end_proxy_now'], p['end_proxy_new']))
    else:
        for label, path in (('current', CURRENT_BIN), ('stock', STOCK_BIN)):
            print(label, json.dumps(chain(Firmware(path), args.rpm, args.gear), indent=1))


if __name__ == '__main__':
    main()
