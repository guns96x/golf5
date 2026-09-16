"""Read-only targeted A2L/BIN/log audit. Writes evidence JSON, never firmware."""
from pathlib import Path
import bisect
import csv
import hashlib
import json
import re
import statistics
import struct

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BIN = ROOT / '03G906021QJ_stage1_refined_CS_OK.bin'
A2L = next((ROOT / 'diagnostic-review/definitions').rglob('*.a2l'))
HEX = A2L.with_suffix('.HEX')
LOG = ROOT / 'logs/VCDS_WOT_Log_20260914_153242.csv'
text = A2L.read_text(encoding='latin1')
image = BIN.read_bytes()
newlines = [m.start() for m in re.finditer('\n', text)]

def blocks(kind):
    return {m[1]: (m[2], bisect.bisect_left(newlines, m.start()) + 1)
            for m in re.finditer(r'/begin ' + kind + r'\s+(\S+)\s+(.*?)/end ' + kind, text, re.S)}

chars, methods, layouts = blocks('CHARACTERISTIC'), blocks('COMPU_METHOD'), blocks('RECORD_LAYOUT')
sizes = {'SWORD': ('h', 2), 'UWORD': ('H', 2), 'SBYTE': ('b', 1),
         'UBYTE': ('B', 1), 'SLONG': ('i', 4), 'ULONG': ('I', 4)}

def physical(raw, method):
    m = re.search(r'COEFFS\s+([^\n]+)', methods[method][0])
    if not m:
        raise ValueError('unsupported conversion ' + method)
    a, b, c, d, e, f = map(float, m[1].split())
    if a == b == d == f == 0 and c and e:
        return [c/(v*e) if v else None for v in raw]
    assert a == d == e == 0 and b and f, (method, (a, b, c, d, e, f))
    return [(v*f-c)/b for v in raw]

# Parse and validate every Intel HEX record; preserve address coverage explicitly.
reference, covered = bytearray(len(image)), bytearray(len(image))
base = 0
for line in HEX.read_text().splitlines():
    data = bytes.fromhex(line.strip()[1:])
    assert sum(data) % 256 == 0 and len(data) == data[0] + 5
    count, addr, typ = data[0], int.from_bytes(data[1:3], 'big'), data[3]
    payload = data[4:4+count]
    if typ == 0:
        addr += base
        assert addr + count <= len(image)
        reference[addr:addr+count] = payload
        covered[addr:addr+count] = b'\x01' * count
    elif typ == 4:
        base = int.from_bytes(payload, 'big') << 16
    elif typ == 2:
        base = int.from_bytes(payload, 'big') << 4
    else:
        assert typ in (1, 3, 5)

def decode(name):
    body, line = chars[name]
    m = re.match(r'"([^"]*)"\s+(\S+)\s+(0x[\da-fA-F]+)\s+(\S+)\s+\S+\s+(\S+)', body)
    desc, kind, addr, layout_name, conv = m.groups()
    addr = int(addr, 16)
    assert 'BYTE_ORDER' not in body
    layout = layouts[layout_name][0]
    fields = sorted((int(m[2]), m[1], m[3], m[4].strip()) for m in re.finditer(
        r'(NO_AXIS_PTS_[XY]|AXIS_PTS_[XY]|FNC_VALUES)\s+(\d+)\s+(\w+)([^\n]*)', layout))
    pos, dims, axes, values, order = addr, {}, [], [], None
    meta = list(re.finditer(r'/begin AXIS_DESCR\s+STD_AXIS\s+(\S+)\s+(\S+)\s+(\d+)', body))
    for _, field, typ, suffix in fields:
        fmt, width = sizes[typ]
        if field.startswith('NO_AXIS'):
            n = struct.unpack_from('>' + fmt, image, pos)[0]
            assert 0 < n <= 128
            dims[field[-1]] = n
            pos += width
        elif field.startswith('AXIS_PTS'):
            n = dims[field[-1]]
            raw = struct.unpack_from('>' + str(n) + fmt, image, pos)
            ax = meta[len(axes)]
            assert n <= int(ax[3])
            axes.append({'input': ax[1], 'conversion': ax[2], 'values': physical(raw, ax[2])})
            pos += width*n
        else:
            n = 1
            for size in dims.values():
                n *= size
            raw = struct.unpack_from('>' + str(n) + fmt, image, pos)
            values, start, order = physical(raw, conv), pos, suffix
            pos += n*width
    assert values and all(covered[addr:pos])
    if kind == 'MAP':
        assert order == 'COLUMN_DIR DIRECT'
    return {'name': name, 'description': desc, 'a2l_line': line, 'address': hex(addr),
            'value_address': hex(start), 'end_exclusive': hex(pos), 'kind': kind,
            'layout': layout_name, 'conversion': conv, 'dimensions': list(dims.values()),
            'axes': axes, 'raw_values': list(raw), 'values': values, 'order': order,
            'hex_reference_changed_bytes': sum(x != y for x, y in zip(image[addr:pos], reference[addr:pos]))}

selected = ['PCR_rBPCtlBas_MAP', 'PCR_pBDesBas_MAP', 'FlMng_qPresSmoke_MAP',
            'PCR_rBPGovLin_CUR', 'PCR_facD_MAP', 'PCR_facI_MAP', 'PCR_facP_MAP',
            'PCR_DT1_MAP', 'PCR_swtQCtlVal_C', 'PCR_swtQCtlType_C',
            'FlMng_swtSmokeVariant_C', 'FlMng_swtqLimSmkQ_C', 'FlMng_swtSmokeSpace_C']
selected += [n for n in chars if re.fullmatch(r'PCR_(DKd|PKp|IKi)(Pos|Neg)?_C', n)]
maps = {n: decode(n) for n in selected}

def interp(m, x, y):
    axes = [a['values'] for a in m['axes']]
    ij = []
    for a, v in zip(axes, (x, y)):
        v = max(a[0], min(a[-1], v))
        i = max(0, min(len(a)-2, bisect.bisect_right(a, v)-1))
        ij.append((i, (v-a[i])/(a[i+1]-a[i])))
    (i, tx), (j, ty) = ij
    ny = len(axes[1])
    z = m['values']
    return sum(wx*wy*z[(i+di)*ny+j+dj] for di, wx in [(0, 1-tx), (1, tx)]
               for dj, wy in [(0, 1-ty), (1, ty)])

rows = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(LOG.open())]
pull = [r for r in rows if 39.734 <= r['RelativeTime_s'] <= 42.848]
for r in pull:
    r['error_actual_minus_specified_mbar'] = r['Boost_Actual_mbar']-r['Boost_Specified_mbar']
    # Hypothetical lookup only: actual PCR_qCtl and IAT-corrected smoke pressure are not logged.
    r['hypothetical_base_at_40mg_pct'] = interp(maps['PCR_rBPCtlBas_MAP'], r['RPM'], 40)
    r['hypothetical_base_at_45mg_pct'] = interp(maps['PCR_rBPCtlBas_MAP'], r['RPM'], 45)
    r['hypothetical_smoke_using_uncorrected_MAP_mg'] = interp(maps['FlMng_qPresSmoke_MAP'], r['RPM'], r['Boost_Actual_mbar'])

measurements = {n: {'description': re.match(r'"([^"]*)"', b)[1], 'a2l_line': line}
                for n, (b, line) in blocks('MEASUREMENT').items()
                if n.startswith('PCR_') and re.search('dnAvrg|facD_mp|rBPCtl|rOut|rPICtl|rPIDCtl|stPCR|swtRgt|qCtl$', n)}
evidence = {
    'artifacts': {str(p.relative_to(ROOT)): {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                                          'bytes': p.stat().st_size} for p in (BIN, A2L, HEX, LOG)},
    'reference': 'Direct Intel HEX address reconstruction; all compared object bytes covered. Companion reference, not a verified factory vehicle read.',
    'decode': 'Big endian per MOD_COMMON; signed types from RECORD_LAYOUT. COLUMN_DIR map index = x_index*ny+y_index. RAT_FUNC physical=(raw*f-c)/b for linear subset; c/(raw*e) for reciprocal subset (raw zero gives null). Static metadata match, active code path not proved.',
    'maps': maps, 'measurements': measurements,
    'log': {'rows': len(rows), 'duration_s': rows[-1]['RelativeTime_s'],
            'all_zero_columns': [k for k in rows[0] if all(r[k] == 0 for r in rows)],
            'median_row_interval_s': statistics.median(b['RelativeTime_s']-a['RelativeTime_s'] for a,b in zip(rows,rows[1:])),
            'pull_duration_s': pull[-1]['RelativeTime_s']-pull[0]['RelativeTime_s'],
            'pull': pull},
    'firmware_written': False, 'checksum_verified': False, 'vehicle_validated': False}
(OUT / 'evidence.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'sha256': evidence['artifacts'][str(BIN.relative_to(ROOT))]['sha256'],
                  'objects': len(maps), 'zero_columns': evidence['log']['all_zero_columns'],
                  'pull_duration_s': evidence['log']['pull_duration_s'],
                  'output': str(OUT / 'evidence.json')}))
