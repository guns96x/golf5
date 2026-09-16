import json
import struct
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open('diagnostic-review/a2l-characteristics-index.json', 'r', encoding='utf-8') as f:
    chars_list = json.load(f)

chars_by_name = {c['name']: c for c in chars_list}

with open('diagnostic-review/reference-from-hex.analysis-only.bin', 'rb') as f:
    ref_bin = f.read()

with open('03G906021QJ_stage1_full_power_dpf_egr_off.bin', 'rb') as f:
    stg_bin = f.read()

print(f"Ref bin size: {len(ref_bin)}, Stg bin size: {len(stg_bin)}")

target_maps = [
    'AccPed_trqEng0_MAP',
    'AccPed_trqEng1_MAP',
    'AccPed_trqEng2_MAP',
    'AccPed_trqEng3_MAP',
    'AccPed_trqEng4_MAP',
    'AccPed_trqEng5_MAP',
    'AccPed_trqEng6_MAP',
    'Gearbx_trqMaxGear1_CUR',
    'Gearbx_trqMaxGear2_CUR',
    'Gearbx_trqMaxGear3_CUR',
    'Gearbx_trqMaxGear4_CUR',
    'Gearbx_trqMaxGear5_CUR',
    'Gearbx_trqMaxGear6_CUR',
    'Eng_tqMaxClu_T_VW',
    'EngPrt_trqLimP_MAP',
    'EngPrt_facTempPreTrbn_MAP',
    'FMTC_trq2qBas_MAP',
    'FlMng_qPresSmoke_MAP',
    'InjCrv_phiBasGear12_MAP',
    'InjCrv_phiBasGear34_MAP',
    'InjCrv_phiBasGear56_MAP',
    'InjVlv_phiInjMI1_MAP0',
    'InjVlv_phiInjMI1_MAP1',
    'InjVlv_phiInjMI1_MAP2',
    'InjVlv_phiInjMI1_MAP3',
    'InjVlv_phiInjMI1_MAP4',
    'InjVlv_phiInjMI1_MAP5',
    'InjVlv_phiInjMI1_MAP6',
    'PCR_pBDesBas_MAP'
]

for name in target_maps:
    c = chars_by_name.get(name)
    if not c:
        print(f"Map {name} NOT FOUND in chars!")
        continue
    addr = int(c['address_hex'], 16)
    print(f"=== {name} @ {c['address_hex']} ({c.get('kind')}, {c.get('layout')}) ===")
    raw_ref = ref_bin[addr:addr+24]
    raw_stg = stg_bin[addr:addr+24]
    diff = "DIFFERENT" if ref_bin[addr:addr+100] != stg_bin[addr:addr+100] else "IDENTICAL"
    print(f"Status in Stage 1 vs Ref: {diff}")
