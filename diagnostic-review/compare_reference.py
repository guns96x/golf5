"""Validate supplied transport formats and compare references without flashing."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent
DEFS = next((ROOT / 'definitions').iterdir())

def ihex(path):
    memory = {}
    base = 0
    counts = Counter()
    eof = False
    for line_no, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        assert line.startswith(':'), (line_no, 'not Intel HEX')
        record = bytes.fromhex(line[1:])
        assert sum(record) % 256 == 0, (line_no, 'checksum')
        n, addr, kind = record[0], int.from_bytes(record[1:3], 'big'), record[3]
        assert len(record) == n + 5, (line_no, 'length')
        payload = record[4:-1]
        counts[kind] += 1
        if kind == 0:
            for i, byte in enumerate(payload):
                pos = base + addr + i
                assert pos not in memory or memory[pos] == byte, (line_no, 'overlap')
                memory[pos] = byte
        elif kind == 1:
            eof = True
        elif kind == 2:
            base = int.from_bytes(payload, 'big') << 4
        elif kind == 4:
            base = int.from_bytes(payload, 'big') << 16
        elif kind not in (3, 5):
            raise ValueError((line_no, kind))
    assert eof
    return memory, dict(counts)

def srec(path):
    memory = {}
    counts = Counter()
    for line_no, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        assert line[0] == 'S'
        kind = int(line[1])
        record = bytes.fromhex(line[2:])
        assert sum(record) % 256 == 255, (line_no, 'checksum')
        assert len(record) == record[0] + 1, (line_no, 'length')
        counts[kind] += 1
        if kind in (1, 2, 3):
            addr_bytes = kind + 1
            addr = int.from_bytes(record[1:1+addr_bytes], 'big')
            for i, byte in enumerate(record[1+addr_bytes:-1]):
                pos = addr + i
                assert pos not in memory or memory[pos] == byte, (line_no, 'overlap')
                memory[pos] = byte
    return memory, dict(counts)

hm, hc = ihex(next(DEFS.glob('*.HEX')))
sm, sc = srec(next(DEFS.glob('*.S19')))
assert hm == sm, 'HEX and S19 data differ'
assert min(hm) == 0 and len(hm) == max(hm) + 1
reference = bytes(hm[i] for i in range(len(hm)))
(ROOT / 'reference-from-hex.analysis-only.bin').write_bytes(reference)

images = {
    'first_attachment': next(Path(r'\\?\C:\Users\pavlo\.cloudcli\assets').glob('1789027452850-*')).read_bytes(),
    'original_off_attachment': (ROOT / 'extracted' / '03G906021QJ (DPF EGR OFF) NoCS.Bin').read_bytes(),
    'new_stage1_on': (ROOT / 'new-inputs' / 'on' / '03G906021QJ.Bin').read_bytes(),
    'new_off': (ROOT / 'new-inputs' / 'off' / '03G906021QJ (DPF EGR OFF) NoCS.Bin').read_bytes(),
    'supplied_hex_s19_reference': reference,
}

def ranges_of(indices):
    result = []
    for i in indices:
        if result and i == result[-1][1] + 1:
            result[-1][1] = i
        else:
            result.append([i, i])
    return result

report = {
    'hex_record_checksums_valid': True,
    's19_record_checksums_valid': True,
    'hex_s19_equal': True,
    'reference_address_range': [hex(min(hm)), hex(max(hm))],
    'hex_record_counts': hc,
    's19_record_counts': sc,
    'images': {},
    'pair_comparisons': {},
    'limitations': ['Transport record checksum validity does not validate Bosch ECU checksums.',
                    'Reference supplied by user; factory authenticity not independently established.',
                    'Extracted reference is for analysis only; not a flash recommendation.'],
}
for name, data in images.items():
    ids = [{ 'offset':hex(m.start()), 'text':m.group().decode('ascii') }
           for m in re.finditer(rb'[ -~]{8,}', data)
           if re.search(rb'03G906|103739|R4 1,9|EDC16|BOSCH|P447', m.group())]
    report['images'][name] = {'size':len(data), 'sha256':hashlib.sha256(data).hexdigest(), 'ids':ids,
                            'leading_ff':len(data)-len(data.lstrip(b'\xff'))}

for left, right in [('first_attachment','new_stage1_on'),('original_off_attachment','new_off'),
                    ('new_stage1_on','new_off'),('supplied_hex_s19_reference','new_stage1_on'),
                    ('supplied_hex_s19_reference','new_off')]:
    a,b = images[left],images[right]
    assert len(a)==len(b)
    indices = [i for i,(x,y) in enumerate(zip(a,b)) if x!=y]
    ranges = ranges_of(indices)
    key = left+'__vs__'+right
    report['pair_comparisons'][key] = {
        'different_bytes':len(indices), 'different_ranges':len(ranges),
        'blocks':[{ 'start':hex(s),'diff':sum(x!=y for x,y in zip(a[s:s+65536],b[s:s+65536]))}
                  for s in range(0,len(a),65536) if a[s:s+65536]!=b[s:s+65536]],
        'ranges':[{ 'start':hex(s),'end':hex(e),'size':e-s+1 } for s,e in ranges],
    }

(ROOT / 'reference-comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
for comp in report['pair_comparisons'].values():
    comp.pop('ranges')
print(json.dumps(report,indent=2))
