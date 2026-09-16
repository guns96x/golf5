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
    lo, hi = int(sel // 1), min(int(sel // 1) + 1, 6)
    d_lo = fw['InjVlv_phiInjMI1_MAP%d' % lo].lookup(rpm, q)
    d_hi = fw['InjVlv_phiInjMI1_MAP%d' % hi].lookup(rpm, q)
    dur = d_lo + (d_hi - d_lo) * (sel - lo)
    return {'soi_deg_btdc_hyp': soi, 'duration_deg_hyp': dur, 'duration_ms_hyp': ph.injection_ms(dur, rpm),
            'electrical_command_end_proxy_deg_atdc': dur - soi}


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
    else:
        for label, path in (('current', CURRENT_BIN), ('stock', STOCK_BIN)):
            print(label, json.dumps(chain(Firmware(path), args.rpm, args.gear), indent=1))


if __name__ == '__main__':
    main()
