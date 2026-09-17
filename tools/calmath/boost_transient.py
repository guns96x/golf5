"""Synchronized boost-request/actual transient metrics."""

import math

_REQUIRED = ('t_s', 'boost_requested_mbar', 'map_actual_mbar')


def _missing(samples):
    missing = []
    for key in _REQUIRED:
        if not samples or any(s.get(key) is None for s in samples):
            missing.append(key)
    return missing


def _step_index(samples):
    if len(samples) < 2:
        return 0
    changes = [float(samples[i]['boost_requested_mbar']) - float(samples[i - 1]['boost_requested_mbar'])
               for i in range(1, len(samples))]
    return max(range(1, len(samples)), key=lambda i: changes[i - 1])


def analyze_boost_transient(samples, saturation_low_pct=5.0, saturation_high_pct=95.0):
    """Calculate dynamic boost-control metrics from synchronized runtime channels.

    Static calibration values are intentionally not accepted as a substitute for
    ``boost_requested_mbar``. Missing runtime request therefore returns HOLD.
    """
    missing = _missing(samples)
    if missing:
        return {'status': 'HOLD', 'missing_required_channels': missing}

    rows = sorted(samples, key=lambda s: float(s['t_s']))
    if rows != list(samples):
        raise ValueError('sample timestamps must be strictly increasing')
    times = [float(s['t_s']) for s in rows]
    if any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError('sample timestamps must be strictly increasing')

    req = [float(s['boost_requested_mbar']) for s in rows]
    act = [float(s['map_actual_mbar']) for s in rows]
    err = [r - a for r, a in zip(req, act)]

    area = 0.0
    dmap = []
    for i in range(1, len(rows)):
        dt = times[i] - times[i - 1]
        area += 0.5 * (err[i - 1] + err[i]) * dt
        dmap.append((act[i] - act[i - 1]) / dt)

    step_i = _step_index(rows)
    t90 = None
    if len(rows) >= 2 and step_i > 0:
        baseline = act[step_i - 1]
        target = req[step_i]
        if target > baseline:
            threshold = baseline + 0.90 * (target - baseline)
            for i in range(step_i, len(rows)):
                if act[i] >= threshold:
                    t90 = times[i] - times[step_i]
                    break

    duty = [float(s['n75_pct']) for s in rows if s.get('n75_pct') is not None]
    sat = None
    if duty:
        sat = sum(x <= saturation_low_pct or x >= saturation_high_pct for x in duty) / len(duty)

    return {
        'status': 'CALCULATED',
        'missing_required_channels': [],
        'peak_positive_error_mbar': max(err),
        'peak_negative_error_mbar': min(err),
        'rms_error_mbar': math.sqrt(sum(e * e for e in err) / len(err)),
        'signed_error_area_mbar_s': area,
        'peak_dmap_dt_mbar_s': max(dmap) if dmap else None,
        'time_to_90pct_step_s': t90,
        'actuator_saturation_fraction': sat,
        'step_index': step_i,
    }
