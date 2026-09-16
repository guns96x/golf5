# WOT Calibration Chain Audit & Fuel-Torque Investigation (Gears 3, 4, 5)
**Vehicle**: Volkswagen Golf 5 1.9 TDI (Engine BLS, 77 kW / 105 PS OEM)  
**ECU**: Bosch EDC16U34  
**Hardware ID**: `03G906021QJ` (HW 0281014064)  
**Software Version**: `1037391847` (P447HAXN)  
**Active Calibration**: `03G906021QJ_stage1_full_power_dpf_egr_off.bin`  
**Reference Baseline**: `diagnostic-review/reference-from-hex.analysis-only.bin`  
**Telemetry Analyzed**: `logs/20260916/Turbo_Pair_20260916_112035.csv` (4th gear WOT pull)  
**Turbocharger**: BorgWarner BV39 (VNT / vacuum actuator)  
**Date of Audit**: 2026-09-16 (Revised per Epistemic Ground-Truth Rules)  

---

## Executive Summary & Epistemic Ground Rules

The driver reports **sluggish, weak acceleration in 3rd, 4th, and 5th gears**, despite telemetry confirming **sufficient manifold pressure (actual MAP 2280–2330 mbar vs 2214 mbar target)** and **strong mass airflow (MAF up to 108.5 g/s)** during a 4th-gear WOT pull.

This audit models the static calibration chain of Bosch EDC16U34 across the primary torque, smoke, duration, and SOI paths. To preserve strict scientific integrity, the following **epistemic boundaries** govern this analysis:

1. **Telemetry Isolation**:
   - The dataset `logs/20260916/Turbo_Pair_20260916_112035.csv` represents a **4th-gear WOT pull** ($\text{speed}/\text{rpm} \approx 0.0318$).
   - Empirical MAP/MAF values apply **only to Gear 4**. No dedicated WOT logs currently exist for Gear 3 or Gear 5 in the 2026-09-16 dataset. For Gears 3 and 5, telemetry is explicitly designated as `UNAVAILABLE`.
2. **Input Quantity Rigor for Smoke Limiter**:
   - The Y-axis of `FlMng_qPresSmoke_MAP` is `FlMng_pIATCorr_mp` (temperature-corrected charge air pressure), not raw MAP.
   - Because `FlMng_pIATCorr_mp` is not logged in existing telemetry, evaluating the smoke map at raw MAP is an **unverified approximation hypothesis**.
3. **FMTC Endpoint Behavior**:
   - The torque axis of `FMTC_trq2qBas_MAP` terminates at 336.0 Nm. Whether the EDC16U34 runtime code clamps requests >336 Nm or linearly extrapolates is **statically unproven without live RAM variable logging** (`CoEng_trqInrSet` vs `InjUn_qMI1Des`). Both clamped and extrapolated quantities are reported.
4. **Limiter Arbitration**:
   - Comparing `FMTC_IQ` vs calculated `Smoke_IQ` represents a **static script hypothesis**, not measured ECU arbitration. The active binding limiter in the vehicle is **UNKNOWN** without synchronous VCDS Group 008 logging.
5. **Combustion Phasing Proxy**:
   - The metric $\text{Duration} - \text{SOI}$ represents the **electrical command end proxy**, not the physical end of combustion or needle closure.

---

## Complete WOT Calibration Chain Audit Table

- **Accelerator Pedal**: 100% WOT.
- **Ambient Pressure**: 1005 hPa nominal.
- **Gear-Specific Map Mapping (per A2L definitions)**:
  - Gear 3: `AccPed_trqEng2_MAP` (`0x1C2F7A`)
  - Gear 4: `AccPed_trqEng3_MAP` (`0x1C30D0`)
  - Gear 5: `AccPed_trqEng4_MAP` (`0x1C3226`)

| Gear | RPM | Driver Wish (Nm) | Atm Prot Lim (Nm) | Arbitrated Trq (Nm) | FMTC IQ (Clamped) (mg) | FMTC IQ (Extrap) (mg) | Telemetry Source | Actual MAP (mbar) | Smoke Input Description | Smoke IQ Approx (mg) | Static Cand Min IQ (mg) | Commanded SOI (°BTDC) | Dur Map Index | Commanded Duration (°CA) | Electrical Command End Proxy (°ATDC) | Specified Boost Target (mbar) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **3** | **1500** | 373.8 | 337.5 | 337.5 | 66.12 | 66.53 | *UNAVAILABLE* | — | Specified Target Boost Proxy | 51.51 | **51.51** | 12.60 | 2.45 | 23.32 | **10.72** | 1795 |
| **3** | **1750** | 368.9 | 367.2 | 367.2 | 64.24 | 72.54 | *UNAVAILABLE* | — | Specified Target Boost Proxy | 56.50 | **56.50** | 14.32 | 2.11 | 27.96 | **13.64** | 2057 |
| **3** | **2000** | 363.9 | 375.2 | 363.9 | 63.14 | 70.22 | *UNAVAILABLE* | — | Specified Target Boost Proxy | 56.50 | **56.50** | 15.96 | 1.86 | 30.04 | **14.08** | 2197 |
| **3** | **2250** | 358.9 | 373.9 | 358.9 | 62.57 | 67.94 | *UNAVAILABLE* | — | Specified Target Boost Proxy | 56.50 | **56.50** | 17.25 | 1.68 | 31.18 | **13.93** | 2214 |
| **3** | **2500** | 354.0 | 364.5 | 354.0 | 61.76 | 65.12 | *UNAVAILABLE* | — | Specified Target Boost Proxy | 56.50 | **56.50** | 18.87 | 1.45 | 32.65 | **13.78** | 2214 |
| **3** | **2750** | 349.6 | 357.7 | 349.6 | 61.99 | 64.91 | *UNAVAILABLE* | — | Specified Target Boost Proxy | 62.15 | **61.99** | 20.58 | 1.20 | 37.24 | **16.66** | 2214 |
| **3** | **3000** | 345.2 | 348.2 | 345.2 | 62.57 | 64.77 | *UNAVAILABLE* | — | Specified Target Boost Proxy | 67.80 | **62.57** | 22.24 | 0.97 | 39.17 | **16.93** | 2214 |
| **3** | **3500** | 339.1 | 336.1 | 336.1 | 63.99 | 64.01 | *UNAVAILABLE* | — | Specified Target Boost Proxy | 67.80 | **63.99** | 25.90 | 0.44 | 40.65 | **14.75** | 2214 |
| **3** | **4000** | 332.9 | 318.6 | 318.6 | 62.07 | 62.07 | *UNAVAILABLE* | — | Specified Target Boost Proxy | 67.80 | **62.07** | 29.16 | 0.00 | 42.14 | **12.98** | 2209 |
| **4** | **1500** | 373.8 | 337.5 | 337.5 | 66.12 | 66.53 | Turbo_Pair_112035 | 1920.0 | Actual raw MAP Proxy | 54.18 | **54.18** | 12.84 | 2.36 | 25.07 | **12.23** | 1828 |
| **4** | **1750** | 368.9 | 367.2 | 367.2 | 64.24 | 72.54 | Turbo_Pair_112035 | 2230.0 | Actual raw MAP Proxy | 56.50 | **56.50** | 14.32 | 2.11 | 27.96 | **13.64** | 2057 |
| **4** | **2000** | 363.9 | 375.2 | 363.9 | 63.14 | 70.22 | Turbo_Pair_112035 | 2310.0 | Actual raw MAP Proxy | 56.50 | **56.50** | 15.96 | 1.86 | 30.04 | **14.08** | 2197 |
| **4** | **2250** | 358.9 | 373.9 | 358.9 | 62.57 | 67.94 | Turbo_Pair_112035 | 2320.0 | Actual raw MAP Proxy | 56.50 | **56.50** | 17.25 | 1.68 | 31.18 | **13.93** | 2214 |
| **4** | **2500** | 354.0 | 364.5 | 354.0 | 61.76 | 65.12 | Turbo_Pair_112035 | 2320.0 | Actual raw MAP Proxy | 56.50 | **56.50** | 18.87 | 1.45 | 32.65 | **13.78** | 2214 |
| **4** | **2750** | 349.6 | 357.7 | 349.6 | 61.99 | 64.91 | Turbo_Pair_112035 | 2300.0 | Actual raw MAP Proxy | 62.15 | **61.99** | 20.58 | 1.20 | 37.24 | **16.66** | 2214 |
| **4** | **3000** | 345.2 | 348.2 | 345.2 | 62.57 | 64.77 | Turbo_Pair_112035 | 2210.0 | Actual raw MAP Proxy | 67.80 | **62.57** | 22.24 | 0.97 | 39.17 | **16.93** | 2214 |
| **4** | **3500** | 339.1 | 336.1 | 336.1 | 63.99 | 64.01 | Turbo_Pair_112035 | 2160.0 | Actual raw MAP Proxy | 67.80 | **63.99** | 25.90 | 0.44 | 40.65 | **14.75** | 2214 |
| **4** | **4000** | 332.9 | 318.6 | 318.6 | 62.07 | 62.07 | Turbo_Pair_112035 | 2160.0 | Actual raw MAP Proxy | 67.80 | **62.07** | 29.16 | 0.00 | 42.14 | **12.98** | 2209 |
| **5** | **1500** | 373.8 | 337.5 | 337.5 | 66.12 | 66.53 | *UNAVAILABLE* | — | Specified Target Boost Proxy | 51.51 | **51.51** | 12.60 | 2.45 | 23.32 | **10.72** | 1795 |
| **5** | **1750** | 368.9 | 367.2 | 367.2 | 64.24 | 72.54 | *UNAVAILABLE* | — | Specified Target Boost Proxy | 56.50 | **56.50** | 14.32 | 2.11 | 27.96 | **13.64** | 2057 |
| **5** | **2000** | 363.9 | 375.2 | 363.9 | 63.14 | 70.22 | *UNAVAILABLE* | — | Specified Target Boost Proxy | 56.50 | **56.50** | 15.96 | 1.86 | 30.04 | **14.08** | 2197 |
| **5** | **2250** | 358.9 | 373.9 | 358.9 | 62.57 | 67.94 | *UNAVAILABLE* | — | Specified Target Boost Proxy | 56.50 | **56.50** | 17.25 | 1.68 | 31.18 | **13.93** | 2214 |
| **5** | **2500** | 354.0 | 364.5 | 354.0 | 61.76 | 65.12 | *UNAVAILABLE* | — | Specified Target Boost Proxy | 56.50 | **56.50** | 18.87 | 1.45 | 32.65 | **13.78** | 2214 |
| **5** | **2750** | 349.6 | 357.7 | 349.6 | 61.99 | 64.91 | *UNAVAILABLE* | — | Specified Target Boost Proxy | 62.15 | **61.99** | 20.58 | 1.20 | 37.24 | **16.66** | 2214 |
| **5** | **3000** | 345.2 | 348.2 | 345.2 | 62.57 | 64.77 | *UNAVAILABLE* | — | Specified Target Boost Proxy | 67.80 | **62.57** | 22.24 | 0.97 | 39.17 | **16.93** | 2214 |
| **5** | **3500** | 339.1 | 336.1 | 336.1 | 63.99 | 64.01 | *UNAVAILABLE* | — | Specified Target Boost Proxy | 67.80 | **63.99** | 25.90 | 0.44 | 40.65 | **14.75** | 2214 |
| **5** | **4000** | 332.9 | 318.6 | 318.6 | 62.07 | 62.07 | *UNAVAILABLE* | — | Specified Target Boost Proxy | 67.80 | **62.07** | 29.16 | 0.00 | 42.14 | **12.98** | 2209 |

---

## Detailed Investigation (Sections A through J)

### Section A: Strongest Candidate Hypotheses for Sluggish Pull

1. **Candidate Hypothesis 1: Smoke Limiter Plateau (`FlMng_qPresSmoke_MAP`)**  
   - *Observation*: The map's pressure axis terminates at 2000 hPa. At 1750–2500 RPM, the 2000 hPa row holds a flat value of **56.50 mg/stroke**.  
   - *Limitation*: The true input to this map is `FlMng_pIATCorr_mp` (temperature-corrected pressure), not raw MAP. If `FlMng_pIATCorr_mp >= 2000 hPa`, the lookup is limited to 56.50 mg; if intake air heating reduces `FlMng_pIATCorr_mp` below 2000 hPa, the limit drops further (e.g. 51.0–52.1 mg at 1800 hPa).  
   - *Hypothesis*: If this map acts as the binding limiter in runtime, it imposes a 5.3 to 7.7 mg/stroke restriction below Driver Wish/Torque limiter demand (~62–64 mg), creating a perceptible flat spot at 1800–2500 RPM.
2. **Candidate Hypothesis 2: Late Electrical Command Phasing (`electrical_command_end_proxy`)**  
   - *Observation*: Stage 1 modified Duration maps MAP1..4 by +8% in the 55–60 mg columns while SOI advance in those columns was modest (+1.2° to +1.6° CA).  
   - *Calculation*: The difference $\text{Duration} - \text{SOI}$ reaches **16.7° to 16.9° ATDC** at 2750–3000 RPM.  
   - *Limitation*: This calculation represents an electrical pulse duration proxy. Injector needle dynamics, hydraulic delay, and combustion ignition delay mean physical combustion phasing cannot be proved from this metric alone.  
   - *Hypothesis*: If electrical command extends towards ~17° ATDC, physical injection may finish deep into the expansion stroke, reducing thermodynamic expansion ratio, elevating pre-turbine exhaust temperature, and causing sluggish high-load performance.
3. **Candidate Hypothesis 3: FMTC Endpoint Behavior**  
   - *Observation*: The torque axis of `FMTC_trq2qBas_MAP` ends at 336.0 Nm, while Driver Wish requests up to 374 Nm and atmospheric limits allow up to 380 Nm.  
   - *Status*: Whether the ECU clamps to the 336 Nm node (outputting ~62–63 mg) or extrapolates along the slope (which would output 68–72 mg) is **UNKNOWN** without RAM logging.

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
| `Turbo_Pair_20260916_112035.csv` is a 4th-gear WOT pull | **FACT** | Telemetry speed/rpm ratio calculation (~0.0318). |
| 3rd-gear and 5th-gear WOT telemetry in 20260916 dataset | **UNKNOWN** | No isolated WOT logs for gears 3 and 5 in dataset. |
| Runtime smoke limiter is actively clamping fuel to 56.50 mg in car | **STATIC INFERENCE (UNVERIFIED INPUT)** | Requires VCDS Group 008 runtime log to prove active binding state. |
| FMTC runtime behavior beyond 336 Nm (clamp vs linear extrapolation) | **UNKNOWN** | Statically unproven; requires RAM logging of internal variables. |
| Physical combustion end / torque loss from electrical duration proxy | **UNKNOWN** | Electrical command proxy does not prove physical combustion end. |

---

### Section E: Calibration Strategy Requirements (vNext Planning Direction)

*No firmware binary is being modified at this stage. The following items define the technical requirements for a future vNext calibration:*

1. **Verify Active Limiter via Telemetry First**:
   - Before editing maps, log VCDS Group 008 (Driver Wish, Torque Limiter, Smoke Limiter) to determine which limiter is actively binding during a 4th-gear pull.
2. **Smoke Map Coherence**:
   - If Group 008 proves that Smoke Limiter is binding at 56.5 mg despite adequate boost and clean exhaust, harmonize `FlMng_qPresSmoke_MAP` with the 2214 mbar boost target.
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

1. **VCDS Group 008 Logging (WOT pull in 4th gear, 1500 to 4000 RPM)**:
   - Field 1: Engine Speed (RPM)
   - Field 2: Driver's Wish IQ (mg/stroke)
   - Field 3: Torque Limitation IQ (mg/stroke)
   - Field 4: Smoke Limitation IQ (mg/stroke)
   - *Criterion*: Confirms whether Field 4 (Smoke Limitation) is the minimum binding value at 56.5 mg.
2. **VCDS Group 004 Logging (WOT pull)**:
   - Field 2: Commanded Start of Injection (°BTDC)
   - Field 3: Commanded Injection Duration (°CA)
   - Field 4: Synchro Angle / Torsion Value
3. **Dedicated Gear 3 & Gear 5 WOT Logging**:
   - Capture isolated WOT pulls for 3rd and 5th gears to evaluate gear-dependent boost rise and airflow characteristics.

---
*Audit strictly read-only. No firmware binary images were generated or altered.*
