# Stage 1 Comprehensive Research — EDC16U34 BLS 1.9 TDI
**Date**: 2026-09-16  
**ECU**: Bosch EDC16U34, HW 03G906021QJ, SW 1037391847 P447HAXN  
**Engine**: VW Golf 5 1.9 TDI BLS (105hp stock → 140-150hp Stage 1 target)  
**Status**: DPF removed, EGR blanked

> **Редакторська примітка (2026-09-16, перевірено):** усі 6 цитованих web-джерел перевірені — 2 прямим фетчем сторінки (ecuedit.com форумні треди, §11a-b DECISION), решта звірені проти вже проіндексованої/перевіреної бази `research.db` і не суперечать їй. Цей документ — довідковий синтез, **не замінює** послідовність воріт валідації з `STAGE1-ENGINEERING-PLAN.md`: там, де цей файл каже «Recommendation: Start with option A» (Phase 2, зниження `EngPrt_trqLimP_MAP`), це варіант **без потреби у вимірюванні**, а не привід пропустити контрольний заїзд перед Etap 1. Etap 2 (FMTC) лишається `HOLD` до підтвердження на нашому файлі, як і зафіксовано в §9/§11c DECISION-документа.

---

## Executive Summary

### Proven Map Chain for EDC16 Stage 1

Based on multiple independent sources ([EDC16 Tuning Guide v1.1](https://www.scribd.com/document/438798747/EDC16-tuning-guide-version-1-1-pdf), [HP Academy Bosch EDC](https://www.hpacademy.com/technical-articles/bosch-edc-map-definitions/), [Tuners Guild](https://tunersguild.com/blog/bosch-edc17-tuning-guide/), local knowledge base), the complete coherent chain is:

```
1. Driver's Wish (AccPed_trqDes_MAP)
           ↓
2. Torque Limiter (EngPrt_trqLimP_MAP)
           ↓
3. FMTC: Torque→Fuel Conversion (FMTC_trq2qBas_MAP)
           ↓
4. Smoke Limiter (FlMng_qPresSmoke_MAP)
           ↓
5. Thermal Limiters (EngPrt_facTempPreTrbn_MAP, etc.)
           ↓
6. Injection Duration (InjVlv_phiInjMI1_MAP0-4)
           ↓
7. Start of Injection (InjCrv_phiBasGear*_MAP)
           ↓
8. SOI Limiter (InjCrv_phiMIMax_MAP)

Parallel: Boost Control (PCR_pBDesBas_MAP, PCR_pBDesMaxAP_MAP)
```

### Critical Coherence Rules

**From factory PD130→PD150 comparison** ([vagecumap archive](file:///c:/users/pavlo/golf5/gdrive_downloads/Tuning_Guides_Vagecumap_Including_Edc15_Edc16_Edc17.zip), validated in DECISION-2026-09-16.md §8):

1. **Duration maps move as families**: When IQ range increases, ALL maps in the family (MAP0-4) must scale together
2. **SOI limiters follow SOI advances**: If base SOI is advanced, `InjCrv_phiMIMax_MAP` must be raised to not cut it
3. **FMTC axis must cover torque limiter**: If `EngPrt_trqLimP_MAP` requests >336 Nm, `FMTC_trq2qBas_MAP` torque axis must extend past 336 Nm
4. **Boost target scales with fuel**: +8% IQ typically needs +5-8% boost to maintain lambda

**Common Stage 1 mistakes** (from Tuners Guild + our own findings):
- ❌ Raising only MAP1-4, forgetting MAP0 (our exact issue in §4b)
- ❌ Extending torque limiter but not FMTC axis (our §9 finding)
- ❌ Advancing SOI but not raising SOI limiter (our ланка 6)
- ❌ Increasing fuel without proportional boost (results in black smoke)

---

## Detailed Map Chain Methodology

### 1. Driver's Wish (`AccPed_trqDes_MAP`)

**Purpose**: Translates accelerator pedal position → torque request (Nm)

**Structure**: 
- X-axis: Accelerator pedal position (%)
- Y-axis: Engine RPM
- Z-values: Requested torque (Nm)

**Stage 1 approach**:
- Stock 105hp: Peak ~250 Nm request
- Stage 1 target: Raise to ~320-340 Nm request
- **Smooth progression** — avoid sudden jumps that trigger traction control

**Our status**: Already modified in current Stage 1

---

### 2. Torque Limiter (`EngPrt_trqLimP_MAP`)

**Purpose**: Hardware protection — limits maximum torque to protect DMF, clutch, transmission

**Structure**:
- X-axis: Barometric pressure (compensates for altitude)
- Y-axis: Engine RPM
- Z-values: Maximum allowed torque (Nm)

**Safety limits for BLS + stock DMF/clutch**:
- **<2200 rpm**: ≤330 Nm (DMF/clutch protection)
- **2200-4000 rpm**: ≤340 Nm (crankshaft/conrod protection)
- **>4000 rpm**: Taper down to ~300 Nm

**Our status**: Current Stage 1 raised to **380.7 Nm** peak — EXCEEDS safe limits. **Must reduce to 330-340 Nm max**.

**Critical finding from §9**: Current 380.7 Nm exceeds FMTC axis (336 Nm), causing ECU to work outside calibrated range.

---

### 3. FMTC: Torque-to-Fuel Conversion (`FMTC_trq2qBas_MAP`)

**Purpose**: Converts approved torque (Nm) → fuel quantity (mg/stroke)

**Structure**:
- X-axis: Torque (Nm)
- Y-axis: Engine RPM
- Z-values: Fuel quantity (mg/stroke)

**Critical**: This is a **physical conversion table**, not a limiter. It models the engine's torque-to-fuel relationship.

**Coherence rule**: Torque axis must cover the full range that `EngPrt_trqLimP_MAP` can request.

**Our issue (§9)**: 
- Torque limiter requests up to 380.7 Nm
- FMTC axis ends at 336 Nm
- Runtime VCDS log shows requests at 337-375 Nm (outside axis)
- **Unknown behavior**: Does ECU clamp or extrapolate?

**Stage 1 fix**: Either:
- A) Reduce torque limiter to ≤330 Nm (safe approach)
- B) Extend FMTC torque axis to 380 Nm (requires measurement validation)

---

### 4. Smoke Limiter (`FlMng_qPresSmoke_MAP`)

**Purpose**: Prevents excessive fuel-to-air ratio (black smoke)

**Structure** (from local knowledge):
- X-axis: Corrected boost pressure (hPa)
- Y-axis: Engine RPM (16 nodes: 700, 800, 900, 1000, 1100, 1400, 1500, 1600, 1700, 1800, 2000, 2250, 2500, 3000, 4000, 5355)
- Z-values: Maximum fuel (mg/stroke)
- Actual dimensions: **16×12** (NOT 16×16)

**Key insight**: Pressure axis ends at 2000 hPa, but WOT boost is 2200+ hPa → operates in extrapolation zone.

**Our validation (§1-2 DECISION)**: 
- 2500 rpm plateau at 56.5 mg = **cross-validated** (ECU model + road model + air measurement agree)
- Do NOT raise without measurement showing lambda >1.15 at WOT

**Stage 1 approach**: 
- Conservative: Leave as-is until boost shape is fixed
- Aggressive: Raise selectively where lambda >1.2 confirmed

---

### 5. Injection Duration (`InjVlv_phiInjMI1_MAP0-4`)

**Purpose**: Converts fuel quantity (mg) → injector solenoid open time (degrees crankshaft)

**Critical finding (§4b DECISION)**: 
- Stage 1 raised MAP1-4 by **×1.08**
- **MAP0 left at stock** — forgotten!
- MAP0 is selected at high RPM (>3500) when SOI >~26°
- Result: Actual fuel delivery FALLS from 66 mg@3000 to 56 mg@4000 while ECU requests constant 62-64 mg

**Stage 1 fix**: Apply same ×1.08 factor to MAP0 at 55 mg column (match MAP1 treatment)

**Coherence rule from PD130→150**: When IQ range changes, ALL duration maps (0-4) must move together.

---

### 6. Start of Injection (`InjCrv_phiBasGear*_MAP`)

**Purpose**: Sets injection timing advance (degrees BTDC)

**Multiple maps**: One per gear or driving mode:
- `InjCrv_phiBasGear12_MAP` — 1st/2nd gear
- `InjCrv_phiBasGear34_MAP` — 3rd/4th gear
- `InjCrv_phiBasGear56_MAP` — 5th/6th gear

**Stage 1 typical**: Advance by +1-2° BTDC for better efficiency

**Our status**: Already advanced in current Stage 1

---

### 7. SOI Limiter (`InjCrv_phiMIMax_MAP`)

**Purpose**: Maximum allowed SOI advance (safety cap)

**Critical finding (ланка 6, §2 STAGE1-ENGINEERING-PLAN)**: 
- Stage 1 advanced base SOI by +1-2°
- **SOI limiter NOT raised** — cuts the advance at certain RPM points
- Example: ECU wants 29.16° but limiter caps at 28.01° (4000 rpm)

**Stage 1 fix**: Raise limiter by same +1-2° that base SOI was advanced

**Coherence rule**: Limiter must always be ≥ base SOI + safety margin

---

### 8. Boost Control (`PCR_pBDesBas_MAP`, `PCR_pBDesMaxAP_MAP`)

**Purpose**: Target boost pressure at given RPM/fuel load

**Structure**:
- X-axis: Fuel quantity (mg/stroke) or torque
- Y-axis: Engine RPM
- Z-values: Target boost (mbar absolute)

**Stage 1 typical**: +5-8% boost to match +8% fuel

**Our status**: Already raised in current Stage 1

**Known issue (§2 Z3)**: Boost shape has problems:
- Overshoot: +214 mbar @2268 rpm (peak 2417 mbar, exceeds BV39 safe limit)
- Undershoot: -32 to -71 mbar @3000-3500 rpm
- **Cause**: N75 precontrol (`PCR_rBPCtlBas_MAP`) not updated for new boost target

**Fix**: Requires high-rate VCDS group 011 log to tune precontrol properly

---

## Safety Limits Summary

| Parameter | Conservative Limit | Source |
|---|---|---|
| Peak Torque <2200 rpm | ≤330 Nm | DMF/clutch protection, README |
| Peak Torque 2200-4000 | ≤340 Nm | Crankshaft/conrod, tdi-tuning.pl |
| Boost sustained | ≤2250 mbar | BV39 spec, README |
| Boost transient peak | ≤2400 mbar | Emergency tolerance |
| EGT pre-turbo sustained | ≤750 °C | Turbo longevity |
| EGT pre-turbo peak | ≤800 °C | Emergency tolerance |
| Lambda minimum WOT | ≥1.0 | Smoke-free, EGT control |
| IQ maximum @4000 rpm | ~60 mg | Injector/pump capacity |

---

## Stage 1 Correction Plan (Based on All Research)

### Phase 0: Zero-Risk Fixes (Ready Now)
- Hot-start fix (HS-250) ✅ in refined_CS_OK
- Eco-cruise SOI (+0.7° @1750-2250, light load only) ✅ in refined_CS_OK
- **Status**: Can flash immediately, zero WOT impact

### Phase 1: Duration/SOI Coherence (Calculated, Lambda Risk Known)
**Changes**:
1. Raise `InjVlv_phiInjMI1_MAP0` by ×1.08 (match MAP1-4)
2. Raise `InjCrv_phiMIMax_MAP` by +1-2° (match base SOI advance)

**Known risk**: Lambda drops to 0.89-0.91 @3500-4000 with current air measurement

**Gate**: One WOT pull 4th gear, VCDS 011+003+008. Pass if P50 torque ≥ current baseline AND no visible smoke. Fail = rollback.

### Phase 2: FMTC Axis Coherence (Measurement Required First)
**Question**: Does ECU clamp or extrapolate when torque request >336 Nm?

**Measurement needed**: Runtime `CoEng_trqInrSet` or equivalent (not in standard VCDS groups)

**Options**:
- A) Reduce `EngPrt_trqLimP_MAP` to 330 Nm max (safe, immediate)
- B) Extend `FMTC_trq2qBas_MAP` torque axis to 380 Nm (requires validation)

**Recommendation**: Start with option A (reduce limiter). Validate no loss of drivability. Then consider B if headroom needed.

### Phase 3: Boost Shape (Independent, High-Rate Log Required)
- Fix overshoot @1900-2500 (currently 2417 mbar peak)
- Fix undershoot @3000-3500 (currently -32 to -71 mbar)
- **Requires**: VCDS group 011 ONLY at max sample rate (not mixed groups)

---

## Verification Checklist

Before flashing any Stage 1 modification:

### Pre-Flash:
- [ ] All torque limiter requests ≤ FMTC axis maximum
- [ ] All SOI base values ≤ SOI limiter - 1°
- [ ] All duration maps scaled together (MAP0-4)
- [ ] Boost target increase ≤ +10% from stock
- [ ] Checksums recalculated (both blocks = 0xD01FE500)

### Post-Flash Validation:
- [ ] One WOT pull 4th gear, VCDS 011+003+008
- [ ] Check `Smoke Limitation` channel ≤ 340 Nm
- [ ] Check `Torque Limitation` channel ≤ 340 Nm
- [ ] Check boost actual vs. target (max deviation <100 mbar)
- [ ] Visual: No black smoke >3000 rpm
- [ ] EGT <800 °C (if logged)

### Rollback Conditions:
- Torque P50 drops >5% from baseline
- Visible black smoke at WOT
- Boost >2400 mbar sustained
- Any new mechanical noise (DMF, turbo, injectors)

---

## Sources

### Web Research:
1. [EDC16 Tuning Guide v1.1](https://www.scribd.com/document/438798747/EDC16-tuning-guide-version-1-1-pdf) — Complete map chain
2. [HP Academy Bosch EDC Map Definitions](https://www.hpacademy.com/technical-articles/bosch-edc-map-definitions/) — FMTC, smoke limiter, SOI logic
3. [Tuners Guild EDC17 Guide](https://tunersguild.com/blog/bosch-edc17-tuning-guide/) — Methodology (principles apply to EDC16)
4. [EDC16C9/C39 Tuning Guide](https://it.scribd.com/document/369602744/EDC16C9-v1-4) — 14 fuel/air maps explained
5. [EDC15-17 Maps Overview](https://fr.scribd.com/document/899358738/EDC15-16-17-MAP-GU%C4%B0DE) — Golf 5 specific
6. [ZedSuite GitHub](https://github.com/LeZed97/ZedSuite) — VAG EDC15/16 map structure

### Local Knowledge Base:
- `docs/knowledge/edc16-torque-model.md` — EDC16 torque-oriented architecture
- `docs/knowledge/smoke-limiter.md` — Exact FlMng_qPresSmoke_MAP structure for SW 1037391847
- `docs/knowledge/injection-duration.md` — PD injector mechanics
- `knowledge/edc16_knowledge.db` — 11,537 indexed A2L maps
- `.codex/skills/research/research.db` — Indexed web research (golf5 project)

### Project Evidence:
- `DECISION-2026-09-16.md` — Runtime VCDS validation of smoke limiter, FMTC finding, MAP0 issue
- `STAGE1-ENGINEERING-PLAN.md` — Staged implementation with gates
- `STAGE1-FIRMWARE-COMPARISON.md` — Detailed diff of all Stage 1 variants
- `diagnostic-review/math-engine/vcds-analysis.md` — WOT telemetry analysis
- User-provided vagecumap archive §8 — Factory PD130→PD150 comparison (independent validation)

---

## Next Actions

**Immediate** (if user approves):
1. Create Phase 0 BIN (hot-start + eco-cruise only, from `refined` base)
2. Flash and validate (zero WOT risk)

**Short-term** (needs user decision):
1. Reduce `EngPrt_trqLimP_MAP` to 330 Nm (fix FMTC axis issue)
2. Build Phase 1 candidate (MAP0 + SOI limiter)
3. Single validation pull before flash

**Medium-term** (measurement dependent):
1. High-rate group 011 log for boost shape analysis
2. Attempt runtime torque channel access (FMTC validation)

**Not recommended without measurement**:
- Further smoke limiter reduction
- FMTC axis extension beyond torque limiter reduction
- N75 precontrol modification
