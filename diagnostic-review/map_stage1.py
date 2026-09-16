"""Map supplied reference-to-Stage1 byte changes using A2L declared extents."""
from pathlib import Path
import json
import re
import bisect

ROOT=Path(__file__).resolve().parent
text=next((ROOT/'definitions').rglob('*.a2l')).read_text(encoding='latin1')
ref=(ROOT/'reference-from-hex.analysis-only.bin').read_bytes()
on=(ROOT/'new-inputs'/'on'/'03G906021QJ.Bin').read_bytes()
off=(ROOT/'new-inputs'/'off'/'03G906021QJ (DPF EGR OFF) NoCS.Bin').read_bytes()
characteristics=[]
linebreaks=[m.start() for m in re.finditer('\n',text)]
for m in re.finditer(r'/begin CHARACTERISTIC\s+(.*?)\s*/end CHARACTERISTIC',text,re.S):
    body=m.group(1)
    h=re.match(r'(\S+)\s+"((?:""|\\.|[^"\\])*)"\s+(\S+)\s+(0x[0-9a-fA-F]+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)',body)
    if not h:
        raise ValueError(body[:300])
    name,desc,kind,addr,layout,maxdiff,compu,lower,upper=h.groups()
    address=int(addr,16)
    extent=re.search(r'/begin IF_DATA ETK\s+DP_BLOB\s+(0x[0-9A-Fa-f]+)\s+(0x[0-9A-Fa-f]+|[0-9]+)',body)
    if not extent:
        raise ValueError((name,'no extent'))
    assert int(extent[1],16)==address
    size=int(extent[2],0)
    c={'name':name,'description':desc,'kind':kind,'address':address,'address_hex':hex(address),
       'size':size,'layout':layout,'conversion':compu,'lower':lower,'upper':upper,
       'a2l_line':bisect.bisect_left(linebreaks,m.start())+1}
    characteristics.append(c)

changed=[]
covered=set()
for c in characteristics:
    start=c['address']; end=start+c['size']
    indices=[i for i in range(start,end) if i>=0x180000 and i<len(ref) and ref[i]!=on[i]]
    if not indices:
        continue
    covered.update(indices)
    entry=c|{'changed_bytes':len(indices),'first_changed':hex(indices[0]),'last_changed':hex(indices[-1])}
    if c['size']<=64:
        entry|={'reference_hex':ref[start:end].hex(' '),'stage1_hex':on[start:end].hex(' ')}
    changed.append(entry)

allchanges={i for i in range(0x180000,len(ref)) if ref[i]!=on[i]}
report={'parsed_characteristics':len(characteristics),'reference_to_stage1_changed_bytes_180000_onward':len(allchanges),
        'mapped_changed_bytes':len(covered),'unmapped_changed_bytes':len(allchanges-covered),
        'changed_characteristics':changed}
(ROOT/'a2l-characteristics-index.json').write_text(json.dumps(characteristics,indent=2),encoding='utf-8')
(ROOT/'stage1-map-review.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='changed_characteristics'},indent=2))
for c in changed:
    print(f"{c['address_hex']} {c['size']:4} {c['changed_bytes']:4} {c['name']} | {c['description']}")
