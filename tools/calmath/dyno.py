"""Monte Carlo virtual dyno: engine torque from fixed-gear acceleration.

Uncertainty sources propagated jointly:
  - vehicle/road parameters (params.VEHICLE)
  - per-sample OBD timing (+/- latency/2)
  - derivative smoothing window
  - speed/rpm ratio (measured median) x OBD speed scale error
"""
import math
import random
import statistics

from . import physics as ph
from . import telemetry as tm
from .params import VEHICLE

# OBD rpm arrives at ~2.3 Hz with ~0.9 s gaps every 4 samples (other PIDs polled), so windows
# below 2.5 s leave too few points for a quadratic fit.
WINDOWS_S = (2.5, 3.0, 3.5, 4.0)
NOMINAL_WINDOW_S = 3.0


def time_at_rpm(seg, rpm):
    for (t0, r0, _), (t1, r1, _) in zip(seg, seg[1:]):
        if r0 <= rpm <= r1 and r1 > r0:
            return t0 + (t1 - t0) * (rpm - r0) / (r1 - r0)
    return None


def derivative_bank(seg, rpm_bins, n_jitter, rng):
    """bank[(jitter_i, window)][rpm] = (rpm_fit, drpm_dt) for every bin inside the segment."""
    bank = {}
    for j in range(n_jitter):
        offs = [rng.uniform(-u, u) for (_, _, u) in seg]
        for w in WINDOWS_S:
            row = {}
            for rb in rpm_bins:
                t = time_at_rpm(seg, rb)
                # only bins with at least half a window of data on both sides
                if t is None or t - seg[0][0] < w / 2 or seg[-1][0] - t < w / 2:
                    continue
                d = tm.local_poly_derivative(seg, t, w, offs)
                if d and d[1] > 0:
                    row[rb] = d
            bank[(j, w)] = row
    return bank


def draw(rng, spec):
    return rng.uniform(spec['min'], spec['max'])


def run(segments, rpm_bins, baro_mbar, n=10000, n_jitter=150, seed=20260916):
    """segments: list of dicts {name, seg, kmh_per_rpm, optional bins}. `bins` restricts a segment to rpm points
    where it is valid (e.g. boost established). Returns raw torque draws per segment and rpm."""
    rng = random.Random(seed)
    banks = [derivative_bank(s['seg'], s.get('bins', rpm_bins), n_jitter, rng) for s in segments]
    samples = {s['name']: {rb: [] for rb in rpm_bins} for s in segments}
    for _ in range(n):
        p = {k: draw(rng, VEHICLE[k]) for k in ('mass_kg', 'cda_m2', 'crr', 'eta_driveline',
                                                 'inertia_engine_kgm2', 'inertia_wheels_kgm2', 'wheel_radius_m')}
        p['rho_air'] = ph.air_density(baro_mbar * 100.0, draw(rng, VEHICLE['ambient_temp_k']))
        scale = draw(rng, VEHICLE['speed_scale'])
        j = rng.randrange(n_jitter)
        w = rng.choice(WINDOWS_S)
        for s, bank in zip(segments, banks):
            p['grade_rad'] = math.atan(draw(rng, VEHICLE['grade_frac']))  # independent road per pull
            v_per_rpm = s['kmh_per_rpm'] * scale / 3.6
            for rb, (r_fit, drdt) in bank[(j, w)].items():
                samples[s['name']][rb].append(ph.road_load_engine_torque_nm(rb, drdt, v_per_rpm, p))
    return samples


def pct(vals, q):
    if not vals:
        return None
    v = sorted(vals)
    k = (len(v) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def summarize(vals):
    if len(vals) < 50:
        return None
    return {'p05': pct(vals, 0.05), 'p50': pct(vals, 0.5), 'p95': pct(vals, 0.95), 'n': len(vals),
            'std': statistics.pstdev(vals)}


def nominal_torque(segment, rpm_bins, overrides=None):
    """Deterministic torque at mid-range parameters (for sensitivity tables)."""
    p = {k: (VEHICLE[k]['min'] + VEHICLE[k]['max']) / 2 for k in VEHICLE}
    p.update(overrides or {})
    q = {k: p[k] for k in ('mass_kg', 'cda_m2', 'crr', 'eta_driveline', 'inertia_engine_kgm2',
                           'inertia_wheels_kgm2', 'wheel_radius_m')}
    q['rho_air'] = ph.air_density(p.get('baro_mbar', 1005.5) * 100.0, p['ambient_temp_k'])
    q['grade_rad'] = math.atan(p['grade_frac'])
    v_per_rpm = segment['kmh_per_rpm'] * p['speed_scale'] / 3.6
    out = {}
    for rb in rpm_bins:
        t = time_at_rpm(segment['seg'], rb)
        half = NOMINAL_WINDOW_S / 2
        if t is None or t - segment['seg'][0][0] < half or segment['seg'][-1][0] - t < half:
            continue
        d = tm.local_poly_derivative(segment['seg'], t, NOMINAL_WINDOW_S)
        if d and d[1] > 0:
            out[rb] = ph.road_load_engine_torque_nm(rb, d[1], v_per_rpm, q)
    return out
