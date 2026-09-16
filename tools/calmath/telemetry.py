"""OBD telemetry: per-sample timestamps, WOT segmentation, fixed-gear speed/rpm ratio.

Rows of the phone logger's pair CSV are NOT synchronous (see *_age_ms). The engine therefore works
from individual PID responses: each response is one measurement with its own time.
Sample time estimate: response timestamp - latency/2, uncertainty +/- latency/2.
"""
import csv
import glob
import os
import statistics

PID = {'010C': 'rpm', '010B': 'map_mbar', '0110': 'maf_g_s', '010D': 'speed_kmh',
       '0104': 'load_pct', '010F': 'iat_c', '0105': 'coolant_c'}


def decode_obd(raw):
    """Decode a mode-01 response hex string (SAE J1979 scaling)."""
    raw = raw.strip().strip('"')
    if len(raw) < 6 or not raw.startswith('41'):
        return None
    pid, data = '01' + raw[2:4], bytes.fromhex(raw[4:])
    if pid == '010C' and len(data) >= 2:
        return pid, (256 * data[0] + data[1]) / 4.0
    if pid == '010B':
        return pid, data[0] * 10.0  # kPa -> mbar
    if pid == '0110' and len(data) >= 2:
        return pid, (256 * data[0] + data[1]) / 100.0
    if pid == '010D':
        return pid, float(data[0])
    if pid == '0104':
        return pid, data[0] * 100.0 / 255.0
    if pid in ('010F', '0105'):
        return pid, data[0] - 40.0
    return None


def load_events(path):
    """Returns (series, meta). series[channel] = list of (t_s, value, t_unc_s), time relative to first sample."""
    name = os.path.basename(path)
    samples = []
    baro = None
    with open(path, encoding='utf-8', errors='replace') as f:
        rows = list(csv.DictReader(f))
    if name.startswith('Event_RAW'):
        for r in rows:
            if r['pid'] == 'BARO':
                baro = float(r['value'])
            if r['status'] != 'VALID' or r['pid'] not in PID:
                continue
            lat = float(r['latency_ms'] or 0)
            samples.append((PID[r['pid']], int(r['timestamp_utc_ms']) - lat / 2, float(r['value']), lat / 2))
    elif name.startswith('Turbo_Fast_Log'):
        for r in rows:
            dec = decode_obd(r['raw_response'])
            if not dec:
                continue
            baro = float(r['baro_mbar'])
            lat = float(r['latency_ms'] or 0)
            samples.append((PID[dec[0]], int(r['timestamp_ms']) - lat / 2, dec[1], lat / 2))
    else:
        raise ValueError('unsupported log format: ' + name)
    if not samples:
        return {}, {'file': path, 'baro_mbar': baro}
    t0 = min(s[1] for s in samples)
    series = {}
    for ch, t, v, u in sorted(samples, key=lambda s: s[1]):
        series.setdefault(ch, []).append(((t - t0) / 1000.0, v, u / 1000.0))
    return series, {'file': path, 'baro_mbar': baro, 't0_utc_ms': t0}


def interp_at(series, t):
    if not series or t < series[0][0] or t > series[-1][0]:
        return None
    for (t0, v0, _), (t1, v1, _) in zip(series, series[1:]):
        if t0 <= t <= t1:
            return v0 if t1 == t0 else v0 + (v1 - v0) * (t - t0) / (t1 - t0)
    return series[-1][1]


def wot_segments(series, min_span_rpm=700, min_duration_s=4.0, max_drop_rpm=60, min_map_boost_mbar=600, baro=1013.0):
    """Contiguous rpm rises under boost. A segment ends at an rpm drop > max_drop_rpm (gear change / lift)
    or when manifold pressure falls below baro + min_map_boost_mbar."""
    rpm = series.get('rpm', [])
    mp = series.get('map_mbar', [])
    segs, cur = [], []
    for s in rpm:
        m = interp_at(mp, s[0])
        boosted = m is not None and m >= baro + min_map_boost_mbar
        if cur and (s[1] < cur[-1][1] - max_drop_rpm or not boosted):
            segs.append(cur)
            cur = []
        if boosted:
            if cur and s[1] < cur[-1][1]:
                continue  # small dip inside tolerance: skip sample, keep segment
            cur.append(s)
    if cur:
        segs.append(cur)
    out = []
    for seg in segs:
        if len(seg) >= 6 and seg[-1][1] - seg[0][1] >= min_span_rpm and seg[-1][0] - seg[0][0] >= min_duration_s:
            out.append(seg)
    return out


def gear_ratio(series, seg, max_speed_rpm_gap_s=0.35):
    """km/h per rpm from speed samples inside the segment, each paired with rpm interpolated at the speed
    sample's own time. Returns median, MAD, n, and the pairs."""
    t_lo, t_hi = seg[0][0], seg[-1][0]
    pairs = []
    for t, v, u in series.get('speed_kmh', []):
        if t_lo <= t <= t_hi and v > 10:
            r = interp_at(seg, t)
            if r:
                pairs.append((t, v, r, v / r))
    if not pairs:
        return None
    ratios = [p[3] for p in pairs]
    med = statistics.median(ratios)
    mad = statistics.median([abs(x - med) for x in ratios])
    return {'kmh_per_rpm': med, 'mad': mad, 'n': len(pairs), 'pairs': pairs}


# Gear clusters measured on this car (fresh speed / rpm, 2026-09-16 logs). Tolerance +/-6 %.
KNOWN_GEARS = {3: 0.0250, 4: 0.0351}


def classify_gear(kmh_per_rpm):
    for g, k in KNOWN_GEARS.items():
        if abs(kmh_per_rpm - k) / k <= 0.06:
            return g
    return None


def local_poly_derivative(seg, t, window_s, t_offsets=None):
    """Weighted local quadratic least squares around t (tricube weights). Returns (rpm_fit, drpm_dt) or None.
    t_offsets: optional per-sample time perturbations (timing uncertainty draw)."""
    pts = []
    for i, (ts, v, _) in enumerate(seg):
        tt = ts + (t_offsets[i] if t_offsets else 0.0)
        d = (tt - t) / (window_s / 2.0)
        if abs(d) < 1.0:
            pts.append((tt - t, v, (1 - abs(d) ** 3) ** 3))
    if len(pts) < 4:
        return None
    # normal equations for v = c0 + c1*x + c2*x^2
    s = [[0.0] * 3 for _ in range(3)]
    b = [0.0] * 3
    for x, v, w in pts:
        xp = [1.0, x, x * x]
        for i in range(3):
            b[i] += w * xp[i] * v
            for j in range(3):
                s[i][j] += w * xp[i] * xp[j]
    c = _solve3(s, b)
    return None if c is None else (c[0], c[1])


def _solve3(a, b):
    m = [row[:] + [bb] for row, bb in zip(a, b)]
    for col in range(3):
        piv = max(range(col, 3), key=lambda r: abs(m[r][col]))
        if abs(m[piv][col]) < 1e-12:
            return None
        m[col], m[piv] = m[piv], m[col]
        for r in range(3):
            if r != col:
                f = m[r][col] / m[col][col]
                for k in range(col, 4):
                    m[r][k] -= f * m[col][k]
    return [m[i][3] / m[i][i] for i in range(3)]


def all_logs(pattern_list=('logs/20260916/Event_RAW_*.csv', 'logs/VCDS_Logs/Turbo_Fast_Log_*.csv')):
    files = []
    for p in pattern_list:
        files += sorted(glob.glob(p))
    return files
