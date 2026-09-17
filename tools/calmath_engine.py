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

CURRENT_BIN = '03G906021QJ_stage1_full_power_dpf_egr_off.bin'
STOCK_BIN = 'diagnostic-review/reference-from-hex.analysis-only.bin'
OUT_DIR = 'diagnostic-review/math-engine'
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
    soi, soi_map, soi_max = soi_limited(fw, rpm, gear, q_cmd)
    sel = fw['InjVlv_numMI1_CUR'].lookup(soi)
    lo, hi = int(sel // 1), min(int(sel // 1) + 1, 6)
    dur_map = fw['InjVlv_phiInjMI1_MAP%d' % lo]
    d_lo = dur_map.lookup(rpm, q_cmd)
    d_hi = fw['InjVlv_phiInjMI1_MAP%d' % hi].lookup(rpm, q_cmd)
    dur = d_lo + (d_hi - d_lo) * (sel - lo)
    out.update({'soi_deg_btdc_hyp': soi, 'soi_map_deg': soi_map, 'soi_limiter_deg': soi_max,
                'soi_limited': soi_map > soi_max, 'duration_map_selector': sel, 'duration_deg_hyp': dur,
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


def soi_limited(fw, rpm, gear, q):
    """Base SOI from the gear map, capped by the SOI limiter InjCrv_phiMIMax_MAP (rpm x coolant).
    Corrections between the two (atmospheric, IAT, dynamic advance) are not modelled."""
    soi_map = fw['InjCrv_phiBasGear34_MAP' if gear in (3, 4) else 'InjCrv_phiBasGear56_MAP'].lookup(rpm, q)
    soi_max = fw['InjCrv_phiMIMax_MAP'].lookup(rpm, COOLANT_C)
    return min(soi_map, soi_max), soi_map, soi_max


def chain_with_q(fw, rpm, gear, q):
    soi, soi_map, soi_max = soi_limited(fw, rpm, gear, q)
    sel = fw['InjVlv_numMI1_CUR'].lookup(soi)
    dur = duration_at(fw, rpm, q, sel)
    return {'soi_deg_btdc_hyp': soi, 'soi_map_deg': soi_map, 'soi_limiter_deg': soi_max, 'soi_limited': soi_map > soi_max,
            'duration_map_selector': sel, 'duration_deg_hyp': dur,
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


MAP0_CANDIDATE_NAME = '03G906021QJ_v2_map0-duration-restore_CS_OK.bin'
MAP0_FIX_TARGET_MG = 55.0  # the only column InjVlv_phiInjMI1_MAP0 shares with the scaled MAP1..4 axis
MAP0_FIX_REFERENCE_MAP = 'InjVlv_phiInjMI1_MAP1'
MAP0_PLAN_BINS = (3000, 3250, 3500, 3750, 4000)


def _cell_address(characteristic, ix, iy):
    ny = len(characteristic.y)
    values_start = characteristic.address + 4 + 2 * len(characteristic.x) + 2 * ny
    return values_start + 2 * (ix * ny + iy)


def _encode_raw_s16(characteristic, value):
    conv = a2l.db()['compu'][characteristic.conversion]['coeffs']
    return int(round((value * conv[1] + conv[2]) / conv[5]))


def map0_duration_fix_cells(cur, stock):
    """Rule from DECISION-2026-09-16.md #4b: Stage 1 scaled InjVlv_phiInjMI1_MAP1..4 by
    ~x1.079 at their 55 mg column but left MAP0 (axis ending at 55 mg) untouched. Apply the
    SAME per-rpm ratio, measured directly from MAP1 cur/stock at 55 mg, to MAP0's 55 mg column
    only (its only column shared with the scaled maps). No other column or map is touched."""
    map0 = cur['InjVlv_phiInjMI1_MAP0']
    ref_cur, ref_stock = cur[MAP0_FIX_REFERENCE_MAP], stock[MAP0_FIX_REFERENCE_MAP]
    iy = map0.y.index(MAP0_FIX_TARGET_MG)
    cells, ratios = [], []
    for ix, rpm in enumerate(map0.x):
        ratio = ref_cur.lookup(rpm, MAP0_FIX_TARGET_MG) / ref_stock.lookup(rpm, MAP0_FIX_TARGET_MG)
        old_deg = map0.grid[ix][iy]
        new_deg = old_deg * ratio
        addr = _cell_address(map0, ix, iy)
        old_raw = struct.unpack_from('>h', cur.data, addr)[0]
        new_raw = _encode_raw_s16(map0, new_deg)
        ratios.append(ratio)
        cells.append({'map': map0.name, 'rpm_node': rpm, 'q_node_mg': MAP0_FIX_TARGET_MG, 'address': '0x%X' % addr,
                      'old_raw': old_raw, 'new_raw': new_raw, 'old_raw_hex': '%04X' % (old_raw & 0xFFFF),
                      'new_raw_hex': '%04X' % (new_raw & 0xFFFF), 'old_deg': old_deg, 'new_deg': new_deg,
                      'ratio_source': '%s(rpm,%.0fmg) cur/stock' % (MAP0_FIX_REFERENCE_MAP, MAP0_FIX_TARGET_MG),
                      'ratio': ratio})
    return cells, ratios


def build_map0_candidate(write_bin=True):
    cur, stock = Firmware(CURRENT_BIN), Firmware(STOCK_BIN)
    cells, ratios = map0_duration_fix_cells(cur, stock)

    buf = bytearray(cur.data)
    for c in cells:
        struct.pack_into('>h', buf, int(c['address'], 16), c['new_raw'])
    fix_checksums(buf)
    new = bytes(buf)

    diff = [i for i in range(len(new)) if new[i] != cur.data[i]]
    allowed = set()
    for c in cells:
        a = int(c['address'], 16)
        allowed |= {a, a + 1}
    for _, cs in CHECKSUM_BLOCKS:
        allowed |= set(range(cs, cs + 4))
    verify = {
        'size_bytes': len(new),
        'checksum_block_sums': ['%08X' % s for s in block_sums(new)],
        'checksum_ok': all(s == CHECKSUM_TARGET for s in block_sums(new)),
        'changed_bytes_outside_cells_and_checksums': sorted('0x%X' % i for i in diff if i not in allowed),
        'ratio_min': min(ratios), 'ratio_max': max(ratios),
    }
    if not verify['checksum_ok'] or verify['changed_bytes_outside_cells_and_checksums']:
        raise SystemExit('MAP0 candidate verification FAILED: %s' % verify)

    # predicted effect: re-derive the WOT chain at each 250-rpm bin with the patched MAP0,
    # against the same VCDS runtime evidence used for the smoke-column candidate.
    cur_patched = Firmware(CURRENT_BIN)
    cur_patched.data = new
    cur_patched._c = {}
    with open(os.path.join(OUT_DIR, 'vcds-analysis.json'), encoding='utf-8') as f:
        vres = json.load(f)
    effects = []
    for rpm in MAP0_PLAN_BINS:
        c_before = chain(cur, rpm, PLAN_GEAR)
        c_after = chain(cur_patched, rpm, PLAN_GEAR)
        eq_before, status_before, _ = stock_equivalent_q(cur, stock, rpm, c_before['q_cmd_clamp_mg'], PLAN_GEAR)
        eq_after, status_after, _ = stock_equivalent_q(cur_patched, stock, rpm, c_after['q_cmd_clamp_mg'], PLAN_GEAR)
        air = [r['maf_act_mg'] for r in vres['rows'] if r['rpm'] == rpm and r['gear'] == PLAN_GEAR]
        air_med = statistics.median(air) if air else None
        row = {'rpm': rpm, 'q_cmd_mg': c_before['q_cmd_clamp_mg'],
               'stock_eq_before_mg': eq_before, 'stock_eq_before_status': status_before,
               'stock_eq_after_mg': eq_after, 'stock_eq_after_status': status_after,
               'delivered_fuel_gain_mg': eq_after - eq_before,
               'duration_selector_before': c_before['duration_map_selector'],
               'duration_selector_after': c_after['duration_map_selector'],
               'air_mg_stroke_median': air_med,
               'lambda_before': ph.lambda_from(air_med, eq_before, 14.5) if air_med else None,
               'lambda_after': ph.lambda_from(air_med, eq_after, 14.5) if air_med else None}
        effects.append(row)

    plan = {'generated_utc': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'base_bin': {'path': CURRENT_BIN, 'sha256': cur.sha256}, 'candidate_bin': None,
            'rule': 'DECISION-2026-09-16.md #4b: scale InjVlv_phiInjMI1_MAP0 55 mg column by the SAME per-rpm '
                    'cur/stock ratio already present in InjVlv_phiInjMI1_MAP1 at its 55 mg column (Stage 1 scaled '
                    'MAP1..4 but left MAP0 stock). Only the 55 mg column of MAP0 changes; no other map, column or '
                    'switch is touched.',
            'cells': cells, 'predicted_effect': effects, 'verification': None,
            'status': 'PROVISIONAL — supported by static calculation and the 2026-09-16 VCDS air data used above; '
                      'NOT yet cross-validated by a runtime Duration/selector measurement (per '
                      'diagnostic-review/chatgpt/EVIDENCE-MATRIX-2026-09-16.md this hypothesis remains HOLD until '
                      'one exists). Do not flash from this plan alone.',
            'validation_protocol': [
                'Flash, clear DTCs, same road both directions, gear 4 WOT 2750->4100, VCDS groups 011+003+008.',
                'Pass: at 3000-4000 rpm road torque P50 measurably higher than the current vcds-analysis baseline, '
                'by more than the pull-to-pull spread.',
                'Pass: no new smoke reported at 3000-4000 rpm; EGT (if logged) does not exceed prior readings.'],
            'abort_criteria': ['visible smoke appears above 3000 rpm where none was present before',
                               'road torque P50 at any 3000-3750 bin lower than the current baseline',
                               'new DTC'],
            'rollback': CURRENT_BIN}
    if not write_bin:
        plan['verification'] = 'NOT BUILT (plan only; BIN creation requires explicit approval)'
        with open(os.path.join(OUT_DIR, 'candidate-map0-v2.json'), 'w', encoding='utf-8') as f:
            json.dump(plan, f, indent=1, ensure_ascii=False)
        return plan

    os.makedirs(CANDIDATE_DIR, exist_ok=True)
    out_path = os.path.join(CANDIDATE_DIR, MAP0_CANDIDATE_NAME)
    with open(out_path, 'wb') as f:
        f.write(new)
    verify['sha256'] = hashlib.sha256(new).hexdigest()
    plan['verification'] = verify
    plan['candidate_bin'] = out_path.replace('\\', '/')
    with open(os.path.join(OUT_DIR, 'candidate-map0-v2.json'), 'w', encoding='utf-8') as f:
        json.dump(plan, f, indent=1, ensure_ascii=False)
    return plan


VNEXT_CANDIDATE_NAME = '03G906021QJ_vNext_hotstart-ecocruise-map0_CS_OK.bin'
REFINED_BIN = '03G906021QJ_stage1_refined_CS_OK.bin'
# Objects copied whole-byte from the already-audited refined_CS_OK build (see
# diagnostic-review/deep-audit and README firmware-lineage: HS-250 hot-start fix and the
# Gear 5/6 cruise SOI advance). Both are outside the WOT fuel path this project has been
# validating; neither touches a cell inside 1750-4000 rpm at >=55 mg/stroke.
VNEXT_COPY_FROM_REFINED = ('StSys_trqStrtBas_MAP', 'InjCrv_phiBasGear56_MAP')
# FlMng_qPresSmoke_MAP also differs between current and refined_CS_OK by one cell
# (2500 rpm / 2000 hPa: 56.5 -> 58.5 mg) but that predates this project's math engine and
# sits inside the Z1 plateau this session independently CROSS_VALIDATED as correct as-is
# (DECISION-2026-09-16.md #2). Deliberately NOT carried forward; noted so it is not lost.
VNEXT_EXCLUDED_FROM_REFINED = {
    'FlMng_qPresSmoke_MAP': 'refined_CS_OK raises the 2500 rpm/2000 hPa cell 56.5->58.5 mg; '
                            'this session independently found the current 56.5 mg plateau '
                            'cross-validated (paired ECU-model/road/air estimates within '
                            'uncertainty) and did not re-derive the refined value, so it is '
                            'excluded rather than blindly re-applied.'}


def build_vnext_candidate(write_bin=True):
    cur, stock, refined = Firmware(CURRENT_BIN), Firmware(STOCK_BIN), Firmware(REFINED_BIN)
    buf = bytearray(cur.data)
    copied = []
    for name in VNEXT_COPY_FROM_REFINED:
        obj = cur[name]
        a, n = obj.address, obj.size
        changed = [i for i in range(a, a + n) if cur.data[i] != refined.data[i]]
        buf[a:a + n] = refined.data[a:a + n]
        copied.append({'map': name, 'address': '0x%X' % a, 'size_bytes': n,
                       'bytes_actually_changed': len(changed), 'source': REFINED_BIN})

    map0_cells, map0_ratios = map0_duration_fix_cells(cur, stock)
    for c in map0_cells:
        struct.pack_into('>h', buf, int(c['address'], 16), c['new_raw'])
    fix_checksums(buf)
    new = bytes(buf)

    diff = [i for i in range(len(new)) if new[i] != cur.data[i]]
    allowed = set()
    for name in VNEXT_COPY_FROM_REFINED:
        obj = cur[name]
        allowed |= set(range(obj.address, obj.address + obj.size))
    for c in map0_cells:
        a = int(c['address'], 16)
        allowed |= {a, a + 1}
    for _, cs in CHECKSUM_BLOCKS:
        allowed |= set(range(cs, cs + 4))
    verify = {
        'size_bytes': len(new),
        'checksum_block_sums': ['%08X' % s for s in block_sums(new)],
        'checksum_ok': all(s == CHECKSUM_TARGET for s in block_sums(new)),
        'changed_bytes_outside_known_objects_and_checksums': sorted('0x%X' % i for i in diff if i not in allowed),
        'total_changed_bytes_vs_current': len(diff),
    }
    if not verify['checksum_ok'] or verify['changed_bytes_outside_known_objects_and_checksums']:
        raise SystemExit('vNext candidate verification FAILED: %s' % verify)

    plan = {'generated_utc': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'base_bin': {'path': CURRENT_BIN, 'sha256': cur.sha256},
            'components': [
                {'name': 'hot-start fix (HS-250)', 'map': 'StSys_trqStrtBas_MAP', 'risk': 'none at WOT',
                 'status': 'previously audited (diagnostic-review/deep-audit), copied byte-for-byte from '
                          'refined_CS_OK', 'summary': '250 rpm / 40-100C cranking cells 0 -> 108-125 Nm; '
                          'idle-speed cranking only, does not touch any fuel/boost/torque map used at load.'},
                {'name': 'eco cruise SOI advance', 'map': 'InjCrv_phiBasGear56_MAP', 'risk': 'none at WOT',
                 'status': 'previously audited, copied byte-for-byte from refined_CS_OK',
                 'summary': '1750-2250 rpm at 15/20/25 mg/stroke (light cruise load) advanced +0.703 deg BTDC; '
                           'the 55-60 mg WOT columns of this same map are untouched by this change.'},
                {'name': 'MAP0 duration restore', 'map': 'InjVlv_phiInjMI1_MAP0', 'risk': 'PROVISIONAL, WOT-only',
                 'status': 'new this session, NOT independently runtime-verified',
                 'summary': 'see candidate-map0-v2.json / DECISION-2026-09-16.md #4b and #6d for the lambda '
                           'caveat: raises delivered fuel at 3000-4000 rpm toward the level MAP1..4 already '
                           'request, which pushes lambda to ~0.89-0.91 with the 2026-09-16 measured air.'},
            ],
            'excluded_from_refined_CS_OK': VNEXT_EXCLUDED_FROM_REFINED,
            'copied_objects': copied, 'map0_cells': map0_cells, 'verification': None, 'candidate_bin': None,
            'status': 'PARTIAL HOLD: hot-start and eco-cruise components are ready to flash on their own merits. '
                     'The MAP0 component is the one piece this file should not be flashed with, without first '
                     'doing the single check in DECISION-2026-09-16.md #6c (one WOT pull in 4th, watch for smoke '
                     'above 3000 rpm) OR flashing hot-start+eco-cruise alone first as a separate, smaller step.',
            'rollback': CURRENT_BIN}
    if not write_bin:
        plan['verification'] = 'NOT BUILT (plan only; BIN creation requires explicit approval)'
        with open(os.path.join(OUT_DIR, 'candidate-vnext.json'), 'w', encoding='utf-8') as f:
            json.dump(plan, f, indent=1, ensure_ascii=False)
        return plan

    os.makedirs(CANDIDATE_DIR, exist_ok=True)
    out_path = os.path.join(CANDIDATE_DIR, VNEXT_CANDIDATE_NAME)
    with open(out_path, 'wb') as f:
        f.write(new)
    verify['sha256'] = hashlib.sha256(new).hexdigest()
    plan['verification'] = verify
    plan['candidate_bin'] = out_path.replace('\\', '/')
    with open(os.path.join(OUT_DIR, 'candidate-vnext.json'), 'w', encoding='utf-8') as f:
        json.dump(plan, f, indent=1, ensure_ascii=False)
    return plan


STAGE0_CANDIDATE_NAME = '03G906021QJ_stage0_hotstart-ecocruise_CS_OK.bin'
STAGE0_WOT_Q_MIN_MG = 40.0  # gear-map columns at/above this are the WOT path and must stay byte-identical


def build_stage0_candidate(write_bin=True):
    """STAGE1-ENGINEERING-PLAN.md Stage 0 alone: hot-start + eco-cruise copied from refined_CS_OK,
    no WOT-path edit, so it can be flashed and judged independently of MAP0/SOI-limiter."""
    cur, refined = Firmware(CURRENT_BIN), Firmware(REFINED_BIN)
    buf = bytearray(cur.data)
    copied = []
    for name in VNEXT_COPY_FROM_REFINED:
        obj = cur[name]
        a, n = obj.address, obj.size
        changed = [i for i in range(a, a + n) if cur.data[i] != refined.data[i]]
        buf[a:a + n] = refined.data[a:a + n]
        copied.append({'map': name, 'address': '0x%X' % a, 'size_bytes': n,
                       'bytes_actually_changed': len(changed), 'source': REFINED_BIN})
    fix_checksums(buf)
    new = bytes(buf)

    patched = Firmware(CURRENT_BIN)
    patched.data, patched._c, patched.sha256 = new, {}, hashlib.sha256(new).hexdigest()
    diff = [i for i in range(len(new)) if new[i] != cur.data[i]]
    allowed = set()
    for name in VNEXT_COPY_FROM_REFINED:
        obj = cur[name]
        allowed |= set(range(obj.address, obj.address + obj.size))
    for _, cs in CHECKSUM_BLOCKS:
        allowed |= set(range(cs, cs + 4))
    g_old, g_new = cur['InjCrv_phiBasGear56_MAP'], patched['InjCrv_phiBasGear56_MAP']
    cell_changes = [{'map': name, 'x': o.x[ix], 'y': o.y[iy], 'old': o.grid[ix][iy], 'new': p.grid[ix][iy]}
                    for name in VNEXT_COPY_FROM_REFINED
                    for o, p in ((cur[name], patched[name]),)
                    for ix in range(len(o.x)) for iy in range(len(o.y)) if o.grid[ix][iy] != p.grid[ix][iy]]
    verify = {
        'size_bytes': len(new),
        'checksum_block_sums': ['%08X' % s for s in block_sums(new)],
        'checksum_ok': all(s == CHECKSUM_TARGET for s in block_sums(new)),
        'changed_bytes_outside_known_objects_and_checksums': sorted('0x%X' % i for i in diff if i not in allowed),
        'total_changed_bytes_vs_current': len(diff),
        'axes_unchanged': all(cur[n].x == patched[n].x and cur[n].y == patched[n].y for n in VNEXT_COPY_FROM_REFINED),
        'gear56_wot_columns_unchanged': all(g_old.grid[ix][iy] == g_new.grid[ix][iy]
                                            for ix in range(len(g_old.x)) for iy, q in enumerate(g_old.y)
                                            if q >= STAGE0_WOT_Q_MIN_MG),
        'wot_chain_gear4_unchanged': all(chain(cur, r, PLAN_GEAR) == chain(patched, r, PLAN_GEAR) for r in RPM_BINS),
    }
    if (not verify['checksum_ok'] or verify['changed_bytes_outside_known_objects_and_checksums']
            or not verify['axes_unchanged'] or not verify['gear56_wot_columns_unchanged']
            or not verify['wot_chain_gear4_unchanged']):
        raise SystemExit('Stage 0 candidate verification FAILED: %s' % verify)

    plan = {'generated_utc': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'base_bin': {'path': CURRENT_BIN, 'sha256': cur.sha256},
            'components': ['hot-start fix (HS-250): StSys_trqStrtBas_MAP',
                           'eco cruise SOI advance: InjCrv_phiBasGear56_MAP (gears 5/6, light load only)'],
            'copied_objects': copied, 'cell_changes': cell_changes, 'verification': verify, 'candidate_bin': None,
            'status': 'READY — no WOT-path change (verified: gear-4 static chain identical at every rpm bin, '
                      'gear 5/6 SOI columns >= 40 mg identical).',
            'validation_protocol': ['Flash, clear DTCs.',
                                    'Hot start: engine at operating temperature, stop 10-30 min, restart; compare '
                                    'cranking time with before.',
                                    'Cruise 5th/6th at 1750-2250 rpm: no new rattle/harshness; MFA consumption '
                                    'over the same route.'],
            'abort_criteria': ['harder or longer hot start', 'audible combustion knock at light cruise', 'new DTC'],
            'rollback': CURRENT_BIN}
    if write_bin:
        os.makedirs(CANDIDATE_DIR, exist_ok=True)
        out_path = os.path.join(CANDIDATE_DIR, STAGE0_CANDIDATE_NAME)
        with open(out_path, 'wb') as f:
            f.write(new)
        verify['sha256'] = patched.sha256
        plan['candidate_bin'] = out_path.replace('\\', '/')
    else:
        plan['verification_note'] = 'NOT BUILT (plan only)'
    with open(os.path.join(OUT_DIR, 'candidate-stage0.json'), 'w', encoding='utf-8') as f:
        json.dump(plan, f, indent=1, ensure_ascii=False)
    return plan


SOI_LIMITER_MAP = 'InjCrv_phiMIMax_MAP'
SOI_BASE_MAPS = ('InjCrv_phiBasGear34_MAP', 'InjCrv_phiBasGear56_MAP')
SOI_CHECK_RPM = range(400, 5001, 25)  # dense grid: the limiter and base maps have different rpm nodes
# Below this the OEM limiter row is coolant-shaped (13.99 deg at -10 C vs 15.00 elsewhere, 400-1500 rpm):
# a deliberate cold-cranking strategy, not a load-path limit. Stage 1's 55/60 mg advance does reach
# past it at 400-575 rpm / -10 C, but that is cranking, outside the WOT coherence fix, and is left as is.
SOI_FIX_MIN_RPM = 1750


def soi_base_max(fw, rpm):
    """Highest base SOI either gear map can request at this rpm, over every q node."""
    return max(fw[name].lookup(rpm, q) for name in SOI_BASE_MAPS for q in fw[name].y)


def soi_limiter_clips(fw, min_rpm=0):
    """(rpm, base_max, limiter) wherever the base SOI exceeds the limiter at any coolant column."""
    lim = fw[SOI_LIMITER_MAP]
    out = []
    for rpm in SOI_CHECK_RPM:
        if rpm < min_rpm:
            continue
        base = soi_base_max(fw, rpm)
        cap = min(lim.lookup(rpm, t) for t in lim.y)
        if base > cap + 1e-9:
            out.append((rpm, base, cap))
    return out


def soi_limiter_fix_cells(cur, stock):
    """Rule from STAGE1-ENGINEERING-PLAN.md §2 link 6: Stage 1 advanced the 55/60 mg columns of
    both base SOI gear maps (~x1.08) but left InjCrv_phiMIMax_MAP stock, so the limiter now cuts
    that advance at 2250, 2500 and 4000-5000 rpm. The factory limiter never clips the factory
    base maps (asserted below), i.e. OEM intent is 'limiter above base'. Restore that: raise a
    limiter node only to the highest base SOI Stage 1 already requests there, rounded UP to the
    next raw step, never lower anything, never exceed the current base request. Coolant columns
    at those rpm are flat in the OEM map and are kept flat. Only rpm >= SOI_FIX_MIN_RPM."""
    stock_clips = soi_limiter_clips(stock)
    if stock_clips:
        raise SystemExit('OEM limiter clips OEM base SOI, rule premise invalid: %s' % stock_clips[:5])
    lim = cur[SOI_LIMITER_MAP]
    conv = lim.conversion
    cells = []
    for ix, rpm in enumerate(lim.x):
        if rpm < SOI_FIX_MIN_RPM:
            continue
        required = soi_base_max(cur, rpm)
        for iy, coolant in enumerate(lim.y):
            old = lim.grid[ix][iy]
            if old >= required:
                continue
            addr = _cell_address(lim, ix, iy)
            old_raw = struct.unpack_from('>h', cur.data, addr)[0]
            new_raw = _encode_raw_s16(lim, required)
            while a2l.to_phys(new_raw, conv) < required:
                new_raw += 1
            cells.append({'map': lim.name, 'rpm_node': rpm, 'coolant_node_c': coolant, 'address': '0x%X' % addr,
                          'old_raw': old_raw, 'new_raw': new_raw, 'old_raw_hex': '%04X' % (old_raw & 0xFFFF),
                          'new_raw_hex': '%04X' % (new_raw & 0xFFFF), 'old_deg': old,
                          'new_deg': a2l.to_phys(new_raw, conv), 'required_base_soi_deg': required,
                          'stock_base_soi_deg': soi_base_max(stock, rpm)})
    return cells


VNEXT2_CANDIDATE_NAME = '03G906021QJ_vNext2_hotstart-ecocruise-map0-soilim_CS_OK.bin'
VNEXT2_EFFECT_BINS = tuple(range(2000, 4001, 250))


def build_vnext2_candidate(write_bin=True):
    """vNext (hot-start + eco-cruise + MAP0) plus the SOI-limiter coherence fix, as one package:
    raising the limiter moves the duration selector toward MAP0 (29.16 deg -> selector 0.0), so the
    limiter fix without the MAP0 fix would REDUCE delivered fuel at 4000 rpm. They ship together."""
    cur, stock, refined = Firmware(CURRENT_BIN), Firmware(STOCK_BIN), Firmware(REFINED_BIN)
    buf = bytearray(cur.data)
    copied = []
    for name in VNEXT_COPY_FROM_REFINED:
        obj = cur[name]
        a, n = obj.address, obj.size
        changed = [i for i in range(a, a + n) if cur.data[i] != refined.data[i]]
        buf[a:a + n] = refined.data[a:a + n]
        copied.append({'map': name, 'address': '0x%X' % a, 'size_bytes': n,
                       'bytes_actually_changed': len(changed), 'source': REFINED_BIN})
    map0_cells, _ = map0_duration_fix_cells(cur, stock)
    soi_cells = soi_limiter_fix_cells(cur, stock)
    for c in map0_cells + soi_cells:
        struct.pack_into('>h', buf, int(c['address'], 16), c['new_raw'])
    fix_checksums(buf)
    new = bytes(buf)

    patched = Firmware(CURRENT_BIN)
    patched.data, patched._c, patched.sha256 = new, {}, hashlib.sha256(new).hexdigest()
    diff = [i for i in range(len(new)) if new[i] != cur.data[i]]
    allowed = set()
    for name in VNEXT_COPY_FROM_REFINED:
        obj = cur[name]
        allowed |= set(range(obj.address, obj.address + obj.size))
    for c in map0_cells + soi_cells:
        a = int(c['address'], 16)
        allowed |= {a, a + 1}
    for _, cs in CHECKSUM_BLOCKS:
        allowed |= set(range(cs, cs + 4))
    lim_new = patched[SOI_LIMITER_MAP]
    verify = {
        'size_bytes': len(new),
        'checksum_block_sums': ['%08X' % s for s in block_sums(new)],
        'checksum_ok': all(s == CHECKSUM_TARGET for s in block_sums(new)),
        'changed_bytes_outside_known_objects_and_checksums': sorted('0x%X' % i for i in diff if i not in allowed),
        'total_changed_bytes_vs_current': len(diff),
        'soi_limiter_clips_before': len(soi_limiter_clips(cur, SOI_FIX_MIN_RPM)),
        'soi_limiter_clips_after': soi_limiter_clips(patched, SOI_FIX_MIN_RPM),
        'soi_limiter_cold_cranking_clips_left_untouched': soi_limiter_clips(patched)[:1] and
            ['%d-%d rpm' % (soi_limiter_clips(patched)[0][0], soi_limiter_clips(patched)[-1][0])],
        'soi_limiter_never_lowered': all(lim_new.grid[i][j] >= cur[SOI_LIMITER_MAP].grid[i][j] - 1e-9
                                         for i in range(len(lim_new.x)) for j in range(len(lim_new.y))),
        'soi_limiter_max_headroom_over_base_deg': max(
            (min(lim_new.lookup(r, t) for t in lim_new.y) - soi_base_max(cur, r))
            for r in lim_new.x if any(c['rpm_node'] == r for c in soi_cells)) if soi_cells else None,
    }
    if (not verify['checksum_ok'] or verify['changed_bytes_outside_known_objects_and_checksums']
            or verify['soi_limiter_clips_after'] or not verify['soi_limiter_never_lowered']
            or (verify['soi_limiter_max_headroom_over_base_deg'] or 0) > 1.5 / 42.6666666666667):
        raise SystemExit('vNext2 candidate verification FAILED: %s' % verify)

    with open(os.path.join(OUT_DIR, 'vcds-analysis.json'), encoding='utf-8') as f:
        vres = json.load(f)
    effects = []
    for rpm in VNEXT2_EFFECT_BINS:
        b, a = chain(cur, rpm, PLAN_GEAR), chain(patched, rpm, PLAN_GEAR)
        eq_b, st_b, _ = stock_equivalent_q(cur, stock, rpm, b['q_cmd_clamp_mg'], PLAN_GEAR)
        eq_a, st_a, _ = stock_equivalent_q(patched, stock, rpm, a['q_cmd_clamp_mg'], PLAN_GEAR)
        air = [r['maf_act_mg'] for r in vres['rows'] if r['rpm'] == rpm and r['gear'] == PLAN_GEAR]
        air_med = statistics.median(air) if air else None
        effects.append({'rpm': rpm, 'q_cmd_mg': b['q_cmd_clamp_mg'],
                        'soi_before_deg': b['soi_deg_btdc_hyp'], 'soi_after_deg': a['soi_deg_btdc_hyp'],
                        'soi_limited_before': b['soi_limited'], 'soi_limited_after': a['soi_limited'],
                        'selector_before': b['duration_map_selector'], 'selector_after': a['duration_map_selector'],
                        'stock_eq_before_mg': eq_b, 'stock_eq_before_status': st_b,
                        'stock_eq_after_mg': eq_a, 'stock_eq_after_status': st_a,
                        'delivered_fuel_gain_mg': eq_a - eq_b, 'air_mg_stroke_median': air_med,
                        'lambda_before': ph.lambda_from(air_med, eq_b, 14.5) if air_med else None,
                        'lambda_after': ph.lambda_from(air_med, eq_a, 14.5) if air_med else None,
                        'electrical_end_proxy_before_deg_atdc': b['electrical_command_end_proxy_deg_atdc'],
                        'electrical_end_proxy_after_deg_atdc': a['electrical_command_end_proxy_deg_atdc']})

    plan = {'generated_utc': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'base_bin': {'path': CURRENT_BIN, 'sha256': cur.sha256},
            'components': [
                {'name': 'hot-start fix (HS-250)', 'map': 'StSys_trqStrtBas_MAP', 'risk': 'none at WOT',
                 'status': 'previously audited, copied byte-for-byte from refined_CS_OK'},
                {'name': 'eco cruise SOI advance', 'map': 'InjCrv_phiBasGear56_MAP', 'risk': 'none at WOT',
                 'status': 'previously audited, copied byte-for-byte from refined_CS_OK'},
                {'name': 'MAP0 duration restore', 'map': 'InjVlv_phiInjMI1_MAP0', 'risk': 'PROVISIONAL, WOT-only',
                 'status': 'DECISION-2026-09-16.md #4b; lambda ~0.89-0.91 at 3500-4000 with measured air'},
                {'name': 'SOI limiter coherence', 'map': SOI_LIMITER_MAP, 'risk': 'PROVISIONAL, WOT-only',
                 'status': 'STAGE1-ENGINEERING-PLAN.md §2 link 6; limiter raised only to the base SOI Stage 1 '
                           'already requests (zero added headroom beyond one raw step); corrections applied '
                           'between base map and limiter (IAT/atmospheric/dynamic) are not modelled'},
            ],
            'excluded': dict(VNEXT_EXCLUDED_FROM_REFINED, **{
                'FMTC_trq2qBas_MAP': 'axis-end gap (link 2) is HOLD until clamp-vs-extrapolate is measured '
                                     '(STAGE1-ENGINEERING-PLAN.md Stage 2); no edit.'}),
            'copied_objects': copied, 'map0_cells': map0_cells, 'soi_limiter_cells': soi_cells,
            'predicted_effect_gear4': effects, 'verification': verify, 'candidate_bin': None,
            'status': 'PROVISIONAL — static calculation only. Flash only as Stage 1 of STAGE1-ENGINEERING-PLAN.md '
                      'with its validation gate; hot-start + eco-cruise alone (build-vnext minus MAP0) remains '
                      'the zero-risk alternative.',
            'validation_protocol': [
                'Flash, clear DTCs, gear 4 WOT 2750->4100 both directions, VCDS groups 011+003+008.',
                'Pass: road torque P50 at 3000-4000 not below the vcds-analysis baseline; no visible smoke.'],
            'abort_criteria': ['visible smoke above 3000 rpm', 'road torque P50 below baseline at any 3000-3750 bin',
                               'audible knock/harshness at 2250-2500 or 4000 rpm WOT', 'new DTC'],
            'rollback': CURRENT_BIN}
    json_path = os.path.join(OUT_DIR, 'candidate-vnext2.json')
    if write_bin:
        os.makedirs(CANDIDATE_DIR, exist_ok=True)
        out_path = os.path.join(CANDIDATE_DIR, VNEXT2_CANDIDATE_NAME)
        with open(out_path, 'wb') as f:
            f.write(new)
        verify['sha256'] = patched.sha256
        plan['candidate_bin'] = out_path.replace('\\', '/')
    else:
        plan['verification_note'] = 'NOT BUILT (plan only; BIN creation requires explicit approval)'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(plan, f, indent=1, ensure_ascii=False)
    return plan


SMOKE_LAMBDA_TARGET = 1.12      # what the calibration already runs at 2000-2500 rpm, cross-validated (DECISION #2)
SMOKE_AFR_STOICH = 14.5
SMOKE_ROAD_LOGS = ('logs/20260917/Event_RAW_20260917_121649.csv',)
SMOKE_WOT_MIN_LOAD = 90.0
SMOKE_NODE_HALF_WINDOW_RPM = 250
SMOKE_MIN_SAMPLES = 4
SMOKE_TRANSIENT_COLUMN_HPA = 1800.0
SMOKE_WOT_COLUMN_HPA = 2000.0
SMOKE_ABOVE_DATA_VE_FACTOR = 0.95   # rpm nodes above the logged range: air per corrected hPa taken 5% below the last node


def wot_air_evidence(cur):
    """Measured WOT air per smoke-map rpm node, pooled from the VCDS 2026-09-16 runtime rows (group 003 MAF, 3rd/4th)
    and the OBD road log 2026-09-17 (4th/5th, MAF + MAP + IAT). Returns {node: {...}} with median air mg/stroke,
    median IAT-corrected boost (smoke-map pressure axis) and sample count."""
    import maf_speed_density_check as sd
    corr = cur['FlMng_pIATCorr_MAP']
    smoke = cur['FlMng_qPresSmoke_MAP']
    pts = []
    with open(os.path.join(OUT_DIR, 'vcds-analysis.json'), encoding='utf-8') as f:
        for r in json.load(f)['rows']:
            pts.append({'rpm': r['rpm'], 'air': r['maf_act_mg'], 'pc': None, 'src': 'vcds-20260916'})
    for path in SMOKE_ROAD_LOGS:
        for x in sd.samples(sd.load(path)):
            if (x['load'] or 0) >= SMOKE_WOT_MIN_LOAD:
                pc = corr.lookup(x['map'], x['iat'])
                if pc >= SMOKE_WOT_COLUMN_HPA:
                    pts.append({'rpm': x['rpm'], 'air': x['maf_mg'], 'pc': pc, 'src': os.path.basename(path)})
    out = {}
    for node in smoke.x:
        near = [p for p in pts if abs(p['rpm'] - node) <= SMOKE_NODE_HALF_WINDOW_RPM]
        if len(near) < SMOKE_MIN_SAMPLES:
            continue
        pcs = [p['pc'] for p in near if p['pc']]
        out[node] = {'air_mg': statistics.median(p['air'] for p in near), 'n': len(near),
                     'pc_hpa': statistics.median(pcs) if pcs else None,
                     'sources': sorted({p['src'] for p in near})}
    return out


def q_cmd_for_stock_equivalent(cur, stock, rpm, q_eq_target, gear=PLAN_GEAR):
    """ECU fuel request whose delivered (stock-duration-equivalent) mass equals q_eq_target."""
    lo, hi = 10.0, 90.0
    for _ in range(50):
        mid = (lo + hi) / 2
        if stock_equivalent_q(cur, stock, rpm, mid, gear)[0] < q_eq_target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def smoke_air_coherent_cells(cur, stock, lambda_target=SMOKE_LAMBDA_TARGET):
    """FlMng_qPresSmoke_MAP 1800/2000 hPa columns re-derived from measured air instead of the Stage 1 blanket
    +13%/+13% scaling. Rule per rpm node with logged WOT air:
      2000 hPa column (clamped for every corrected boost >= 2000, i.e. all established WOT):
          delivered fuel = measured WOT air / (14.5 x lambda_target)
      1800 hPa column (spool / gear-change transient): same, with air scaled by 1800 / median WOT corrected boost.
    ECU request is the q whose stock-equivalent delivery equals that fuel. Cells are only ever LOWERED (never above
    the current Stage 1 value). Floors: 1800 hPa column never below the OEM cell; 2000 hPa column never below the fuel
    the OEM calibration actually delivered at WOT (its torque-path request - the OEM smoke cell of 60 mg at >=3000 rpm
    was never binding, so it is not a validated smoke limit). Nodes without data are unchanged,
    except nodes above the logged rpm range which keep the last data node's air-per-hPa x SMOKE_ABOVE_DATA_VE_FACTOR."""
    smoke = cur['FlMng_qPresSmoke_MAP']
    smoke_stock = stock['FlMng_qPresSmoke_MAP']
    ev = wot_air_evidence(cur)
    data_nodes = sorted(ev)
    iy_wot, iy_tr = smoke.y.index(SMOKE_WOT_COLUMN_HPA), smoke.y.index(SMOKE_TRANSIENT_COLUMN_HPA)
    cells = []
    for ix, rpm in enumerate(smoke.x):
        if rpm in ev:
            e, basis = ev[rpm], 'measured'
        elif data_nodes and rpm > data_nodes[-1]:
            last = ev[data_nodes[-1]]
            e, basis = dict(last, air_mg=last['air_mg'] * SMOKE_ABOVE_DATA_VE_FACTOR), 'above-range from %d' % data_nodes[-1]
        else:
            continue
        pc_wot = e['pc_hpa'] or ev[min(data_nodes, key=lambda n: abs(n - rpm) if ev[n]['pc_hpa'] else 1e9)]['pc_hpa']
        oem_wot_delivered = chain(stock, rpm, PLAN_GEAR)['q_cmd_clamp_mg']
        for iy, air in ((iy_wot, e['air_mg']), (iy_tr, e['air_mg'] * SMOKE_TRANSIENT_COLUMN_HPA / pc_wot)):
            q_eq = air / (SMOKE_AFR_STOICH * lambda_target)
            q_cmd = q_cmd_for_stock_equivalent(cur, stock, rpm, q_eq)
            old, oem = smoke.grid[ix][iy], smoke_stock.grid[ix][iy]
            floor = oem if iy == iy_tr else q_cmd_for_stock_equivalent(cur, stock, rpm, oem_wot_delivered)
            new = max(floor, min(old, q_cmd))
            new_raw = _encode_raw_s16(smoke, new)
            new_phys = a2l.to_phys(new_raw, smoke.conversion)
            if new_raw == _encode_raw_s16(smoke, old):
                continue
            addr = _cell_address(smoke, ix, iy)
            cells.append({'map': smoke.name, 'rpm_node': rpm, 'pressure_node_hpa': smoke.y[iy], 'address': '0x%X' % addr,
                          'old_raw': struct.unpack_from('>h', cur.data, addr)[0], 'new_raw': new_raw,
                          'old_mg': old, 'oem_mg': oem, 'new_mg': new_phys, 'q_cmd_for_target_mg': q_cmd,
                          'target_delivered_mg': q_eq, 'air_mg': air, 'air_basis': basis, 'n_samples': e['n'],
                          'floor_mg': floor, 'bound': 'floor' if q_cmd < floor else 'lambda_target'})
    return cells, ev


VNEXT3_CANDIDATE_NAME = '03G906021QJ_vNext3_stage0-smoke-air-coherent_CS_OK.bin'


VNEXT6_CANDIDATE_NAME = '03G906021QJ_vNext6_stage1-fuel-only-l115_CS_OK.bin'


def build_vnext6_candidate(write_bin=True):
    """vNext3 rule at lambda 1.15, no SOI edit. 3000-4000 rpm analysis (2026-09-17): ~85-90% of the end-of-injection
    gain comes from removing unburnable fuel; the vNext5 SOI advance adds only 0.6-0.9 deg EOI while taking the 45 mg
    column to OEM+2.5 deg and 0.26-0.30 deg under the limiter. Engine-life priority: keep Stage 1 timing."""
    return build_vnext3_candidate(write_bin, lambda_target=BALANCED_LAMBDA_TARGET, out_name=VNEXT6_CANDIDATE_NAME,
                                  json_name='candidate-vnext6.json')


def build_vnext3_candidate(write_bin=True, lambda_target=SMOKE_LAMBDA_TARGET, out_name=VNEXT3_CANDIDATE_NAME,
                           json_name='candidate-vnext3.json'):
    """Stage 0 (hot-start + eco-cruise) + smoke limiter re-derived from measured air (all gears: the smoke map is
    rpm x corrected boost, gear-independent; the 1800 hPa column governs spool after every gear change)."""
    cur, stock, refined = Firmware(CURRENT_BIN), Firmware(STOCK_BIN), Firmware(REFINED_BIN)
    buf = bytearray(cur.data)
    for name in VNEXT_COPY_FROM_REFINED:
        obj = cur[name]
        buf[obj.address:obj.address + obj.size] = refined.data[obj.address:obj.address + obj.size]
    cells, ev = smoke_air_coherent_cells(cur, stock, lambda_target)
    for c in cells:
        struct.pack_into('>h', buf, int(c['address'], 16), c['new_raw'])
    fix_checksums(buf)
    new = bytes(buf)
    patched = Firmware(CURRENT_BIN)
    patched.data, patched._c, patched.sha256 = new, {}, hashlib.sha256(new).hexdigest()

    diff = [i for i in range(len(new)) if new[i] != cur.data[i]]
    allowed = set()
    for name in VNEXT_COPY_FROM_REFINED:
        obj = cur[name]
        allowed |= set(range(obj.address, obj.address + obj.size))
    for c in cells:
        a = int(c['address'], 16)
        allowed |= {a, a + 1}
    for _, cs in CHECKSUM_BLOCKS:
        allowed |= set(range(cs, cs + 4))
    s_old, s_new, s_oem = cur['FlMng_qPresSmoke_MAP'], patched['FlMng_qPresSmoke_MAP'], stock['FlMng_qPresSmoke_MAP']
    cellwise = [(s_old.grid[i][j], s_new.grid[i][j], s_oem.grid[i][j]) for i in range(len(s_old.x)) for j in range(len(s_old.y))]
    verify = {
        'size_bytes': len(new),
        'checksum_block_sums': ['%08X' % s for s in block_sums(new)],
        'checksum_ok': all(s == CHECKSUM_TARGET for s in block_sums(new)),
        'changed_bytes_outside_known_objects_and_checksums': sorted('0x%X' % i for i in diff if i not in allowed),
        'smoke_never_raised': all(n <= o + 1e-9 for o, n, _ in cellwise),
        'smoke_1800_never_below_oem': all(s_new.grid[i][s_old.y.index(SMOKE_TRANSIENT_COLUMN_HPA)] >=
                                          s_oem.grid[i][s_old.y.index(SMOKE_TRANSIENT_COLUMN_HPA)] - 0.02
                                          for i in range(len(s_old.x))),
        'smoke_axes_unchanged': s_old.x == s_new.x and s_old.y == s_new.y,
    }
    if (not verify['checksum_ok'] or verify['changed_bytes_outside_known_objects_and_checksums']
            or not verify['smoke_never_raised'] or not verify['smoke_1800_never_below_oem'] or not verify['smoke_axes_unchanged']):
        raise SystemExit('vNext3 candidate verification FAILED: %s' % verify)

    with open(os.path.join(OUT_DIR, 'vcds-analysis.json'), encoding='utf-8') as f:
        vrows = json.load(f)['rows']
    effects = []
    for rpm in range(2000, 4001, 250):
        rows = [r for r in vrows if r['rpm'] == rpm and r['gear'] == PLAN_GEAR]
        if not rows:
            continue
        q_rt = statistics.median(r['q_runtime_mg'] for r in rows)
        burned = [r['implied_burned_q_mg']['p50'] for r in rows if r.get('implied_burned_q_mg')]
        near = [e for n, e in ev.items() if abs(n - rpm) <= 500]
        air = statistics.median(r['maf_act_mg'] for r in rows)
        cap_old = s_old.lookup(rpm, SMOKE_WOT_COLUMN_HPA)
        cap_new = s_new.lookup(rpm, SMOKE_WOT_COLUMN_HPA)
        q_old, q_new = min(q_rt, cap_old), min(q_rt, cap_new)
        eq_old = stock_equivalent_q(cur, stock, rpm, q_old, PLAN_GEAR)[0]
        eq_new = stock_equivalent_q(patched, stock, rpm, q_new, PLAN_GEAR)[0]
        effects.append({'rpm': rpm, 'q_runtime_logged_mg': q_rt, 'q_cmd_new_mg': q_new,
                        'delivered_before_mg': eq_old, 'delivered_after_mg': eq_new,
                        'burned_p50_from_road_torque_mg': statistics.median(burned) if burned else None,
                        'air_mg_vcds_gear4': air, 'lambda_before': ph.lambda_from(air, eq_old, SMOKE_AFR_STOICH),
                        'lambda_after': ph.lambda_from(air, eq_new, SMOKE_AFR_STOICH)})

    plan = {'generated_utc': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'base_bin': {'path': CURRENT_BIN, 'sha256': cur.sha256},
            'lambda_target': lambda_target,
            'air_evidence_by_rpm_node': ev, 'smoke_cells': cells, 'predicted_effect_gear4': effects,
            'components': ['Stage 0: StSys_trqStrtBas_MAP + InjCrv_phiBasGear56_MAP from refined_CS_OK',
                           'FlMng_qPresSmoke_MAP 1800/2000 hPa columns from measured air (lower-only, OEM floor)'],
            'not_changed_on_purpose': {
                'InjVlv_phiInjMI1_MAP0 / InjCrv_phiMIMax_MAP': 'adding fuel above 3000 rpm contradicts measured air (HOLD)',
                'FMTC_trq2qBas_MAP axis': 'with the smoke cap binding at WOT the >336 Nm request no longer sets fuel',
                'PCR_* boost / N75': 'overshoot to 2420-2470 hPa in 5th is a governor issue; needs fast 011 log',
                'Gearbx_trqMaxGear*_CUR': 'gear limits are 3000 Nm (inactive) in OEM and Stage 1; gear via CAN'},
            'verification': verify, 'candidate_bin': None,
            'status': 'CANDIDATE — every edit only removes fuel the measured air cannot burn at lambda %.2f, the '
                      'lambda the calibration already runs without smoke at 2000-2500 rpm.' % lambda_target,
            'validation_protocol': ['Flash, clear DTCs.', 'Same OBD drive-log protocol as 2026-09-17: 4th and 5th WOT '
                                    '2000->4000, plus 2nd/3rd pulls from 1500 rpm.',
                                    'Pass: 0-100/60-120 or pull time not slower; no smoke on gear changes.'],
            'abort_criteria': ['noticeably slower pull 3000-4000 rpm', 'new DTC'],
            'rollback': CURRENT_BIN}
    if write_bin:
        os.makedirs(CANDIDATE_DIR, exist_ok=True)
        out_path = os.path.join(CANDIDATE_DIR, out_name)
        with open(out_path, 'wb') as f:
            f.write(new)
        verify['sha256'] = patched.sha256
        plan['candidate_bin'] = out_path.replace('\\', '/')
    with open(os.path.join(OUT_DIR, json_name), 'w', encoding='utf-8') as f:
        json.dump(plan, f, indent=1, ensure_ascii=False, default=str)
    return plan


EDGE_LAMBDA_TARGET = 1.10            # power-edge smoke target (DPF physically removed, EGR blanked)
EDGE_RAISE_MAX_MG = 1.5              # max smoke-cell increase over Stage 1 where fuel still converts (2000-2500)
EDGE_SOI_MIN_RPM = 3000.0
EDGE_SOI_Q_COLUMNS = (45.0, 55.0, 60.0)
EDGE_SOI_MAX_OVER_OEM_DEG = 2.5
EDGE_SOI_LIMITER_MARGIN_DEG = 0.25
EDGE_SOI_MAPS = ('InjCrv_phiBasGear34_MAP', 'InjCrv_phiBasGear56_MAP')  # gears 1/2 left as Stage 1
VNEXT4_CANDIDATE_NAME = '03G906021QJ_vNext4_stage1-edge_CS_OK.bin'


def soi_edge_cells(fw, stock):
    """Earlier main-injection start at 3000+ rpm WOT columns so the (duration - SOI) end-of-injection proxy moves
    back toward OEM. Per cell: never retard, never above the UNCHANGED OEM SOI limiter minus a margin, never more
    than EDGE_SOI_MAX_OVER_OEM_DEG over the OEM cell."""
    lim = stock['InjCrv_phiMIMax_MAP']
    cells = []
    for name in EDGE_SOI_MAPS:
        m, m_oem = fw[name], stock[name]
        for ix, rpm in enumerate(m.x):
            if rpm < EDGE_SOI_MIN_RPM:
                continue
            cap = min(lim.lookup(rpm, t) for t in lim.y) - EDGE_SOI_LIMITER_MARGIN_DEG
            for q in EDGE_SOI_Q_COLUMNS:
                iy = m.y.index(q)
                old, oem = m.grid[ix][iy], m_oem.grid[ix][iy]
                new = min(cap, oem + EDGE_SOI_MAX_OVER_OEM_DEG)
                if new <= old + 1e-6:
                    continue
                raw = _encode_raw_s16(m, new)
                while a2l.to_phys(raw, m.conversion) > new + 1e-9:
                    raw -= 1
                addr = _cell_address(m, ix, iy)
                cells.append({'map': name, 'rpm_node': rpm, 'q_node_mg': q, 'address': '0x%X' % addr,
                              'old_raw': struct.unpack_from('>h', fw.data, addr)[0], 'new_raw': raw,
                              'old_deg': old, 'oem_deg': oem, 'new_deg': a2l.to_phys(raw, m.conversion),
                              'limiter_minus_margin_deg': cap})
    return cells


def _patched(base, buf):
    fw = Firmware(CURRENT_BIN)
    fw.data, fw._c, fw.sha256 = bytes(buf), {}, hashlib.sha256(bytes(buf)).hexdigest()
    return fw


VNEXT5_CANDIDATE_NAME = '03G906021QJ_vNext5_stage1-balanced_CS_OK.bin'
BALANCED_LAMBDA_TARGET = 1.15  # ecuedit practitioners: AFR 17-18 smokeless on 1.9 PD 105hp


def build_vnext5_candidate(write_bin=True):
    """Balanced Stage 1 (owner priorities: pull + engine life + fuel economy): vNext4 SOI/EOI correction, smoke at
    lambda 1.15, no fuel added anywhere (2000-2500 rpm stays at the Stage 1 ~320 Nm plateau, clutch-friendly)."""
    return build_vnext4_candidate(write_bin, lambda_target=BALANCED_LAMBDA_TARGET, raise_max_mg=0.0,
                                  out_name=VNEXT5_CANDIDATE_NAME, json_name='candidate-vnext5.json')


def build_vnext4_candidate(write_bin=True, lambda_target=EDGE_LAMBDA_TARGET, raise_max_mg=EDGE_RAISE_MAX_MG,
                           out_name=VNEXT4_CANDIDATE_NAME, json_name='candidate-vnext4.json'):
    """Power-edge Stage 1: Stage 0 + SOI advance 3000+ rpm (inside OEM limiter) + smoke columns at lambda 1.10
    derived on the SOI-patched calibration (SOI moves the duration selector, so delivered fuel is recomputed)."""
    cur, stock, refined = Firmware(CURRENT_BIN), Firmware(STOCK_BIN), Firmware(REFINED_BIN)
    buf = bytearray(cur.data)
    for name in VNEXT_COPY_FROM_REFINED:
        obj = cur[name]
        buf[obj.address:obj.address + obj.size] = refined.data[obj.address:obj.address + obj.size]
    step1 = _patched(cur, buf)
    soi_cells = soi_edge_cells(step1, stock)
    for c in soi_cells:
        struct.pack_into('>h', buf, int(c['address'], 16), c['new_raw'])
    step2 = _patched(cur, buf)

    smoke = step2['FlMng_qPresSmoke_MAP']
    smoke_cells, ev = [], wot_air_evidence(step2)
    iy_wot, iy_tr = smoke.y.index(SMOKE_WOT_COLUMN_HPA), smoke.y.index(SMOKE_TRANSIENT_COLUMN_HPA)
    data_nodes = sorted(ev)
    for ix, rpm in enumerate(smoke.x):
        if rpm in ev:
            e = ev[rpm]
        elif data_nodes and rpm > data_nodes[-1]:
            e = dict(ev[data_nodes[-1]], air_mg=ev[data_nodes[-1]]['air_mg'] * SMOKE_ABOVE_DATA_VE_FACTOR)
        else:
            continue
        pc_wot = e['pc_hpa'] or statistics.median(v['pc_hpa'] for v in ev.values() if v['pc_hpa'])
        oem_wot = chain(stock, rpm, PLAN_GEAR)['q_cmd_clamp_mg']
        for iy, air in ((iy_wot, e['air_mg']), (iy_tr, e['air_mg'] * SMOKE_TRANSIENT_COLUMN_HPA / pc_wot)):
            q_eq = air / (SMOKE_AFR_STOICH * lambda_target)
            q_cmd = q_cmd_for_stock_equivalent(step2, stock, rpm, q_eq)
            old, oem = smoke.grid[ix][iy], stock['FlMng_qPresSmoke_MAP'].grid[ix][iy]
            if iy == iy_tr:
                new = max(oem, min(old, q_cmd))
            else:
                floor = q_cmd_for_stock_equivalent(step2, stock, rpm, oem_wot)
                upper = old + raise_max_mg if rpm <= 2500 else old
                new = max(floor, min(upper, q_cmd))
            raw = _encode_raw_s16(smoke, new)
            if raw == _encode_raw_s16(smoke, old):
                continue
            addr = _cell_address(smoke, ix, iy)
            smoke_cells.append({'map': smoke.name, 'rpm_node': rpm, 'pressure_node_hpa': smoke.y[iy],
                                'address': '0x%X' % addr, 'old_raw': struct.unpack_from('>h', cur.data, addr)[0],
                                'new_raw': raw, 'old_mg': old, 'new_mg': a2l.to_phys(raw, smoke.conversion),
                                'target_delivered_mg': q_eq, 'air_mg': air})
    for c in smoke_cells:
        struct.pack_into('>h', buf, int(c['address'], 16), c['new_raw'])
    fix_checksums(buf)
    new = bytes(buf)
    patched = _patched(cur, buf)

    diff = [i for i in range(len(new)) if new[i] != cur.data[i]]
    allowed = set()
    for name in VNEXT_COPY_FROM_REFINED:
        obj = cur[name]
        allowed |= set(range(obj.address, obj.address + obj.size))
    for c in soi_cells + smoke_cells:
        a = int(c['address'], 16)
        allowed |= {a, a + 1}
    for _, cs in CHECKSUM_BLOCKS:
        allowed |= set(range(cs, cs + 4))
    lim = stock['InjCrv_phiMIMax_MAP']
    s_old, s_new = cur['FlMng_qPresSmoke_MAP'], patched['FlMng_qPresSmoke_MAP']
    verify = {
        'checksum_block_sums': ['%08X' % s for s in block_sums(new)],
        'checksum_ok': all(s == CHECKSUM_TARGET for s in block_sums(new)),
        'changed_bytes_outside_known_objects_and_checksums': sorted('0x%X' % i for i in diff if i not in allowed),
        'soi_limiter_unchanged': patched['InjCrv_phiMIMax_MAP'].grid == lim.grid,
        'soi_edits_within_limiter_and_oem_plus_cap': all(
            c['new_deg'] <= min(lim.lookup(c['rpm_node'], t) for t in lim.y) + 1e-6 and
            c['new_deg'] <= c['oem_deg'] + EDGE_SOI_MAX_OVER_OEM_DEG + 1e-6 and c['new_deg'] > c['old_deg']
            for c in soi_cells),
        'smoke_raise_bounded': all(s_new.grid[i][j] <= s_old.grid[i][j] + raise_max_mg + 0.03
                                   for i in range(len(s_old.x)) for j in range(len(s_old.y))),
    }
    if (not verify['checksum_ok'] or verify['changed_bytes_outside_known_objects_and_checksums']
            or not verify['soi_limiter_unchanged'] or not verify['soi_edits_within_limiter_and_oem_plus_cap']
            or not verify['smoke_raise_bounded']):
        raise SystemExit('vNext4 candidate verification FAILED: %s' % verify)

    with open(os.path.join(OUT_DIR, 'vcds-analysis.json'), encoding='utf-8') as f:
        vrows = json.load(f)['rows']
    effects = []
    for rpm in range(2000, 4001, 250):
        rows = [r for r in vrows if r['rpm'] == rpm and r['gear'] == PLAN_GEAR]
        if not rows:
            continue
        q_rt = statistics.median(r['q_runtime_mg'] for r in rows)
        air = statistics.median(r['maf_act_mg'] for r in rows)
        q_new = min(chain(patched, rpm, PLAN_GEAR)['q_cmd_clamp_mg'], s_new.lookup(rpm, SMOKE_WOT_COLUMN_HPA))
        a, b = chain_with_q(cur, rpm, PLAN_GEAR, q_rt), chain_with_q(patched, rpm, PLAN_GEAR, q_new)
        eq_a = stock_equivalent_q(cur, stock, rpm, q_rt, PLAN_GEAR)[0]
        eq_b = stock_equivalent_q(patched, stock, rpm, q_new, PLAN_GEAR)[0]
        burned = [r['implied_burned_q_mg']['p50'] for r in rows if r.get('implied_burned_q_mg')]
        effects.append({'rpm': rpm, 'delivered_before_mg': eq_a, 'delivered_after_mg': eq_b,
                        'lambda_before': ph.lambda_from(air, eq_a, SMOKE_AFR_STOICH),
                        'lambda_after': ph.lambda_from(air, eq_b, SMOKE_AFR_STOICH),
                        'soi_before': a['soi_deg_btdc_hyp'], 'soi_after': b['soi_deg_btdc_hyp'],
                        'eoi_proxy_before': a['electrical_command_end_proxy_deg_atdc'],
                        'eoi_proxy_after': b['electrical_command_end_proxy_deg_atdc'],
                        'burned_p50_now_mg': statistics.median(burned) if burned else None})
    plan = {'generated_utc': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'base_bin': {'path': CURRENT_BIN, 'sha256': cur.sha256}, 'lambda_target': lambda_target,
            'soi_cells': soi_cells, 'smoke_cells': smoke_cells, 'predicted_effect_gear4': effects,
            'verification': verify, 'candidate_bin': None,
            'not_changed_on_purpose': {
                'InjCrv_phiMIMax_MAP': 'OEM SOI limiter is the peak-pressure guard; all advance stays below it',
                'InjCrv_phiBasGear12_MAP': 'gears 1/2 keep Stage 1 timing (fast transients, traction)',
                'PCR_* boost': 'overshoot to 2420-2470 hPa in 5th must be understood from a fast group-011 log first',
                'low-rpm torque (<2000)': 'kept at Stage 1 (~310 Nm inner) per user choice: power over DMF margin'},
            'rollback': CURRENT_BIN}
    if write_bin:
        os.makedirs(CANDIDATE_DIR, exist_ok=True)
        out_path = os.path.join(CANDIDATE_DIR, out_name)
        with open(out_path, 'wb') as f:
            f.write(new)
        verify['sha256'] = patched.sha256
        plan['candidate_bin'] = out_path.replace('\\', '/')
    with open(os.path.join(OUT_DIR, json_name), 'w', encoding='utf-8') as f:
        json.dump(plan, f, indent=1, ensure_ascii=False, default=str)
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
    b0 = sub.add_parser('build-map0')
    b0.add_argument('--plan-only', action='store_true', help='fit and report cells without creating a BIN')
    bn = sub.add_parser('build-vnext')
    bn.add_argument('--plan-only', action='store_true', help='fit and report cells without creating a BIN')
    b00 = sub.add_parser('build-stage0')
    b00.add_argument('--plan-only', action='store_true', help='report cells without creating a BIN')
    bn6 = sub.add_parser('build-vnext6')
    bn6.add_argument('--plan-only', action='store_true', help='report cells without creating a BIN')
    bn5 = sub.add_parser('build-vnext5')
    bn5.add_argument('--plan-only', action='store_true', help='report cells without creating a BIN')
    bn4 = sub.add_parser('build-vnext4')
    bn4.add_argument('--plan-only', action='store_true', help='report cells without creating a BIN')
    bn3 = sub.add_parser('build-vnext3')
    bn3.add_argument('--plan-only', action='store_true', help='report cells without creating a BIN')
    bn2 = sub.add_parser('build-vnext2')
    bn2.add_argument('--plan-only', action='store_true', help='fit and report cells without creating a BIN')
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
    elif args.cmd == 'build-map0':
        plan = build_map0_candidate(write_bin=not args.plan_only)
        print(plan['status'])
        for c in plan['cells']:
            print('%s rpm=%-6.0f %-6s %s(%s) -> %s(%s) ratio=%.4f' % (
                c['map'], c['rpm_node'], c['address'], _f(c['old_deg'], 3), c['old_raw_hex'],
                _f(c['new_deg'], 3), c['new_raw_hex'], c['ratio']))
        for e in plan['predicted_effect']:
            print('rpm=%-5.0f q_cmd=%.1f eq %.1f(%s)->%.1f(%s) delta=%+.1f mg  lambda %s->%s  selector %.2f->%.2f' % (
                e['rpm'], e['q_cmd_mg'], e['stock_eq_before_mg'], e['stock_eq_before_status'],
                e['stock_eq_after_mg'], e['stock_eq_after_status'], e['delivered_fuel_gain_mg'],
                _f(e['lambda_before'], 3), _f(e['lambda_after'], 3),
                e['duration_selector_before'], e['duration_selector_after']))
        print(plan['verification'])
    elif args.cmd == 'build-vnext':
        plan = build_vnext_candidate(write_bin=not args.plan_only)
        for c in plan['components']:
            print('- %s [%s]: %s' % (c['name'], c['risk'], c['status']))
        print('excluded:', list(plan['excluded_from_refined_CS_OK']))
        print(plan['status'])
        print(plan['verification'])
    elif args.cmd == 'build-stage0':
        plan = build_stage0_candidate(write_bin=not args.plan_only)
        for c in plan['cell_changes']:
            print('%-26s x=%-7.1f y=%-7.2f %8.3f -> %8.3f' % (c['map'], c['x'], c['y'], c['old'], c['new']))
        print(plan['status'])
        print(plan['verification'], plan.get('verification_note', ''), plan['candidate_bin'])
    elif args.cmd in ('build-vnext4', 'build-vnext5'):
        plan = (build_vnext5_candidate if args.cmd == 'build-vnext5' else build_vnext4_candidate)(write_bin=not args.plan_only)
        for e in plan['predicted_effect_gear4']:
            print('rpm %4d delivered %.1f -> %.1f mg  lambda %.2f -> %.2f  SOI %.1f -> %.1f  EOI proxy %.1f -> %.1f' % (e['rpm'], e['delivered_before_mg'], e['delivered_after_mg'], e['lambda_before'], e['lambda_after'], e['soi_before'], e['soi_after'], e['eoi_proxy_before'], e['eoi_proxy_after']))
        print(plan['verification'], plan['candidate_bin'])
    elif args.cmd in ('build-vnext3', 'build-vnext6'):
        plan = (build_vnext6_candidate if args.cmd == 'build-vnext6' else build_vnext3_candidate)(write_bin=not args.plan_only)
        for c in plan['smoke_cells']:
            print('%5.0f rpm %4.0f hPa  %5.2f -> %5.2f mg  (%s)' % (c['rpm_node'], c['pressure_node_hpa'], c['old_mg'], c['new_mg'], c['bound']))
        for e in plan['predicted_effect_gear4']:
            print('rpm %4d delivered %.1f -> %.1f mg  lambda %.2f -> %.2f' % (e['rpm'], e['delivered_before_mg'], e['delivered_after_mg'], e['lambda_before'], e['lambda_after']))
        print(plan['verification'], plan['candidate_bin'])
    elif args.cmd == 'build-vnext2':
        plan = build_vnext2_candidate(write_bin=not args.plan_only)
        for c in plan['components']:
            print('- %s [%s]: %s' % (c['name'], c['risk'], c['status']))
        for c in plan['soi_limiter_cells']:
            print('%s rpm=%-6.0f coolant=%-6.1f %s %.2f(%s) -> %.2f(%s) base=%.2f' % (
                c['map'], c['rpm_node'], c['coolant_node_c'], c['address'], c['old_deg'], c['old_raw_hex'],
                c['new_deg'], c['new_raw_hex'], c['required_base_soi_deg']))
        for e in plan['predicted_effect_gear4']:
            print('rpm=%-5.0f q=%.1f SOI %.2f->%.2f sel %.2f->%.2f eq %.1f->%.1f (%+.1f mg) lambda %s->%s' % (
                e['rpm'], e['q_cmd_mg'], e['soi_before_deg'], e['soi_after_deg'], e['selector_before'],
                e['selector_after'], e['stock_eq_before_mg'], e['stock_eq_after_mg'], e['delivered_fuel_gain_mg'],
                _f(e['lambda_before'], 3), _f(e['lambda_after'], 3)))
        print(plan['status'])
        print(plan['verification'], plan.get('verification_note', ''))
    else:
        for label, path in (('current', CURRENT_BIN), ('stock', STOCK_BIN)):
            print(label, json.dumps(chain(Firmware(path), args.rpm, args.gear), indent=1))


if __name__ == '__main__':
    main()
