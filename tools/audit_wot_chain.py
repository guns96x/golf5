import struct
import json
import bisect
import sys
import math

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open('diagnostic-review/reference-from-hex.analysis-only.bin', 'rb') as f:
    ref_bin = f.read()

with open('03G906021QJ_stage1_full_power_dpf_egr_off.bin', 'rb') as f:
    stg_bin = f.read()

def decode_curve_s16(data, addr, x_scale=1.0, val_scale=0.1):
    nx = struct.unpack_from('>h', data, addr)[0]
    x_axis = [round(x * x_scale, 4) for x in struct.unpack_from('>' + str(nx) + 'h', data, addr + 2)]
    values = [round(v * val_scale, 4) for v in struct.unpack_from('>' + str(nx) + 'h', data, addr + 2 + 2*nx)]
    return {'nx': nx, 'x_axis': x_axis, 'values': values}

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

def interp_1d(x_nodes, y_vals, x):
    if x <= x_nodes[0]:
        return y_vals[0]
    if x >= x_nodes[-1]:
        return y_vals[-1]
    idx = bisect.bisect_right(x_nodes, x) - 1
    x0, x1 = x_nodes[idx], x_nodes[idx+1]
    y0, y1 = y_vals[idx], y_vals[idx+1]
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)

def interp_2d(x_nodes, y_nodes, grid, x, y):
    # clamp x
    if x <= x_nodes[0]:
        i0, i1, fx = 0, 0, 0.0
    elif x >= x_nodes[-1]:
        i0, i1, fx = len(x_nodes)-1, len(x_nodes)-1, 0.0
    else:
        idx = bisect.bisect_right(x_nodes, x) - 1
        i0, i1 = idx, idx + 1
        fx = (x - x_nodes[i0]) / (x_nodes[i1] - x_nodes[i0])

    # clamp y
    if y <= y_nodes[0]:
        j0, j1, fy = 0, 0, 0.0
    elif y >= y_nodes[-1]:
        j0, j1, fy = len(y_nodes)-1, len(y_nodes)-1, 0.0
    else:
        idx = bisect.bisect_right(y_nodes, y) - 1
        j0, j1 = idx, idx + 1
        fy = (y - y_nodes[j0]) / (y_nodes[j1] - y_nodes[j0])

    v00 = grid[i0][j0]
    v01 = grid[i0][j1]
    v10 = grid[i1][j0]
    v11 = grid[i1][j1]

    v0 = v00 + (v01 - v00) * fy
    v1 = v10 + (v11 - v10) * fy
    return v0 + (v1 - v0) * fx

# Load telemetry
log_data = []
with open('logs/20260916/Turbo_Pair_20260916_112035.csv', 'r') as f:
    headers = [h.strip() for h in f.readline().split(',')]
    for line in f:
        parts = [p.strip() for p in line.split(',')]
        if len(parts) >= len(headers):
            row = dict(zip(headers, parts))
            try:
                rpm = float(row['rpm'])
                map_val = float(row['map_mbar_abs'])
                baro = float(row['baro_mbar'])
                load = float(row['load_pct']) if row['load_pct'] else 0.0
                maf = float(row['maf_g_s']) if row['maf_g_s'] else 0.0
                speed = float(row['speed_kmh']) if row['speed_kmh'] else 0.0
                log_data.append({'rpm': rpm, 'map': map_val, 'baro': baro, 'load': load, 'maf': maf, 'speed': speed})
            except ValueError:
                continue

# Filter WOT points from log
wot_log = [d for d in log_data if d['load'] >= 90.0]

def get_nearest_telemetry(rpm_target):
    # Find closest RPM in wot_log
    closest = min(wot_log, key=lambda d: abs(d['rpm'] - rpm_target))
    return closest

# Load Maps
accped_maps = {
    3: decode_map_s16(stg_bin, 0x1C30D0, 1.0, 0.01, 0.1),
    4: decode_map_s16(stg_bin, 0x1C3226, 1.0, 0.01, 0.1),
    5: decode_map_s16(stg_bin, 0x1C337C, 1.0, 0.01, 0.1),
}

gear_trq_limits = {
    3: decode_curve_s16(stg_bin, 0x1D855E, 1.0, 0.1),
    4: decode_curve_s16(stg_bin, 0x1D859C, 1.0, 0.1),
    5: decode_curve_s16(stg_bin, 0x1D85DA, 1.0, 0.1),
}

trq_lim_p = decode_map_s16(stg_bin, 0x1D4732, 1.0, 1.0, 0.1) # X: Pressure (hPa), Y: RPM, Val: Nm
fmtc = decode_map_s16(stg_bin, 0x1D729C, 1.0, 0.1, 0.01) # X: RPM, Y: Torque (Nm), Val: IQ (mg)
smoke_map = decode_map_s16(stg_bin, 0x1D6490, 1.0, 1.0, 0.01) # X: RPM, Y: Pres (hPa), Val: IQ (mg)
soi_gear34 = decode_map_s16(stg_bin, 0x1DAAF8, 1.0, 0.01, 0.0234375) # X: RPM, Y: IQ (mg), Val: °CA BTDC
soi_gear56 = decode_map_s16(stg_bin, 0x1DACF8, 1.0, 0.01, 0.0234375)
boost_target_map = decode_map_s16(stg_bin, 0x1EB0B2, 1.0, 0.01, 1.0) # X: RPM, Y: IQ (mg), Val: mbar

# Duration maps
dur_maps = {
    0: decode_map_s16(stg_bin, 0x1E4F3E, 1.0, 0.01, 0.0234375),
    1: decode_map_s16(stg_bin, 0x1E5032, 1.0, 0.01, 0.0234375),
    2: decode_map_s16(stg_bin, 0x1E52B4, 1.0, 0.01, 0.0234375),
    3: decode_map_s16(stg_bin, 0x1E5536, 1.0, 0.01, 0.0234375),
    4: decode_map_s16(stg_bin, 0x1E57B8, 1.0, 0.01, 0.0234375),
    5: decode_map_s16(stg_bin, 0x1E5A3A, 1.0, 0.01, 0.0234375),
    6: decode_map_s16(stg_bin, 0x1E5CBC, 1.0, 0.01, 0.0234375),
}

# InjVlv_numMI1_CUR selector curve:
# X: SOI (AngleCrS), Val: Map_Select (0..6)
dur_sel_curve = decode_curve_s16(stg_bin, 0x1E4F20, 0.0234375, 1.0 / 256.0)

def calc_duration(rpm, iq, soi):
    # Determine map selector from SOI
    map_idx_float = interp_1d(dur_sel_curve['x_axis'], dur_sel_curve['values'], soi)
    # Clamp map_idx_float to available range (0 to 4 in Stage 1)
    map_idx_float = max(0.0, min(4.0, map_idx_float))
    m_low = int(math.floor(map_idx_float))
    m_high = int(math.ceil(map_idx_float))
    frac = map_idx_float - m_low
    dur_low = interp_2d(dur_maps[m_low]['x_axis'], dur_maps[m_low]['y_axis'], dur_maps[m_low]['grid'], rpm, iq)
    dur_high = interp_2d(dur_maps[m_high]['x_axis'], dur_maps[m_high]['y_axis'], dur_maps[m_high]['grid'], rpm, iq)
    dur = dur_low + (dur_high - dur_low) * frac
    return dur, map_idx_float

rpms_to_audit = [1500, 1750, 2000, 2250, 2500, 2750, 3000, 3500, 4000]
gears_to_audit = [3, 4, 5]

audit_results = {}

for gear in gears_to_audit:
    audit_results[gear] = []
    for rpm in rpms_to_audit:
        telem = get_nearest_telemetry(rpm)
        baro = telem['baro']
        act_map = telem['map']
        act_maf = telem['maf']

        # 1 & 2. Driver Wish at 100% pedal
        acc_m = accped_maps[gear]
        dw_trq = interp_2d(acc_m['x_axis'], acc_m['y_axis'], acc_m['grid'], rpm, 100.0)

        # 3. Gear-specific limiter
        gear_lim_curve = gear_trq_limits[gear]
        gear_lim = interp_1d(gear_lim_curve['x_axis'], gear_lim_curve['values'], rpm)

        # 4. Atmospheric / protection limiter
        # In trq_lim_p: X is pressure (700, 850, 900), Y is RPM
        # Note: 1005 hPa is >= 900 hPa node, so clamped to 900 hPa row
        trq_prot = interp_2d(trq_lim_p['x_axis'], trq_lim_p['y_axis'], trq_lim_p['grid'], baro, rpm)

        # 5. Arbitrated torque request
        arb_trq = min(dw_trq, gear_lim, trq_prot)

        # 6. Resulting IQ from FMTC_trq2qBas_MAP
        # Note: FMTC torque axis ends at 336.0 Nm. If arb_trq > 336.0, it is clamped to 336.0!
        fmtc_max_trq = fmtc['y_axis'][-1]
        is_saturated = arb_trq > fmtc_max_trq
        clamped_trq_for_fmtc = min(arb_trq, fmtc_max_trq)
        iq_from_trq = interp_2d(fmtc['x_axis'], fmtc['y_axis'], fmtc['grid'], rpm, clamped_trq_for_fmtc)

        # 7. Smoke limiter IQ at actual boost
        smoke_iq = interp_2d(smoke_map['x_axis'], smoke_map['y_axis'], smoke_map['grid'], rpm, act_map)

        # 8. Binding IQ
        binding_iq = min(iq_from_trq, smoke_iq)
        binding_limiter = "Smoke Limiter (FlMng_qPresSmoke_MAP)" if smoke_iq < iq_from_trq else "Torque Request (DW/TrqLim)"

        # 9 & 11. Commanded SOI
        soi_map = soi_gear34 if gear in [3, 4] else soi_gear56
        soi = interp_2d(soi_map['x_axis'], soi_map['y_axis'], soi_map['grid'], rpm, binding_iq)

        # 10. Commanded Duration
        duration, map_idx = calc_duration(rpm, binding_iq, soi)

        # 12. Commanded EOI = Duration - SOI (°ATDC)
        eoi = duration - soi

        # 13. Boost target vs actual
        boost_des = interp_2d(boost_target_map['x_axis'], boost_target_map['y_axis'], boost_target_map['grid'], rpm, binding_iq)

        entry = {
            'rpm': rpm,
            'gear': gear,
            'driver_wish_trq_nm': round(dw_trq, 2),
            'gear_lim_trq_nm': round(gear_lim, 2),
            'atm_prot_trq_nm': round(trq_prot, 2),
            'arbitrated_trq_nm': round(arb_trq, 2),
            'fmtc_saturated': is_saturated,
            'iq_from_torque_mg': round(iq_from_trq, 2),
            'actual_map_mbar': round(act_map, 1),
            'actual_maf_gs': round(act_maf, 2),
            'smoke_iq_limit_mg': round(smoke_iq, 2),
            'binding_iq_mg': round(binding_iq, 2),
            'binding_limiter': binding_limiter,
            'iq_deficit_mg': round(iq_from_trq - smoke_iq, 2) if smoke_iq < iq_from_trq else 0.0,
            'commanded_soi_btdc': round(soi, 2),
            'duration_map_selected': round(map_idx, 2),
            'commanded_duration_ca': round(duration, 2),
            'commanded_eoi_atdc': round(eoi, 2),
            'boost_target_mbar': round(boost_des, 1),
            'boost_delta_mbar': round(act_map - boost_des, 1),
            'nearest_log_rpm': telem['rpm']
        }
        audit_results[gear].append(entry)

# Print Summary Table
print(f"{'Gear':<4} | {'RPM':<5} | {'DW Nm':<6} | {'Prot Nm':<7} | {'Arb Nm':<6} | {'Trq IQ':<6} | {'Smk IQ':<6} | {'Bind IQ':<7} | {'Limiter':<12} | {'SOI':<5} | {'Dur':<5} | {'EOI':<5} | {'MAP Des':<7} | {'MAP Act':<7}")
print("-" * 115)
for gear in gears_to_audit:
    for e in audit_results[gear]:
        print(f"{e['gear']:<4} | {e['rpm']:<5} | {e['driver_wish_trq_nm']:<6.1f} | {e['atm_prot_trq_nm']:<7.1f} | {e['arbitrated_trq_nm']:<6.1f} | {e['iq_from_torque_mg']:<6.2f} | {e['smoke_iq_limit_mg']:<6.2f} | {e['binding_iq_mg']:<7.2f} | {e['binding_limiter'][:12]:<12} | {e['commanded_soi_btdc']:<5.1f} | {e['commanded_duration_ca']:<5.1f} | {e['commanded_eoi_atdc']:<5.1f} | {e['boost_target_mbar']:<7.0f} | {e['actual_map_mbar']:<7.0f}")

with open('diagnostic-review/wot-chain-audit-2026-09-16.json', 'w', encoding='utf-8') as f:
    json.dump(audit_results, f, indent=2)
print("\nSaved diagnostic-review/wot-chain-audit-2026-09-16.json successfully.")
