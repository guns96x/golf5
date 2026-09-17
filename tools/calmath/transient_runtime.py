"""Runtime analysis for active driveline damping and dynamic smoke."""

from .transient_torque import torque_delta, iq_delta, integrated_deficit, intervention_status

_REQUIRED = ('t_s', 'rpm', 'torque_before_asd_nm', 'torque_after_asd_nm')


def _missing(samples):
    missing = []
    for key in _REQUIRED:
        if not samples or any(s.get(key) is None for s in samples):
            missing.append(key)
    return missing


def _time_to_fraction(samples, fraction=0.90):
    if not samples:
        return None
    t0 = float(samples[0]['t_s'])
    for s in samples:
        before = float(s['torque_before_asd_nm'])
        after = float(s['torque_after_asd_nm'])
        if before <= 0:
            continue
        if after / before >= fraction:
            return float(s['t_s']) - t0
    return None


def analyze_runtime(samples, fmtc_map, uncertainty_nm, fmtc_policy='clamp'):
    """Quantify ASD torque/IQ intervention while keeping dynamic smoke separate."""
    missing = _missing(samples)
    if missing:
        return {
            'status': 'HOLD',
            'missing_required_channels': missing,
            'samples': [],
            'peak_asd_deficit_nm': None,
            'integrated_asd_deficit_nm_s': None,
            'time_to_90pct_post_asd_torque_s': None,
            'peak_dynamic_smoke_mg': None,
        }

    rows = []
    deficits = []
    dyn_smoke = []
    for s in samples:
        delta_nm = torque_delta(s['torque_before_asd_nm'], s['torque_after_asd_nm'])
        q = iq_delta(fmtc_map, s['rpm'], s['torque_before_asd_nm'], s['torque_after_asd_nm'], fmtc_policy)
        ds = s.get('dynamic_smoke_mg')
        if ds is not None:
            dyn_smoke.append(float(ds))
        row = dict(s)
        row.update({
            'delta_t_asd_nm': delta_nm,
            'q_before_asd_mg': q['q_before_mg'],
            'q_after_asd_mg': q['q_after_mg'],
            'delta_q_asd_mg': q['delta_q_mg'],
            'fmtc_policy': fmtc_policy,
        })
        rows.append(row)
        deficits.append({'t_s': float(s['t_s']), 'delta_nm': delta_nm})

    integ = integrated_deficit(deficits)
    peak = integ['peak_deficit_nm']
    return {
        'status': intervention_status(peak, uncertainty_nm),
        'missing_required_channels': [],
        'samples': rows,
        'peak_asd_deficit_nm': peak,
        'integrated_asd_deficit_nm_s': integ['nm_s'],
        'time_to_90pct_post_asd_torque_s': _time_to_fraction(rows, 0.90),
        'peak_dynamic_smoke_mg': max(dyn_smoke) if dyn_smoke else None,
        'uncertainty_nm': float(uncertainty_nm),
    }
