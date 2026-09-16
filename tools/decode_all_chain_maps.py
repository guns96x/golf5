import struct
import json
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open('diagnostic-review/reference-from-hex.analysis-only.bin', 'rb') as f:
    ref_bin = f.read()

with open('03G906021QJ_stage1_full_power_dpf_egr_off.bin', 'rb') as f:
    stg_bin = f.read()

def decode_curve_s16(data, addr, x_scale=1.0, val_scale=0.1):
    nx = struct.unpack_from('>h', data, addr)[0]
    x_axis = [x * x_scale for x in struct.unpack_from('>' + str(nx) + 'h', data, addr + 2)]
    values = [v * val_scale for v in struct.unpack_from('>' + str(nx) + 'h', data, addr + 2 + 2*nx)]
    return {'nx': nx, 'x_axis': x_axis, 'values': values}

def decode_map_s16(data, addr, x_scale=1.0, y_scale=1.0, val_scale=0.1):
    nx, ny = struct.unpack_from('>hh', data, addr)
    x_axis = [x * x_scale for x in struct.unpack_from('>' + str(nx) + 'h', data, addr + 4)]
    y_axis = [y * y_scale for y in struct.unpack_from('>' + str(ny) + 'h', data, addr + 4 + 2*nx)]
    v_start = addr + 4 + 2*(nx + ny)
    # in EDC16, Kf_Xs16_Ys16_Ws16 is typically stored as nx rows of ny columns or nx columns of ny rows
    raw_vals = struct.unpack_from('>' + str(nx * ny) + 'h', data, v_start)
    grid = []
    for i in range(nx):
        row = [raw_vals[i*ny + j] * val_scale for j in range(ny)]
        grid.append(row)
    return {'nx': nx, 'ny': ny, 'x_axis': x_axis, 'y_axis': y_axis, 'grid': grid}

print("=== 1. AccPed_trqEngLim_MAP (0x1C3628) ===")
# x: VehDa_rVn (6), y: Eng_nAvrg (7), val: TrqPrp (scale: let's check compu method)
# In A2L, TrqPrp compu method: let's find out!
print("Raw ref header:", ref_bin[0x1C3628:0x1C3628+20].hex(' '))
print("Raw stg header:", stg_bin[0x1C3628:0x1C3628+20].hex(' '))
is_diff = ref_bin[0x1C3628:0x1C3628+0x72] != stg_bin[0x1C3628:0x1C3628+0x72]
print(f"AccPed_trqEngLim_MAP diff in Stage 1: {is_diff}")

print("\n=== 2. Gearbx_trqMaxGear3_CUR (0x1D855E) ===")
c3_ref = decode_curve_s16(ref_bin, 0x1D855E, 1.0, 0.1)
c3_stg = decode_curve_s16(stg_bin, 0x1D855E, 1.0, 0.1)
print("Gear 3 limit RPM:", c3_ref['x_axis'])
print("Gear 3 limit Ref Nm:", c3_ref['values'])
print("Gear 3 limit Stg Nm:", c3_stg['values'])

print("\n=== 3. Gearbx_trqMaxGear4_CUR (0x1D859C) ===")
c4_ref = decode_curve_s16(ref_bin, 0x1D859C, 1.0, 0.1)
print("Gear 4 limit Ref Nm:", c4_ref['values'])

print("\n=== 4. Gearbx_trqMaxGear5_CUR (0x1D85DA) ===")
c5_ref = decode_curve_s16(ref_bin, 0x1D85DA, 1.0, 0.1)
print("Gear 5 limit Ref Nm:", c5_ref['values'])

print("\n=== 5. EngPrt_trqLimP_MAP (0x1D4732) ===")
# nx=3 (ambient pressure), ny=21 (RPM)
p_ref = decode_map_s16(ref_bin, 0x1D4732, 1.0, 1.0, 0.1)
p_stg = decode_map_s16(stg_bin, 0x1D4732, 1.0, 1.0, 0.1)
print("Atmospheric pressures (hPa):", p_ref['x_axis'])
print("RPM nodes:", p_ref['y_axis'])
print("Torque at 1000 hPa Ref Nm:", p_ref['grid'][2] if len(p_ref['grid']) > 2 else p_ref['grid'])
print("Torque at 1000 hPa Stg Nm:", p_stg['grid'][2] if len(p_stg['grid']) > 2 else p_stg['grid'])

