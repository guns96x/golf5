import struct
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open('diagnostic-review/reference-from-hex.analysis-only.bin', 'rb') as f:
    ref_bin = f.read()

with open('03G906021QJ_stage1_full_power_dpf_egr_off.bin', 'rb') as f:
    stg_bin = f.read()

def decode_map_s16(data, addr, x_scale=1.0, y_scale=1.0, val_scale=0.01):
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

# In A2L:
# InjCrv_phiBasGear34_MAP @ 0x1DAAF8:
# X: Eng_nAvrg (16), factor 1.0
# Y: InjCrv_qSOI (14), factor 0.01 (InjMass)
# Val: AngleCrS, factor 0.0234375 (3/128) or 0.0234375? Let's check compu method in A2L!
# InjVlv_phiInjMI1_MAP1..4:
# X: Eng_nAvrg (19)
# Y: InjUn_qMI1DesCorr (15), factor 0.01
# Val: AngleCrS, factor 0.0234375

print("=== Checking AngleCrS compu method in A2L ===")
