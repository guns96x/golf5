import struct
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open('diagnostic-review/reference-from-hex.analysis-only.bin', 'rb') as f:
    ref_bin = f.read()

with open('03G906021QJ_stage1_full_power_dpf_egr_off.bin', 'rb') as f:
    stg_bin = f.read()

def decode_map_s16(data, addr, x_scale=1.0, y_scale=1.0, val_scale=0.0234375):
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

print("=== InjCrv_phiBasGear34_MAP (0x1DAAF8) ===")
# X: Eng_nAvrg (16), Y: InjCrv_qSOI (14), val: deg CrS (0.0234375)
soi34_ref = decode_map_s16(ref_bin, 0x1DAAF8, 1.0, 0.01, 0.0234375)
soi34_stg = decode_map_s16(stg_bin, 0x1DAAF8, 1.0, 0.01, 0.0234375)

print("RPM nodes:", soi34_ref['x_axis'])
print("IQ nodes (mg):", soi34_ref['y_axis'])

print("\n--- SOI Gear 3/4 Ref (°CA BTDC) ---")
print(f"{'RPM':>6} | " + " | ".join([f"{q:>5.1f}" for q in soi34_ref['y_axis']]))
for i, rpm in enumerate(soi34_ref['x_axis']):
    row_str = " | ".join([f"{v:>5.2f}" for v in soi34_ref['grid'][i]])
    print(f"{rpm:>6.0f} | {row_str}")

print("\n--- SOI Gear 3/4 Stage 1 (°CA BTDC) ---")
print(f"{'RPM':>6} | " + " | ".join([f"{q:>5.1f}" for q in soi34_stg['y_axis']]))
for i, rpm in enumerate(soi34_stg['x_axis']):
    row_str = " | ".join([f"{v:>5.2f}" for v in soi34_stg['grid'][i]])
    print(f"{rpm:>6.0f} | {row_str}")

print("\n=== InjCrv_phiBasGear56_MAP (0x1DACF8) ===")
soi56_ref = decode_map_s16(ref_bin, 0x1DACF8, 1.0, 0.01, 0.0234375)
soi56_stg = decode_map_s16(stg_bin, 0x1DACF8, 1.0, 0.01, 0.0234375)

print("\n--- SOI Gear 5/6 Stage 1 (°CA BTDC) ---")
print(f"{'RPM':>6} | " + " | ".join([f"{q:>5.1f}" for q in soi56_stg['y_axis']]))
for i, rpm in enumerate(soi56_stg['x_axis']):
    row_str = " | ".join([f"{v:>5.2f}" for v in soi56_stg['grid'][i]])
    print(f"{rpm:>6.0f} | {row_str}")

