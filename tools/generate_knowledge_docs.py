#!/usr/bin/env python3
"""
tools/generate_knowledge_docs.py — Knowledge Document Generator for EDC16U34 Bootstrap Pack
Strictly aligns all 20 technical documents with deep-audit ground truth,
exact A2L offsets/dimensions, raw epistemic statuses, and verified firmware lineage.
"""

import os
from pathlib import Path

DOCS_DIR = Path("docs/knowledge")
DOCS_DIR.mkdir(parents=True, exist_ok=True)

DOCUMENTS = {}

# 1. source-index.md
DOCUMENTS["source-index.md"] = """# Source Index — EDC16U34 Engineering Knowledge Base

This document catalogues all foundational, engineering, diagnostic, and project-specific sources ingested into the **EDC16U34 Knowledge Base** (`knowledge/edc16_knowledge.db`).

## Authority & Applicability Scoring System

In accordance with [RESEARCH_POLICY.md](RESEARCH_POLICY.md):
- **Authority Score (1–5)**: Credibility of publisher and scientific/engineering rigor (5 = OEM/Bosch/ASAM, 4 = SAE/ETAS/Textbooks, 3 = Ross-Tech/TDIClub, 2 = Tuner blogs, 1 = Unverified forums).
- **Applicability Score (1–5)**: Exactness of fit to this specific vehicle: **VW Golf 5 2008, 1.9 TDI BLS, Bosch EDC16U34, HW 03G906021QJ, SW 1037391847, Turbo BV39 54399880072** (5 = Exact SW/HW/Binary/Log, 4 = EDC16U34 BLS family, 3 = Generic EDC16 / Pumpe-Düse, 2 = Generic Diesel, 1 = Generic ICE).

---

## Tier A: OEM Literature & Authoritative Standards

| ID | Title & Author | Publisher & Date | Authority | Applicability | Key Topics & Evidence | Reference Link |
|---|---|---|:---:|:---:|---|---|
| S-01 | **Diesel Engine Management: Systems and Components** (K. Reif) | Springer / Bosch (2014) | 5 | 3 | Air-path control, VNT operation, fuel injection, sensors, EDC electronic control | [Springer](https://link.springer.com/book/10.1007/978-3-658-03981-3) |
| S-02 | **Dieselmotor-Management 4th ed.** (Bosch) | Vieweg+Teubner (2004) | 5 | 4 | Pumpe-Düse unit injection, EDC16 charge-pressure control, torque architecture | [Springer](https://link.springer.com/book/10.1007/978-3-322-80331-3) |
| S-03 | **VW SSP 304 — Electronic Diesel Control EDC16** | Volkswagen AG (2003) | 5 | 4 | Torque-oriented engine management, metering, SOI, boost regulation, N75 PWM | [VW SSP 304 PDF](https://www.vaglinks.com/docs/ssp/VWUSA.COM_SSP_304_EDC-16.pdf) |
| S-04 | **VW SSP 209 — 1.9-ltr. TDI Engine with Pump-Injection System** | Volkswagen AG (1999) | 5 | 4 | PD unit injector design, cam actuation, fuel supply circuit, vacuum circuit | [VW SSP 209](https://procarmanuals.com/self-study-program-209-1-9-ltr-tdi-engine-pump-injection-system-design-function/) |
| S-05 | **VW SSP 336 — Catalytic Coated Diesel Particulate Filter** | Volkswagen AG (2005) | 5 | 4 | Thermal management, regeneration strategy, exhaust differential pressure | [VW SSP 336 PDF](https://www.vaglinks.com/Docs/SSP/VWUSA.COM_SSP_336_VW_Diesel_particulate_filter.pdf) |
| S-06 | **VW Workshop Manual — 4-cyl Diesel BKC/BLS/BXE** | Volkswagen AG (2008) | 5 | 5 | Mechanical tolerances, connecting rod specs, torque limits, vacuum specs | [VW Hub](https://www.vag-hub.com/vw-engine/) |
| S-07 | **ASAM MCD-2 MC (ASAP2 / A2L Standard 1.7.1)** | ASAM e.V. (2020) | 5 | 5 | A2L grammar, CHARACTERISTIC, RECORD_LAYOUT, COMPU_METHOD scaling | [ASAM MCD-2](https://www.asam.net/standards/detail/mcd-2-mc/) |
| S-08 | **ETAS INCA Measurement & Calibration Documentation** | ETAS GmbH (2021) | 4 | 3 | XCP calibration protocol, measurement raster, sample rate trade-offs | [ETAS Docs](https://docs.etas.com/inca/) |
| S-09 | **EVC WinOLS 5 Manual & ASAP2 Import Guide** | EVC electronic (2023) | 4 | 4 | DAMOS import alignment, map axis deduction, interpolation rules | [EVC WinOLS PDF](https://www.evc.de/ftp/winols/winols%20HelpEn.pdf) |
| S-10 | **EVC Bosch EDC16 Checksum Algorithm (OLS242)** | EVC electronic (2022) | 5 | 5 | Bosch EDC16 multipoint checksum, block structure, and integrity checks | [EVC Checksums](https://www.evc.de/en/product/ols/plugins_detail.asp) |

---

## Tier B: Engineering Textbooks, Control Theory & Turbocharging

| ID | Title & Author | Publisher & Date | Authority | Applicability | Key Topics & Evidence | Reference Link |
|---|---|---|:---:|:---:|---|---|
| S-11 | **Internal Combustion Engine Fundamentals 2nd ed.** (J.B. Heywood) | McGraw-Hill (2018) | 5 | 2 | Thermodynamics of diesel combustion, air-fuel ratio, charge heating | [McGraw-Hill](https://www.mheducation.com/highered/mhp/product/internal-combustion-engine-fundamentals-2e.html) |
| S-12 | **Bosch Automotive Handbook 11th ed.** | Wiley / Bosch (2022) | 5 | 2 | Standard sensor curves, actuator dynamics, combustion chemistry | [Wiley](https://uat.store.wiley.com/en-us/automotive-handbook-11th-edition-p-9781119911906) |
| S-13 | **Modeling and Control of ICE Systems 2nd ed.** (Guzzella & Onder) | Springer (2010) | 5 | 3 | Turbocharger control: feed-forward vs feedback PID, anti-windup | [Springer](https://link.springer.com/book/10.1007/978-3-642-10775-7) |
| S-14 | **Automotive Control Systems** (Kiencke & Nielsen) | Springer (2005) | 5 | 3 | Driveline oscillation damping, torque structure, driveability filters | [Springer](https://link.springer.com/book/10.1007/b137654) |
| S-15 | **Turbocharging the ICE** (Watson & Janota) | Macmillan / Springer (1982) | 5 | 3 | Turbine pulse energy, variable nozzle mechanics, compressor maps | [Springer](https://link.springer.com/book/10.1007/978-1-349-04024-7) |
| S-16 | **Understanding Compressor Maps** | BorgWarner (2022) | 5 | 4 | Pressure ratio, corrected flow, surge/choke limits for BV39 | [BorgWarner](https://www.borgwarner.com/aftermarket/exhaust-gas-management/news/2022/05/23/understanding-compressor-maps-sizing-a-turbocharger) |
| S-17 | **Model-Based Control of VGT and EGR** (Ammann et al.) | SAE (2003-01-0357) | 4 | 3 | Interaction between VGT and EGR: zero EGR increases turbine enthalpy | [SAE MOBILUS](https://saemobilus.sae.org/papers/model-based-control-vgt-egr-a-turbocharged-common-rail-diesel-engine-theory-passenger-car-implementation-2003-01-0357) |

---

## Tier C: Exact Project Evidence & Verified Ground Truth

> [!IMPORTANT]
> **Source of Truth Hierarchy**:
> `diagnostic-review/*` + raw A2L + exact BINs + real telemetry logs = **PRIMARY SOURCE OF TRUTH**.
> `docs/knowledge/*` represents the curated draft synthesis subject to continuous verification.

| ID | Resource Name | Local Repository Path | Role / Status | Notes |
|---|---|---|---|---|
| P-01 | **Factory A2L Definition Dataset** | `diagnostic-review/definitions/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.a2l` | Primary Definition | Exact 12.6 MB ASAP2 matching SW 1037391847 with 11,537 characteristics |
| P-02 | **Reference Factory Binary** | `diagnostic-review/reference-from-hex.analysis-only.bin` | Baseline Reference | 2,097,152 bytes uncorrupted OEM baseline (stock request: 2050 mbar) |
| P-03 | **Stage 1 Full Power (Active in Car)** | `03G906021QJ_stage1_full_power_dpf_egr_off.bin` | **Currently Flashed in Car** | Active in vehicle: boost target 2214 mbar, PoI2 off (0.0 mg), CTSCD restored to 0x0B, EGT protection active |
| P-04 | **Stage 1 Refined CS_OK** | `03G906021QJ_stage1_refined_CS_OK.bin` | Candidate Image | Static audit only (not flash approved without logging plan); contains HS-250 fix and Gear 5/6 cruise SOI (+0.703°) |
| P-05 | **Stage 1 Ideal (Rejected Build)** | `03G906021QJ_ideal_stage1_dpf_egr_off.bin` | **Rejected Test Build** | Test build with factory duration maps that drove too sluggishly; rejected |
| P-06 | **Calibration Enhancements Audit** | `diagnostic-review/calibration-enhancements-deep-audit-2026-09-11.md` | Ground Truth Audit | Authoritative audit of HS-250, N75-A, SMK-2500, and cruise SOI |
| P-07 | **VCDS WOT Log (2026-09-14)** | `logs/VCDS_WOT_Log_20260914_114936.csv` | Measured Run | Multi-group log capturing 2310–2320 mbar boost peak vs 2214 mbar request |
| P-08 | **Turbo Fast OBD Log** | `logs/Turbo_Fast_Log_20260914_210903.csv` | Measured Run | High-frequency MAP and RPM transient recording |
"""

# 2. ecu-architecture.md
DOCUMENTS["ecu-architecture.md"] = """# Bosch EDC16U34 ECU Architecture

## Hardware Overview

The engine management computer installed in this vehicle is the **Bosch EDC16U34-3.42** electronic diesel control unit.

- **VAG Part Number**: `03G 906 021 QJ`
- **Bosch Hardware Number**: `0 281 014 065`
- **Bosch Software Version**: `1037391847` (Family `391847`, Project code `P447_HAXN`)
- **Engine Application**: 1.9 TDI 8V Pumpe-Düse (Engine code `BLS`, 77 kW / 105 HP, with factory DPF)

### Microcontroller & Memory Architecture

```
+-------------------------------------------------------------+
|                 Bosch EDC16U34 ECU Core                     |
|                                                             |
|  +-------------------------------------------------------+  |
|  | Microcontroller: Motorola/Freescale MPC562 (PowerPC)   |  |
|  | - 32-bit RISC core, 56 MHz or 66 MHz                  |  |
|  | - Internal SRAM: 512 KB                               |  |
|  +-------------------------------------------------------+  |
|                             |                               |
|                             v                               |
|  +-------------------------------------------------------+  |
|  | External Flash Memory (2,097,152 bytes / 2 MB)        |  |
|  | Part: AMD AM29BL802CB / ST M58BW016DB                |  |
|  |                                                       |  |
|  | 0x000000 - 0x03FFFF: Bootloader & Microcode           |  |
|  | 0x040000 - 0x1BFFFF: Operating System & Engine Code   |  |
|  | 0x1C0000 - 0x1FFFFF: Calibration Block (Maps & Axes)  |  |
|  +-------------------------------------------------------+  |
|                             |                               |
|                             v                               |
|  +-------------------------------------------------------+  |
|  | Serial EEPROM: ST95320 / ST95640 (4 KB / 8 KB)        |  |
|  | - Immobilizer data, coding, mileage, injector trims   |  |
|  +-------------------------------------------------------+  |
+-------------------------------------------------------------+
```

### Memory Map Layout in Flash

In SW `1037391847`, all calibration parameters and maps reside in the upper **256 KB** of the flash image (offset range `0x1C0000` to `0x1FFFFF`).

- **Flash Base Address**: `0x000000`
- **Calibration Area Base**: `0x1C0000`
- **N75 Pre-Control Map (`PCR_rBPCtlBas_MAP`)**: `0x1E9FD0` (16×13)
- **Base Boost Target Map (`PCR_pBDesBas_MAP`)**: `0x1EB0B2` / `0x1E9A40` (16×10 / 16×16 depending on variant bank)
- **Smoke Limiter (`FlMng_qPresSmoke_MAP`)**: `0x1D6490` (16×12)
- **Hot-Start Base Torque (`StSys_trqStrtBas_MAP`)**: `0x1F070C` (9×9)
- **Hot-Start Term 50 Torque (`StSys_trqStrt_MAP`)**: `0x1F07EA` (9×9)
- **Cruise SOI 5-6 Gear (`InjCrv_phiBasGear56_MAP`)**: `0x1DACF8` (16×14)

---

## Operating System & Execution Tasks

EDC16 operates on a deterministic real-time OSEK-compliant operating system with two execution domains:
1. **Time-triggered tasks**:
   - `10 ms raster`: Fast PID controllers (boost pressure closed-loop, rail pressure, air control).
   - `20 ms raster`: Smoke limitation, driver wish calculation, torque coordinator.
   - `100 ms raster`: Thermal modeling (modeled EGT, oil temp derating, ambient compensation).
2. **Angle-triggered tasks (Synchronous with Crankshaft Rotation)**:
   - Fired at defined crank angle intervals (every 180° crank angle for a 4-cylinder engine).
   - Computes exact Start of Injection (SOI), BIP (Beginning of Injection Period), and Unit Injector solenoid energization duration.
"""

# 3. edc16-torque-model.md
DOCUMENTS["edc16-torque-model.md"] = """# EDC16 Torque-Oriented Engine Management

## Architectural Principle

As defined in **VW SSP 304**, EDC16 is a **torque-oriented** engine control system. Unlike older EDC15 systems where the accelerator pedal directly mapped to fuel quantity (mg/stroke), EDC16 treats **torque (Nm)** as the universal internal currency.

```
[Driver Wish / Pedal]  --> [Outer Torque Request]
[Cruise Control / AC]  --> [Outer Torque Request]
                                |
                                v
                   [Torque Coordinator & Filters]
                                |
                                v
               [Friction & Parasitic Subtraction]
                                |
                                v
                   [Indicated / Inner Torque]
                                |
           +--------------------+--------------------+
           |                                         |
           v                                         v
   [Torque Limiter Map]                     [Smoke Limiter]
   (TrqLim_trqEng_MAP)                     (Air/Fuel Lambda)
           |                                         |
           +--------------------+--------------------+
                                |
                                v
                    [Arbitrated Minimum Torque]
                                |
                                v
           [Torque-to-Quantity Conversion Map]
           (TrqConv_qInd_MAP / TrqConv_qEng_MAP)
                                |
                                v
                    [Injected Fuel Quantity (mg/stroke)]
                                |
           +--------------------+--------------------+
           |                                         |
           v                                         v
   [Duration Maps]                           [Start of Injection]
   (InjCrv_phiDur_MAP)                       (InjCrv_phiMI1Des_MAP)
```

## Step-by-Step Torque Flow

1. **Outer Torque Generation**:
   - `DrvDem_tq_MAP`: Inputs are Engine RPM and Accelerator Pedal %; output is requested driver torque in Nm.
2. **Torque Coordinator**:
   - Arbitrates between driver wish, cruise control (GRA), ESP/traction intervention (ASR/MSR), and engine drag torque control.
3. **Inner Torque Conversion**:
   - Accounts for internal mechanical friction, oil pump, alternator, and coolant pump drag (`TrqLoss_trqLoss_MAP`).
4. **Limitation Layer**:
   - `TrqLim_trqEng_MAP`: Primary mechanical torque limiter as a function of RPM and atmospheric pressure. Protects the dual-mass flywheel (DMF), clutch, conrods, and transmission.
5. **Conversion to Injected Quantity**:
   - `TrqConv_qInd_MAP`: Converts indicated torque (Nm) to injected fuel mass (mg/stroke).
"""

# 4. boost-control.md
DOCUMENTS["boost-control.md"] = """# EDC16 Boost Pressure Control Architecture

## Boost Target Formation

In the Bosch EDC16U34 system for the 1.9 TDI BLS, the target manifold absolute pressure (MAP) is governed by the **PCR (Pressure Charge Regulation)** functional subsystem.

$$\\text{Final Boost Target} = \\min\\Big(\\text{PCR\\_pBDesBas\\_MAP}(\\text{RPM}, \\text{IQ}) + \\Delta p_{\\text{ambient}} + \\Delta p_{\\text{temp}}, \\text{PCR\\_pBDesMax\\_CUR}(\\text{RPM})\\Big)$$

### 1. Base Boost Target Map (`PCR_pBDesBas_MAP`)
- **Stock Reference High-Load Request**: **2050 mbar** absolute.
- **Stage 1 Active Request**: **2214 mbar** absolute (104 values modified versus stock reference; verified by deep-audit).
- **Units**: mbar absolute.

> [!NOTE]
> Previous draft documentation mistakenly referenced a 2350 mbar ceiling. The actual verified Stage 1 high-load request across the 2000–3500 RPM full-load plateau is **2214 mbar**.

### 2. Atmospheric & Environmental Corrections
- Altitude compensation (`PCR_pBDesAtm_MAP`): Derates boost request as ambient barometric pressure decreases below 1000 mbar to prevent turbocharger overspeed in thin air.
- Charge temperature compensation (`PCR_pBDesT_MAP`): Derates target if intake air temperature (IAT) exceeds calibrated thermal thresholds.

---

## Closed-Loop Boost Regulation Architecture

```
                    +---------------------------+
                    |  PCR_rBPCtlBas_MAP        |
                    |  (Feed-Forward / Pre-Ctrl)|
                    +---------------------------+
                                  |
                                  v
+-------------------+        [ + / Sum ] -------> [ Actuator Output: N75 PWM % ]
| Boost Error (e)   |             ^
| = Actual - Target |             |
+-------------------+             |
          |             +-------------------+
          +------------>| Closed-Loop PID   |
                        | (P + I + D Terms) |
                        +-------------------+
```

1. **Feed-Forward Control (`PCR_rBPCtlBas_MAP`)**:
   - A static 2D starting point for the closed-loop controller.
   - In SW 1037391847, this map remained **100% stock reference** in Stage 1, while boost request was raised from 2050 to 2214 mbar.
2. **Feedback Correction (PID)**:
   - Reacts to dynamic boost error ($e = p_{\\text{actual}} - p_{\\text{target}}$).
"""

# 5. vnt-n75-control.md
DOCUMENTS["vnt-n75-control.md"] = """# VNT / N75 Actuator Mechanics & Pre-Control

## Turbocharger Specification

- **Turbocharger Model**: BorgWarner / KKK BV39
- **OEM Part Reference**: `5439 988 0072` / `03G253014M`
- **Type**: Variable Nozzle Turbine (VNT) with pneumatic vacuum actuator and N75 electro-pneumatic solenoid.

---

## Pre-Control Map (`PCR_rBPCtlBas_MAP`)

- **A2L Symbol**: `PCR_rBPCtlBas_MAP` (line 394165 in A2L)
- **Description**: *Basissteuerkennfeld für Ladedruck* (Base control map for charge pressure)
- **Address**: `0x1E9FD0`
- **Actual Dimensions**: **16 × 13** (NOT 16×16!)
- **Axes**: Engine Speed (RPM, 16 points) × Injected Quantity (mg/stroke, 13 points)
- **Data Format**: 16-bit signed, factor 0.01 (% duty)
- **Status in Stage 1**: **Identical to stock reference** (zero changes).

---

## Actuator Duty Cycle Polarity — Statically Unproven

> [!WARNING]
> **Static Data Cannot Prove Actuator Polarity**:
> In VAG EDC16 implementations:
> - Physical vacuum pulls the actuator rod against internal spring pressure to move vanes toward the narrow/closed position (maximum turbine drive).
> - However, whether higher numeric percentage in `PCR_rBPCtlBas_MAP` commands more vacuum or less vacuum in SW 1037391847 is **NOT PROVED from static data alone**.
> - The repository's deep-audit explicitly states:
>   > *"The numerical duty direction is not proved from static data. Use the small N75-A surface only if a sign test proves that lower Prc increases initial boost slope."*
> 
> Therefore, no arbitrary 3–6% pre-control edits should be applied without first executing a controlled single-group sign-test.

---

## The `N75-A` Micro-Experiment Specification

If a sign-test proves that lower table numbers increase turbine spool drive, the deep-audit defined a conservative **0.2–0.75 percentage-point** test pocket (NOT 3–6%):

| RPM \\ IQ | 30 mg | 32 mg | 35 mg | 38 mg | 40 mg | 45 mg | Offset Range |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1750 | 56.53→56.28 | 51.00→50.50 | 49.45→48.95 | 47.14→46.64 | 47.43→47.03 | 47.00→46.80 | `0x1EA0B8–0x1EA0C2` |
| 1900 | 47.42→47.02 | 47.00→46.25 | 44.13→43.38 | 44.34→43.59 | 43.87→43.27 | 45.06→44.76 | `0x1EA0D2–0x1EA0DC` |
| 2000 | 46.00→45.75 | 46.00→45.50 | 43.21→42.71 | 43.03→42.53 | 43.34→42.94 | 43.96→43.76 | `0x1EA0EC–0x1EA0F6` |

Status: **HOLD** until sign-test logging is completed.
"""

# 6. fueling-and-limiters.md
DOCUMENTS["fueling-and-limiters.md"] = """# Fueling Architecture & Limiter Hierarchy

## Fuel Quantity Selection Logic

In Bosch EDC16U34, the final injected quantity ($q_{\\text{final}}$ in mg/stroke) delivered to the Pumpe-Düse unit injectors is arbitrated through a strict cascade of limiters:

$$q_{\\text{final}} = \\min(q_{\\text{driver\\_wish}}, q_{\\text{torque\\_limiter}}, q_{\\text{smoke\\_limiter}}, q_{\\text{component\\_protection}})$$

```
                                  +-----------------------+
                                  | Driver Wish IQ        |
                                  | (DrvDem_q_MAP)        |
                                  +-----------------------+
                                              |
                                              v
+-----------------------+         +-----------------------+
| Torque Limiter IQ     |-------->| Arbitrated Minimum IQ |
| (TrqLim_q_MAP)        |         | = min(...)            |
+-----------------------+         +-----------------------+
                                              ^
+-----------------------+                     |
| Smoke Limiter IQ      |---------------------+
| (FlMng_qPresSmoke_MAP)|                     |
+-----------------------+                     |
                                              |
+-----------------------+                     |
| Thermal / Derating IQ |---------------------+
+-----------------------+
```

## Diagnostic Verification via VCDS (Measuring Block 008)

During full-throttle acceleration (3rd gear WOT), log **Measuring Block 008**:
- `Field 1`: Engine Speed (RPM)
- `Field 2`: Driver Wish IQ (mg/stroke) — should be highest (~60–70 mg)
- `Field 3`: Torque Limit IQ (mg/stroke) — calibrated mechanical limit
- `Field 4`: Smoke Limit IQ (mg/stroke) — smoke limiter active value

Whichever field (3 or 4) has the **lower value** is the active governing limiter at that exact RPM.
"""

# 7. smoke-limiter.md
DOCUMENTS["smoke-limiter.md"] = """# Smoke Limiter Strategy: MAP-Based Calibration

## Exact Definition in SW 1037391847

In factory 1.9 TDI BLS configurations equipped with DPF, Bosch utilizes a **MAP-based (manifold pressure) smoke limitation system** as the primary active smoke limiter:

- **A2L Symbol**: `FlMng_qPresSmoke_MAP` (line 462199 in A2L)
- **Description**: *Rauchbegrenzungskennfeld abhängig vom Ladedruck* (Smoke limitation map dependent on charge pressure)
- **Address in Flash**: `0x1D6490` (NOT `0x1E4280`!)
- **Actual Dimensions**: **16 × 12** (NOT 16×16!)
- **RPM Nodes (16)**: `700, 800, 900, 1000, 1100, 1400, 1500, 1600, 1700, 1800, 2000, 2250, 2500, 3000, 4000, 5355`
- **Pressure Nodes (12)**: Corrected pressure hPa (`FlMng_pIATCorr_mp`)
- **Resolution**: 0.01 mg/stroke

> [!IMPORTANT]
> **No 2750 RPM Node Exists**:
> The axis jumps directly from 2500 RPM to 3000 RPM. Any proposal to create a flat "2500–2750 plateau" must understand that 2750 RPM is calculated via linear interpolation between the 2500 and 3000 RPM columns.

## Status in Current Stage 1

- The 1800 and 2000 hPa rows are already modified by approximately +13% over stock reference.
- At 2500 RPM / 2000 hPa: 50.0 mg (ref) → **56.5 mg** (current).
- At 3000 RPM / 2000 hPa: 60.0 mg (ref) → **67.8 mg** (current).
- Deep-audit proposed micro-experiment `SMK-2500` would edit only offset `0x1D6602` (2500 RPM / 2000 hPa: 56.5 mg → 58.5 mg) conditionally.
"""

# 8. injection-duration.md
DOCUMENTS["injection-duration.md"] = """# Pumpe-Düse Injection Duration Maps

## Unit Injector Actuation Mechanics

In the 1.9 TDI BLS Pumpe-Düse system:
- High injection pressure (up to 2050 bar) is generated mechanically by the engine camshaft pressing each unit injector rocker arm.
- The ECU controls fuel delivery by energizing the fast-switching solenoid valve inside each injector.
- Duration is expressed in **Degrees of Crankshaft Angle (°CA)** required to deliver the desired fuel volume at a specific RPM and pressure.

## Duration Map Calibration Integrity

> [!CAUTION]
> **Do Not Falsify Duration Maps**:
> Common amateur tuning methods modify duration maps to inject more fuel without altering torque or IQ limiters (so-called "duration tricking").
> This breaks:
> 1. Real-time consumption calculation on the dashboard.
> 2. Onboard thermal protection models (which compute exhaust gas temperature from genuine IQ).
> 3. ESP/ASR torque coordination.
> 
> In this project, all duration maps remain strictly calibrated to genuine physical injector delivery curves.
"""

# 9. injection-timing.md
DOCUMENTS["injection-timing.md"] = """# Start of Injection (SOI) & Temperature Compensation

## Start of Injection (SOI) Overview

- **A2L Base Map**: `InjCrv_phiMI1Des_MAP`
- **Gear 5-6 Cruise Map**: `InjCrv_phiBasGear56_MAP` at `0x1DACF8` (16 × 14, RPM × mg/stroke)
- **Units**: Degrees Crank Angle Before Top Dead Center (°BTDC) with resolution 0.0234375° CA

## Eco Cruise Advance

In candidate build `stage1_refined_CS_OK`, cruise SOI in Gear 5/6 is advanced by exactly **+0.703125° CA** (30 LSBs) across 1750–2250 RPM and 15–25 mg/stroke to optimize combustion phasing with EGR closed.
"""

# 10. hot-start.md
DOCUMENTS["hot-start.md"] = """# Hot-Start Hesitation & Cranking Torque Architecture

## The Bosch EDC16 Hot Start Problem

A widespread issue in VAG 1.9 TDI Pumpe-Düse engines running EDC16 is prolonged cranking when the engine is at normal operating temperature (75–90°C coolant).

### Root Cause in Calibration (Ground Truth)

The primary cranking torque map is **`StSys_trqStrtBas_MAP`**:
- **Address in Flash**: `0x1F070C`
- **Actual Dimensions**: **9 × 9** (RPM × Coolant °C)
- **RPM Nodes**: `0, 200, 250, 280, 450, 600, 900, 1550, 1600`
- **Coolant Nodes**: Approximately `−24, −18, −10, 0, 20, 40, 60, 80, 100°C`

At 250 RPM, `StSys_trqStrtBas_MAP` delivers **0.0 Nm** across 40°C, 60°C, 80°C, and 100°C. Both base and terminal-50 maps match completely at 280 RPM (108–125 Nm).
As the starter motor and battery age, hot cranking RPM plateaus between 240 and 275 RPM, causing extended dry cranking without fuel delivery.

### The Verified `HS-250` Patch

> [!IMPORTANT]
> **Do Not Perform a Bulk Copy**:
> A bulk copy from `StSys_trqStrt_MAP` alters 14 cells down to 0 RPM, potentially defeating deliberate cranking protection.
> Instead, populate ONLY the 4 missing cells at 250 RPM:

| RPM | Coolant | Current Value | `HS-250` Patch | Flash Offset | Big-Endian S16 Byte Diff |
|---:|---:|---:|---:|---:|---|
| 250 | 39.96°C | 0 Nm | **125 Nm** | `0x1F0762` | `0000 → 04E2` |
| 250 | 59.96°C | 0 Nm | **112 Nm** | `0x1F0764` | `0000 → 0460` |
| 250 | 79.96°C | 0 Nm | **108 Nm** | `0x1F0766` | `0000 → 0438` |
| 250 | 99.96°C | 0 Nm | **108 Nm** | `0x1F0768` | `0000 → 0438` |

This exact patch is implemented in `03G906021QJ_stage1_refined_CS_OK.bin`.
"""

# 11. thermal-protection.md
DOCUMENTS["thermal-protection.md"] = """# Thermal Protection & Component Safety (Bauteilschutz)

## Modeled Exhaust Gas Temperature (EGT)

The 1.9 TDI BLS uses an onboard thermodynamic model to estimate pre-turbine exhaust gas temperature.

- **Limit Threshold**: Pre-turbine EGT must not exceed **805°C continuous** on the BorgWarner BV39 turbocharger.
- **Protection Map**: `EngPrt_facTempPreTrbn_MAP` progressively derates torque when temperature exceeds safe thresholds.
- **Status in Current Vehicle**: Restored and active in `stage1_full_power_dpf_egr_off.bin`.
"""

# 12. hardware-limits.md
DOCUMENTS["hardware-limits.md"] = """# Hardware Mechanical & Thermal Limits — Golf 5 1.9 TDI BLS

## Engine & Drivetrain Boundaries

| Component | Hardware Specification | Safe Calibration Limit | Failure Mode / Consequence |
|---|---|---|---|
| **Turbocharger** | BorgWarner BV39 (`54399880072`) | 2214 mbar target, 2300 mbar transient limit | Shaft overspeed, bearing fatigue, compressor wheel burst |
| **Connecting Rods** | BLS Powdered-Metal Fractured Rods | 330–350 Nm torque maximum | Conrod bending under high cylinder pressure below 2000 RPM |
| **Dual Mass Flywheel** | LUK / Sachs 228mm DMF | 330 Nm, smooth ramp above 2200 RPM | Spring bottoming, vibration, rotational imbalance, clutch slip |
| **Unit Injectors** | BLS OEM Bosch PD | 60–62 mg/stroke maximum delivery | Solenoid duty limits, excessive duration (>35° CA) |
| **Intercooler** | OEM Front-Mounted Plastic End-Tank | 2.5 bar absolute burst limit | End-tank seam separation, charge pipe pop-off |
"""

# 13. a2l-map-index.md
DOCUMENTS["a2l-map-index.md"] = """# Active A2L Map Catalog — SW 1037391847

Curated list of verified active calibration maps in Bosch EDC16U34 SW `1037391847` based on `calibration-enhancements-deep-audit-2026-09-11.md`:

| Map Name | Flash Address | Actual Dimensions | Axes | Unit / Resolution | Verified Role & Status |
|---|---|---|---|---|---|
| `PCR_rBPCtlBas_MAP` | `0x1E9FD0` | **16 × 13** | RPM × mg/stroke | 0.01 % | N75 Pre-control base map; 100% stock reference; polarity unproven |
| `PCR_pBDesBas_MAP` | `0x1EB0B2` | **16 × 10** | RPM × mg/stroke | mbar abs | Boost target; Stage 1 high-load request = **2214 mbar** |
| `FlMng_qPresSmoke_MAP` | `0x1D6490` | **16 × 12** | RPM × corrected hPa | 0.01 mg/stroke | MAP-based smoke limiter; 1800/2000 hPa rows modified +13% |
| `StSys_trqStrtBas_MAP` | `0x1F070C` | **9 × 9** | RPM × coolant °C | 0.1 Nm | Base cranking torque; targets 250 RPM cells in `HS-250` patch |
| `StSys_trqStrt_MAP` | `0x1F07EA` | **9 × 9** | RPM × coolant °C | 0.1 Nm | Terminal-50 cranking torque; reference for HS-250 values |
| `InjCrv_phiBasGear56_MAP` | `0x1DACF8` | **16 × 14** | RPM × mg/stroke | 0.0234375° CA | Cruise SOI 5-6 gear; +0.703° CA in candidate build |
| `TrqLim_trqEng_MAP` | `0x1D9C90` | 21 × 3 | RPM × atmospheric | Nm indicated | Main torque limiter bounding indicated engine torque |
| `DrvDem_tq_MAP` | `0x1D2A40` | 12 × 16 | RPM × pedal % | Nm requested | Driver wish torque request |
| `AirCtl_qHigh_CUR` | `0x1C9DAA` | 20 × 1 | Temp | mg/stroke | EGR hysteresis high threshold (zeroed for EGR OFF) |
| `AirCtl_qMiddle_CUR` | `0x1C9EA0` | 20 × 1 | Temp | mg/stroke | EGR hysteresis middle threshold (zeroed for EGR OFF) |
"""

# 14. firmware-lineage.md
DOCUMENTS["firmware-lineage.md"] = """# Firmware Lineage & Version Control

## Baseline Firmware Images

1. **Factory OEM Baseline**:
   - **File**: `diagnostic-review/reference-from-hex.analysis-only.bin`
   - **Origin**: Extracted from official factory HEX dataset `03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.HEX`
   - **Size**: 2,097,152 bytes (2.0 MB)
   - **Stock High-Load Boost Target**: **2050 mbar**
   - **Status**: Pure stock calibration reference.

2. **Stage 1 Full Power (CURRENTLY FLASHED IN VEHICLE)**:
   - **File**: `03G906021QJ_stage1_full_power_dpf_egr_off.bin`
   - **SHA-256**: `d8296554b0342a9a4eb1ca0af0a17ccbbecc066349907448213ea6179ad2bfe0`
   - **High-Load Boost Request**: **2214 mbar**
   - **Features**: PoI2 zeroed (no unburned fuel smoke), CTSCD restored to 0x0B (no 87°C derate), EGT protection active.
   - **Status**: Currently installed and running in the vehicle.

3. **Stage 1 Refined CS_OK (Candidate Build)**:
   - **File**: `03G906021QJ_stage1_refined_CS_OK.bin`
   - **SHA-256**: `a517affa3f89bf2ba188a84c6b6810b20f61fa297de4917e99cba5f1f18e2b44`
   - **High-Load Boost Request**: **2214 mbar**
   - **Features**: Adds `HS-250` hot start fix and Gear 5/6 cruise SOI (+0.703° CA); checksums verified.
   - **Status**: Static audit complete; NOT flash approved without logging plan.

4. **Stage 1 Ideal DPF & EGR OFF (REJECTED BUILD)**:
   - **File**: `03G906021QJ_ideal_stage1_dpf_egr_off.bin`
   - **Status**: **REJECTED**. Retained stock duration maps and drove too sluggishly.
"""

# 15. log-index.md
DOCUMENTS["log-index.md"] = """# Telemetry & Diagnostic Log Index

## Log Inventory

| Log File | Format | Sampling Rate | Channels Logged | Primary Objective |
|---|---|---|---|---|
| `VCDS_WOT_Log_20260914_114936.csv` | VCDS CSV | ~1.2 Hz (multi-group) | RPM, Specified Boost, Actual Boost, N75 Duty, Driver Wish, Torque Limit, Smoke Limit, MAF | Multi-group log capturing 2310–2320 mbar boost peak vs 2214 mbar request |
| `Turbo_Fast_Log_20260914_210903.csv` | High-Rate OBD CSV | ~4.2 Hz | RPM, MAP absolute, Baro, Boost gauge, MAF, Speed, Engine Load | High-frequency MAP rise time and transient oscillation analysis |
"""

# 16. experiment-results.md
DOCUMENTS["experiment-results.md"] = """# Experiment Results: Overboost Investigation (2310–2320 mbar)

## Observed Phenomenon

In the 3rd gear full-throttle acceleration run:
- **Engine Speed Range**: 1900–2600 RPM
- **Specified Boost Target**: **2214 mbar absolute** (calibrated Stage 1 request)
- **Actual Measured MAP**: Peaked at **~2310–2320 mbar absolute** at ~2180 RPM
- **Overshoot Magnitude**: $+96\\dots+106\\text{ mbar}$ ($+4.5\\dots+4.8\\%$ above specified target)

```
Boost (mbar)
2350 |
2320 |                   * * (Peak 2310–2320 mbar)
2300 |                 *     *
2214 |  Specified --> *-------*---------------- (2214 mbar)
2100 |              *           *
2000 |            *               *
1900 |          *
     +----------------------------------------> RPM / Time
             1800  2000  2200  2400  2600
```

## Epistemic Evaluation: Competing Hypotheses A–G

> [!NOTE]
> In accordance with [RESEARCH_POLICY.md](RESEARCH_POLICY.md), the root cause is **NOT** declared an established fact. The following competing hypotheses are under active evaluation:

- **Hypothesis A (Specified Target Elevated)**: *Rejected*. Stage 1 request is confirmed at 2214 mbar.
- **Hypothesis B (Feed-Forward Duty Elevated Post-EGR Delete)**: *Hypothesis (RAW)*. With EGR closed, 100% of exhaust gas expands across the turbine. If stock feed-forward (`PCR_rBPCtlBas_MAP`) was tuned for 15–30% EGR bypass, it holds vanes too closed during transient spool-up. Requires sign-test to confirm.
- **Hypothesis C (PID Transient Damping)**: *Hypothesis (RAW)*. PID derivative or proportional gain may be under-damped for the rapid spool-up rate.
- **Hypothesis D (Sensor / Sampling Alias)**: *Hypothesis (RAW)*. The ~1.2 Hz sampling rate of multi-group VCDS logging obscures the true peak shape and settling time.
- **Hypothesis G (Mechanical Actuator Hysteresis)**: *Hypothesis (RAW)*. Vacuum bleed rate through N75 solenoid or actuator rod friction creates pneumatic delay.
"""

# 17. conflicting-evidence.md
DOCUMENTS["conflicting-evidence.md"] = """# Conflicting Evidence & Dispute Resolution

## Conflict Case 1: N75 Actuator Duty Polarity in VCDS

- **Claim A (Common Forum Convention)**: "Higher duty percentage means opening the vanes to decrease boost."
- **Claim B (Pneumatic Mechanics / SSP 304)**: "Higher duty percentage energizes the solenoid to apply vacuum, pulling the actuator rod to close the vanes for maximum spool."
- **Audit Ground Truth**: In this specific EDC16U34 SW 1037391847, numerical table direction is **UNPROVEN statically**. A controlled runtime sign-test must be performed before altering `PCR_rBPCtlBas_MAP`.

---

## Conflict Case 2: Smoke Limiter Selection on BLS

- **Claim A**: BLS uses MAF-based smoke limitation (`FlMng_qAirSmoke_MAP`).
- **Claim B**: BLS factory DPF software uses MAP-based smoke limitation (`FlMng_qPresSmoke_MAP`).
- **Resolution**: **Verified**. A2L inspection and binary comparison confirm `FlMng_qPresSmoke_MAP` at `0x1D6490` is actively modified (+13%) in the DPF software branch.
"""

# 18. open-questions.md
DOCUMENTS["open-questions.md"] = """# Project Open Questions & Competing Hypotheses

## Core Project Research Questions

1. Does lower numerical percentage in `PCR_rBPCtlBas_MAP` increase or decrease initial boost rise slope? *(Sign-test required)*.
2. Which limiter actively governs fuel injection during the 1800–2400 RPM spool-up window (Torque limit vs Smoke limit `FlMng_qPresSmoke_MAP`)?
3. How does the IQ axis of `PCR_rBPCtlBas_MAP` extrapolate when IQ exceeds the final defined column (45 mg)?
4. What is the exact settling time of boost regulation when logged at > 4 Hz?
5. Does the candidate build `stage1_refined_CS_OK` resolve warm-start delay cleanly in vehicle testing?
"""

# 19. recommended-tests.md
DOCUMENTS["recommended-tests.md"] = """# Recommended Test Protocols for Vehicle Validation

## Test Protocol 1: High-Rate Boost Closed-Loop Run (MVB 011 Only)

- **Diagnostic Tool**: VCDS (VAG-COM)
- **Engine Control Module**: `01 - Engine`
- **Measurement Selection**: **Select Group 011 ONLY** (do not select Groups 003 or 008 simultaneously).
  - *Reason*: Selecting 1 group increases VCDS sample frequency from ~1.2 Hz to ~3.8–4.5 Hz, capturing the exact shape of the transient peak without alias error.
- **Channels**:
  - `011.1`: Engine Speed (RPM)
  - `011.2`: Boost Specified (mbar)
  - `011.3`: Boost Actual (mbar)
  - `011.4`: N75 Duty Cycle (%)
- **Driving Maneuver**: 3rd gear straight flat road, stabilize at 1400 RPM, floor accelerator pedal to 100% until 3800 RPM, lift off.

---

## Test Protocol 2: Fueling & Limiter Arbitration Run (MVB 008 Only)

- **Measurement Selection**: **Select Group 008 ONLY**.
- **Channels**:
  - `008.1`: Engine Speed (RPM)
  - `008.2`: Driver Wish IQ (mg/stroke)
  - `008.3`: Torque Limiter IQ (mg/stroke)
  - `008.4`: Smoke Limiter IQ (mg/stroke)
- **Driving Maneuver**: Identical 3rd gear WOT pull from 1400 to 3800 RPM.
"""

# 20. research-changelog.md
DOCUMENTS["research-changelog.md"] = """# Research Changelog & Bootstrap History

## Version 1.1.0 — 2026-09-16 (Ground-Truth Alignment Pass)
- **Addresses & Dimensions Aligned with Deep-Audit**:
  - `PCR_rBPCtlBas_MAP`: corrected dimensions to **16×13** at `0x1E9FD0`.
  - `FlMng_qPresSmoke_MAP`: corrected address to **`0x1D6490`** and dimensions to **16×12** (RPM × corrected pressure hPa).
  - `StSys_trqStrtBas_MAP`: confirmed address at **`0x1F070C`** (9×9) and exact `HS-250` cells at `0x1F0762–0x1F0768`.
- **Target Boost Calibration**: Corrected high-load Stage 1 target from draft 2350 mbar to verified **2214 mbar** (stock reference: 2050 mbar).
- **Epistemic Status Sanitization**: Downgraded unverified assertions (overboost root cause, N75 numerical duty direction) from verified to `raw` / `hypothesis`.
- **Firmware Lineage Correction**: Explicitly noted that `stage1_full_power` is active in car, `stage1_refined_CS_OK` is candidate build, and `ideal_stage1` was rejected as sluggish.
- **Database Synchronization**: Re-seeded and re-indexed `knowledge/edc16_knowledge.db` with ground-truth records.
"""


def main():
    for fname, content in DOCUMENTS.items():
        fpath = DOCS_DIR / fname
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
        print(f"Generated {fpath} ({len(content)} bytes)")
    print("\nAll 20 knowledge documents generated and aligned with deep-audit ground truth.")


if __name__ == "__main__":
    main()
