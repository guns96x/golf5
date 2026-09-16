import struct
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

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

# In A2L: EngPrt_facTempPreTrbn_MAP @ 0x1D4EBC
# X: EngPrt_tExhPreTrbn (temperature): (raw - 2731.4)/10 °C
# Y: Eng_nAvrg (RPM): raw RPM
# Val: factor / 8192
nx, ny = struct.unpack_from('>hh', stg_bin, 0x1D4EBC)
raw_x = struct.unpack_from('>' + str(nx) + 'h', stg_bin, 0x1D4EBC + 4)
raw_y = struct.unpack_from('>' + str(ny) + 'h', stg_bin, 0x1D4EBC + 4 + 2*nx)
temps_c = [round((t - 2731.4) / 10, 1) for t in raw_x]
rpms = list(raw_y)
v_start = 0x1D4EBC + 4 + 2*(nx + ny)
raw_vals = struct.unpack_from('>' + str(nx * ny) + 'h', stg_bin, v_start)

print("=== EngPrt_facTempPreTrbn_MAP (0x1D4EBC) ===")
print("Temps (°C):", temps_c)
print("RPMs:", rpms)
for i, t in enumerate(temps_c):
    row_factors = [round(raw_vals[i*ny + j] / 8192.0, 4) for j in range(ny)]
    print(f"Temp {t:>6.1f}°C: {row_factors}")

