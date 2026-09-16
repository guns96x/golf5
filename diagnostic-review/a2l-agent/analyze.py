import re, json
from pathlib import Path

a2l = next(Path(r'C:/Users/pavlo/golf5/diagnostic-review/definitions').glob('**/*.a2l'))
diff = json.loads(Path(r'C:/Users/pavlo/golf5/diagnostic-review/binary-comparison.json').read_text())
ranges = [(int(x['start'],16), int(x['end'],16)) for x in diff['ranges']]
targets = [0x189e34,0x189f26,0x1c9dd8,0x1d4922,0x1d4988,0x1eca82]
if __name__ == '__main__':
    pass
text = a2l.read_text(errors='replace')
binp=Path(r'C:/Users/pavlo/golf5/diagnostic-review/reference-from-hex.analysis-only.bin')
if binp.exists():
    bb=binp.read_bytes()
    for aa in (0x1c9daa,0x1c9ea0,0x1d48f8,0x1d495e,0x1eca6e): print('BYTES',hex(aa),bb[aa:aa+16].hex(' '))
for key in ('AirCtl_qHigh_CUR','AirCtl_qMiddle_CUR','EngPrt_trqNLimSpr_CUR','EngPrt_trqNLim_CUR'):
    mm=re.search(r'/begin CHARACTERISTIC\s+'+re.escape(key)+r'(.*?)/end CHARACTERISTIC',text,re.S)
    if mm:
        print('SELECTED',key)
        print('\n'.join(x.strip() for x in mm.group(1).splitlines() if x.strip())[:3000])
for kind in ('CHARACTERISTIC','AXIS_PTS','MEASUREMENT'):
    pat = re.compile(r'/begin '+kind+r'\s+(.*?)/end '+kind, re.S)
    for m in pat.finditer(text):
        body=m.group(1)
        ls=[x.strip() for x in body.splitlines() if x.strip()]
        if kind=='CHARACTERISTIC' and len(ls)>=4:
            name,desc,typ,addr=ls[:4]
        elif kind=='AXIS_PTS' and len(ls)>=4:
            name,desc,addr,typ=ls[:4]
        elif kind=='MEASUREMENT' and len(ls)>=4:
            name,desc,typ,addr=ls[:4]
        else: continue
        if not re.fullmatch(r'0x[0-9A-Fa-f]+',addr): continue
        a=int(addr,16)
        mm=re.search(r'DP_BLOB\s+0x[0-9A-Fa-f]+\s+0x[0-9A-Fa-f]+\s+0x([0-9A-Fa-f]+)',body,re.S)
        size=int(mm.group(1),16) if mm else 1
        hit=[(hex(s),hex(e)) for s,e in ranges if a<=e and a+size-1>=s]
        if hit:
            print(json.dumps({'kind':kind,'name':name,'desc':desc,'type':typ,'addr':hex(a),'size':hex(size),'hits':hit},ensure_ascii=False))
        near=[hex(t) for t in targets if abs(a-t)<0x200]
        if 0x188000 <= a <= 0x18b000:
            print('REGION',hex(a),name,desc,typ)
        if near:
            print(json.dumps({'near':near,'kind':kind,'name':name,'desc':desc,'type':typ,'addr':hex(a)},ensure_ascii=False))
