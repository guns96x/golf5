import struct
import json
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open('diagnostic-review/reference-from-hex.analysis-only.bin', 'rb') as f:
    ref_bin = f.read()

with open('03G906021QJ_stage1_full_power_dpf_egr_off.bin', 'rb') as f:
    stg_bin = f.read()

def decode_map_s16(data, addr, x_scale=1.0, y_scale=1.0, val_scale=0.1):
    nx, ny = struct.unpack_from('>hh', data, addr)
    x_axis = [round(x * x_scale, 4) for x in struct.unpack_from('>' + str(nx) + 'h', data, addr + 4)]
    y_axis = [round(y * y_scale, 4) for y in struct.unpack_from('>' + str(ny) + 'h', data, addr + 4 + 2*nx)]
    v_start = addr + 4 + 2*(nx + ny)
    raw_vals = struct.unpack_from('>' + str(nx * ny) + 'h', data, v_start)
    grid = []
    for i in range(nx):
        row = [round(raw_vals[i*ny + j] * val_scale, 4) for j in range(ny)]
        grid.append(row)
    return {'nx': nx, 'ny': ny, 'x_axis': x_axis, 'y_axis': y_axis, 'grid': grid}

print("=== FMTC_trq2qBas_MAP (0x1D729C) ===")
# In A2L:
# X axis: Eng_nAvrg (EngN) -> 16 points (factor 1.0)
# Y axis: CoEng_trqInrSet (Trq) -> 15 points (factor 0.1)
# Values: InjMassCyc -> factor 0.01 (mg/stroke)
fmtc_ref = decode_map_s16(ref_bin, 0x1D729C, 1.0, 0.1, 0.01)
fmtc_stg = decode_map_s16(stg_bin, 0x1D729C, 1.0, 0.1, 0.01)

print("FMTC nx (RPM count):", fmtc_ref['nx'], fmtc_ref['x_axis'])
print("FMTC ny (Torque count):", fmtc_ref['ny'], fmtc_ref['y_axis'])
print("Ref FMTC torque axis:", fmtc_ref['y_axis'])
print("Stg FMTC torque axis:", fmtc_stg['y_axis'])

print("\nCompare FMTC values at 2000 RPM (row index):")
rpm_idx_2000 = fmtc_ref['x_axis'].index(2000.0)
print(f"RPM 2000 (index {rpm_idx_2000}):")
print("Ref values across torque:", fmtc_ref['grid'][rpm_idx_2000])
print("Stg values across torque:", fmtc_stg['grid'][rpm_idx_2000])

print("\nCompare FMTC values at 2500 RPM:")
rpm_idx_2500 = fmtc_ref['x_axis'].index(2500.0)
print("Ref values across torque:", fmtc_ref['grid'][rpm_idx_2500])
print("Stg values across torque:", fmtc_stg['grid'][rpm_idx_2500])

print("\nCompare FMTC values at 3000 RPM:")
rpm_idx_3000 = fmtc_ref['x_axis'].index(3000.0)
print("Ref values across torque:", fmtc_ref['grid'][rpm_idx_3000])
print("Stg values across torque:", fmtc_stg['grid'][rpm_idx_3000])

print("\n=== AccPed maps ===")
# Let's decode AccPed_trqEng0_MAP to AccPed_trqEng6_MAP
# In A2L:
# X axis: Eng_nAvrg (16)
# Y axis: AccPed_rChkdVal (8) -> scale? Let's check pedal axis values!
acc_names = [f'AccPed_trqEng{i}_MAP' for i in range(7)]
acc_addrs = [0x1C2CCE, 0x1C2E24, 0x1C2F7A, 0x1C30D0, 0x1C3226, 0x1C337C, 0x1C34D2]

for name, addr in zip(acc_names, acc_addrs):
    m_ref = decode_map_s16(ref_bin, addr, 1.0, 0.01, 0.1) # pedal scale might be 0.01 or 0.1%
    m_stg = decode_map_s16(stg_bin, addr, 1.0, 0.01, 0.1)
    # print pedal axis and max torque at 100% pedal across RPM
    pedal_axis = m_ref['y_axis']
    wot_idx = -1
    wot_ref = [m_ref['grid'][r][wot_idx] for r in range(m_ref['nx'])]
    wot_stg = [m_stg['grid'][r][wot_idx] for r in range(m_stg['nx'])]
    print(f"\n{name} (Pedal axis: {pedal_axis}):")
    print(f"RPM axis: {m_ref['x_axis']}")
    print(f"Ref WOT Torque (Nm): {wot_ref}")
    print(f"Stg WOT Torque (Nm): {wot_stg}")
