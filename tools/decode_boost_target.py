import struct
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open('diagnostic-review/reference-from-hex.analysis-only.bin', 'rb') as f:
    ref_bin = f.read()

with open('03G906021QJ_stage1_full_power_dpf_egr_off.bin', 'rb') as f:
    stg_bin = f.read()

def decode_map_s16(data, addr, x_scale=1.0, y_scale=1.0, val_scale=1.0):
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

# In A2L: PCR_pBDesBas_MAP @ 0x1EB0B2
# X: Eng_nAvrg (16)
# Y: PCR_qDes (10), factor 0.01 (InjMass)
# Val: Pres_hPa (factor 1.0 or 0.1? Let's check!)
p_ref = decode_map_s16(ref_bin, 0x1EB0B2, 1.0, 0.01, 1.0)
p_stg = decode_map_s16(stg_bin, 0x1EB0B2, 1.0, 0.01, 1.0)

print("=== PCR_pBDesBas_MAP (0x1EB0B2) ===")
print("RPM nodes:", p_ref['x_axis'])
print("IQ nodes (mg):", p_ref['y_axis'])

print("\n--- Boost Target (mbar) Ref ---")
print(f"{'RPM':>6} | " + " | ".join([f"{q:>5.1f}" for q in p_ref['y_axis']]))
for i, rpm in enumerate(p_ref['x_axis']):
    row_str = " | ".join([f"{v:>5.0f}" for v in p_ref['grid'][i]])
    print(f"{rpm:>6.0f} | {row_str}")

print("\n--- Boost Target (mbar) Stage 1 ---")
print(f"{'RPM':>6} | " + " | ".join([f"{q:>5.1f}" for q in p_stg['y_axis']]))
for i, rpm in enumerate(p_stg['x_axis']):
    row_str = " | ".join([f"{v:>5.0f}" for v in p_stg['grid'][i]])
    print(f"{rpm:>6.0f} | {row_str}")

