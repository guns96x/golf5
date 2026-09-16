"""Read-only firmware audit; writes JSON analysis, never firmware images."""
from pathlib import Path
import json
import re
import struct
import hashlib

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent


def blocks(text, kind):
    return {m[1]: m[2] for m in re.finditer(
        r'/begin ' + kind + r'\s+(\S+)\s+(.*?)/end ' + kind, text, re.S)}


def ranges(indices):
    result = []
    for i in sorted(indices):
        if result and result[-1][1] == i:
            result[-1][1] = i + 1
        else:
            result.append([i, i + 1])
    return result


def main():
    text = next((ROOT / 'definitions').rglob('*.a2l')).read_text(encoding='latin1')
    chars = blocks(text, 'CHARACTERISTIC')
    methods = blocks(text, 'COMPU_METHOD')
    layouts = blocks(text, 'RECORD_LAYOUT')
    idx = json.loads((ROOT / 'a2l-characteristics-index.json').read_text())
    images = {k: p.read_bytes() for k, p in {
        'reference': ROOT / 'reference-from-hex.analysis-only.bin',
        'on': ROOT / 'new-inputs/on/03G906021QJ.Bin',
        'off': ROOT / 'new-inputs/off/03G906021QJ (DPF EGR OFF) NoCS.Bin',
    }.items()}
    sizes = {'SBYTE': ('b', 1), 'UBYTE': ('B', 1), 'SWORD': ('h', 2),
             'UWORD': ('H', 2), 'SLONG': ('i', 4), 'ULONG': ('I', 4)}

    def physical(raw, method):
        body = methods.get(method, '')
        m = re.search(r'COEFFS\s+([\d.eE+\-\s]+)', body)
        if not m:
            return None
        coeff = [float(x) for x in m[1].split()]
        if len(coeff) != 6:
            return None
        a, b, c, d, e, f = coeff
        # A2L RAT_FUNC maps physical -> internal; invert linear subset only.
        if a == d == e == 0 and b and f:
            return [round((v * f - c) / b, 8) for v in raw]
        return None

    def decode(c, image, addr=None):
        addr = c['address'] if addr is None else addr
        layout = layouts[c['layout']]
        fields = []
        for m in re.finditer(r'(NO_AXIS_PTS_[XYZ]|AXIS_PTS_[XYZ]|FNC_VALUES)\s+(\d+)\s+(\w+)([^\n]*)', layout):
            fields.append((int(m[2]), m[1], m[3], m[4].strip()))
        dims, axes, vals = {}, [], None
        pos = addr
        value_start = None
        for _, kind, typ, suffix in sorted(fields):
            if typ not in sizes:
                raise ValueError('unsupported type ' + typ)
            fmt, size = sizes[typ]
            if kind.startswith('NO_AXIS'):
                n = struct.unpack_from('>' + fmt, image, pos)[0]
                if not 0 < n <= 128:
                    raise ValueError('invalid dimension ' + str(n))
                dims[kind[-1]] = n
                pos += size
            elif kind.startswith('AXIS_PTS'):
                n = dims[kind[-1]]
                axes.append(list(struct.unpack_from('>' + str(n) + fmt, image, pos)))
                pos += n * size
            else:
                if c['kind'] == 'VAL_BLK':
                    raise ValueError('VAL_BLK unsupported')
                n = 1
                for d in dims.values():
                    n *= d
                vals = list(struct.unpack_from('>' + str(n) + fmt, image, pos))
                value_start = pos
                pos += n * size
        if vals is None or pos - addr > c['size']:
            raise ValueError('extent/layout unsupported')
        ax_meta = []
        for j, m in enumerate(re.finditer(r'/begin AXIS_DESCR\s+(\S+)\s+(\S+)\s+(\S+)\s+(\d+)', chars[c['name']])):
            if j >= len(axes) or len(axes[j]) > int(m[4]):
                raise ValueError('axis exceeds A2L max')
            ax_meta.append({'input': m[2], 'conversion': m[3], 'raw': axes[j],
                            'physical': physical(axes[j], m[3])})
        return {'address': hex(addr), 'size': pos - addr,
                'values_address': hex(value_start), 'end': hex(pos),
                'dims': list(dims.values()), 'axes': ax_meta,
                'raw': vals, 'physical': physical(vals, c['conversion']),
                'value_order': next((s for _, k, _, s in fields if k == 'FNC_VALUES'), '')}

    ref, on = images['reference'], images['on']
    delta = {i for i in range(0x180000, len(ref)) if ref[i] != on[i]}
    covered = set()
    decoded, unsupported = [], []
    for c in idx:
        a = c['address']
        if a < 0x180000 or a + c['size'] > len(ref):
            continue
        if ref[a:a+c['size']] == on[a:a+c['size']]:
            continue
        try:
            ds = {k: decode(c, v) for k, v in images.items()}
        except (ValueError, KeyError, struct.error) as e:
            unsupported.append({'name': c['name'], 'error': str(e)})
            continue
        end = max(int(d['end'], 16) for d in ds.values())
        active_delta = delta.intersection(range(a, end))
        if not active_delta:
            continue
        covered.update(active_delta)
        original = ref[a:int(ds['reference']['end'], 16)]
        copies = []
        p = 0x180000
        while True:
            p = ref.find(original, p)
            if p < 0:
                break
            cp_end = p + len(original)
            changed = delta.intersection(range(p, cp_end))
            copied_edits = on[p:cp_end] == on[a:a+len(original)]
            if p != a:
                copies.append({'address': hex(p), 'changed_bytes': len(changed),
                               'same_stage1_bytes': copied_edits})
            # Identity is a byte match, not proof of runtime role/coding selector.
            if copied_edits:
                covered.update(changed)
            p += 1
        changed_values = []
        for i, (r, s) in enumerate(zip(ds['reference']['raw'], ds['on']['raw'])):
            if r != s:
                rp, sp = ds['reference']['physical'], ds['on']['physical']
                changed_values.append({'flat_index': i, 'raw_ref': r, 'raw_on': s,
                                       'ref': rp[i] if rp else None, 'on': sp[i] if sp else None})
        decoded.append({'name': c['name'], 'description': c['description'],
                        'a2l_line': c['a2l_line'], 'conversion': c['conversion'],
                        'active_changed_bytes': len(active_delta), 'tables': ds,
                        'changed_values': changed_values, 'identical_reference_copies': copies})
    # Identify structurally matching alternate calibration tables. These do NOT
    # inherit confirmed symbol names or runtime selection from the A2L.
    direct_and_exact_count = len(covered)
    structural = []
    candidates = [
        ('AccPed_trqEng0_MAP', a, 'same dimensions; RPM/pedal-like axes differ')
        for a in [0x186668, 0x1867BE, 0x186914, 0x186A6A, 0x186BC0,
                  0x186D16, 0x186E6C, 0x186FC2, 0x193DB4, 0x193F0A,
                  0x194060, 0x1941B6, 0x19430C, 0x194462, 0x1945B8, 0x19470E]
    ] + [
        ('InjCrv_phiBasGear12_MAP', a, 'header and axes identical; data differ')
        for a in [0x18CA88, 0x18CC88, 0x18CE88, 0x198520, 0x198720, 0x198920]
    ] + [('PCR_pBDesBas_MAP', 0x19132E, 'header and axes identical; data differ')]
    by_name = {c['name']: c for c in idx}
    for proxy, a, basis in candidates:
        c = by_name[proxy]
        ds = {k: decode(c, v, a) for k, v in images.items()}
        end = int(ds['reference']['end'], 16)
        assert len({d['size'] for d in ds.values()}) == 1
        assert ds['reference']['axes'] == ds['on']['axes'] == ds['off']['axes']
        for axis in ds['reference']['axes']:
            assert all(x < y for x, y in zip(axis['raw'], axis['raw'][1:]))
        changes = delta.intersection(range(a, end))
        assert not changes.intersection(covered), (hex(a), 'overlapping attribution')
        covered.update(changes)
        structural.append({'address': hex(a), 'proxy_symbol_NOT_verified': proxy,
                           'basis': basis, 'changed_bytes': len(changes), 'tables': ds})
    unmatched = ranges(delta - covered)
    result = {'hashes': {k: hashlib.sha256(v).hexdigest() for k, v in images.items()},
              'stage1_delta': len(delta), 'direct_and_identical_copy_bytes': direct_and_exact_count,
              'classified_bytes_including_structural_candidates': len(covered),
              'unmapped_bytes': len(delta-covered), 'unmapped_ranges': [
                  {'start': hex(a), 'end_exclusive': hex(b), 'ref': ref[a:b].hex(), 'on': on[a:b].hex()}
                  for a, b in unmatched],
              'unsupported': unsupported, 'maps': decoded,
              'structural_alternates': structural}
    (OUT / 'stage1-physical-audit.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('maps','unmapped_ranges','structural_alternates')}, indent=2))
    for m in decoded:
        r, s = m['tables']['reference'], m['tables']['on']
        print(m['name'], r['address'], r['dims'], 'changed', m['active_changed_bytes'],
              'values', len(m['changed_values']), 'range',
              (min(r['physical']), max(r['physical'])) if r['physical'] else None,
              (min(s['physical']), max(s['physical'])) if s['physical'] else None,
              'copy_count', len(m['identical_reference_copies']))
    print('STRUCTURAL_ALTERNATES', len(structural), sum(x['changed_bytes'] for x in structural))
    print('UNMAPPED', [(x['start'],x['end_exclusive']) for x in result['unmapped_ranges']])


if __name__ == '__main__':
    main()
