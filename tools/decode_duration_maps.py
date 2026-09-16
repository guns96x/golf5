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

map_addrs = {
    'MAP0': 0x1E4F3E,
    'MAP1': 0x1E5032,
    'MAP2': 0x1E52B4,
    'MAP3': 0x1E5536,
    'MAP4': 0x1E57B8,
    'MAP5': 0x1E5A3A,
    'MAP6': 0x1E5CBC
}

for name, addr in map_addrs.items():
    m_ref = decode_map_s16(ref_bin, addr, 1.0, 0.01, 0.0234375)
    m_stg = decode_map_s16(stg_bin, addr, 1.0, 0.01, 0.0234375)
    is_diff = ref_bin[addr:addr+len(ref_bin[addr:addr+650])] != stg_bin[addr:addr+len(stg_bin[addr:addr+650])]
    print(f"=== {name} @ {hex(addr)} (Diff: {is_diff}) ===")
    print("RPM nodes:", m_ref['x_axis'])
    print("IQ nodes:", m_ref['y_axis'])
    # Print values at 2000, 2500, 3000, 4000 RPM at 50, 55, 60 mg
    for rpm in [1500, 2000, 2500, 3000, 4000]:
        if rpm in m_ref['x_axis']:
            r_idx = m_ref['x_axis'].index(rpm)
            print(f"  RPM {rpm}:")
            for q in [40.0, 50.0, 55.0, 60.0]:
                if q in m_ref['y_axis']:
                    q_idx = m_ref['y_axis'].index(q)
                    ref_dur = m_ref['grid'][r_idx][q_idx]
                    stg_dur = m_stg['grid'][r_idx][q_idx]
                    print(f"    {q} mg: Ref = {ref_dur:.2f}° CA, Stg = {stg_dur:.2f}° CA (diff {stg_dur - ref_dur:+.2f}°)")
