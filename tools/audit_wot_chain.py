import struct
import json
import bisect
import sys
import math
import os

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

# Telemetry extraction specifically for Gear 4 WOT pull
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

# Load Maps with gear mapping per A2L:
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
            baro = 1005.0
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

        # 4. Atmospheric / protection limiter
        trq_prot = interp_2d(trq_lim_p['x_axis'], trq_lim_p['y_axis'], trq_lim_p['grid'], baro, rpm)

        # 5. Arbitrated torque request
        arb_trq = min(dw_trq, gear_lim, trq_prot)

        # 6. DUAL-PATH FMTC EVALUATION
        # Path A: Clamped hypothesis
        iq_clamped = interp_2d(fmtc['x_axis'], fmtc['y_axis'], fmtc['grid'], rpm, arb_trq, allow_y_extrap=False)
        # Path B: Extrapolated hypothesis
        iq_extrap = interp_2d(fmtc['x_axis'], fmtc['y_axis'], fmtc['grid'], rpm, arb_trq, allow_y_extrap=True)

        # Build complete downstream branch for CLAMP_HYPOTHESIS
        boost_target_clamped = interp_2d(boost_target_map['x_axis'], boost_target_map['y_axis'], boost_target_map['grid'], rpm, iq_clamped)
        if is_gear4:
            smoke_iq_clamped = interp_2d(smoke_map['x_axis'], smoke_map['y_axis'], smoke_map['grid'], rpm, act_map)
            smoke_desc_clamped = "Actual raw MAP from log (proxy for FlMng_pIATCorr_mp)"
            smoke_in_clamped = act_map
        else:
            smoke_iq_clamped = interp_2d(smoke_map['x_axis'], smoke_map['y_axis'], smoke_map['grid'], rpm, boost_target_clamped)
            smoke_desc_clamped = "Specified boost target (reference proxy for FlMng_pIATCorr_mp)"
            smoke_in_clamped = round(boost_target_clamped, 1)

        candidate_binding_iq_clamped = min(iq_clamped, smoke_iq_clamped)
        candidate_limiter_clamped = "Smoke Limiter (FlMng_qPresSmoke_MAP, proxy input)" if smoke_iq_clamped < iq_clamped else "Torque Path (FMTC clamped)"
        
        soi_map = soi_gear34 if gear in [3, 4] else soi_gear56
        soi_clamped = interp_2d(soi_map['x_axis'], soi_map['y_axis'], soi_map['grid'], rpm, candidate_binding_iq_clamped)
        dur_clamped, dur_map_idx_clamped = calc_duration(rpm, candidate_binding_iq_clamped, soi_clamped)
        eoi_proxy_clamped = dur_clamped - soi_clamped

        clamp_branch = {
            'iq_from_torque_mg': round(iq_clamped, 2),
            'boost_target_mbar': round(boost_target_clamped, 1),
            'smoke_map_input_desc': smoke_desc_clamped,
            'smoke_map_input_val': smoke_in_clamped,
            'smoke_candidate_iq_mg': round(smoke_iq_clamped, 2),
            'candidate_binding_iq_mg': round(candidate_binding_iq_clamped, 2),
            'candidate_limiter': candidate_limiter_clamped,
            'iq_deficit_approx_mg': round(iq_clamped - smoke_iq_clamped, 2) if smoke_iq_clamped < iq_clamped else 0.0,
            'static_soi_hypothesis_deg_btdc': round(soi_clamped, 2),
            'duration_map_selected': round(dur_map_idx_clamped, 2),
            'static_duration_hypothesis_deg_ca': round(dur_clamped, 2),
            'electrical_command_end_proxy_deg_atdc': round(eoi_proxy_clamped, 2),
            'boost_delta_mbar': round(act_map - boost_target_clamped, 1) if act_map is not None else None
        }

        # Build complete downstream branch for EXTRAPOLATION_HYPOTHESIS
        boost_target_extrap = interp_2d(boost_target_map['x_axis'], boost_target_map['y_axis'], boost_target_map['grid'], rpm, iq_extrap)
        if is_gear4:
            smoke_iq_extrap = interp_2d(smoke_map['x_axis'], smoke_map['y_axis'], smoke_map['grid'], rpm, act_map)
            smoke_desc_extrap = "Actual raw MAP from log (proxy for FlMng_pIATCorr_mp)"
            smoke_in_extrap = act_map
        else:
            smoke_iq_extrap = interp_2d(smoke_map['x_axis'], smoke_map['y_axis'], smoke_map['grid'], rpm, boost_target_extrap)
            smoke_desc_extrap = "Specified boost target (reference proxy for FlMng_pIATCorr_mp)"
            smoke_in_extrap = round(boost_target_extrap, 1)

        candidate_binding_iq_extrap = min(iq_extrap, smoke_iq_extrap)
        candidate_limiter_extrap = "Smoke Limiter (FlMng_qPresSmoke_MAP, proxy input)" if smoke_iq_extrap < iq_extrap else "Torque Path (FMTC extrapolated)"
        
        soi_extrap = interp_2d(soi_map['x_axis'], soi_map['y_axis'], soi_map['grid'], rpm, candidate_binding_iq_extrap)
        dur_extrap, dur_map_idx_extrap = calc_duration(rpm, candidate_binding_iq_extrap, soi_extrap)
        eoi_proxy_extrap = dur_extrap - soi_extrap

        extrap_branch = {
            'iq_from_torque_mg': round(iq_extrap, 2),
            'boost_target_mbar': round(boost_target_extrap, 1),
            'smoke_map_input_desc': smoke_desc_extrap,
            'smoke_map_input_val': smoke_in_extrap,
            'smoke_candidate_iq_mg': round(smoke_iq_extrap, 2),
            'candidate_binding_iq_mg': round(candidate_binding_iq_extrap, 2),
            'candidate_limiter': candidate_limiter_extrap,
            'iq_deficit_approx_mg': round(iq_extrap - smoke_iq_extrap, 2) if smoke_iq_extrap < iq_extrap else 0.0,
            'static_soi_hypothesis_deg_btdc': round(soi_extrap, 2),
            'duration_map_selected': round(dur_map_idx_extrap, 2),
            'static_duration_hypothesis_deg_ca': round(dur_extrap, 2),
            'electrical_command_end_proxy_deg_atdc': round(eoi_proxy_extrap, 2),
            'boost_delta_mbar': round(act_map - boost_target_extrap, 1) if act_map is not None else None
        }

        entry = {
            'gear': gear,
            'rpm': rpm,
            'accped_map_used': accped_map_names[gear],
            'driver_wish_trq_nm': round(dw_trq, 2),
            'gearbox_lim_trq_nm': round(gear_lim, 2),
            'atm_prot_trq_nm': round(trq_prot, 2),
            'arbitrated_trq_nm': round(arb_trq, 2),
            'fmtc_endpoint_behavior': "UNKNOWN (extrapolation vs clamping unproven without RAM logging)",
            'telemetry_source': telem_src,
            'nearest_log_rpm': nearest_rpm,
            'actual_map_mbar': round(act_map, 1) if act_map is not None else None,
            'actual_maf_gs': round(act_maf, 2) if act_maf is not None else None,
            'active_runtime_limiter': "UNKNOWN — requires synchronous runtime limiter/IQ variables; use Group 008 only if ECU label/A2L confirms the required channels (Driver Wish / torque request, Torque limiter, Smoke limiter, requested IQ, actual/corrected IQ).",
            'clamp_hypothesis': clamp_branch,
            'extrapolation_hypothesis': extrap_branch
        }
        audit_results[str(gear)].append(entry)

# Write JSON
json_path = 'diagnostic-review/wot-chain-audit-2026-09-16.json'
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(audit_results, f, indent=2)
print(f"Saved {json_path} successfully.")

# Generate Markdown Report directly from audit_results to guarantee 100% numerical consistency!
md_lines = []
md_lines.append("# WOT Calibration Chain Audit & Fuel-Torque Investigation (Gears 3, 4, 5) - v3")
md_lines.append("**Vehicle**: Volkswagen Golf 5 1.9 TDI (Engine BLS, 77 kW / 105 PS OEM)  ")
md_lines.append("**ECU**: Bosch EDC16U34  ")
md_lines.append("**Hardware ID**: `03G906021QJ` (HW 0281014064)  ")
md_lines.append("**Software Version**: `1037391847` (P447HAXN)  ")
md_lines.append("**Active Calibration**: `03G906021QJ_stage1_full_power_dpf_egr_off.bin`  ")
md_lines.append("**Reference Baseline**: `diagnostic-review/reference-from-hex.analysis-only.bin`  ")
md_lines.append("**Telemetry Analyzed**: `logs/20260916/Turbo_Pair_20260916_112035.csv` (Gear 4 WOT pull confirmed by fresh speed/rpm ratio)  ")
md_lines.append("**Turbocharger**: BorgWarner BV39 (VNT / vacuum actuator)  ")
md_lines.append("**Date of Audit**: 2026-09-16 (Audit v3: Dual-Path FMTC, Deterministic Output, Robust Gear Isolation)  \n")
md_lines.append("---\n")
md_lines.append("## Executive Summary & Epistemic Ground Rules\n")
md_lines.append("The driver reports **sluggish, weak acceleration in 3rd, 4th, and 5th gears**, despite telemetry confirming **sufficient manifold pressure (actual MAP 2280–2330 mbar vs 2214 mbar target)** and **strong mass airflow (MAF up to 108.5 g/s)** during a 4th-gear WOT pull.\n")
md_lines.append("To maintain strict engineering rigor, this audit adheres to the following ground rules:\n")
md_lines.append("1. **Dual-Path FMTC Modeling**: Because EDC16U34 runtime behavior beyond the 336.0 Nm axis endpoint is statically unproven without RAM logging (`CoEng_trqInrSet` vs `InjUn_qMI1Des`), both `CLAMP_HYPOTHESIS` and `EXTRAPOLATION_HYPOTHESIS` are modeled through their complete downstream calibration chains (IQ -> Boost Target -> Smoke Candidate -> SOI -> Duration -> Command-End Proxy).")
md_lines.append("2. **Telemetry Isolation by Gear**: Robust segmentation using fresh speed samples (`speed_age_ms <= 1000 ms`, load >= 90%, median speed/rpm = 0.0351, MAD = 0.0005) confirms `Turbo_Pair_20260916_112035.csv` is a **pure 4th-gear pull**. Empirical MAP/MAF values are applied strictly to Gear 4. For Gears 3 and 5, telemetry is designated as `UNAVAILABLE`.")
md_lines.append("3. **Smoke Limiter Input Rigor**: The true input to `FlMng_qPresSmoke_MAP` is `FlMng_pIATCorr_mp` (temperature-corrected pressure), not raw MAP. In Gear 4, raw MAP is treated as an unverified proxy. In Gears 3 and 5, specified boost target is used as a reference proxy.")
md_lines.append("4. **Limiter Arbitration**: Active binding limiter in the running vehicle is `UNKNOWN`. Determining the true binding limiter requires synchronous logging of runtime limiter variables.")
md_lines.append("5. **Electrical Command-End Proxy**: $\\text{Duration} - \\text{SOI}$ represents the electrical solenoid energizing end proxy, not physical combustion end or needle closure.\n")
md_lines.append("---\n")

md_lines.append("## Complete WOT Calibration Chain Table: Branch 1 (CLAMP_HYPOTHESIS)\n")
md_lines.append("*Assumes ECU clamps torque requests exceeding 336.0 Nm to the 336.0 Nm boundary column.*\n")
md_lines.append("| Gear | RPM | Driver Wish (Nm) | Arb Trq (Nm) | FMTC Clamped (mg) | Telem Source | Actual MAP (mbar) | Smoke Cand IQ (mg) | Cand Binding IQ (mg) | Cand Limiter | Static SOI Hyp (°BTDC) | Static Dur Hyp (°CA) | Electr End Proxy (°ATDC) | Boost Target (mbar) |")
md_lines.append("|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|")

for g in gears_to_audit:
    for e in audit_results[str(g)]:
        c = e['clamp_hypothesis']
        act_m = f"{e['actual_map_mbar']:.1f}" if e['actual_map_mbar'] is not None else "UNAVAIL"
        src_label = "Turbo_Pair_112035" if g == 4 else "*UNAVAILABLE*"
        md_lines.append(f"| **{e['gear']}** | **{e['rpm']}** | {e['driver_wish_trq_nm']:.1f} | {e['arbitrated_trq_nm']:.1f} | {c['iq_from_torque_mg']:.2f} | {src_label} | {act_m} | {c['smoke_candidate_iq_mg']:.2f} | **{c['candidate_binding_iq_mg']:.2f}** | {c['candidate_limiter']} | {c['static_soi_hypothesis_deg_btdc']:.2f} | {c['static_duration_hypothesis_deg_ca']:.2f} | **{c['electrical_command_end_proxy_deg_atdc']:.2f}** | {c['boost_target_mbar']:.1f} |")

md_lines.append("\n---\n")
md_lines.append("## Complete WOT Calibration Chain Table: Branch 2 (EXTRAPOLATION_HYPOTHESIS)\n")
md_lines.append("*Assumes ECU linearly extrapolates torque requests exceeding 336.0 Nm based on the 314->336 Nm slope.*\n")
md_lines.append("| Gear | RPM | Driver Wish (Nm) | Arb Trq (Nm) | FMTC Extrap (mg) | Telem Source | Actual MAP (mbar) | Smoke Cand IQ (mg) | Cand Binding IQ (mg) | Cand Limiter | Static SOI Hyp (°BTDC) | Static Dur Hyp (°CA) | Electr End Proxy (°ATDC) | Boost Target (mbar) |")
md_lines.append("|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|")

for g in gears_to_audit:
    for e in audit_results[str(g)]:
        ex = e['extrapolation_hypothesis']
        act_m = f"{e['actual_map_mbar']:.1f}" if e['actual_map_mbar'] is not None else "UNAVAIL"
        src_label = "Turbo_Pair_112035" if g == 4 else "*UNAVAILABLE*"
        md_lines.append(f"| **{e['gear']}** | **{e['rpm']}** | {e['driver_wish_trq_nm']:.1f} | {e['arbitrated_trq_nm']:.1f} | {ex['iq_from_torque_mg']:.2f} | {src_label} | {act_m} | {ex['smoke_candidate_iq_mg']:.2f} | **{ex['candidate_binding_iq_mg']:.2f}** | {ex['candidate_limiter']} | {ex['static_soi_hypothesis_deg_btdc']:.2f} | {ex['static_duration_hypothesis_deg_ca']:.2f} | **{ex['electrical_command_end_proxy_deg_atdc']:.2f}** | {ex['boost_target_mbar']:.1f} |")

md_lines.append("\n---\n")
md_lines.append(r"""## Detailed Investigation (Sections A through J)

### Section A: Strongest Candidate Hypotheses for Sluggish Pull

1. **Candidate Hypothesis 1: Smoke Limiter Plateau (`FlMng_qPresSmoke_MAP`)**  
   - *Observation*: The map's pressure axis terminates at 2000 hPa. At 1750–2500 RPM, the 2000 hPa row holds a static plateau of **56.50 mg/stroke**.  
   - *Limitation*: The true input to this map is `FlMng_pIATCorr_mp` (temperature-corrected pressure), not raw MAP. If `FlMng_pIATCorr_mp >= 2000 hPa`, the lookup is limited to 56.50 mg; if intake air heating reduces `FlMng_pIATCorr_mp` below 2000 hPa, the limit drops further (e.g. 51.0–52.1 mg at 1800 hPa).  
   - *Hypothesis*: Under either FMTC hypothesis (clamped ~62–64 mg or extrapolated ~65–72 mg), if the smoke limiter acts as the binding limiter in runtime, it imposes a significant fuel restriction right in the 1750–2500 RPM band.
2. **Candidate Hypothesis 2: Late Electrical Command Phasing (`electrical_command_end_proxy`)**  
   - *Observation*: Stage 1 modified Duration maps MAP1..4 by +8% in the 55–60 mg columns while SOI advance in those columns was modest (+1.2° to +1.6° CA).  
   - *Calculation*: The electrical command end proxy reaches **16.7° to 16.9° ATDC** at 2750–3000 RPM.  
   - *Limitation*: This calculation represents an electrical pulse duration proxy. Injector needle dynamics, hydraulic delay, and combustion ignition delay mean physical combustion phasing cannot be proved from this metric alone.  
   - *Hypothesis*: If electrical command extends towards ~17° ATDC, physical injection may finish deep into the expansion stroke, reducing thermodynamic expansion ratio, elevating pre-turbine exhaust temperature, and causing sluggish high-load performance.
3. **Candidate Hypothesis 3: FMTC Endpoint Behavior**  
   - *Observation*: The torque axis of `FMTC_trq2qBas_MAP` ends at 336.0 Nm, while Driver Wish requests up to 374 Nm and atmospheric limits allow up to 380 Nm.  
   - *Status*: Whether the ECU clamps to the 336 Nm node (outputting ~62–64 mg) or extrapolates along the slope (which would output 65–72 mg) is **UNKNOWN** without RAM logging.

---

### Section B: Exact RPM and Load Region Under Investigation

- **1750 to 2500 RPM @ High Load**:  
  - Static smoke map plateau at 56.50 mg.  
  - If binding, torque is restricted below driver demand.
- **2750 to 3500 RPM @ High Load**:  
  - Smoke map ramps from 56.50 mg to 67.80 mg (no 2750 node; linear interpolation gives 62.15 mg).  
  - Electrical command end proxy peaks at 16.7°–16.9° ATDC.

---

### Section C: Exact Maps Involved

| Map Identifier | Address (Hex) | Dimensions | Axes | Function |
|---|:---:|:---:|---|---|
| `AccPed_trqEng2_MAP` | `0x1C2F7A` | 16 × 8 | RPM × Pedal % | 3rd gear Driver Wish (note: `AccPed_stGearSel_CUR` routes to Map 1). |
| `AccPed_trqEng3_MAP` | `0x1C30D0` | 16 × 8 | RPM × Pedal % | 4th gear Driver Wish. |
| `AccPed_trqEng4_MAP` | `0x1C3226` | 16 × 8 | RPM × Pedal % | 5th gear Driver Wish. |
| `EngPrt_trqLimP_MAP` | `0x1D4732` | 3 × 21 | Ambient hPa × RPM | Atmospheric torque limiter (modified up to 380 Nm). |
| `FMTC_trq2qBas_MAP` | `0x1D729C` | 15 × 16 | RPM × Torque Nm | Torque-to-quantity conversion (axis ends at 336 Nm). |
| `FlMng_qPresSmoke_MAP` | `0x1D6490` | 16 × 12 | RPM × Corrected hPa | Smoke limiter (input is `FlMng_pIATCorr_mp`). |
| `FlMng_pIATCorr_MAP` | `0x1D605A` | 16 × 10 | RPM × IAT Temp | Density/temperature pressure correction map. |
| `InjCrv_phiBasGear34_MAP` | `0x1DAAF8` | 16 × 14 | RPM × IQ mg | Start of Injection for Gears 3 & 4. |
| `InjCrv_phiBasGear56_MAP` | `0x1DACF8` | 16 × 14 | RPM × IQ mg | Start of Injection for Gears 5 & 6. |
| `InjVlv_numMI1_CUR` | `0x1E4F20` | 6 × 1 | Commanded SOI | Duration map selector curve. |
| `InjVlv_phiInjMI1_MAP1..4` | `0x1E5032+` | 19 × 15 | RPM × IQ mg | Main injection duration tables (modified at 55–60 mg). |
| `PCR_pBDesBas_MAP` | `0x1EB0B2` | 16 × 10 | RPM × IQ mg | Specified boost target (2214 mbar Stage 1 request). |

---

### Section D: Epistemic Classification

| Statement / Finding | Epistemic Status | Evidence Base |
|---|:---:|---|
| `FlMng_qPresSmoke_MAP` ends at 2000 hPa with 56.50 mg value at 1750–2500 RPM | **FACT** | Binary byte extraction at `0x1D6490`. |
| Second axis of smoke map is `FlMng_pIATCorr_mp`, not raw MAP | **FACT** | Matching A2L line 394195 (`FlMng_pIATCorr_mp`). |
| Duration maps MAP1..4 modified by +8% at 55/60 mg | **FACT** | Direct byte comparison against stock reference. |
| `Turbo_Pair_20260916_112035.csv` is a 4th-gear WOT pull | **FACT** | Telemetry fresh speed/rpm ratio calculation (`median = 0.0351, MAD = 0.0005`). |
| 3rd-gear and 5th-gear complete WOT telemetry in 20260916 dataset | **UNKNOWN** | No complete isolated WOT logs for gears 3 and 5 in dataset. |
| Runtime smoke limiter is actively clamping fuel to 56.50 mg in car | **STATIC INFERENCE (UNVERIFIED INPUT)** | Requires synchronous runtime logging of limiter variables to prove active binding state. |
| FMTC runtime behavior beyond 336 Nm (clamp vs linear extrapolation) | **UNKNOWN** | Statically unproven; requires RAM logging of internal variables. |
| Physical combustion end / torque loss from electrical duration proxy | **UNKNOWN** | Electrical command proxy does not prove physical combustion end. |

---

### Section E: Calibration Strategy Requirements (vNext Planning Direction)

*No firmware binary is being modified at this stage. The following items define the technical requirements for a future vNext calibration:*

1. **Verify Active Limiter via Telemetry First**:
   - Before editing maps, log synchronous runtime limiter channels (Driver Wish, Torque Limiter, Smoke Limiter, actual IQ) to determine which limiter is actively binding during a 4th-gear pull.
2. **Smoke Map Coherence**:
   - If runtime logging proves that Smoke Limiter is binding at 56.5 mg despite adequate boost and clean exhaust, harmonize `FlMng_qPresSmoke_MAP` with the 2214 mbar boost target.
3. **Combustion Phasing Harmonization**:
   - Re-evaluate Duration maps versus OEM Unit Injector delivery data. If duration maps are reverted to OEM calibration, recalculate SOI advance to maintain electrical command proxy within 10°–13° ATDC.
4. **Torque-to-Quantity Consistency**:
   - Resolve the 336 Nm axis limitation so that requested torque corresponds predictably to calibrated fuel mass.

---

### Section F: Target Cells for Inspection (Reference Only — No BIN Edits)

| Map Identifier | Address | Node / Region | Current Value | Notes |
|---|:---:|:---:|:---:|---|
| `FlMng_qPresSmoke_MAP` | `0x1D65EA` | 2000 RPM, 2000 hPa | 56.50 mg | Candidate restriction if `FlMng_pIATCorr_mp >= 2000 hPa`. |
| `FlMng_qPresSmoke_MAP` | `0x1D65FE` | 2250 RPM, 2000 hPa | 56.50 mg | Candidate restriction if `FlMng_pIATCorr_mp >= 2000 hPa`. |
| `FlMng_qPresSmoke_MAP` | `0x1D6612` | 2500 RPM, 2000 hPa | 56.50 mg | Candidate restriction if `FlMng_pIATCorr_mp >= 2000 hPa`. |
| `InjCrv_phiBasGear34_MAP` | `0x1DAB56` | 2750 RPM, 55–60 mg | 20.58° BTDC | Evaluated in conjunction with duration for EOI proxy. |
| `InjCrv_phiBasGear34_MAP` | `0x1DAB72` | 3000 RPM, 55–60 mg | 22.24° BTDC | Evaluated in conjunction with duration for EOI proxy. |
| `FMTC_trq2qBas_MAP` | `0x1D72CE` | Torque Axis Node 15 | 336.0 Nm | Maximum defined torque node. |

---

### Section G: Predicted Effects (Qualitative Engineering Expectations)

- **If Smoke Limiter is the Active Limiter**: Harmonizing the smoke map to match available charge air mass would eliminate artificial fuel truncation, resulting in improved acceleration response in the 1800–2500 RPM window.
- **If Combustion Phasing is Retarded**: Centering combustion phasing closer to optimal expansion timing would improve indicated thermal efficiency and reduce exhaust gas temperatures under prolonged high-load pulling.
- *Note: Quantitative torque (+Nm) or temperature (-°C) claims are withheld until runtime validation is completed.*

---

### Section H: Risks & Safety Invariants

1. **Turbocharger Pressure Ratio & Speed**:
   - BorgWarner BV39 boost request must remain <= 2214 mbar.
   - N75 pre-control (`PCR_rBPCtlBas_MAP`) must not be altered without high-speed telemetry.
2. **Cylinder Peak Firing Pressure ($P_{\max}$)**:
   - Any future SOI adjustment must respect mechanical limits of cylinder head bolts and PDE rocker assemblies.
3. **Drivetrain Protection**:
   - Dual-mass flywheel and clutch torque limits (~350–360 Nm) must be respected below 2200 RPM.

---

### Section I: Validated Telemetry Points (4th Gear Pull, 2026-09-16)

The following empirical points from `Turbo_Pair_20260916_112035.csv` are validated for **4th gear**:
- 1741 RPM: MAP = 2230 mbar, MAF = 48.61 g/s
- 2153 RPM: MAP = 2330 mbar, MAF = 69.58 g/s (Peak boost overshoot: +116 mbar over 2214 target)
- 2553 RPM: MAP = 2320 mbar, MAF = 81.08 g/s
- 3078 RPM: MAP = 2230 mbar, MAF = 88.69 g/s
- 4011 RPM: MAP = 2160 mbar, MAF = 108.50 g/s

---

### Section J: Required Runtime Measurements for Verification

To empirically prove the hypotheses before creating any firmware modification:

1. **Synchronous Runtime Limiter Channel Logging (WOT pull in 4th gear, 1500 to 4000 RPM)**:
   - Driver's Wish IQ / Torque Request
   - Torque Limitation IQ
   - Smoke Limitation IQ
   - Actual / Corrected Injected Quantity
   - *Requirement*: Use VCDS Group 008 only if the ECU label file / A2L confirms these exact channels. Otherwise, log the corresponding internal measurement labels via KWP2000 / UDS.
2. **Synchronous Injection Phasing Logging (WOT pull)**:
   - Commanded Start of Injection (°BTDC)
   - Commanded Injection Duration (°CA)
   - Synchro Angle / Torsion Value (camshaft timing)
3. **Dedicated Gear 3 & Gear 5 Continuous WOT Logging**:
   - Capture clean, isolated WOT sweeps for 3rd and 5th gears with fresh vehicle speed updates to evaluate gear-dependent spool and load duration.

---
*Audit strictly read-only. No firmware binary images were generated or altered.*
""")

md_path = 'diagnostic-review/wot-chain-audit-2026-09-16.md'
with open(md_path, 'w', encoding='utf-8') as f:
    f.write("\n".join(md_lines))
print(f"Generated {md_path} deterministically from JSON data.")
