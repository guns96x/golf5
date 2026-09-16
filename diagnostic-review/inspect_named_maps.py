from pathlib import Path
import re,json,struct
ROOT=Path(__file__).resolve().parent
t=next((ROOT/'definitions').rglob('*.a2l')).read_text(encoding='latin1')
index={c['name']:c for c in json.loads((ROOT/'a2l-characteristics-index.json').read_text())}
names=['EngPrt_trqNLimSpr_CUR','EngPrt_trqNLim_CUR','EGT_swtEGTActv_C','LSU_swtVal_C','PFlt_tSurfInit_C','EngPrt_facTempPreTrbn_MAP','PFlt_numEngPOp1_CA']
needed=set()
for name in names:
    m=re.search(r'/begin CHARACTERISTIC\s+'+re.escape(name)+r'\s+(.*?)/end CHARACTERISTIC',t,re.S)
    print('\nCHARACTERISTIC',name,'line',index[name]['a2l_line'])
    body=m.group(1)
    print(body)
    needed.add(('COMPU_METHOD',index[name]['conversion']))
    needed.add(('RECORD_LAYOUT',index[name]['layout']))
    for ax in re.finditer(r'/begin AXIS_DESCR\s+\S+\s+\S+\s+(\S+)',body):
        needed.add(('COMPU_METHOD',ax[1]))
    c=index[name]; s=c['address'];e=s+c['size']
    for label,path in [('reference',ROOT/'reference-from-hex.analysis-only.bin'),('on',ROOT/'new-inputs'/'on'/'03G906021QJ.Bin'),('off',ROOT/'new-inputs'/'off'/'03G906021QJ (DPF EGR OFF) NoCS.Bin')]:
        b=path.read_bytes()[s:e]
        print(label,b.hex(' '))
for kind,name in sorted(needed):
    m=re.search(r'/begin '+kind+r'\s+'+re.escape(name)+r'\s+(.*?)/end '+kind,t,re.S)
    print('\n',kind,name,m.group(1) if m else 'NOT FOUND')
