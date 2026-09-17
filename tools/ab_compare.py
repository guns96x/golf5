"""A/B comparison of VCDS measuring-block logs: current Stage 1 vs a candidate BIN.
Protocol: diagnostic-review/math-engine/AB-TEST-PROTOCOL-vNext6.1.md

  python tools/ab_compare.py --current A.CSV B.CSV --candidate C.CSV D.CSV [--gear 4] [--out diagnostic-review/ab-test]

Each CSV may contain 011+008, 011+003 or 011+003+008 (several sessions per file are fine). Pulls are detected from
rpm/boost; both directions of the protocol are pooled per firmware (median), which averages grade and wind.
Per pull: real 011 sample interval, time 2750->4000 rpm, peak boost and boost error, and per rpm bin the logged
channels plus road torque from the rpm rate (gear given by --gear, VCDS logs carry no road speed).
"""
import argparse
import datetime
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from calmath import dyno, telemetry as tm  # noqa: E402

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BINS = (2750, 3000, 3250, 3500, 3750, 4000)
BARO_MBAR = 1005.0
GEAR_KMH_PER_RPM = {3: 0.0255, 4: 0.0357, 5: 0.0465}
CHANNELS = ('boost_spec_mbar', 'map_mbar', 'n75_duty_pct', 'maf_act_mg', 'trq_request_nm', 'trq_limit_nm', 'trq_smoke_nm')
MC_DRAWS = 3000
ABORT_MAP_MBAR = 2450
WOT_SPEC_MIN_MBAR = 2100
# rpm rise rate reference at 2500 rpm from the 2026-09-16 phone pulls (vcds-analysis.json gear_reference).
# A VCDS log has no road speed, so the gear is taken from the pull's own rate at 2750 rpm; the torque change
# 2500->2750 is small next to the ~2x rate step between gears. Unclassified pulls are excluded, not guessed.
GEAR_RATE_REF_RPM_S = {3: 359.4, 4: 170.4}
GEAR_RATE_TOL = 0.35


def classify_by_rate(seg):
    t = dyno.time_at_rpm(seg, 2750)
    d = tm.local_poly_derivative(seg, t, 1.5) if t is not None else None
    if not d:
        return None, None
    g, rel = min(((g, abs(d[1] / r - 1)) for g, r in GEAR_RATE_REF_RPM_S.items()), key=lambda x: x[1])
    return (g if rel <= GEAR_RATE_TOL else None), d[1]


def pulls_from(paths, gear):
    out, skipped = [], []
    for path in paths:
        for series, meta in tm.load_vcds(path):
            dts = [b[0] - a[0] for a, b in zip(series.get('map_mbar', []), series.get('map_mbar', [])[1:])]
            interval = statistics.median(dts) if dts else None
            for seg in tm.wot_segments(series, baro=BARO_MBAR, min_span_rpm=900):
                if seg[0][1] > 2750 or seg[-1][1] < 3750:
                    continue  # protocol pull must cover 2750 -> ~4000
                name = '%s %s@%.1fs' % (os.path.basename(path), meta['label'], seg[0][0])
                g_rate, rate = classify_by_rate(seg)
                if g_rate != gear:
                    skipped.append({'pull': name, 'rate_2750_rpm_s': rate, 'rate_gear': g_rate, 'wanted_gear': gear})
                    continue
                t_lo, t_hi = dyno.time_at_rpm(seg, 2750), dyno.time_at_rpm(seg, min(4000, seg[-1][1]))
                win = [x for x in series.get('map_mbar', []) if seg[0][0] <= x[0] <= seg[-1][0]]
                spec = series.get('boost_spec_mbar', [])
                # boost error only while the ECU requests full boost: at the lift the spec collapses to ~1200 mbar
                # while MAP is still high, which is not an overshoot
                errs = [m - tm.interp_at(spec, t) for t, m, _ in win
                        if (tm.interp_at(spec, t) or 0) >= WOT_SPEC_MIN_MBAR]
                out.append({'name': name, 'series': series, 'seg': seg, 'kmh_per_rpm': GEAR_KMH_PER_RPM[gear],
                            'gear_from_rate': g_rate, 'rate_2750_rpm_s': rate,
                            'groups': meta['groups'], 'sample_interval_011_s': interval,
                            'time_2750_to_end_s': (t_hi - t_lo) if t_lo is not None and t_hi is not None else None,
                            'end_rpm': seg[-1][1], 'peak_map_mbar': max((m for _, m, _ in win), default=None),
                            'peak_boost_error_mbar': max(errs, default=None),
                            'abort_threshold_crossed': any(m >= ABORT_MAP_MBAR for _, m, _ in win)})
    return out, skipped


def per_bin(pulls):
    if not pulls:
        return {}
    for p in pulls:
        p['bins'] = [b for b in BINS if p['seg'][0][1] <= b <= p['seg'][-1][1]]
    mc = dyno.run(pulls, BINS, BARO_MBAR, n=MC_DRAWS)
    res = {}
    for b in BINS:
        rows = []
        for p in pulls:
            if b not in p['bins']:
                continue
            t = dyno.time_at_rpm(p['seg'], b)
            ch = {k: tm.interp_at(p['series'].get(k, []), t) for k in CHANNELS}
            trq = dyno.summarize(mc[p['name']][b])
            rows.append(dict(ch, road_torque_p50_nm=trq and trq['p50']))
        if rows:
            res[b] = {'n_pulls': len(rows)}
            for k in CHANNELS + ('road_torque_p50_nm',):
                vals = [r[k] for r in rows if r[k] is not None]
                res[b][k] = statistics.median(vals) if vals else None
            if res[b]['map_mbar'] is not None and res[b]['boost_spec_mbar'] is not None:
                res[b]['boost_error_mbar'] = res[b]['map_mbar'] - res[b]['boost_spec_mbar']
    return res


def summary(pulls):
    def med(k):
        v = [p[k] for p in pulls if p[k] is not None]
        return statistics.median(v) if v else None
    return {'n_pulls': len(pulls), 'median_time_2750_to_end_s': med('time_2750_to_end_s'),
            'median_peak_map_mbar': med('peak_map_mbar'), 'median_peak_boost_error_mbar': med('peak_boost_error_mbar'),
            'median_sample_interval_011_s': med('sample_interval_011_s'),
            'pulls_crossing_abort_map': sum(p['abort_threshold_crossed'] for p in pulls)}


def fmt(v, nd=0):
    return '-' if v is None else ('%.*f' % (nd, v))


def render(res):
    L = ['# A/B comparison — %s' % res['generated_utc'], '',
         'Gear assumed: %d. Pulls pooled over both directions (median).' % res['gear'], '',
         '| | current | candidate |', '|---|---|---|']
    for k, nd in (('n_pulls', 0), ('median_time_2750_to_end_s', 2), ('median_peak_map_mbar', 0),
                  ('median_peak_boost_error_mbar', 0), ('median_sample_interval_011_s', 2), ('pulls_crossing_abort_map', 0)):
        L.append('| %s | %s | %s |' % (k, fmt(res['current']['summary'][k], nd), fmt(res['candidate']['summary'][k], nd)))
    L += ['', '| rpm | road torque P50 Nm cur → cand | boost spec / actual cur → cand | N75 % cur → cand | '
              'smoke lim Nm cur → cand | MAF mg cur → cand |', '|---|---|---|---|---|---|']
    for b in BINS:
        c, d = res['current']['bins'].get(b, {}), res['candidate']['bins'].get(b, {})
        L.append('| %d | %s → %s | %s/%s → %s/%s | %s → %s | %s → %s | %s → %s |' % (
            b, fmt(c.get('road_torque_p50_nm')), fmt(d.get('road_torque_p50_nm')),
            fmt(c.get('boost_spec_mbar')), fmt(c.get('map_mbar')), fmt(d.get('boost_spec_mbar')), fmt(d.get('map_mbar')),
            fmt(c.get('n75_duty_pct'), 1), fmt(d.get('n75_duty_pct'), 1), fmt(c.get('trq_smoke_nm')), fmt(d.get('trq_smoke_nm')),
            fmt(c.get('maf_act_mg')), fmt(d.get('maf_act_mg'))))
    L += ['', 'Pulls:', '']
    for side in ('current', 'candidate'):
        for p in res[side]['pulls']:
            L.append('- %s: %s, groups %s, 011 interval %s s, 2750->%s rpm in %s s, peak MAP %s, peak error %s%s' % (
                side, p['name'], '+'.join(p['groups']), fmt(p['sample_interval_011_s'], 2), fmt(p['end_rpm']),
                fmt(p['time_2750_to_end_s'], 2), fmt(p['peak_map_mbar']), fmt(p['peak_boost_error_mbar']),
                ' **ABORT THRESHOLD CROSSED**' if p['abort_threshold_crossed'] else ''))
        for sk in res[side]['skipped_pulls']:
            L.append('- %s: SKIPPED %s (rate %s rpm/s -> gear %s, wanted %s)' % (
                side, sk['pull'], fmt(sk['rate_2750_rpm_s']), sk['rate_gear'], sk['wanted_gear']))
    return '\n'.join(L) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--current', nargs='+', required=True)
    ap.add_argument('--candidate', nargs='+', required=True)
    ap.add_argument('--gear', type=int, default=4, choices=sorted(GEAR_RATE_REF_RPM_S),
                    help='only pulls whose rpm rate matches this gear are compared (3 or 4)')
    ap.add_argument('--out', default='diagnostic-review/ab-test')
    a = ap.parse_args()
    res = {'generated_utc': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'gear': a.gear}
    for side, paths in (('current', a.current), ('candidate', a.candidate)):
        pulls, skipped = pulls_from(paths, a.gear)
        res[side] = {'files': paths, 'summary': summary(pulls), 'bins': per_bin(pulls), 'skipped_pulls': skipped,
                     'pulls': [{k: v for k, v in p.items() if k not in ('series', 'seg', 'bins')} for p in pulls]}
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, 'ab-compare.json'), 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    md = render(res)
    with open(os.path.join(a.out, 'ab-compare.md'), 'w', encoding='utf-8') as f:
        f.write(md)
    print(md)


if __name__ == '__main__':
    main()
