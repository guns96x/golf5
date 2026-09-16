import re
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

a2l_path = 'diagnostic-review/definitions/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.a2l'

names = [
    'AccPed_trqEng3_MAP',
    'AccPed_trqEng4_MAP',
    'AccPed_trqEng5_MAP',
    'Gearbx_trqMaxGear3_CUR',
    'Gearbx_trqMaxGear4_CUR',
    'Gearbx_trqMaxGear5_CUR',
    'EngPrt_trqLimP_MAP',
    'Eng_tqMaxClu_T_VW',
    'Eng_tqIdRed_M_VW',
    'FMTC_trq2qBas_MAP',
    'FlMng_qPresSmoke_MAP',
    'InjCrv_phiBasGear34_MAP',
    'InjCrv_phiBasGear56_MAP',
    'InjVlv_phiInjMI1_MAP1',
    'InjVlv_phiInjMI1_MAP2',
    'PCR_pBDesBas_MAP'
]

with open(a2l_path, 'r', encoding='latin-1') as f:
    content = f.read()

for name in names:
    pattern = rf'/begin CHARACTERISTIC\s+{re.escape(name)}\b(.*?)/end CHARACTERISTIC'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        print(f"================ {name} ================")
        print(match.group(0)[:1200])
    else:
        print(f"NOT FOUND: {name}")

