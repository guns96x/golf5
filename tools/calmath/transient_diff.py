"""Read-only helpers for comparing decoded transient calibration objects."""


def characteristic_snapshot(characteristic):
    kind = characteristic.kind
    if kind == 'MAP':
        values = [float(v) for row in characteristic.grid for v in row]
        shape = [len(characteristic.x), len(characteristic.y)]
        axes = [list(map(float, characteristic.x)), list(map(float, characteristic.y))]
    elif kind == 'CURVE':
        values = list(map(float, characteristic.values))
        shape = [len(characteristic.x)]
        axes = [list(map(float, characteristic.x))]
    else:
        values = [float(characteristic.value)]
        shape = [1]
        axes = []
    return {
        'name': characteristic.name,
        'kind': kind,
        'address': int(characteristic.address),
        'unit': characteristic.unit,
        'shape': shape,
        'axes': axes,
        'values': values,
    }


def compare_snapshots(base, other, tolerance=1e-12):
    for key in ('kind', 'shape', 'unit'):
        if base.get(key) != other.get(key):
            raise ValueError('snapshot structure mismatch for %s' % key)
    if base.get('axes') != other.get('axes'):
        raise ValueError('snapshot axis mismatch')
    a = base['values']
    b = other['values']
    if len(a) != len(b):
        raise ValueError('snapshot value-count mismatch')
    deltas = [float(y) - float(x) for x, y in zip(a, b)]
    changed = [d for d in deltas if abs(d) > tolerance]
    return {
        'identical': not changed,
        'changed_points': len(changed),
        'total_points': len(deltas),
        'min_delta': min(deltas) if deltas else 0.0,
        'max_delta': max(deltas) if deltas else 0.0,
        'max_abs_delta': max((abs(d) for d in deltas), default=0.0),
    }
