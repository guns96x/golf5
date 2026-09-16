# Source ledger — EDC16U34 calibration engineering workstream

Date: 2026-09-16
Branch: `chatgpt-analysis-2026-09-16`

This ledger records what each external or project source is allowed to support. A source does not automatically prove that a specific runtime path is active in this ECU.

## Tier A — primary / authoritative

### Volkswagen SSP 304 — Electronic Diesel Control EDC 16, Design and Function
URLs:
- https://www.volkspage.net/technik/ssp/ssp/SSP_304_d1.pdf
- https://www.volkspage.net/technik/ssp/ssp/SSP_304_d2.pdf

Supported claims:
- Bosch EDC16 is torque-oriented: internal and external torque demands are collected/evaluated/coordinated before torque realization.
- Specified torque is converted into a required fuel quantity using driver demand, RPM, air and temperature inputs.
- Fuel quantity is limited for mechanical protection and smoke; the limit depends on engine speed, air mass and air pressure.
- Active pulse damping deliberately withholds part of demanded fuel during a pedal/load step and modifies fuel according to crank-speed oscillations.
- Active pulse damping is switched off when the clutch is depressed to obtain quicker engine response.
- EDC16 calculates start of injection from RPM and calculated fuel quantity with further environmental corrections.

Applicability:
- SSP 304 illustrates EDC16 using V10/R5 applications, not the exact BLS calibration.
- It proves Bosch/VW EDC16 design concepts, not the exact activation/magnitude of `ASDdc` in the current BLS binary.

Authority: Tier A for system concept.

### Volkswagen SSP 209 — 1.9-ltr TDI Engine with Pump Injection System
URL:
- https://www.volkspage.net/technik/ssp/ssp/SSP_209.pdf

Supported claims:
- Unit-injector solenoid activation controls commencement of injection and injection quantity.
- Injection quantity depends on how long the solenoid valve remains activated/closed.
- The ECU monitors BIP/COI from injector-current behavior as feedback for actual commencement of injection.
- Electrical activation start/end and actual injection commencement are distinct events.

Applicability:
- Strong physical basis for PD injector command interpretation.
- Does not provide the exact BLS injector flow-vs-duration surface at every operating condition.

Authority: Tier A for PD injection mechanism.

### Exact project A2L/DAMOS
Project path:
`diagnostic-review/definitions/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.a2l`

Supported claims:
- names/descriptions of `CHARACTERISTIC` and `MEASUREMENT` objects;
- addresses, dimensions, axis variables, record layouts, conversion methods and units;
- presence of `ASDdc`, `ASDrf`, dynamic-smoke and injection-selector variables in this software definition.

Known relevant symbols:
- `ASDdc_trq`
- `CoEng_trqInrLtdDrv`
- `CoEng_trqSetASDUnLim`
- `CoEng_trqLimASDdc_mp`
- `FMTC_qAct`
- `ASDdc_stActGear_mp`
- `FlMng_qDynSmoke_MAP`
- `FlMng_qDynSmoke_mp`
- `FlMng_facDynSmoke_CUR`
- `FlMng_facDynSmkAP_CUR`
- `FlMng_facDynSmkTemp_CUR`
- `FlMng_pIATCorr_mp`
- `InjVlv_numMI1_CUR`
- `InjVlv_phiInjMI1_MAP0..N`

Limitations:
- Static presence and matching address do not prove runtime activation in the installed ECU.

Authority: Tier A for static software/calibration metadata.

### ASAM MCD-2 MC / ASAP2 (A2L)
URL:
- https://www.asam.net/standards/detail/mcd-2-mc/

Supported claims:
- A2L describes ECU measurement/calibration objects, memory locations, data types, dimensions, record layouts and conversions.
- `CHARACTERISTIC`, `MEASUREMENT`, axis and conversion metadata are appropriate sources for deterministic decoding.

Limitations:
- ASAM defines the representation, not Bosch's application-specific runtime logic.

Authority: Tier A for A2L semantics.

### Ross-Tech TDI VCDS logging guidance
URL:
- https://www.ross-tech.com/vag-com/cars/tdi.html

Supported claims:
- Measuring Blocks can be logged to files.
- Ross-Tech recommends logging Group 011 boost requested/actual versus RPM under a full-load acceleration for TDI boost diagnosis.

Limitations:
- The published procedure is general/legacy TDI guidance and explicitly notes application variation.
- A measuring-block group number must not be assumed to carry identical fields on every ECU; exact label/A2L confirmation is required.

Authority: Tier A for VCDS procedure, not exact BLS channel identity.

### BorgWarner VTG technical material
URLs:
- https://www.borgwarner.com/technologies/boosting-technologies
- https://www.borgwarner.com/docs/default-source/default-document-library/turbochargers-with-variable-turbine-geometry-(vtg).pdf

Supported claims:
- Variable turbine geometry uses adjustable vanes to alter turbine-side flow/pressure behavior and improve transient boost response.
- Vane actuation is a control variable; boost behavior must be evaluated dynamically, not from a single static boost number.

Exact-part note:
- Exact installed cross-reference reported by project: BV39 / `54399880072` / `03G253014M` for BLS.
- No manufacturer compressor/turbine map or validated exact safe boost/shaft-speed envelope for this exact part has yet been found.
- Therefore a family-level BorgWarner statement must not be converted into an exact safe-limit claim.

Authority: Tier A for VTG principle; `UNKNOWN` for exact turbo limit envelope.

## Tier B — engineering literature / manufacturer-origin mirrors

### Bosch EDC16 functional-description mirrors
Examples:
- https://pdfcoffee.com/edc16c-funktionsbeschreibung-p177-6a2-pdf-free.html
- https://pdfcoffee.com/softwaredocumentation-edc16-p-363-f80-jtd30-pdf-free.html

Supported leads:
- Bosch naming expands `ASDdc` as active surge/jerk damper disturbance compensator (`Aktiver Ruckeldämpfer Störregler`).
- Documentation mirrors expose function names and relationships useful for finding corresponding A2L measurements/calibrations.

Limitations:
- Hosting is not Bosch; provenance/content integrity must be treated below direct OEM documentation.
- Different EDC16 projects can have different calibration/application logic.

Authority: Tier B / corroborating source only.

### Active driveline damping literature
Representative paper/result:
- "Model Based Predictive Engine Torque Control for Improved Driveability" and cited active damping literature.

Supported claim:
- Engine-torque modulation is an established method for damping low-frequency driveline oscillations after torque/load steps.

Limitations:
- Not a direct description of this Bosch calibration.

Authority: Tier B for physical/control plausibility.

### EPA vehicle road-load / fuel-consumption modeling material
Representative sources:
- https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=P1001D6I.TXT
- https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=P1002KAD.TXT

Supported claims:
- vehicle road load comprises rolling resistance and aerodynamic drag plus inertial demand; coastdown/road-load parameter uncertainty matters.
- road-derived power/torque is sensitive to road-load assumptions.

Limitations:
- exact Golf mass/CdA/Crr/grade/driveline efficiency must be measured/sourced separately.

Authority: Tier B/A-agency engineering reference for road-load methodology.

## Tier C — practitioner / discovery-only

### AutoDTC / community EDC16 map lists
Examples:
- https://autodtc.net/damos-id-edc16-vag-ecu/
- https://autodtc.ru/info/karty-dlya-damosov-v-winols/bosch-edc16-karty-dlya-damosov-winols/

Useful lead:
- identifies `FlMng_qDynSmoke_MAP` as a dynamic injection-quantity/smoke-related map in VAG EDC16 families.

Restriction:
- cannot establish exact meaning, active runtime path or calibration value by itself.
- exact project A2L and runtime measurement take precedence.

## Project evidence hierarchy

Within this repository, use this ordering:

1. exact runtime measurements from the installed firmware with synchronized timestamps;
2. exact installed/current BIN + matching A2L;
3. reference/old firmware binaries decoded with the same A2L;
4. VW/Bosch primary design documentation;
5. engineering literature;
6. community sources as discovery leads only.

## Open source gaps

The following require further research before they can be treated as engineering limits:

- exact BV39 `54399880072` compressor/turbine map or shaft-speed/EGT/EMP envelope;
- exact BLS/EDC16U34 runtime formula feeding `FlMng_pIATCorr_mp` if it cannot be logged directly;
- exact activation/state machine details for this project's `ASDdc` beyond A2L naming and calibrations;
- exact physical fuel mass represented by a given PD electrical Duration outside the OEM calibrated surface;
- exact drivetrain torque limit for the installed gearbox/clutch/DMF combination.
