#!/usr/bin/env python3
"""
tools/generate_knowledge_docs.py — Knowledge Document Generator for EDC16U34 Bootstrap Pack
EPISTEMIC HARDENING VERSION (1.2.0):
- Removes unconfirmed MCU/OS assertions (MPC562 CALRAM 32 KB per NXP datasheet).
- Changes map catalog to Statically Matched (runtime_active_proven = false).
- Separates static calibration target (2214 mbar) from runtime requested boost (UNKNOWN in OBD stream).
- Disentangles 14.09.2026 legacy logs from 16.09.2026 fresh telemetry.
- Splits hot-start static identity (completed) from in-vehicle validation (pending).
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
> - **Primary Ground Truth**: `diagnostic-review/*` + raw matching A2L (`03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.a2l`) + exact reference/active BINs + real telemetry logs.
> - **Draft Knowledge Layer**: `docs/knowledge/*` represents the synthesized working model subject to continuous verification and sign-test logging.

| ID | Resource Name | Local Repository Path | Role / Status | Notes |
|---|---|---|---|---|
| P-01 | **Factory A2L Definition Dataset** | `diagnostic-review/definitions/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.a2l` | Primary Definition | Exact 12.6 MB ASAP2 matching SW 1037391847 with 11,537 characteristics |
| P-02 | **Reference Factory Binary** | `diagnostic-review/reference-from-hex.analysis-only.bin` | Baseline Reference | 2,097,152 bytes uncorrupted OEM baseline (stock request: 2050 mbar) |
| P-03 | **Stage 1 Full Power (Active in Car)** | `03G906021QJ_stage1_full_power_dpf_egr_off.bin` | **Currently Flashed in Car** | Active in vehicle: boost target 2214 mbar, PoI2 off (0.0 mg), CTSCD restored to 0x0B, EGT protection active |
| P-04 | **Stage 1 Refined CS_OK** | `03G906021QJ_stage1_refined_CS_OK.bin` | Candidate Image | Static audit only (not flash approved without logging plan); contains HS-250 fix and Gear 5/6 cruise SOI (+0.703°) |
| P-05 | **Stage 1 Ideal (Rejected Build)** | `03G906021QJ_ideal_stage1_dpf_egr_off.bin` | **Rejected Test Build** | Test build with factory duration maps that drove too sluggishly; rejected |
| P-06 | **Calibration Enhancements Audit** | `diagnostic-review/calibration-enhancements-deep-audit-2026-09-11.md` | Ground Truth Audit | Authoritative audit of HS-250, N75-A, SMK-2500, and cruise SOI |
| P-07 | **Telemetry Run 2026-09-16 (11:20:35)** | `logs/20260916/Turbo_Pair_20260916_112035.csv` | Active Vehicle Telemetry | Log under stage1_full_power showing rapid spool and ~2310–2330 mbar peak MAP |
| P-08 | **Legacy VCDS Log (2026-09-14)** | `logs/VCDS_WOT_Log_20260914_114936.csv` | Legacy Diagnostic Run | Old garage software run before PoI2 zeroing, CTSCD repair, and EGT limiter restoration |
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
|  | - 32-bit RISC core, 56/66 MHz                          |  |
|  | - Internal SRAM: 32 KB CALRAM (per NXP MPC562 spec)   |  |
|  +-------------------------------------------------------+  |
|                             |                               |
|                             v                               |
|  +-------------------------------------------------------+  |
|  | External Flash Memory (2,097,152 bytes / 2 MB)        |  |
|  | Typical parts: AMD AM29BL802CB / ST M58BW016DB family  |  |
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
- **Base Boost Target Map (`PCR_pBDesBas_MAP`)**: `0x1EB0B2` (16×10)
- **Smoke Limiter (`FlMng_qPresSmoke_MAP`)**: `0x1D6490` (16×12)
- **Hot-Start Base Torque (`StSys_trqStrtBas_MAP`)**: `0x1F070C` (9×9)
- **Hot-Start Term 50 Torque (`StSys_trqStrt_MAP`)**: `0x1F07EA` (9×9)
- **Cruise SOI 5-6 Gear (`InjCrv_phiBasGear56_MAP`)**: `0x1DACF8` (16×14)

---

## Operating System & Execution Tasks

> [!NOTE]
> Bosch EDC16 systems typically execute multi-rate time-triggered tasks (e.g., 10 ms boost regulation, 20 ms torque coordination, 100 ms thermal monitoring) alongside angle-synchronous injection tasks (every 180° crank angle). Exact task raster scheduling in SW 1037391847 remains a typical Bosch reference model until disassembler verification is completed.
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

> [!IMPORTANT]
> **Static Target vs Runtime Request**:
> - `calibration_map_high_load = 2214 mbar` is the static value in the calibration map.
> - In any specific vehicle run, `runtime_specified` may differ due to transient filtering, cold/hot temperature scaling, or atmospheric derating.
> - In the 16.09.2026 OBD pair log (`Turbo_Pair_20260916_112035.csv`), `runtime_specified` was **UNKNOWN** because that specific PID channel was not polled.

### 2. Atmospheric & Environmental Corrections
- Altitude compensation (`PCR_pBDesAtm_MAP`): Derates boost request as ambient barometric pressure decreases below 1000 mbar to prevent turbocharger overspeed in thin air.
- Charge temperature compensation (`PCR_pBDesT_MAP`): Derates target if intake air temperature (IAT) exceeds calibrated thermal thresholds.
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
> Therefore, no arbitrary pre-control edits should be applied without first executing a controlled single-group sign-test.

---

## The `N75-A` Micro-Experiment Specification

If a sign-test proves that lower table numbers increase turbine spool drive, the deep-audit defined a conservative **0.2–0.75 percentage-point** test pocket:

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
- Deep-audit proposed micro-experiment `SMK-2500` would edit only offset `0x1D6602` (2500 RPM / 2000 hPa: 56.5 mg → 58.5 mg) conditionally after logging confirms it is the binding limiter.
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
- **Static Status**: `STATICALLY_MATCHED` (A2L line 268931)

At 250 RPM, `StSys_trqStrtBas_MAP` delivers **0.0 Nm** across 40°C, 60°C, 80°C, and 100°C. Both base and terminal-50 maps match completely at 280 RPM (108–125 Nm).
As the starter motor and battery age, hot cranking RPM plateaus between 240 and 275 RPM, causing extended dry cranking without fuel delivery.

### The Verified `HS-250` Patch

| RPM | Coolant | Current Value | `HS-250` Patch | Flash Offset | Big-Endian S16 Byte Diff |
|---:|---:|---:|---:|---:|---|
| 250 | 39.96°C | 0 Nm | **125 Nm** | `0x1F0762` | `0000 → 04E2` |
| 250 | 59.96°C | 0 Nm | **112 Nm** | `0x1F0764` | `0000 → 0460` |
| 250 | 79.96°C | 0 Nm | **108 Nm** | `0x1F0766` | `0000 → 0438` |
| 250 | 99.96°C | 0 Nm | **108 Nm** | `0x1F0768` | `0000 → 0438` |

> [!NOTE]
> **Static Identification vs Vehicle Validation**:
> - `TASK-HOTSTART-MAP-IDENTITY`: **COMPLETED** (offsets, dimensions, and values statically verified).
> - `TASK-HOTSTART-HS250-VALIDATION`: **PENDING** (requires in-vehicle warm restart log to validate starting time without shudder).
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
| **Turbocharger** | BorgWarner BV39 (`54399880072`) | 2214 mbar target, ~2350 mbar continuous limit | Shaft overspeed, bearing fatigue, compressor wheel burst |
| **Connecting Rods** | BLS Powdered-Metal Fractured Rods | 330–350 Nm torque maximum | Conrod bending under high cylinder pressure below 2000 RPM |
| **Dual Mass Flywheel** | LUK / Sachs 228mm DMF | 330 Nm, smooth ramp above 2200 RPM | Spring bottoming, vibration, rotational imbalance, clutch slip |
| **Unit Injectors** | BLS OEM Bosch PD | 60–62 mg/stroke maximum delivery | Solenoid duty limits, excessive duration (>35° CA) |
| **Intercooler** | OEM Front-Mounted Plastic End-Tank | 2.5 bar absolute burst limit | End-tank seam separation, charge pipe pop-off |
"""

# 13. a2l-map-index.md
DOCUMENTS["a2l-map-index.md"] = """# Statically Matched A2L Map Catalog — SW 1037391847

> [!IMPORTANT]
> **Static Match vs Runtime Execution**:
> Agreement between A2L symbol names, addresses, and dimensions proves **static structure**, but does **NOT** prove which duplicate or variant map bank actively executes at runtime in the vehicle.
> All maps below carry `static_match_proven = true` and `runtime_active_proven = false` until runtime component logging demonstrates execution.

| Map Name | Flash Address | Actual Dimensions | Axes | Unit / Resolution | Match Status | Runtime Active |
|---|---|---|---|---|---|:---:|
| `PCR_rBPCtlBas_MAP` | `0x1E9FD0` | **16 × 13** | RPM × mg/stroke | 0.01 % | `STATICALLY_MATCHED` | `unproven` |
| `PCR_pBDesBas_MAP` | `0x1EB0B2` | **16 × 10** | RPM × mg/stroke | mbar abs | `STATICALLY_MATCHED` | `unproven` |
| `FlMng_qPresSmoke_MAP` | `0x1D6490` | **16 × 12** | RPM × corrected hPa | 0.01 mg/stroke | `STATICALLY_MATCHED` | `unproven` |
| `StSys_trqStrtBas_MAP` | `0x1F070C` | **9 × 9** | RPM × coolant °C | 0.1 Nm | `STATICALLY_MATCHED` | `unproven` |
| `StSys_trqStrt_MAP` | `0x1F07EA` | **9 × 9** | RPM × coolant °C | 0.1 Nm | `STATICALLY_MATCHED` | `unproven` |
| `InjCrv_phiBasGear56_MAP` | `0x1DACF8` | **16 × 14** | RPM × mg/stroke | 0.0234375° CA | `STATICALLY_MATCHED` | `unproven` |
| `TrqLim_trqEng_MAP` | `0x1D9C90` | 21 × 3 | RPM × atmospheric | Nm indicated | `STATICALLY_MATCHED` | `unproven` |
| `DrvDem_tq_MAP` | `0x1D2A40` | 12 × 16 | RPM × pedal % | Nm requested | `STATICALLY_MATCHED` | `unproven` |
| `AirCtl_qHigh_CUR` | `0x1C9DAA` | 20 × 1 | Temp | mg/stroke | `STATICALLY_MATCHED` | `unproven` |
| `AirCtl_qMiddle_CUR` | `0x1C9EA0` | 20 × 1 | Temp | mg/stroke | `STATICALLY_MATCHED` | `unproven` |
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

## Delineation of Log Datasets

Logs from 14.09.2026 and 16.09.2026 must be treated as **independent datasets** captured under different calibrations:

### 1. Active Telemetry Runs (16.09.2026) — Under `stage1_full_power`
- **File**: `logs/20260916/Turbo_Pair_20260916_112035.csv`
- **Firmware in Vehicle**: `stage1_full_power_dpf_egr_off.bin`
- **Channels Logged**: RPM, MAP absolute, Barometric pressure, Speed, Engine Load, MAF.
- **Observations**: Fast spool (1890 mbar at 1459 RPM, 2020 mbar at 1573 RPM); actual MAP plateau at **~2310–2330 mbar** across 1900–2600 RPM.
- **Limitation**: Synchronous requested boost was **NOT LOGGED** in this OBD pair stream (`runtime_specified = UNKNOWN`).

### 2. Legacy Diagnostic Runs (14.09.2026) — Under Old Garage Calibration
- **File**: `logs/VCDS_WOT_Log_20260914_114936.csv`
- **Firmware in Vehicle**: Old garage calibration (pre-repair: CTSCD bugged, PoI2 active).
- **Channels Logged**: Multi-group VCDS (~1.2 Hz) capturing RPM, Specified Boost, Actual Boost, N75 Duty, IQ channels.
- **Notes**: Demonstrates old calibration lag (-336 mbar deficit at 1400 RPM) and transient spikes under the defective baseline.
"""

# 16. experiment-results.md
DOCUMENTS["experiment-results.md"] = """# Experiment Results: Boost Telemetry Analysis (16.09.2026 Run)

## Telemetry Observation (Pull 11:20:35)

Captured from road acceleration run under `stage1_full_power_dpf_egr_off.bin`:

| RPM | Actual MAP (mbar abs) | Calibrated Map Target | Synchronous Runtime Request |
|---:|---:|---:|:---:|
| 1459 | 1890 | 1650 | *UNKNOWN* |
| 1573 | 2020 | 1850 | *UNKNOWN* |
| 1741 | 2230 | 2050 | *UNKNOWN* |
| 1906 | 2320 | 2214 | *UNKNOWN* |
| 2153 | **2330** (Peak) | 2214 | *UNKNOWN* |
| 2329 | 2320 | 2214 | *UNKNOWN* |
| 2553 | 2320 | 2214 | *UNKNOWN* |
| 2707 | 2310 | 2214 | *UNKNOWN* |
| 2980 | 2210 | 2214 | *UNKNOWN* |

## Rigorous Epistemic Breakdown

- **`calibration_map_high_load`**: **2214 mbar** (verified static plateau in `PCR_pBDesBas_MAP`).
- **`runtime_specified`**: **UNKNOWN** (channel not polled in this OBD pair run).
- **`runtime_actual_peak`**: **~2310–2330 mbar** (measured by MAP sensor G31).
- **`overshoot_vs_runtime_request`**: **UNKNOWN** (mathematical overshoot cannot be asserted without synchronous requested boost).

---

## Competing Hypotheses A–G (Status: RAW)

1. **Hypothesis A (Static Request Elevated)**: *Disproved*. High-load map request is verified at 2214 mbar.
2. **Hypothesis B (Zero-EGR Mass Flow / VNT Pre-Control)**: *Hypothesis*. 100% closed EGR diverts full exhaust mass through turbine; stock feed-forward may hold vanes too closed.
3. **Hypothesis C (PID Transient Damping)**: *Hypothesis*. Derivative/proportional gains under-damped for spool-up rate.
4. **Hypothesis D (Dynamic Corrections Active)**: *Hypothesis*. Temperature or atmospheric compensation may have temporarily adjusted target above 2214 mbar.
5. **Hypothesis G (Actuator Hysteresis)**: *Hypothesis*. Vacuum bleed rate or rod friction creates pneumatic lag.

> [!IMPORTANT]
> To definitively resolve these hypotheses, **Test Protocol 1 (MVB 011 single-group high-rate run)** must be executed to record synchronous requested boost, actual boost, and N75 duty at >3.8 Hz.
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
2. What is the synchronous runtime requested boost during the 1900–2600 RPM pull? *(MVB 011 log required)*.
3. Which limiter actively governs fuel injection during the 1800–2400 RPM spool-up window (Torque limit vs Smoke limit `FlMng_qPresSmoke_MAP`)?
4. How does the IQ axis of `PCR_rBPCtlBas_MAP` extrapolate when IQ exceeds the final defined column (45 mg)?
5. Does the candidate build `stage1_refined_CS_OK` resolve warm-start delay cleanly without shudder in vehicle testing?
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

## Version 1.2.0 — 2026-09-16 (Epistemic Hardening Pass)
- **Schema & Database Hardening**:
  - `claims` table: Default project identifiers changed to `NULL` to prevent generic Tier A/B literature bleeding into vehicle-specific claims.
  - `map_definitions` table: Replaced `is_verified_active` with explicit `static_match_proven` and `runtime_active_proven`.
- **Map Catalog Status**: Changed catalog status to `STATICALLY_MATCHED (A2L)` with explicit disclaimer that static agreement does not prove runtime duplicate table selection.
- **Telemetry Disentanglement**:
  - Separated 14.09.2026 legacy logs from 16.09.2026 telemetry.
  - Recorded: `calibration_map_high_load = 2214 mbar`, `runtime_specified = UNKNOWN`, `runtime_actual_peak = 2310–2330 mbar`, `overshoot_vs_runtime_request = UNKNOWN`.
- **Task Splitting**: Split hot-start into `TASK-HOTSTART-MAP-IDENTITY` (completed) and `TASK-HOTSTART-HS250-VALIDATION` (pending).
- **Hardware Corrections**: Corrected MPC562 internal CALRAM specification to 32 KB per NXP datasheet.
"""


def main():
    for fname, content in DOCUMENTS.items():
        fpath = DOCS_DIR / fname
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
        print(f"Generated {fpath} ({len(content)} bytes)")
    print("\nAll 20 knowledge documents generated and epistemically hardened.")


if __name__ == "__main__":
    main()
