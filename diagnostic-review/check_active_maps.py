"""Check dynamic map lengths before attributing differences to active tables."""
from pathlib import Path
import json,re,struct
ROOT=Path(__file__).resolve().parent
idx={c['name']:c for c in json.loads((ROOT/'a2l-characteristics-index.json').read_text())}
paths={'reference':ROOT/'reference-from-hex.analysis-only.bin','on':ROOT/'new-inputs'/'on'/'03G906021QJ.Bin','off':ROOT/'new-inputs'/'off'/'03G906021QJ (DPF EGR OFF) NoCS.Bin'}
images={k:p.read_bytes() for k,p in paths.items()}
checks=['AirCtl_qHigh_CUR','AirCtl_qMiddle_CUR','EngPrt_trqNLimSpr_CUR','EngPrt_trqNLim_CUR','PFlt_numEngPOp1_CA']
checks+= [c['name'] for c in json.loads((ROOT/'stage1-map-review.json').read_text())['changed_characteristics']]
report=[]
for name in dict.fromkeys(checks):
 c=idx[name];a=c['address'];entry={'name':name,'offset':hex(a),'reserved_bytes':c['size'],'layouts':{}}
 for label,data in images.items():
  layout=c['layout']
  if layout.startswith('Kl_Xs16_Ws16'):
   nx=struct.unpack_from('>h',data,a)[0];header=2;size=2+4*nx
   assert 0<nx and size<=c['size']
   dims=[nx];values_start=a+2+2*nx
  elif layout=='Kf_Xs16_Ys16_Ws16':
   nx,ny=struct.unpack_from('>hh',data,a);header=4;size=4+2*(nx+ny+nx*ny)
   assert nx>0 and ny>0 and size<=c['size']
   dims=[nx,ny];values_start=a+4+2*(nx+ny)
  elif layout=='Kf_Xu8_Yu8_Wu8':
   nx,ny=data[a:a+2];size=2+nx+ny+nx*ny
   assert nx>0 and ny>0 and size<=c['size']
   dims=[nx,ny];values_start=a+2+nx+ny
  else:
   entry['layouts'][label]={'unsupported':layout};continue
  entry['layouts'][label]={'dimensions':dims,'active_bytes':size,'values_offset':hex(values_start),'end_exclusive':hex(a+size)}
  if name.startswith('EngPrt_trqNLim'):
   entry['layouts'][label]['rpm_axis']=list(struct.unpack_from('>'+str(nx)+'h',data,a+2))
   entry['layouts'][label]['torque_Nm']=[x/10 for x in struct.unpack_from('>'+str(nx)+'h',data,values_start)]
 if not any('unsupported' in x for x in entry['layouts'].values()):
  for left,right in [('reference','on'),('on','off')]:
   end=max(int(entry['layouts'][left]['end_exclusive'],16),int(entry['layouts'][right]['end_exclusive'],16))
   entry[left+'_to_'+right+'_active_changed_bytes']=sum(x!=y for x,y in zip(images[left][a:end],images[right][a:end]))
 report.append(entry)
(ROOT/'active-map-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
for e in report:
 print(json.dumps(e))

# Physical values for the temperature-protection map, per provided A2L:
# X temperature (raw-2731.4)/10 degC; Y rpm raw; factor raw/8192.
c=idx['EngPrt_facTempPreTrbn_MAP'];a=c['address'];r=images['reference'];o=images['on']
nx,ny=struct.unpack_from('>hh',r,a)
x=struct.unpack_from('>'+str(nx)+'h',r,a+4)
y=struct.unpack_from('>'+str(ny)+'h',r,a+4+2*nx)
v=a+4+2*(nx+ny)
print('TEMPERATURE_PROTECTION_AXES',json.dumps({'x_degC':[round((q-2731.4)/10,2) for q in x],'y_rpm':y}))
print('TEMPERATURE_PROTECTION_CHANGED_VALUES',json.dumps([
 {'flat_index':i,'reference':struct.unpack_from('>h',r,v+2*i)[0]/8192,'on':struct.unpack_from('>h',o,v+2*i)[0]/8192}
 for i in range(nx*ny) if r[v+2*i:v+2*i+2]!=o[v+2*i:v+2*i+2]]))
