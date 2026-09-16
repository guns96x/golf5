"""Read raw source/candidate bytes; emit evidence for the performance review.

No firmware writes. End-angle differences are arithmetic proxies, not measured
hydraulic EOI: the two maps have different input signals and runtime corrections.
"""
from pathlib import Path
import hashlib
import json
import struct

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PINS = {
    'reference': ('reference-from-hex.analysis-only.bin', 'cf891152a97fb63609b40fc590fd86f38b034119b516e936eb8c0173e2551d26'),
    'on': ('new-inputs/on/03G906021QJ.Bin', 'a1fc76a6ca961604999980733f89f13a77aa903af52b1ca43567be3dc76e5bc4'),
    'off': ('new-inputs/off/03G906021QJ (DPF EGR OFF) NoCS.Bin', '8b0f9b9a89435d72d93960bf77b3e154342979c6ed070768eb11493ca67dd134'),
    'minimal20': ('deep-audit/03G906021QJ_stage1-preserving-dpf-egr-off.review.bin', '29b5f585c78973046a9cf2161c86eda9f1541d8066e481c93ce4eda746c2e492'),
    'duration229': ('deep-audit/03G906021QJ_stage1-preserving-restore-duration.review.bin', 'c41a1b3eb0b50d8944a0932f2cf0bb904548e0b416559c0232d5f9c17c086b81'),
}


def raw_map(blob, address):
    nx, ny = struct.unpack_from('>hh', blob, address)
    assert 0 < nx <= 32 and 0 < ny <= 32
    p = address + 4
    xs = struct.unpack_from(f'>{nx}h', blob, p)
    p += nx * 2
    ys = struct.unpack_from(f'>{ny}h', blob, p)
    p += ny * 2
    values = struct.unpack_from(f'>{nx * ny}h', blob, p)
    return xs, ys, values, p


def angle_at(blob, address, rpm, iq):
    xs, ys, values, _ = raw_map(blob, address)
    # A2L EngSpeed /1, InjMassCyc /100, AngleCrS *3/128.
    return values[xs.index(rpm) * len(ys) + ys.index(int(iq * 100))] * 3 / 128


def main():
    images = {k: (ROOT / path).read_bytes() for k, (path, _) in PINS.items()}
    hashes = {k: hashlib.sha256(b).hexdigest() for k, b in images.items()}
    assert hashes == {k: h for k, (_, h) in PINS.items()}
    off, ref = images['off'], images['reference']
    minimal = {i for i, (a, b) in enumerate(zip(off, images['minimal20'])) if a != b}
    duration = {i for i, (a, b) in enumerate(zip(off, images['duration229'])) if a != b}
    thermal = {i for i in range(0x1D4EE0, 0x1D4F60) if off[i] != ref[i]}
    durset = set()
    duration_axes = []
    for addr in (0x1E5032, 0x1E52B4, 0x1E5536, 0x1E57B8):
        xs, ys, vals, start = raw_map(ref, addr)
        _, _, onvals, _ = raw_map(off, addr)
        changed_columns = sorted({i % len(ys) for i, (a, b) in enumerate(zip(vals, onvals)) if a != b})
        duration_axes.append({'address': hex(addr), 'last_rpm': xs[-1],
                              'changed_iq_columns': [ys[i] / 100 for i in changed_columns]})
        durset.update(i for i in range(start, start + 2 * len(vals)) if off[i] != ref[i])
    assert minimal == thermal | {0x1CF2F6} and len(minimal) == 20
    assert duration == minimal | durset and len(durset) == 209
    rows = []
    for rpm in (2000, 3000, 4000, 4500):
        for iq in (55, 60):
            row = {'rpm': rpm, 'same_numeric_iq_not_same_runtime_signal': iq}
            for key in ('reference', 'off', 'duration229'):
                dur = angle_at(images[key], 0x1E5032, rpm, iq)
                soi = angle_at(images[key], 0x1DA8F8, rpm, iq)
                row[key] = {'duration_deg': dur, 'soi_deg': soi,
                            'duration_minus_soi_proxy_deg': dur - soi}
            rows.append(row)
    tx, ty, rv, _ = raw_map(ref, 0x1D4EBC)
    _, _, ov, _ = raw_map(off, 0x1D4EBC)
    thermal_rows = [{'temp_c': (tx[i // len(ty)] - 2731.4) / 10,
                     'rpm': ty[i % len(ty)], 'reference_factor': a / 8192,
                     'off_factor': b / 8192, 'factor_reduction_percent': 100 * (1 - a / b)}
                    for i, (a, b) in enumerate(zip(rv, ov)) if a != b]
    assert len(thermal_rows) == 12
    result = {'source_sha256': hashes, 'minimal20_diff_exact': True,
              'duration229_diff_exact': True,
              'minimal20_preserves_all_other_bytes_including_power_maps': True,
              'duration_axes': duration_axes, 'angle_proxies': rows,
              'thermal_cells': thermal_rows,
              'maximum_factor_reduction_percent': max(x['factor_reduction_percent'] for x in thermal_rows),
              'limits': ['No hydraulic EOI or real torque/power inferred.',
                         'No checksum validation, ECU readback or vehicle test.',
                         'Unchanged bytes do not guarantee unchanged runtime outputs.']}
    (HERE / 'luna-review-evidence.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print('PASS: pinned sources; exact 20/229-byte deltas; all other bytes preserved.')
    print('Maximum thermal factor ratio reduction:', result['maximum_factor_reduction_percent'])
    for row in rows:
        print(row)


if __name__ == '__main__':
    main()
