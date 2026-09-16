"""Pure math for EDC16 injection-duration map selection and inversion."""

import bisect
import math


def selector_components(selector, map_count):
    """Return lower map index, upper map index, and upper-map weight.

    Integer selectors resolve to one map. Values outside available maps clamp to
    the nearest valid map; the function does not invent non-existent maps.
    """
    if map_count < 1:
        raise ValueError('map_count must be >= 1')
    s = max(0.0, min(float(selector), float(map_count - 1)))
    nearest = round(s)
    if abs(s - nearest) <= 1e-12:
        i = int(nearest)
        return i, i, 0.0
    lo = int(math.floor(s))
    hi = min(lo + 1, map_count - 1)
    return lo, hi, s - lo


def blend_duration(maps, rpm, q_mg, selector, y_policy='clamp'):
    """Blend duration between the two maps selected by the selector."""
    lo, hi, w = selector_components(selector, len(maps))
    d0 = float(maps[lo].lookup(float(rpm), float(q_mg), y_policy))
    if lo == hi:
        return d0
    d1 = float(maps[hi].lookup(float(rpm), float(q_mg), y_policy))
    return d0 + (d1 - d0) * w


def _active_q_nodes(maps, selector):
    lo, hi, _ = selector_components(selector, len(maps))
    nodes = set(float(x) for x in maps[lo].y)
    if hi != lo:
        nodes.update(float(x) for x in maps[hi].y)
    return sorted(nodes)


def invert_blended_duration(maps, rpm, duration_deg, selector):
    """Invert stock blended duration to an OEM-duration-equivalent IQ.

    No extrapolation is performed. When the target duration lies outside the
    represented blended surface the nearest q-axis bound is returned with an
    explicit status.
    """
    q_nodes = _active_q_nodes(maps, selector)
    if not q_nodes:
        raise ValueError('active duration maps have no q-axis nodes')
    durations = [blend_duration(maps, rpm, q, selector, 'clamp') for q in q_nodes]
    if any(b < a - 1e-12 for a, b in zip(durations, durations[1:])):
        raise ValueError('blended duration surface is not monotone in IQ')

    target = float(duration_deg)
    if target < durations[0]:
        return q_nodes[0], 'BELOW_AXIS'
    if target > durations[-1]:
        return q_nodes[-1], 'ABOVE_AXIS'
    if abs(target - durations[0]) <= 1e-12:
        return q_nodes[0], 'IN_RANGE'
    if abs(target - durations[-1]) <= 1e-12:
        return q_nodes[-1], 'IN_RANGE'

    j = bisect.bisect_right(durations, target) - 1
    j = max(0, min(j, len(q_nodes) - 2))
    d0, d1 = durations[j], durations[j + 1]
    q0, q1 = q_nodes[j], q_nodes[j + 1]
    if abs(d1 - d0) <= 1e-12:
        return q0, 'IN_RANGE'
    q = q0 + (q1 - q0) * (target - d0) / (d1 - d0)
    return q, 'IN_RANGE'
