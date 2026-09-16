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

def interp_2d(x_nodes, y_nodes, grid, x, y, allow_y_extrap=False):
    # clamp x
    if x <= x_nodes[0]:
        i0, i1, fx = 0, 0, 0.0
    elif x >= x_nodes[-1]:
        i0, i1, fx = len(x_nodes)-1, len(x_nodes)-1, 0.0
    else:
        idx = bisect.bisect_right(x_nodes, x) - 1
        i0, i1 = idx, idx + 1
        fx = (x - x_nodes[i0]) / (x_nodes[i1] - x_nodes[i0])

    # evaluate along y for both i0 and i1
    def get_row_val(row_idx, target_y):
        row = grid[row_idx]
        if target_y <= y_nodes[0]:
            return row[0]
        elif target_y >= y_nodes[-1]:
            if not allow_y_extrap:
                return row[-1]
            else:
                dy = y_nodes[-1] - y_nodes[-2]
                dv = row[-1] - row[-2]
                slope = dv / dy if dy != 0 else 0
                return row[-1] + slope * (target_y - y_nodes[-1])
        else:
            j = bisect.bisect_right(y_nodes, target_y) - 1
            fy = (target_y - y_nodes[j]) / (y_nodes[j+1] - y_nodes[j])
            return row[j] + (row[j+1] - row[j]) * fy

    v0 = get_row_val(i0, y)
    v1 = get_row_val(i1, y)
    return v0 + (v1 - v0) * fx

# Load telemetry specifically for Gear 4 WOT pull
log_data_gear4 = []
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
                log_data_gear4.append({'rpm': rpm, 'map': map_val, 'baro': baro, 'load': load, 'maf': maf, 'speed': speed})
            except ValueError:
                continue

wot_log_gear4 = [d for d in log_data_gear4 if d['load'] >= 90.0]

def get_nearest_telemetry_gear4(rpm_target):
    return min(wot_log_gear4, key=lambda d: abs(d['rpm'] - rpm_target))

# Load Maps with corrected gear assignment per A2L:
# Gear 3: AccPed_trqEng2_MAP @ 0x1C2F7A
# Gear 4: AccPed_trqEng3_MAP @ 0x1C30D0
# Gear 5: AccPed_trqEng4_MAP @ 0x1C3226
accped_maps = {
    3: decode_map_s16(stg_bin, 0x1C2F7A, 1.0, 0.01, 0.1),
    4: decode_map_s16(stg_bin, 0x1C30D0, 1.0, 0.01, 0.1),
    5: decode_map_s16(stg_bin, 0x1C3226, 1.0, 0.01, 0.1),
}

accped_map_names = {
    3: "AccPed_trqEng2_MAP (0x1C2F7A)",
    4: "AccPed_trqEng3_MAP (0x1C30D0)",
    5: "AccPed_trqEng4_MAP (0x1C3226)"
}

gear_trq_limits = {
    3: decode_curve_s16(stg_bin, 0x1D855E, 1.0, 0.1),
    4: decode_curve_s16(stg_bin, 0x1D859C, 1.0, 0.1),
    5: decode_curve_s16(stg_bin, 0x1D85DA, 1.0, 0.1),
}

trq_lim_p = decode_map_s16(stg_bin, 0x1D4732, 1.0, 1.0, 0.1)
fmtc = decode_map_s16(stg_bin, 0x1D729C, 1.0, 0.1, 0.01)
smoke_map = decode_map_s16(stg_bin, 0x1D6490, 1.0, 1.0, 0.01)
soi_gear34 = decode_map_s16(stg_bin, 0x1DAAF8, 1.0, 0.01, 0.0234375)
soi_gear56 = decode_map_s16(stg_bin, 0x1DACF8, 1.0, 0.01, 0.0234375)
boost_target_map = decode_map_s16(stg_bin, 0x1EB0B2, 1.0, 0.01, 1.0)

dur_maps = {
    0: decode_map_s16(stg_bin, 0x1E4F3E, 1.0, 0.01, 0.0234375),
    1: decode_map_s16(stg_bin, 0x1E5032, 1.0, 0.01, 0.0234375),
    2: decode_map_s16(stg_bin, 0x1E52B4, 1.0, 0.01, 0.0234375),
    3: decode_map_s16(stg_bin, 0x1E5536, 1.0, 0.01, 0.0234375),
    4: decode_map_s16(stg_bin, 0x1E57B8, 1.0, 0.01, 0.0234375),
    5: decode_map_s16(stg_bin, 0x1E5A3A, 1.0, 0.01, 0.0234375),
    6: decode_map_s16(stg_bin, 0x1E5CBC, 1.0, 0.01, 0.0234375),
}

dur_sel_curve = decode_curve_s16(stg_bin, 0x1E4F20, 0.0234375, 1.0 / 256.0)

def calc_duration(rpm, iq, soi):
    map_idx_float = interp_1d(dur_sel_curve['x_axis'], dur_sel_curve['values'], soi)
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
    audit_results[str(gear)] = []
    is_gear4 = (gear == 4)
    
    for rpm in rpms_to_audit:
        # Telemetry handling
        if is_gear4:
            telem = get_nearest_telemetry_gear4(rpm)
            baro = telem['baro']
            act_map = telem['map']
            act_maf = telem['maf']
            telem_src = "Turbo_Pair_20260916_112035.csv"
            nearest_rpm = telem['rpm']
        else:
            baro = 1005.0 # nominal sea-level ambient
            act_map = None
            act_maf = None
            telem_src = "UNAVAILABLE (No isolated WOT log for this gear in 20260916 dataset)"
            nearest_rpm = None

        # 1 & 2. Driver Wish at 100% pedal using gear-corrected map
        acc_m = accped_maps[gear]
        dw_trq = interp_2d(acc_m['x_axis'], acc_m['y_axis'], acc_m['grid'], rpm, 100.0)

        # 3. Gear-specific limiter
        gear_lim_curve = gear_trq_limits[gear]
        gear_lim = interp_1d(gear_lim_curve['x_axis'], gear_lim_curve['values'], rpm)

        # 4. Atmospheric / protection limiter at baro pressure
        trq_prot = interp_2d(trq_lim_p['x_axis'], trq_lim_p['y_axis'], trq_lim_p['grid'], baro, rpm)

        # 5. Arbitrated torque request (static min of demand and limits)
        arb_trq = min(dw_trq, gear_lim, trq_prot)

        # 6. Resulting IQ from FMTC_trq2qBas_MAP:
        # Calculate BOTH clamped and extrapolated versions to avoid assumptions!
        fmtc_max_trq = fmtc['y_axis'][-1] # 336.0 Nm
        exceeds_336 = (arb_trq > fmtc_max_trq)
        iq_clamped = interp_2d(fmtc['x_axis'], fmtc['y_axis'], fmtc['grid'], rpm, arb_trq, allow_y_extrap=False)
        iq_extrap = interp_2d(fmtc['x_axis'], fmtc['y_axis'], fmtc['grid'], rpm, arb_trq, allow_y_extrap=True)

        # 7. Smoke limiter IQ:
        # A2L defines input as FlMng_pIATCorr_mp (temperature-corrected pressure), NOT raw MAP!
        # For Gear 4, we evaluate at actual raw MAP as an approximation hypothesis.
        # For Gears 3 and 5, we evaluate at the target boost from PCR_pBDesBas_MAP as a reference hypothesis.
        boost_des_hyp = interp_2d(boost_target_map['x_axis'], boost_target_map['y_axis'], boost_target_map['grid'], rpm, iq_clamped)

        if is_gear4:
            smoke_iq_approx = interp_2d(smoke_map['x_axis'], smoke_map['y_axis'], smoke_map['grid'], rpm, act_map)
            smoke_input_source = "Actual raw MAP from log (proxy for FlMng_pIATCorr_mp)"
            smoke_input_val = act_map
        else:
            smoke_iq_approx = interp_2d(smoke_map['x_axis'], smoke_map['y_axis'], smoke_map['grid'], rpm, boost_des_hyp)
            smoke_input_source = "Specified boost target (reference proxy for FlMng_pIATCorr_mp)"
            smoke_input_val = round(boost_des_hyp, 1)

        # 8. Limiter comparison (STATIC MODEL HYPOTHESIS ONLY - runtime active limiter is UNKNOWN without Group 008)
        static_candidate_limiter = "Smoke Limiter (FlMng_qPresSmoke_MAP, unverified input)" if smoke_iq_approx < iq_clamped else "Torque Path (Driver Wish / TrqLim)"
        binding_iq_static_hyp = min(iq_clamped, smoke_iq_approx)

        # 9 & 11. Commanded SOI
        soi_map = soi_gear34 if gear in [3, 4] else soi_gear56
        soi = interp_2d(soi_map['x_axis'], soi_map['y_axis'], soi_map['grid'], rpm, binding_iq_static_hyp)

        # 10. Commanded Duration
        duration, map_idx = calc_duration(rpm, binding_iq_static_hyp, soi)

        # 12. Electrical command end proxy = Duration - SOI (°ATDC)
        # Note: Proxy only; does not prove physical EOI or torque loss without combustion pressure data.
        eoi_proxy = duration - soi

        entry = {
            'gear': gear,
            'rpm': rpm,
            'accped_map_used': accped_map_names[gear],
            'driver_wish_trq_nm': round(dw_trq, 2),
            'gearbox_lim_trq_nm': round(gear_lim, 2),
            'atm_prot_trq_nm': round(trq_prot, 2),
            'arbitrated_trq_nm': round(arb_trq, 2),
            'fmtc_endpoint_behavior': "UNKNOWN (extrapolation vs clamping unproven without RAM logging)",
            'iq_from_torque_clamped_mg': round(iq_clamped, 2),
            'iq_from_torque_extrapolated_mg': round(iq_extrap, 2),
            'telemetry_source': telem_src,
            'nearest_log_rpm': nearest_rpm,
            'actual_map_mbar': round(act_map, 1) if act_map is not None else None,
            'actual_maf_gs': round(act_maf, 2) if act_maf is not None else None,
            'smoke_map_input_desc': smoke_input_source,
            'smoke_map_input_p_mbar': smoke_input_val,
            'smoke_iq_limit_approx_mg': round(smoke_iq_approx, 2),
            'static_candidate_min_iq_mg': round(binding_iq_static_hyp, 2),
            'static_candidate_limiter': static_candidate_limiter,
            'active_runtime_limiter': "UNKNOWN (requires VCDS Group 008 runtime logging)",
            'iq_deficit_approx_mg': round(iq_clamped - smoke_iq_approx, 2) if smoke_iq_approx < iq_clamped else 0.0,
            'commanded_soi_btdc': round(soi, 2),
            'duration_map_selected': round(map_idx, 2),
            'commanded_duration_ca': round(duration, 2),
            'electrical_command_end_proxy_atdc': round(eoi_proxy, 2),
            'boost_target_mbar': round(boost_des_hyp, 1),
            'boost_delta_mbar': round(act_map - boost_des_hyp, 1) if act_map is not None else None
        }
        audit_results[str(gear)].append(entry)

print("=== REVISED WOT CHAIN AUDIT SUMMARY (EPISTEMICALLY DISCIPLINED) ===")
print(f"{'Gear':<4} | {'RPM':<5} | {'DW Nm':<6} | {'Arb Nm':<6} | {'IQ Clp':<6} | {'IQ Ext':<6} | {'MAP (mbar)':<10} | {'Smk IQ':<6} | {'Cand Min':<8} | {'SOI':<5} | {'Dur':<5} | {'EOI Prx':<7} | {'Telem Source'}")
print("-" * 125)
for gear in gears_to_audit:
    for e in audit_results[str(gear)]:
        act_m = f"{e['actual_map_mbar']:.0f}" if e['actual_map_mbar'] is not None else "UNAVAIL"
        print(f"{e['gear']:<4} | {e['rpm']:<5} | {e['driver_wish_trq_nm']:<6.1f} | {e['arbitrated_trq_nm']:<6.1f} | {e['iq_from_torque_clamped_mg']:<6.2f} | {e['iq_from_torque_extrapolated_mg']:<6.2f} | {act_m:<10} | {e['smoke_iq_limit_approx_mg']:<6.2f} | {e['static_candidate_min_iq_mg']:<8.2f} | {e['commanded_soi_btdc']:<5.1f} | {e['commanded_duration_ca']:<5.1f} | {e['electrical_command_end_proxy_atdc']:<7.1f} | {e['telemetry_source'][:30]}")

with open('diagnostic-review/wot-chain-audit-2026-09-16.json', 'w', encoding='utf-8') as f:
    json.dump(audit_results, f, indent=2)
print("\nUpdated diagnostic-review/wot-chain-audit-2026-09-16.json successfully.")
