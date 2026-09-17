"""Evidence-status rules that prevent single-path calibration conclusions."""

_EVIDENCE_STATUSES = {'MEASURED', 'CALCULATED', 'CROSS_VALIDATED'}
_UNKNOWN_STATUSES = {'UNKNOWN', 'HOLD'}


def assess_hypothesis(evidence):
    """Assess a hypothesis from independent evidence families.

    Cross-validation requires support from at least two distinct evidence
    families. A missing critical family forces HOLD. Direct support and
    contradiction from known evidence yields CONFLICT.
    """
    support = set()
    contradict = set()
    missing_critical = set()

    for item in evidence:
        family = item['family']
        status = item.get('status', 'UNKNOWN')
        direction = item.get('direction', 'unknown')
        critical = bool(item.get('critical', False))

        if critical and (status in _UNKNOWN_STATUSES or direction == 'unknown'):
            missing_critical.add(family)

        if status not in _EVIDENCE_STATUSES:
            continue
        if direction == 'supports':
            support.add(family)
        elif direction == 'contradicts':
            contradict.add(family)

    if support and contradict:
        status = 'CONFLICT'
    elif missing_critical:
        status = 'HOLD'
    elif len(support) >= 2:
        status = 'CROSS_VALIDATED'
    elif len(support) == 1:
        status = 'PROVISIONAL'
    else:
        status = 'UNKNOWN'

    return {
        'status': status,
        'independent_support_families': len(support),
        'support_families': sorted(support),
        'contradict_families': sorted(contradict),
        'missing_critical_families': sorted(missing_critical),
        'evidence_count': len(evidence),
    }
