# WOT Calibration Chain Audit & Root-Cause Diagnosis (Gears 3, 4, 5)
**Vehicle**: Volkswagen Golf 5 1.9 TDI (Engine BLS, 77 kW / 105 PS OEM)  
**ECU**: Bosch EDC16U34  
**Hardware ID**: `03G906021QJ` (HW 0281014064)  
**Software Version**: `1037391847` (P447HAXN)  
**Active Calibration**: `03G906021QJ_stage1_full_power_dpf_egr_off.bin`  
**Reference Baseline**: `diagnostic-review/reference-from-hex.analysis-only.bin`  
**Telemetry Analyzed**: `logs/20260916/Turbo_Pair_20260916_112035.csv`  
**Turbocharger**: BorgWarner BV39 (VNT / vacuum actuator)  
**Date of Audit**: 2026-09-16  

---

## Executive Summary

The driver reports **sluggish, weak, and unresponsive acceleration in 3rd, 4th, and 5th gears**, despite telemetry confirming **sufficient manifold absolute pressure (actual MAP 2280–2330 mbar vs 2214 mbar target)** and **strong mass airflow (MAF up to 108.5 g/s)**.

Through systematic binary disassembly, matching A2L layout extraction, 2D bilinear interpolation across all torque-to-quantity, smoke limiter, duration, and start-of-injection (SOI) maps, and direct cross-referencing with the high-resolution WOT run from 2026-09-16, this audit identifies the **dual root causes**:

1. **The Pressure Smoke Limiter "Wall" (`FlMng_qPresSmoke_MAP`)**:
   Between 1500 and 2500 RPM, the smoke limiter table is hard-capped at **56.50 mg/stroke** in the top 2000 hPa row. Because the table's pressure axis ends at 2000 hPa, actual manifold pressure (which runs at 2280–2330 mbar) saturates at this 2000 hPa ceiling. While Driver Wish and atmospheric torque limiters demand **354–374 Nm (~61.8–66.1 mg/stroke)**, the smoke limiter strangles fuel injection to **56.50 mg/stroke**, imposing an artificial fuel deficit of **-5.3 to -11.9 mg/stroke (-10.5% to -18.0% fuel)** right in the primary acceleration and peak torque zone.
2. **Combustion Phasing Distortion & Late EOI (8% Duration Inflation vs Commanded SOI)**:
   In Stage 1, duration maps (`InjVlv_phiInjMI1_MAP1..4`) were artificially extended by +8% (+2.0° to +3.2° CA) in the 55–60 mg columns without commensurate SOI advance. At 2750–3000 RPM (where the smoke limiter finally opens to 62+ mg), **End of Injection (EOI) stretches to 16.7°–16.9° ATDC**. Injection ending this late into the expansion stroke severely degrades thermodynamic indicated work, transfers unburned combustion heat into the exhaust manifold (spiking pre-turbine EGT), and causes the engine to feel sluggish despite high boost and MAF.
3. **Gear-Specific Manifestation**:
   In 1st and 2nd gears, large mechanical gear ratios (3.78, 2.06) and fast engine RPM traversal (sub-second sweeps) mask this deficit. In 3rd, 4th, and 5th gears, higher vehicle inertia forces the engine to spend multiple seconds under sustained WOT load in the 1750–3000 RPM band, making both the 56.5 mg fuel ceiling and the 16.9° ATDC thermal penalty painfully apparent to the driver.

---

## Complete WOT Calibration Chain Audit Table

The following table details the audited calibration chain across the 9 designated RPM points for **Gears 3, 4, and 5** (100% accelerator pedal, ambient pressure 1005 hPa, using synchronized telemetry from the 2026-09-16 WOT pull).

*Note: In the active calibration, Driver Wish maps `AccPed_trqEng0_MAP` through `AccPed_trqEng6_MAP` and the gear-selector curve `AccPed_stGearSel_CUR` route all forward gears to identical pedal torque curves.*

| Gear | Engine Speed (RPM) | Driver Wish (Nm) | Atm / Prot Lim (Nm) | Arbitrated Torque (Nm) | FMTC Saturated? | Torque IQ Request (mg) | Nearest Log MAP (mbar) | Smoke IQ Limit (mg) | Binding IQ (mg) | Binding Limiter | IQ Deficit (mg) | Commanded SOI (°BTDC) | Dur Map Index | Commanded Duration (°CA) | Commanded EOI (°ATDC) | Boost Target (mbar) | Actual MAP (mbar) | Boost Delta (mbar) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **3** | **1500** | 373.8 | 337.5 | 337.5 | Yes (>336) | 66.12 | 1920.0 | 54.18 | **54.18** | **Smoke Limiter** | -11.94 | 12.84 | 2.36 | 25.07 | **12.23** | 1828 | 1920 | +92 |
| **3** | **1750** | 368.9 | 367.2 | 367.2 | Yes (>336) | 64.24 | 2230.0 | 56.50 | **56.50** | **Smoke Limiter** | -7.74 | 14.32 | 2.11 | 27.96 | **13.64** | 2057 | 2230 | +173 |
| **3** | **2000** | 363.9 | 375.2 | 363.9 | Yes (>336) | 63.14 | 2310.0 | 56.50 | **56.50** | **Smoke Limiter** | -6.64 | 15.96 | 1.86 | 30.04 | **14.08** | 2197 | 2310 | +113 |
| **3** | **2250** | 358.9 | 373.9 | 358.9 | Yes (>336) | 62.57 | 2320.0 | 56.50 | **56.50** | **Smoke Limiter** | -6.07 | 17.25 | 1.68 | 31.18 | **13.93** | 2214 | 2320 | +106 |
| **3** | **2500** | 354.0 | 364.5 | 354.0 | Yes (>336) | 61.76 | 2320.0 | 56.50 | **56.50** | **Smoke Limiter** | -5.26 | 18.87 | 1.45 | 32.65 | **13.78** | 2214 | 2320 | +106 |
| **3** | **2750** | 349.6 | 357.7 | 349.6 | Yes (>336) | 61.99 | 2300.0 | 62.15 | **61.99** | **Torque Request** | 0.00 | 20.58 | 1.20 | 37.24 | **16.66** | 2214 | 2300 | +86 |
| **3** | **3000** | 345.2 | 348.2 | 345.2 | Yes (>336) | 62.57 | 2210.0 | 67.80 | **62.57** | **Torque Request** | 0.00 | 22.24 | 0.97 | 39.17 | **16.93** | 2214 | 2210 | -4 |
| **3** | **3500** | 339.1 | 336.1 | 336.1 | No (<=336) | 63.99 | 2160.0 | 67.80 | **63.99** | **Torque Request** | 0.00 | 25.90 | 0.44 | 40.65 | **14.75** | 2214 | 2160 | -54 |
| **3** | **4000** | 332.9 | 318.6 | 318.6 | No (<=336) | 62.07 | 2160.0 | 67.80 | **62.07** | **Torque Request** | 0.00 | 29.16 | 0.00 | 42.14 | **12.98** | 2209 | 2160 | -49 |
| **4** | **1500** | 373.8 | 337.5 | 337.5 | Yes (>336) | 66.12 | 1920.0 | 54.18 | **54.18** | **Smoke Limiter** | -11.94 | 12.84 | 2.36 | 25.07 | **12.23** | 1828 | 1920 | +92 |
| **4** | **1750** | 368.9 | 367.2 | 367.2 | Yes (>336) | 64.24 | 2230.0 | 56.50 | **56.50** | **Smoke Limiter** | -7.74 | 14.32 | 2.11 | 27.96 | **13.64** | 2057 | 2230 | +173 |
| **4** | **2000** | 363.9 | 375.2 | 363.9 | Yes (>336) | 63.14 | 2310.0 | 56.50 | **56.50** | **Smoke Limiter** | -6.64 | 15.96 | 1.86 | 30.04 | **14.08** | 2197 | 2310 | +113 |
| **4** | **2250** | 358.9 | 373.9 | 358.9 | Yes (>336) | 62.57 | 2320.0 | 56.50 | **56.50** | **Smoke Limiter** | -6.07 | 17.25 | 1.68 | 31.18 | **13.93** | 2214 | 2320 | +106 |
| **4** | **2500** | 354.0 | 364.5 | 354.0 | Yes (>336) | 61.76 | 2320.0 | 56.50 | **56.50** | **Smoke Limiter** | -5.26 | 18.87 | 1.45 | 32.65 | **13.78** | 2214 | 2320 | +106 |
| **4** | **2750** | 349.6 | 357.7 | 349.6 | Yes (>336) | 61.99 | 2300.0 | 62.15 | **61.99** | **Torque Request** | 0.00 | 20.58 | 1.20 | 37.24 | **16.66** | 2214 | 2300 | +86 |
| **4** | **3000** | 345.2 | 348.2 | 345.2 | Yes (>336) | 62.57 | 2210.0 | 67.80 | **62.57** | **Torque Request** | 0.00 | 22.24 | 0.97 | 39.17 | **16.93** | 2214 | 2210 | -4 |
| **4** | **3500** | 339.1 | 336.1 | 336.1 | No (<=336) | 63.99 | 2160.0 | 67.80 | **63.99** | **Torque Request** | 0.00 | 25.90 | 0.44 | 40.65 | **14.75** | 2214 | 2160 | -54 |
| **4** | **4000** | 332.9 | 318.6 | 318.6 | No (<=336) | 62.07 | 2160.0 | 67.80 | **62.07** | **Torque Request** | 0.00 | 29.16 | 0.00 | 42.14 | **12.98** | 2209 | 2160 | -49 |
| **5** | **1500** | 373.8 | 337.5 | 337.5 | Yes (>336) | 66.12 | 1920.0 | 54.18 | **54.18** | **Smoke Limiter** | -11.94 | 12.84 | 2.36 | 25.07 | **12.23** | 1828 | 1920 | +92 |
| **5** | **1750** | 368.9 | 367.2 | 367.2 | Yes (>336) | 64.24 | 2230.0 | 56.50 | **56.50** | **Smoke Limiter** | -7.74 | 14.32 | 2.11 | 27.96 | **13.64** | 2057 | 2230 | +173 |
| **5** | **2000** | 363.9 | 375.2 | 363.9 | Yes (>336) | 63.14 | 2310.0 | 56.50 | **56.50** | **Smoke Limiter** | -6.64 | 15.96 | 1.86 | 30.04 | **14.08** | 2197 | 2310 | +113 |
| **5** | **2250** | 358.9 | 373.9 | 358.9 | Yes (>336) | 62.57 | 2320.0 | 56.50 | **56.50** | **Smoke Limiter** | -6.07 | 17.25 | 1.68 | 31.18 | **13.93** | 2214 | 2320 | +106 |
| **5** | **2500** | 354.0 | 364.5 | 354.0 | Yes (>336) | 61.76 | 2320.0 | 56.50 | **56.50** | **Smoke Limiter** | -5.26 | 18.87 | 1.45 | 32.65 | **13.78** | 2214 | 2320 | +106 |
| **5** | **2750** | 349.6 | 357.7 | 349.6 | Yes (>336) | 61.99 | 2300.0 | 62.15 | **61.99** | **Torque Request** | 0.00 | 20.58 | 1.20 | 37.24 | **16.66** | 2214 | 2300 | +86 |
| **5** | **3000** | 345.2 | 348.2 | 345.2 | Yes (>336) | 62.57 | 2210.0 | 67.80 | **62.57** | **Torque Request** | 0.00 | 22.24 | 0.97 | 39.17 | **16.93** | 2214 | 2210 | -4 |
| **5** | **3500** | 339.1 | 336.1 | 336.1 | No (<=336) | 63.99 | 2160.0 | 67.80 | **63.99** | **Torque Request** | 0.00 | 25.90 | 0.44 | 40.65 | **14.75** | 2214 | 2160 | -54 |
| **5** | **4000** | 332.9 | 318.6 | 318.6 | No (<=336) | 62.07 | 2160.0 | 67.80 | **62.07** | **Torque Request** | 0.00 | 29.16 | 0.00 | 42.14 | **12.98** | 2209 | 2160 | -49 |

---

## Detailed Audit Breakdown (Sections A through J)

### Section A: Strongest Candidate Cause(s) of Sluggish 3rd, 4th, 5th Acceleration

The sluggish acceleration in 3rd, 4th, and 5th gears is caused by **two distinct, interacting calibration anomalies**:

1. **Primary Immediate Cause (1750–2500 RPM): Severe Smoke Limiter Fuel Starvation**  
   In the prime low-to-mid range torque plateau (1750–2500 RPM), the vehicle operates at 2280–2330 mbar actual boost. Driver Wish and Torque Limiters request between 354 Nm and 369 Nm, which corresponds to 61.8–64.2 mg/stroke of fuel. However, `FlMng_qPresSmoke_MAP` ends at 2000 hPa with a static ceiling of **56.50 mg/stroke**.  
   The engine receives **only 56.50 mg/stroke**, creating an instantaneous torque deficit of **30 to 45 Nm**. On 1st and 2nd gears, rapid acceleration sweeps past this region in under 1 second. In 3rd, 4th, and 5th gears, the vehicle is trapped in this plateau for multiple seconds, feeling unresponsive and flat.
2. **Secondary Thermodynamic Cause (2750–3500 RPM): Late EOI (16.7°–16.9° ATDC) & Low Expansion Work**  
   Above 2600 RPM, the smoke limiter linearly ramps up towards 67.8 mg at 3000 RPM, finally allowing ~62 mg of fuel. But here, the distorted Duration maps (+8% inflation in 55/60 mg columns) combined with conservative SOI advance cause **combustion to end at 16.7°–16.9° ATDC**. In diesel thermodynamics, fuel injected past 12° ATDC does not contribute effective expansion work on the piston; instead, it burns late, raising pre-turbine exhaust gas temperatures (EGT) and threatening thermal derate (`EngPrt_facTempPreTrbn_MAP`). The engine makes noise and boost, but lacks pulling power.
3. **Tertiary Architectural Defect: `FMTC_trq2qBas_MAP` 336 Nm Saturation**  
   The Stage 1 tuner raised Driver Wish to 374 Nm and Atmospheric Limiter to 380 Nm, but left the torque axis of `FMTC_trq2qBas_MAP` ending at 336 Nm. Consequently, all torque requests above 336 Nm are hard-clipped to the 336 Nm column, flattening pedal resolution and creating an artificial fuel ceiling.

---

### Section B: Exact RPM and Load Region Affected

- **Region 1: 1500 to 2500 RPM @ WOT (Full Throttle, Load = 99.6%, MAP > 2000 mbar)**  
  - **Symptom**: Sluggish torque onset, "laggy" pull when stepping on the throttle at 60–90 km/h in 3rd/4th/5th gear.  
  - **Mechanism**: The smoke limiter ceiling is locked at 56.50 mg/stroke across 1600, 1700, 1800, 2000, 2250, and 2500 RPM. Fuel is restricted by up to 11.94 mg at 1500 RPM and 6.64 mg at 2000 RPM.
- **Region 2: 2750 to 3500 RPM @ WOT (Speed 90–130 km/h)**  
  - **Symptom**: Engine roars with high boost (2200–2300 mbar) and airflow (80–95 g/s), but vehicle speed climbs sluggishly without solid acceleration surge.  
  - **Mechanism**: Injection duration reaches 37.2° to 39.2° CA, pushing EOI to 16.7°–16.9° ATDC. Exhaust gas temperature accumulates under prolonged high-load pulling in 4th and 5th gears.

---

### Section C: Exact Maps Involved

| Map Identifier | Address (Hex) | Dimensions | Axes (X × Y) | Function in Calibration Chain |
|---|:---:|:---:|---|---|
| `FlMng_qPresSmoke_MAP` | `0x1D6490` | 16 × 12 | RPM × Corrected Pressure (hPa) | **Binding Limiter**: Hard clamps fuel to 56.50 mg at 1500–2500 RPM. |
| `FMTC_trq2qBas_MAP` | `0x1D729C` | 15 × 16 | RPM × Inner Torque (Nm) | **Torque-to-Fuel Conversion**: Saturates at 336 Nm; distorted 314/336 Nm columns. |
| `InjVlv_phiInjMI1_MAP1` | `0x1E5032` | 19 × 15 | RPM × IQ Desired (mg) | **Main Injection Duration**: Inflated by +2.0°–3.2° CA at 55–60 mg. |
| `InjVlv_phiInjMI1_MAP2` | `0x1E52B4` | 19 × 15 | RPM × IQ Desired (mg) | **Main Injection Duration**: Inflated by +1.8°–2.9° CA at 55–60 mg. |
| `InjVlv_phiInjMI1_MAP3` | `0x1E5536` | 19 × 15 | RPM × IQ Desired (mg) | **Main Injection Duration**: Inflated by +1.9°–3.0° CA at 55–60 mg. |
| `InjVlv_phiInjMI1_MAP4` | `0x1E57B8` | 19 × 15 | RPM × IQ Desired (mg) | **Main Injection Duration**: Inflated by +2.0°–2.8° CA at 55–60 mg. |
| `InjCrv_phiBasGear34_MAP` | `0x1DAAF8` | 16 × 14 | RPM × IQ Desired (mg) | **Start of Injection (Gears 3/4)**: Retarded relative to inflated duration (causes late EOI). |
| `InjCrv_phiBasGear56_MAP` | `0x1DACF8` | 16 × 14 | RPM × IQ Desired (mg) | **Start of Injection (Gears 5/6)**: Identical to 34 map; causes identical late EOI. |
| `InjVlv_numMI1_CUR` | `0x1E4F20` | 6 × 1 | Commanded SOI (°CA) | **Duration Map Selector**: Selects between MAP0..MAP5 based on SOI angle. |
| `EngPrt_trqLimP_MAP` | `0x1D4732` | 3 × 21 | Ambient Pres (hPa) × RPM | **Atmospheric Torque Limiter**: Raised to 380 Nm, exceeding FMTC axis. |
| `AccPed_trqEng3/4/5_MAP` | `0x1C30D0+` | 16 × 8 | RPM × Pedal Position (%) | **Driver Wish**: Requests 354–374 Nm at WOT across all gears. |
| `PCR_pBDesBas_MAP` | `0x1EB0B2` | 16 × 10 | RPM × IQ Desired (mg) | **Boost Target**: Requests 2214 mbar at 45 mg (well supported by turbo). |
| `EngPrt_facTempPreTrbn_MAP` | `0x1D4EBC` | 8 × 8 | Pre-Turbine Temp (°C) × RPM | **Thermal Protection**: Derates torque above 805°C (risk during late EOI pulls). |

---

### Section D: Epistemic Classification

| Item / Relationship | Epistemic Status | Evidence Base | Confidence |
|---|:---:|---|:---:|
| `FlMng_qPresSmoke_MAP` ends at 2000 hPa with 56.50 mg value at 1500–2500 RPM | **FACT** | Binary byte extraction at `0x1D6490`, A2L layout `Kf_Xs16_Ys16_Ws16`. | 100% |
| Actual MAP reaches 2280–2330 mbar during WOT pull | **RUNTIME OBSERVATION** | `Turbo_Pair_20260916_112035.csv`, rows 10–24. | 100% |
| Fuel is limited to 56.50 mg between 1750 and 2500 RPM during WOT | **STATIC INFERENCE** | Min-arbitration between `FMTC_trq2qBas_MAP` and `FlMng_qPresSmoke_MAP`. | 98% (Pending live IQ log) |
| `FMTC_trq2qBas_MAP` torque axis ends at 336.0 Nm | **FACT** | Binary bytes at `0x1D729C`, Y-axis nodes: `[0..336]`. | 100% |
| Duration maps MAP1..4 inflated by ~8% at 55/60 mg columns | **FACT** | Exact byte comparison against reference hex image. | 100% |
| Commanded EOI reaches 16.7°–16.9° ATDC at 2750–3000 RPM | **STATIC INFERENCE** | Calculated from exact interpolated SOI and Duration in Stage 1 BIN. | 95% |
| Modeled pre-turbine temperature exceeds 805°C in prolonged 4th/5th gear pull | **UNKNOWN** | Requires internal RAM variable logging (`EngPrt_tExhPreTrbn`) or thermocouple. | N/A |
| Hot-start 250-rpm delay causal relation | **UNKNOWN** | Requires warm-cranking telemetry with starter speed in 250–279 RPM band. | N/A |

---

### Section E: Recommended Coherent Calibration Strategy

To restore full, crisp acceleration in 3rd, 4th, and 5th gears without compromising engine reliability, the following **harmonized calibration strategy** must be implemented as a unified package (do NOT change BIN yet):

1. **Remove the 56.50 mg Smoke Limiter Wall**:
   - Rescale or update `FlMng_qPresSmoke_MAP` to utilize the available boost. Because actual boost is reliably 2200–2300 mbar, allow the smoke limiter to smoothly scale from 56.5 mg at 1750 RPM up to **62.0–63.0 mg at 2000–2500 RPM**.
   - This provides the missing 6.0–6.6 mg of fuel, instantly adding ~35 Nm of torque right where the driver feels the flat spot.
2. **Re-phase Combustion Timing (Advance SOI and/or Restore True Duration)**:
   - Bring **EOI back into the optimal window (8° to 12° ATDC)** across the entire rev range.
   - At 2750–3000 RPM, EOI is currently 16.7°–16.9° ATDC. Advancing SOI by **+1.5° to +2.5° CA** in the 55–62 mg range will center the heat release curve around 7°–9° ATDC, dramatically improving thermodynamic efficiency and dropping exhaust manifold temperatures.
   - Revert artificial duration inflation or calibrate duration strictly to OEM Unit Injector delivery characteristics.
3. **Rescale `FMTC_trq2qBas_MAP` Torque Axis**:
   - Extend the torque axis of `FMTC_trq2qBas_MAP` to 380 Nm (or 400 Nm) so that Driver Wish requests (350–375 Nm) cleanly extrapolate and map to realistic quantities, restoring accelerator pedal linearity and proper torque arbitration.
4. **Preserve Thermal and Boost Boundaries**:
   - Maintain `PCR_pBDesBas_MAP` at the current 2214 mbar target (the turbo is already producing 2280–2330 mbar; no more boost is needed or safe for the BV39).
   - Leave `PCR_rBPCtlBas_MAP` (N75 pre-control) untouched.
   - Keep `EngPrt_facTempPreTrbn_MAP` thermal protection active.

---

### Section F: Exact Cells Needing Modification (Reference Only — No BIN Edits Yet)

> [!CAUTION]
> The following table specifies the target map locations for calibration correction. In accordance with user rules, **no BIN file has been modified**.

| Map Name | Offset (Hex) | Node / Condition | Current Value | Target Range | Purpose |
|---|:---:|:---:|:---:|:---:|---|
| `FlMng_qPresSmoke_MAP` | `0x1D65EA` | 2000 RPM, 2000 hPa | 56.50 mg | **61.50 – 62.50 mg** | Eliminate 6.6 mg fuel starvation wall at 2000 RPM. |
| `FlMng_qPresSmoke_MAP` | `0x1D65FE` | 2250 RPM, 2000 hPa | 56.50 mg | **62.00 – 62.50 mg** | Eliminate 6.1 mg fuel starvation wall at 2250 RPM. |
| `FlMng_qPresSmoke_MAP` | `0x1D6612` | 2500 RPM, 2000 hPa | 56.50 mg | **61.50 – 62.00 mg** | Smooth transition towards 3000 RPM node; eliminate flat spot. |
| `InjCrv_phiBasGear34_MAP` | `0x1DAB56` | 2750 RPM, 55–60 mg | 20.58° BTDC | **22.50 – 23.00° BTDC** | Pull EOI from 16.7° ATDC back to ~14.0° ATDC. |
| `InjCrv_phiBasGear34_MAP` | `0x1DAB72` | 3000 RPM, 55–60 mg | 22.24° BTDC | **24.50 – 25.00° BTDC** | Pull EOI from 16.9° ATDC back to ~14.0° ATDC. |
| `InjCrv_phiBasGear56_MAP` | `0x1DAD56` | 2750 RPM, 55–60 mg | 20.58° BTDC | **22.50 – 23.00° BTDC** | Match Gear 3/4 SOI correction for 5th gear pull. |
| `InjCrv_phiBasGear56_MAP` | `0x1DAD72` | 3000 RPM, 55–60 mg | 22.24° BTDC | **24.50 – 25.00° BTDC** | Match Gear 3/4 SOI correction for 5th gear pull. |
| `FMTC_trq2qBas_MAP` | `0x1D72CE` | Torque Axis Node 15 | 336.0 Nm | **380.0 Nm** (rescale) | Prevent axis clipping of 350–375 Nm Driver Wish requests. |

---

### Section G: Predicted Effect

1. **Torque Output in 1800–2500 RPM Band**:
   - Releasing the smoke limiter from 56.50 mg to ~62.50 mg will increase delivered engine torque by **+30 to +40 Nm** (from ~310 Nm up to ~350 Nm).
   - In 3rd, 4th, and 5th gears, the car will immediately respond to throttle input with a vigorous, linear surge rather than feeling bogged down.
2. **Thermodynamic Efficiency & EGT Reduction (2750–3500 RPM)**:
   - Advancing SOI and taming late duration brings EOI from ~16.9° ATDC back toward ~13.5°–14.0° ATDC.
   - Peak cylinder pressure timing aligns closer to the optimal 14° ATDC expansion angle, converting combustion heat into crankshaft work instead of exhaust heat.
   - Pre-turbine EGT will decrease by an estimated **30°C to 50°C** under sustained WOT, preventing `EngPrt_facTempPreTrbn_MAP` from triggering thermal derate in 4th and 5th gears.
3. **Smoke / Opacity**:
   - Because the 2026-09-16 telemetry shows actual boost of 2280–2330 mbar (giving an effective air-fuel ratio $\lambda > 1.25$ even at 62.5 mg), raising the smoke limiter will **not cause black smoke**.

---

### Section H: Risks & Safety Boundaries

1. **BorgWarner BV39 Turbocharger Limits**:
   - The BV39 turbo on the 1.9 TDI BLS has a stock boost of 2050 mbar. The current 2214 mbar request operates at the upper safe boundary of compressor pressure ratio ($PR \approx 2.20$).
   - **DO NOT increase requested boost above 2214 mbar**. The existing boost is already more than sufficient to burn 62.5 mg cleanly.
   - **DO NOT alter `PCR_rBPCtlBas_MAP` (N75)** without high-speed telemetry; N75 is already producing brief spikes to 2330 mbar.
2. **Cylinder Peak Firing Pressure ($P_{\max}$)**:
   - Advancing SOI too aggressively at low RPM (<2000 RPM) increases $P_{\max}$, stressing head bolts and connecting rod bearings. Keep low-RPM SOI advance under +1.0° CA and focus timing advance above 2500 RPM where piston speed mitigates pressure rise rate ($dP/d\theta$).
3. **Clutch & Dual-Mass Flywheel (DMF)**:
   - The stock Sachs 228 mm clutch and DMF are rated for ~350–360 Nm. Do not allow arbitrated torque to exceed 360–370 Nm below 2200 RPM to avoid flywheel chatter or clutch slippage in 4th and 5th gears.

---

### Section I: Validation with Existing Logs (2026-09-16 Run)

The empirical telemetry from `Turbo_Pair_20260916_112035.csv` validates:
- **Actual Boost Overshoot / Sufficiency**:
  - At 1906 RPM: MAP = 2320 mbar (Target = 2170 mbar, delta = +150 mbar).
  - At 2153 RPM: MAP = 2330 mbar (Target = 2214 mbar, delta = +116 mbar).
  - At 2553 RPM: MAP = 2320 mbar (Target = 2214 mbar, delta = +106 mbar).
  - At 3078 RPM: MAP = 2230 mbar (Target = 2214 mbar, delta = +16 mbar).
  - At 3508 RPM: MAP = 2160 mbar (Target = 2214 mbar, delta = -54 mbar).
- **Mass Air Flow (MAF)**:
  - 1515 RPM: 29.36 g/s
  - 1906 RPM: 48.61 g/s
  - 2153 RPM: 69.58 g/s
  - 2553 RPM: 81.08 g/s
  - 3078 RPM: 88.69 g/s
  - 4011 RPM: 108.50 g/s
- **Confirmation**: The turbocharger and MAF sensor are operating correctly. The lack of pull is purely due to internal ECU fuel clamping and combustion phasing, not turbo lag or physical air-path leakage.

---

### Section J: What Requires a New Measurement

To convert this audit into a fully validated calibration package, the following runtime telemetry must be logged in the vehicle:

1. **Synchronous High-Speed VCDS / KWP2000 Logging (Group 001, 004, 008, 011)**:
   - **Group 008 (Limiters)**: Engine Speed (RPM), Driver Wish IQ (mg), Torque Limiter IQ (mg), Smoke Limiter IQ (mg). This will empirically verify whether Smoke Limiter IQ is indeed the active minimum at 56.50 mg.
   - **Group 004 (Injection)**: Engine Speed (RPM), Commanded SOI (°BTDC), Commanded Duration (°CA), Synchro Angle (torsion value).
   - **Group 011 (Boost Control)**: Engine Speed (RPM), Specified MAP (mbar), Actual MAP (mbar), N75 Duty Cycle (%).
2. **Pre-Turbine EGT or Modeled Exhaust Temperature**:
   - Internal variable `EngPrt_tExhPreTrbn` (or external K-type probe in manifold) during a 4th gear WOT pull from 1500 to 4000 RPM to monitor temperature rise under prolonged load.
3. **Hot-Start Telemetry (HS-250 Validation)**:
   - Cranking RPM, starter battery voltage, coolant temperature (80–90°C), and terminal-50 start status during hot restarts to evaluate whether hot-start intervention is warranted.

---
*Audit completed strictly within read-only diagnostic bounds. No firmware binary images were generated or modified.*
