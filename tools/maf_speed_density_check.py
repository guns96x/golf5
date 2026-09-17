"""MAF vs speed-density cross-check from a VCDS Mobile Event_RAW drive log.

  python tools/maf_speed_density_check.py <Event_RAW_*.csv>

Every MAF sample (PID 0110) is paired with RPM and MAP linearly interpolated at the MAF
timestamp (mono_ns) and the nearest IAT (010F) / speed (010D) / load (0104) sample.
implied VE = MAF mg/stroke / (rho(MAP, IAT) x Vcyl). With EGR off the MAF sees all intake air,
so at the same rpm VE should not depend on flow. If WOT (high flow) VE sits clearly below cruise
(low flow) VE at the same rpm, the MAF under-reads at high flow.
"""
import bisect
import csv
import statistics
import sys
from collections import defaultdict

sys.path.insert(0, __file__.rsplit('tools', 1)[0] + 'tools')
from calmath import physics as ph  # noqa: E402
from calmath.params import ENGINE  # noqa: E402

VCYL = ENGINE['displacement_m3']['value'] / ENGINE['n_cyl']['value']
MAX_INTERP_GAP_NS = 1_500_000_000
MAX_NEAREST_NS = {'010F': 6e9, '010D': 3e9, '0104': 3e9}
GEAR_KMH_PER_1000 = {3: 26.0, 4: 35.2, 5: 44.0}  # 4th measured 2026-09-16 (34.5-35.7); 3rd/5th approximate


def load(path):
    series = defaultdict(list)
    for row in csv.DictReader(open(path, encoding='utf-8')):
        if row['status'] != 'VALID' or not row['value']:
            continue
        series[row['pid']].append((int(row['mono_ns']), float(row['value'])))
    for v in series.values():
        v.sort()
    return series


def interp(s, t):
    ts = [x[0] for x in s]
    i = bisect.bisect_left(ts, t)
    if i == 0 or i == len(s):
        return None
    (t0, v0), (t1, v1) = s[i - 1], s[i]
    if t1 - t0 > MAX_INTERP_GAP_NS:
        return None
    return v0 + (v1 - v0) * (t - t0) / (t1 - t0)


def nearest(s, t, max_ns):
    ts = [x[0] for x in s]
    i = bisect.bisect_left(ts, t)
    best = min((c for c in (i - 1, i) if 0 <= c < len(s)), key=lambda c: abs(ts[c] - t), default=None)
    return s[best][1] if best is not None and abs(ts[best] - t) <= max_ns else None


def classify_gear(kmh, rpm):
    if kmh is None or kmh < 20 or rpm < 1000:
        return None
    r = kmh / rpm * 1000
    g = min(GEAR_KMH_PER_1000, key=lambda k: abs(GEAR_KMH_PER_1000[k] - r))
    return g if abs(GEAR_KMH_PER_1000[g] - r) / GEAR_KMH_PER_1000[g] < 0.06 else None


def samples(series):
    out = []
    for t, maf_gs in series['0110']:
        rpm, map_mbar = interp(series['010C'], t), interp(series['010B'], t)
        iat = nearest(series['010F'], t, MAX_NEAREST_NS['010F'])
        if None in (rpm, map_mbar, iat) or rpm < 900:
            continue
        kmh = nearest(series['010D'], t, MAX_NEAREST_NS['010D'])
        load_pct = nearest(series['0104'], t, MAX_NEAREST_NS['0104'])
        maf_mg = maf_gs * 1000.0 / (rpm / 30.0)  # 4 cyl, 4-stroke: rpm/30 intake strokes per second
        sd_mg = ph.air_density(map_mbar * 100.0, iat + 273.15) * VCYL * 1e6
        out.append({'t': t, 'rpm': rpm, 'map': map_mbar, 'iat': iat, 'maf_gs': maf_gs, 'maf_mg': maf_mg,
                    've': maf_mg / sd_mg, 'kmh': kmh, 'load': load_pct, 'gear': classify_gear(kmh, rpm)})
    return out


def main(path):
    s = samples(load(path))
    print('MAF samples usable: %d' % len(s))
    bins = defaultdict(lambda: defaultdict(list))
    for x in s:
        b = int(x['rpm'] // 250 * 250)
        cls = 'WOT' if (x['load'] or 0) >= 90 and x['map'] >= 1900 else ('cruise' if (x['load'] or 100) <= 60 else None)
        if cls:
            bins[b][cls].append(x)
    print('\nrpm bin | cruise: n  VE med  MAP  IAT | WOT: n  VE med  MAP  IAT  MAF mg | WOT/cruise')
    for b in sorted(bins):
        c, w = bins[b]['cruise'], bins[b]['WOT']
        fc = ('%3d  %.3f %5.0f %3.0f' % (len(c), statistics.median(v['ve'] for v in c),
                                           statistics.median(v['map'] for v in c), statistics.median(v['iat'] for v in c))) if c else '  -' + ' ' * 17
        fw = ('%3d  %.3f %5.0f %3.0f %5.0f' % (len(w), statistics.median(v['ve'] for v in w), statistics.median(v['map'] for v in w),
                                                statistics.median(v['iat'] for v in w), statistics.median(v['maf_mg'] for v in w))) if w else '  -'
        ratio = ('%.3f' % (statistics.median(v['ve'] for v in w) / statistics.median(v['ve'] for v in c))) if c and w else ''
        print('%5d   | %s | %s | %s' % (b, fc, fw, ratio))
    return s


if __name__ == '__main__':
    main(sys.argv[1])
