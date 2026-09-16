# Source Index — EDC16U34 Engineering Knowledge Base

This document catalogues all foundational, engineering, diagnostic, and project-specific sources ingested into the **EDC16U34 Knowledge Base** (`knowledge/edc16_knowledge.db`).

## Authority & Applicability Scoring System

In accordance with [RESEARCH_POLICY.md](RESEARCH_POLICY.md):
- **Authority Score (1–5)**: Credibility of the publisher and scientific/engineering rigor (5 = OEM/Bosch/ASAM, 4 = SAE/ETAS/Textbooks, 3 = Ross-Tech/TDIClub, 2 = Tuner blogs, 1 = Unverified forums).
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

## Tier C: Exact Project Evidence (Level 5 / Applicability 5)

| ID | Resource Name | Local Repository Path | SHA-256 Hash | Notes |
|---|---|---|---|---|
| P-01 | **Factory A2L Definition Dataset** | `diagnostic-review/definitions/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.a2l` | `verified` | Exact 12.6 MB ASAP2 matching SW 1037391847 with 11,537 characteristics |
| P-02 | **Reference Factory Binary** | `diagnostic-review/reference-from-hex.analysis-only.bin` | `b3f36070a7b4582f3efce39ff6d46487e45218d6e3cbebe4fbe8cbdbdffca577` | 2,097,152 bytes uncorrupted OEM baseline |
| P-03 | **Stage 1 Refined CS_OK** | `03G906021QJ_stage1_refined_CS_OK.bin` | `verified` | Active tuned image with verified checksum |
| P-04 | **Stage 1 DPF & EGR OFF** | `03G906021QJ_ideal_stage1_dpf_egr_off.bin` | `verified` | Active tuned image with DPF switch and EGR closed |
| P-05 | **VCDS WOT Log (2026-09-14)** | `logs/VCDS_WOT_Log_20260914_114936.csv` | `verified` | Road pull capturing 2330 mbar transient overboost |
| P-06 | **Turbo Fast OBD Log** | `logs/Turbo_Fast_Log_20260914_210903.csv` | `verified` | High-frequency MAP and RPM transient recording |
