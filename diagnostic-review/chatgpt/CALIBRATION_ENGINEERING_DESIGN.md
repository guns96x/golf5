# Calibration Engineering Design — evidence-driven EDC16U34 workstream

Date: 2026-09-16
Branch: `chatgpt-analysis-2026-09-16`
Status: design/specification for independent ChatGPT workstream

## Goal

Build an engineering workflow that explains the engine's behavior from driver demand to measured vehicle acceleration, without guessing which individual map is "the problem". The workstream must separate low/mid/high-rpm behavior, transient vs steady-state behavior, and software-commanded torque vs physically realized torque.

No firmware BIN is to be created or modified until a candidate change is numerically cross-validated.

## Core model

The primary causal chain is:

`pedal / external requests -> torque arbitration -> comfort/transient torque interventions -> torque-to-IQ -> smoke / air limits -> injection timing + duration -> boost/air system -> combustion -> crank torque -> driveline -> vehicle acceleration`

The analysis therefore has four coupled domains:

1. **Demand and torque-control domain**
   - Driver Wish / pedal processing
   - torque limiters and external torque requests
   - gear/state selectors
   - `ASDdc` / `ASDrf` active driveline damping
   - FMTC torque-to-injection conversion
   - dynamic smoke / transient fueling corrections

2. **Air and boost domain**
   - boost request vs actual
   - VNT/N75 feed-forward and feedback
   - MAP/MAF/IAT/barometric pressure
   - boost rise time, control error and actuator saturation
   - cylinder air mass and lambda plausibility

3. **Injection and combustion-command domain**
   - requested IQ
   - Duration map selector (`InjVlv_numMI1_CUR`)
   - `InjVlv_phiInjMI1_MAP0..N`
   - SOI maps and corrections
   - electrical command duration/time
   - OEM-duration-equivalent IQ
   - electrical command-end proxy, explicitly not physical EOI/CA50

4. **Vehicle-response domain**
   - fixed-gear acceleration
   - road-load model
   - wheel/engine torque inference
   - repeatability and uncertainty
   - residuals between ECU model, air/fuel model and road model

## Primary evidence rules

Every result must be labeled as one of:

- `MEASURED`: directly logged or directly decoded from the exact BIN/A2L.
- `CALCULATED`: deterministic result from measured/decoded inputs and an explicit formula.
- `CROSS_VALIDATED`: two or more independent evidence paths support the same conclusion within uncertainty.
- `PROVISIONAL`: plausible but still depends on an unmeasured runtime state or uncertain model input.
- `CONFLICT`: independent models disagree beyond uncertainty.
- `UNKNOWN`: information is not available or the runtime path is not proven.
- `HOLD`: no calibration change is allowed because a release gate is open.

Static map identity must never be described as runtime activity unless runtime evidence exists.

## Engineering source hierarchy

Tier A — primary / authoritative:
- exact matching A2L/DAMOS and exact firmware binaries;
- Volkswagen Self-Study Program documentation;
- Bosch functional descriptions / software documentation where provenance is established;
- ASAM MCD-2 MC/A2L standard;
- BorgWarner technical documentation for VTG behavior;
- Ross-Tech/VCDS documentation for measurement methodology.

Tier B — engineering literature:
- peer-reviewed or textbook material on diesel combustion phasing, air/fuel, road-load and driveline oscillation control.

Tier C — practitioner/community material:
- tuning forums, map lists and community guides are leads only; they cannot independently prove runtime behavior or a safe calibration value.

## Already established primary-source facts

### EDC16 is torque-oriented
Volkswagen SSP 304 describes Bosch EDC16 as a torque-oriented engine-management system in which internal and external torque demands are collected, evaluated and coordinated before torque is realized through actuators.

### Metering derives fuel quantity from torque demand and engine state
VW SSP 304 states that specified torque is calculated from internal/external demands and a required fuel quantity is then determined with inputs including driver demand, engine speed, air, coolant/fuel/intake temperatures. Fuel quantity is additionally limited for mechanical protection and smoke.

### Active pulse damping modifies fueling during load transitions
VW SSP 304 explicitly states that, after a pedal step, the full demanded fuel quantity is not supplied immediately. The controller modifies fuel in response to crank-speed oscillation; clutch disengagement switches the feature off for quicker engine response.

This supports treating the exact A2L `ASDdc` function as a first-class candidate for transient response, especially when symptoms vary with driveline state. It does not by itself prove that ASDdc is causing the current symptom.

### PD injection quantity depends on solenoid activation duration
VW SSP 209 states that injection quantity depends on how long the unit-injector solenoid valve is activated, and that the ECU uses BIP/COI feedback to regulate the actual start of injection. Therefore Duration and SOI must be modeled together, and electrical command duration is not identical to directly measured injected mass.

## Exact A2L paths that require modeling

### Torque / driveline transient path
Known relevant runtime measurements/calibrations include:
- `ASDdc_trq` — torque request/correction from active driveline damping disturbance controller.
- `CoEng_trqInrLtdDrv` — limited inner torque before active damping / without external intervention.
- `CoEng_trqSetASDUnLim` — requested torque after ASD intervention before second limiting stage.
- `CoEng_trqLimASDdc_mp` — requested torque after damping intervention / second limiting stage.
- `FMTC_qAct` — injection-quantity setpoint without jerk-damper intervention.
- `ASDdc_stActGear_mp` and associated gear-dependent calibrations.
- `ASDdc_*PwrOnOff*`, `ASDdc_*LtdPos*`, `ASDdc_*LtdNeg*`, `ASDdc_trqLim*` and parameter-selection maps/curves.

### Dynamic smoke path
Known exact A2L objects include:
- `FlMng_qDynSmoke_MAP`
- `FlMng_qDynSmoke_mp`
- `FlMng_facDynSmoke_CUR`
- `FlMng_facDynSmkAP_CUR`
- `FlMng_facDynSmkTemp_CUR`
- related ramp/switch/correction variables in the FlMng function.

The dynamic path must be separated from static `FlMng_qPresSmoke_MAP`.

### Static smoke input
`FlMng_qPresSmoke_MAP` uses `FlMng_pIATCorr_mp`, not raw MAP. The exact corrected-pressure path must be reconstructed or measured; raw MAP must not be substituted without a documented approximation status.

### Injection-duration selector path
- `InjVlv_numMI1_CUR`
- `InjVlv_phiInjMI1_MAP0..N`
- `InjCrv_phiBasGear34_MAP`
- `InjCrv_phiBasGear56_MAP`

The existing MAP0 finding is treated as a high-rpm candidate only until the full selector/duration model is independently reproduced.

## Analysis zones

The engine must not be diagnosed by one gear or one RPM region. For analysis only, use three operating zones:

- **Z1 transient / low-mid RPM:** 1200–2600 rpm. Primary question: what torque/fuel is removed or delayed during a pedal/load step?
- **Z2 transition / mid RPM:** 2400–3200 rpm. Primary question: where does the dominant bottleneck switch between transient torque control, smoke/air and injection phasing?
- **Z3 high RPM:** 3000–4500 rpm. Primary question: does the duration selector / MAP0 path explain the loss of torque realization as speed rises?

These zones overlap intentionally so no artificial boundary is mistaken for ECU logic.

## Required metrics

For each repeatable segment and RPM bin:

- pedal / driver torque request;
- pre-ASD requested torque;
- ASD torque correction and post-ASD torque;
- torque limiter outputs;
- FMTC/requested IQ;
- dynamic-smoke correction/limit;
- static smoke candidate/limit;
- requested and actual/estimated IQ where available;
- boost request, actual MAP, error and N75/VNT command;
- MAF, IAT, barometric pressure and calculated cylinder air;
- SOI;
- duration-map selector;
- electrical duration in degrees and milliseconds;
- OEM-duration-equivalent IQ;
- electrical command-end proxy;
- road-model torque P05/P50/P95;
- residuals between independent torque models.

Transient metrics:
- time-to-90%-requested torque;
- time-to-90%-boost target;
- peak and integral torque deficit during pedal step;
- boost rise rate `dMAP/dt`;
- RPM acceleration `dRPM/dt`;
- duration of active ASD intervention;
- dynamic-smoke intervention duration.

## Mathematical residual framework

For a time/RPM point:

`delta_T_ASD = T_before_ASD - T_after_ASD`

`delta_q_ASD = FMTC(T_before_ASD) - FMTC(T_after_ASD)`

For model comparison:

`residual_ECU_road = T_ECU_model - T_road`

`residual_airfuel_road = T_airfuel_model - T_road`

A candidate cause is strong only when the location and magnitude of its predicted deficit match the observed residual within uncertainty.

## Validation gates before any calibration change

A map/cell change can enter a candidate plan only if all gates are met:

1. exact calibration identity/address/scaling proven;
2. runtime function/activity either measured or strongly bounded;
3. symptom reproduced in repeatable data;
4. model predicts a numeric deficit or control error larger than uncertainty;
5. at least one independent model supports the direction;
6. predicted effect is quantified in IQ/Nm/kW/response-time terms as applicable;
7. thermal/air/turbo/drivetrain constraints are stated;
8. validation metric and abort threshold are defined;
9. rollback is defined;
10. the generated plan modifies no unrelated path.

Otherwise status is `HOLD`.

## Work packages

### WP1 — Torque/transient control
Decode and model ASDdc/ASDrf, dynamic smoke and torque arbitration. Compare current vs stock vs prior ON calibration. Produce a required-runtime-channel list and calculate maximum possible calibration-level intervention by state.

### WP2 — Air/boost control
Build synchronized request/actual/N75/MAF analysis with rise-time and saturation metrics. Distinguish static target maps from runtime request.

### WP3 — Injection/combustion-command model
Independently reproduce selector, Duration maps, SOI and OEM-duration-equivalent IQ. Test the MAP0 hypothesis across the entire selector transition, not only 4000 rpm.

### WP4 — Vehicle-response / residual analysis
Standardize repeatable segment detection and road-load uncertainty. Compare ECU-model, air/fuel and road torque.

### WP5 — Decision engine
Combine WP1–WP4 into a per-zone evidence matrix. A candidate plan may be generated only when release gates pass. No automatic BIN writing in this phase.

## Immediate deliverable

The first implementation target is a read-only `transient_torque_validator` that:

1. inventories exact ASDdc and dynamic-smoke A2L objects;
2. compares their calibration bytes/decoded values across stock/current/old-ON files;
3. extracts or defines required runtime measurement names;
4. computes torque/IQ intervention deltas when runtime data are available;
5. emits `json` and deterministic `md` reports;
6. never modifies a BIN.
