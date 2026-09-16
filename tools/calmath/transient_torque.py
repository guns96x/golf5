"""Pure math helpers for transient torque interventions.

This module is deliberately independent from BIN/A2L parsing. It accepts an
FMTC-like object for torque->IQ conversion and produces explicit, auditable
numeric deltas.
"""


def torque_delta(before_nm, after_nm):
    """Return signed torque removed by an intervention.

    Positive means torque was removed, negative means torque was added.
    """
    return float(before_nm) - float(after_nm)


def iq_delta(fmtc_map, rpm, before_nm, after_nm, policy='clamp'):
    """Convert a before/after torque intervention to an IQ delta through FMTC."""
    q_before = float(fmtc_map.lookup(float(rpm), float(before_nm), policy))
    q_after = float(fmtc_map.lookup(float(rpm), float(after_nm), policy))
    return {
        'rpm': float(rpm),
        'before_nm': float(before_nm),
        'after_nm': float(after_nm),
        'q_before_mg': q_before,
        'q_after_mg': q_after,
        'delta_q_mg': q_before - q_after,
        'fmtc_policy': policy,
    }


def integrated_deficit(samples):
    """Integrate signed torque deficit over time using the trapezoid rule.

    Samples are mappings containing ``t_s`` and ``delta_nm``. Timestamps must
    be strictly increasing. The integral is signed: positive values represent
    net torque removed over the interval.
    """
    if not samples:
        return {'nm_s': 0.0, 'peak_deficit_nm': 0.0, 'duration_s': 0.0}

    times = [float(s['t_s']) for s in samples]
    deltas = [float(s['delta_nm']) for s in samples]
    for a, b in zip(times, times[1:]):
        if b <= a:
            raise ValueError('sample timestamps must be strictly increasing')

    area = 0.0
    for t0, t1, d0, d1 in zip(times, times[1:], deltas, deltas[1:]):
        area += (d0 + d1) * 0.5 * (t1 - t0)

    return {
        'nm_s': area,
        'peak_deficit_nm': max(deltas),
        'duration_s': times[-1] - times[0],
    }


def intervention_status(delta_nm, uncertainty_nm):
    """Classify whether an intervention exceeds the stated uncertainty."""
    delta = abs(float(delta_nm))
    uncertainty = float(uncertainty_nm)
    if uncertainty < 0:
        raise ValueError('uncertainty_nm must be non-negative')
    return 'CALCULATED' if delta > uncertainty else 'WITHIN_UNCERTAINTY'
