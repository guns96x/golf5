# EDC16U34 transient torque path: ASDdc active damping + dynamic smoke

Date: 2026-09-16
Status: research note / new diagnostic hypothesis
Scope: low-rpm sluggishness on higher gears (user reports 4th/5th feel weak already from low rpm), distinct from the separate 3000-4000 rpm MAP0/Duration issue.

## Executive summary

The existing static WOT model (Driver Wish -> torque limiter -> FMTC -> static smoke -> SOI -> Duration) is insufficient to explain a symptom that is strongly gear- and transient-dependent.

Two EDC16 paths present in the exact 03G906021QJ / P447HAXN A2L have not yet been modeled in the current math engine:

1. `ASDdc` active driveline/jerk damping (Aktiver Ruckeldämpfer / Störungsregler), which can modify requested inner torque during load transitions and is explicitly gear-dependent.
2. `FlMng` dynamic smoke correction, which adds a transient smoke/fueling path distinct from `FlMng_qPresSmoke_MAP`.

For the user's symptom "4th/5th sluggish from low rpm", these should be evaluated before attributing the behavior solely to the static 56.5 mg smoke plateau or to MAP0 Duration.

No BIN change is proposed by this note.

---

## 1. External engineering basis

### 1.1 VW EDC16 active pulse damping

VW Self-Study documentation for EDC16 describes an active pulse damping / driveline damping strategy that modifies injected fuel/engine torque during rapid pedal/load changes to suppress driveline oscillation. The control is relevant during traction/load transitions and is disabled/altered when the clutch is disengaged so that engine response can be faster.

Primary/near-primary reference used during research:
- VW SSP 304, EDC16-related training material: https://www.volkspage.net/technik/ssp/ssp/SSP_304_d2.pdf

Implication for this project:
- A transient higher-gear complaint cannot be modeled correctly from steady-state smoke/boost maps alone.
- The correct quantity to inspect is torque before and after ASDdc intervention, not only Driver Wish and static torque limit.

### 1.2 Bosch EDC16 functional-description evidence

A public mirror of Bosch EDC16 functional-description material describes the active damping logic using pedal, engine torque, engine speed, clutch/gearbox state, vehicle speed and gear/transmission-ratio related parameter selection.

Reference mirror:
- https://pdfcoffee.com/edc16c-funktionsbeschreibung-p177-6a2-pdf-free.html

Use this only as supporting documentation. The exact project A2L below is stronger evidence for variable/map identity.

### 1.3 Dynamic smoke is a separate EDC path

The exact A2L contains a dedicated dynamic smoke map and runtime measurement, separate from the pressure smoke limiter. Independent VAG EDC16 map catalogs also list `FlMng_qDynSmoke_MAP` as a dynamic injection/smoke quantity control.

Supporting reference:
- https://autodtc.net/damos-id-edc16-vag-ecu/

Forum/tuning sources should remain Tier C / lead-only; do not use them for numerical ground truth.

---

## 2. Exact A2L evidence: ASDdc active damping

The matching A2L contains the following runtime measurements:

- `ASDdc_trq`
  - description: `Momentforderung Aktiver Ruckeldämpfer (Störungsregler)`
  - physical meaning: torque demand/correction of the active jerk damper/disturbance controller.

- `CoEng_trqInrAct`
  - description: `inneres Motormoment ohne Ruckeldämpfer ...`
  - inner engine torque without jerk-damper intervention.

- `CoEng_trqInrLtdDrv`
  - description: `begrenztes Sollmoment (inneres Moment) vor Aktiver Ruckel-dämpfer ohne ext. Eingriffe`
  - limited target inner torque before active damping.

- `CoEng_trqSetASDUnLim`
  - description: `Sollmoment nach Eingriff Ruckeldämpfer(Störregler) vor 2.Begrenzung`
  - torque target after active-damper intervention, before second limitation.

- `CoEng_trqLimASDdc_mp`
  - description: `Sollmoment nach Eingriff des Ruckeldämfers nach zweiter Begrenzung`
  - torque target after active-damper intervention and second limitation.

- `FMTC_qAct`
  - description: `Einspritzmenge Sollwert ohne Ruckeldämpfereingriff`
  - requested injected quantity without jerk-damper intervention.

- `InjCtl_qAct`
  - description: `Fahrerwunschmenge inklusive Leerlaufregler ohne Ruckeldämpfer`
  - driver-requested quantity including idle controller, without damping intervention.

This provides an unusually clean runtime diagnostic chain:

`torque before ASDdc -> ASDdc correction -> torque after ASDdc -> resulting IQ path`

Therefore the low-rpm higher-gear problem can be measured directly rather than inferred from pedal feel.

---

## 3. Exact A2L evidence: ASDdc is gear-dependent

The A2L includes gear-dependent ASDdc axes/curves and positive/negative load-transition logic.

Relevant calibration objects include:

- `ASDdc_stActGear_CUR`
  - parameter/map-selection curve using active gear.

- multiple axes using `ASDdc_stActGear_mp`
  - six gear-related support points are present in several calibration objects.

- `ASDdc_dnAvrgLtdPos_CUR`
  - RPM-gradient threshold for positive load transition.

- `ASDdc_dnAvrgLtdNeg_CUR`
  - RPM-gradient threshold for negative load transition.

- `ASDdc_dnAvrgLtdExitPos_CUR`
  - exit threshold for positive load transition.

- `ASDdc_dnAvrgLtdExitNeg_CUR`
  - exit condition for negative load transition.

- `ASDdc_KdPwrOnOff_MAP`
  - gain/factor map for the D2T2 filter in load-transition state.

- `ASDdc_T1PwrOnOff_MAP`
  - related time-constant map for load-transition state.

- `ASDdc_trqPwrOnOffLimPos_MAP`
  - torque threshold for activating the load-transition parameter set for positive torque tendency.

- `ASDdc_trqPwrOnOffLimNeg_MAP`
  - analogous negative-tendency threshold.

- `ASDdc_trqLimHiPwrOnOff_CUR`
- `ASDdc_trqLimLoPwrOnOff_CUR`
- `ASDdc_trqLimHi_CUR`
- `ASDdc_trqLimLo_CUR`
  - controller output limits.

- `ASDdc_dActGearFac_CUR`
  - gear-related factor curve.

- `ASDdc_swtGearSel_C`
  - gear-selection software switch.

- `ASDdc_swtGearbx_C`
  - gearbox/external-intervention selection method.

This is directly relevant to a complaint that differentiates 3rd vs 4th/5th gear.

---

## 4. Exact A2L evidence: dynamic smoke path

The matching A2L contains:

- `FlMng_qDynSmoke_MAP`
  - address `0x1D63EC`
  - description: `Kennfeld für dynamische Rauchmengenerhöhung`
  - dynamic smoke quantity increase map.

- `FlMng_qDynSmoke_mp`
  - runtime measurement
  - description: `Dynamische Rauchmengenerhöhung`.

Related calibration objects in the same FlMng function include:

- `FlMng_facDynSmoke_CUR`
- `FlMng_facDynSmkAP_CUR`
- `FlMng_facDynSmkTemp_CUR`
- `FlMng_dRmpSlpLimSmkL_C`
- `FlMng_qAFSCDSmoke_MAP`
- `FlMng_qAFSCDtEngSmoke0_MAP`
- `FlMng_qAFSCDtEngSmoke1_MAP`
- `FlMng_qAFSCDtEngSmoke2_MAP`
- `FlMng_qPresSmoke_MAP`
- `FlMng_pIATCorr_MAP`
- `FlMng_pIATCorr_mp`

Important: `FlMng_pIATCorr_mp` is explicitly described in the A2L as `Korrigierter Druck zur Rauchbegrenzung` (corrected pressure for smoke limitation). Do not substitute raw MAP for it unless the exact conversion/path has been proven.

The current math engine models the static pressure-smoke path but should not assume this fully represents transient smoke arbitration during pedal tip-in / load transitions.

---

## 5. Updated diagnostic decomposition

The user's symptom must be split into at least two zones.

### Zone A: ~1400-2600 rpm, 4th/5th gear

Symptom: sluggish from low rpm, specifically more noticeable in higher gears.

Priority diagnostic order:

1. ASDdc active damping intervention.
2. Dynamic smoke path.
3. Runtime boost request / actual / N75 transient behavior.
4. Static smoke limiter and torque/IQ arbitration.
5. Other gear-/load-dependent torque interventions.

Do NOT use the high-rpm MAP0 Duration finding as a sufficient explanation for this zone.

### Zone B: ~3000-4000+ rpm

Separate finding already documented by Claude:
- Stage 1 modified `InjVlv_phiInjMI1_MAP1..4` but left `InjVlv_phiInjMI1_MAP0` stock.
- As SOI increases with RPM, selector shifts toward MAP0 and OEM-duration-equivalent fuel falls.

That remains a strong high-rpm candidate, but it does not explain low-rpm 4th/5th sluggishness.

---

## 6. Required mathematical model additions

### 6.1 ASDdc torque delta

For synchronized runtime data compute:

`DeltaT_ASD = T_before_ASD - T_after_ASD`

Recommended variable pairing:

`T_before_ASD = CoEng_trqInrLtdDrv`

`T_after_ASD = CoEng_trqLimASDdc_mp`

Also retain:

`ASDdc_trq`

`CoEng_trqSetASDUnLim`

for consistency checks.

Then convert the torque loss through the same FMTC model used elsewhere:

`q_before = FMTC(rpm, T_before_ASD)`

`q_after = FMTC(rpm, T_after_ASD)`

`Deltaq_ASD = q_before - q_after`

Report per gear and per transient segment:

- peak negative `DeltaT_ASD`
- duration of intervention
- integral of torque deficit over time
- equivalent IQ deficit
- RPM range
- pedal/load-transition state
- gear.

Do not infer the sign convention of `ASDdc_trq` from its name alone; cross-check against before/after torque measurements.

### 6.2 Dynamic smoke delta

If runtime variables permit, compute the contribution of the dynamic smoke path separately from the static smoke path.

At minimum log:

- `FlMng_qDynSmoke_mp`
- `FlMng_pIATCorr_mp`
- final smoke-related limiter quantity/torque if exposed
- RPM
- pedal
- requested torque/IQ
- actual/final IQ request.

Do not equate `FlMng_qDynSmoke_mp` to the final smoke limit without proving the arbitration formula.

### 6.3 Gear comparison

The strongest test is not an absolute number but a controlled 3rd vs 4th vs 5th comparison at matched RPM/pedal/load-transition conditions.

For each gear calculate:

`DeltaT_ASD(rpm,t)`

`Deltaq_ASD(rpm,t)`

`qDynSmoke(rpm,t)`

`BoostSpecified - BoostActual`

and road/RPM acceleration where available.

If 4th/5th exhibit materially larger negative ASDdc torque intervention than 3rd in the same 1400-2400 rpm region, that is direct evidence for the user's gear-specific low-rpm complaint.

---

## 7. Recommended runtime channel set

Highest-value internal A2L variables for a dedicated low-rpm transient run:

- `Eng_nAvrg` or exact engine speed variable used by logger
- accelerator/pedal actual/request
- active gear / `ASDdc_stActGear_mp`
- `CoEng_trqInrLtdDrv`
- `ASDdc_trq`
- `CoEng_trqSetASDUnLim`
- `CoEng_trqLimASDdc_mp`
- `FMTC_qAct`
- `InjCtl_qAct`
- `FlMng_qDynSmoke_mp`
- `FlMng_pIATCorr_mp`
- runtime requested boost (`PCR_pBDes` or exact A2L equivalent)
- actual MAP
- N75/VNT duty

If DAQ bandwidth is insufficient, split into two synchronized-style runs:

Run A — torque/transient:
`RPM, pedal, gear, CoEng_trqInrLtdDrv, ASDdc_trq, CoEng_trqLimASDdc_mp, FMTC_qAct`

Run B — smoke/air/boost:
`RPM, pedal, gear, FlMng_qDynSmoke_mp, FlMng_pIATCorr_mp, boost specified, actual MAP, N75`

Use exact A2L variables where possible rather than assuming generic VCDS group labels expose the same internal signals.

---

## 8. Evidence status

### FACT — exact A2L

- ASDdc runtime torque variables exist.
- ASDdc has gear-dependent calibration axes/curves.
- positive/negative load-transition thresholds and controller-output limits exist.
- `FlMng_qDynSmoke_MAP` exists at `0x1D63EC`.
- `FlMng_qDynSmoke_mp` exists as runtime measurement.
- `FlMng_pIATCorr_mp` is corrected pressure for smoke limitation.

### SUPPORTED EXTERNAL THEORY

- EDC16 uses active driveline/pulse damping during torque/load transitions.
- such control can intentionally modify engine torque to suppress drivetrain oscillations.

### HYPOTHESIS — NOT YET PROVEN ON THIS CAR

- ASDdc is the main reason 4th/5th feel sluggish from low rpm.
- dynamic smoke materially reduces available fueling during the reported low-rpm transient.
- either path differs enough between 3rd and 4th/5th to explain the subjective difference.

These require runtime measurement or a deterministic reconstruction from exact calibrations and input signals.

---

## 9. Immediate engineering implication

Do not modify the current BIN based on this note alone.

Before changing the 1500-2500 rpm smoke/N75/torque maps, extend the mathematical engine with a transient-torque validator that explicitly models or logs ASDdc and dynamic smoke.

Decision rule:

- If ASDdc creates a repeatable, gear-dependent negative torque delta matching the sluggish interval -> investigate/calibrate ASDdc path first.
- If ASDdc delta is small but dynamic smoke creates the IQ deficit -> investigate dynamic smoke path.
- If neither explains it -> continue to boost transient and static limiter chain.

The high-rpm MAP0 Duration finding remains separate and should not be discarded.
