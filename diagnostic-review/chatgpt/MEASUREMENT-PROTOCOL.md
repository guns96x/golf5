# Measurement protocol — EDC16U34 calibration engineering

Date: 2026-09-16
Branch: `chatgpt-analysis-2026-09-16`
Purpose: obtain repeatable evidence for torque-control, boost, air/fuel and injection-command models without relying on subjective feel.

## Safety and test environment

Preferred environment: chassis dyno or a closed/legal test facility with controlled direction/grade and no traffic. Public-road full-load testing at high speed is not part of this protocol.

Abort a run immediately for any new warning/limp state, abnormal mechanical noise, uncontrolled boost deviation, coolant/oil-temperature anomaly, obvious fuel-pressure fault, severe smoke not previously present, clutch slip or loss of traction.

No calibration change is required to execute this measurement protocol.

## Test philosophy

Do not diagnose one gear in isolation. Use operating-condition families:

1. **Transient torque step:** stable low/mid load followed by a repeatable pedal step.
2. **Steady high load:** enough time at a given RPM region for transient interventions to settle.
3. **RPM sweep:** continuous acceleration through the useful engine range.
4. **Repeatability pair:** same test repeated at least three times under similar thermal/environmental conditions.

Different fixed gears may be used as practical load generators, but the report must compare ECU state/load/RPM rather than assume the gear itself is the cause.

## Preconditions and metadata

Record before every test set:

- installed firmware SHA-256;
- ECU identification/SW version;
- coolant temperature;
- fuel temperature if available;
- intake-air temperature;
- barometric pressure;
- ambient temperature;
- vehicle mass estimate and whether passengers/cargo changed;
- tire size and pressure;
- road/dyno identifier and direction;
- DTC scan state;
- whether AC/large electrical loads are on;
- timestamp and logger/software version.

Thermal state should be comparable between repeated runs. Do not merge cold and fully warmed pulls into one repeatability estimate.

## Channel set A — torque arbitration / ASDdc

Highest priority if accessible through A2L/CCP/compatible diagnostic transport:

- `Eng_nAvrg` or equivalent engine RPM;
- accelerator/pedal request;
- active gear/state if available;
- clutch state;
- `CoEng_trqInrLtdDrv`;
- `ASDdc_trq`;
- `CoEng_trqSetASDUnLim`;
- `CoEng_trqLimASDdc_mp`;
- `FMTC_qAct`;
- final/requested injection quantity channel if available;
- external torque intervention/status variables where available.

Primary calculated metrics:

`delta_T_ASD = CoEng_trqInrLtdDrv - CoEng_trqLimASDdc_mp`

and, through the exact FMTC map,

`delta_q_ASD = q(before ASD) - q(after ASD)`.

Do not substitute a static ASDdc calibration limit for runtime `ASDdc_trq`.

## Channel set B — dynamic/static smoke

Priority channels:

- `FlMng_qDynSmoke_mp`;
- `FlMng_pIATCorr_mp`;
- runtime smoke-limiter output / VCDS smoke limitation if exact label is confirmed;
- requested/final IQ;
- MAF;
- MAP;
- IAT;
- barometric pressure;
- RPM.

Goal: distinguish transient dynamic-smoke intervention from the steady/static `FlMng_qPresSmoke_MAP` path.

If `FlMng_pIATCorr_mp` is not available, the report must say `UNKNOWN`; raw MAP can be retained as a separate measured channel but is not the same variable.

## Channel set C — boost/VNT control

Minimum useful set:

- RPM;
- boost/charge-pressure requested;
- MAP actual;
- N75/VNT command/duty or actuator command;
- MAF;
- IAT;
- barometric pressure;
- pedal/load.

Ross-Tech Group 011 is acceptable only when the label file for this ECU confirms which fields are requested boost, actual boost and control command. Never assume a group number alone proves field identity.

Calculated transient metrics:

- boost error `e_p = p_requested - p_actual`;
- peak positive/negative error;
- RMS error over the segment;
- rise time to 90% of the requested step;
- `dMAP/dt` after the pedal/load step;
- integrated signed pressure error;
- fraction of time actuator command is near an endpoint/saturation.

A static `PCR_pBDesBas_MAP` value is not a replacement for runtime requested boost.

## Channel set D — injection command / phasing

Priority channels:

- requested/final IQ;
- SOI/requested injection angle if runtime-accessible;
- duration/on-time if runtime-accessible;
- `InjVlv_numMI1_CUR` selector or equivalent runtime selector if accessible;
- RPM;
- fuel temperature;
- BIP/COI-related measurement if exposed;
- MAF/MAP for context.

Static model outputs from exact current BIN:

- blended Duration from `InjVlv_phiInjMI1_MAP0..N`;
- selector from `InjVlv_numMI1_CUR`;
- base SOI from relevant `InjCrv_phiBas*` map;
- duration degrees and milliseconds;
- electrical command-end proxy.

Terminology rule: when physical injected mass is not measured, report `OEM-duration-equivalent IQ`, not “actual fuel delivered”.

## Channel set E — vehicle response

- synchronized engine RPM;
- vehicle speed from the freshest available source;
- time stamp/monotonic time;
- gear ratio estimate from speed/RPM;
- longitudinal acceleration if available from a calibrated source;
- dyno wheel force/power if on chassis dyno.

The road-load model must carry uncertainty for mass, grade, CdA, Crr, driveline efficiency, wind and rotational inertia. On-road results are reported as intervals, not single-point dyno-equivalent truth.

## Sampling / synchronization requirements

1. Preserve raw per-channel timestamps and latency/age when the logger provides them.
2. Convert each channel to actual measurement time before cross-channel pairing.
3. Never pair MAF/MAP/speed with RPM solely because they are on the same CSV row if acquisition is asynchronous.
4. Record logger update rates for each channel.
5. For rapidly changing pedal-step analysis, a slow multi-group VCDS log may be insufficient; prefer fewer channels per run or A2L/CCP acquisition when available.
6. Separate runs can be used for different channel families if each run has RPM, pedal/load, MAP and a reliable time base for alignment by operating condition.

## Test set 1 — transient pedal-step response

Purpose: quantify torque that is delayed/removed during load application.

Procedure:

- establish a stable engine state below the target load;
- hold steady for at least 2 seconds;
- apply a repeatable rapid pedal step to the chosen target;
- continue until torque/boost response has clearly settled or the planned RPM window ends;
- repeat at least three times in each selected low/mid-RPM condition;
- repeat in more than one load/gear condition so driveline-state dependence can be separated from RPM dependence.

Primary outputs:

- peak `delta_T_ASD`;
- integral `delta_T_ASD dt`;
- duration of ASD intervention;
- dynamic-smoke delta/duration;
- boost rise time;
- time-to-90%-post-ASD torque;
- `dRPM/dt` response.

## Test set 2 — steady high-load sweep

Purpose: validate smoke/IQ/air and injection-selector behavior after transient interventions settle.

Procedure:

- begin below the analysis region with stable thermal state;
- apply high load and sweep through the useful RPM range under controlled conditions;
- capture at least three repeatable sweeps;
- use independent logging sets if necessary to preserve sample rate.

Primary outputs by 250-rpm bins:

- torque request / limiter outputs;
- requested/final IQ;
- smoke limit;
- boost requested/actual;
- MAF/air mass;
- SOI;
- Duration selector/blended Duration;
- road/dyno torque interval;
- ECU-vs-road residual.

## Test set 3 — same-RPM different-load comparison

Purpose: distinguish load/transient effects from pure RPM effects.

Select several RPM anchors (for example around 1500, 1750, 2000, 2250, 2500, 3000 and 3500 rpm where practical) and compare data at different stable loads. Do not force exact anchors when doing so would create an unsafe test condition.

Key question: does torque deficit follow RPM, requested torque, ASDdc state, air availability, or injection selector state?

## Repeatability requirements

For each comparable test family:

- minimum 3 valid runs;
- align by RPM and/or time from pedal step;
- report median and spread rather than a single run;
- calculate segment times such as 1500→2000, 1750→2500, 2000→3000, 2500→3500 where the recorded run naturally covers them;
- reject runs with clutch slip, traction intervention, gear change inside the segment, logger dropout or obvious driver-input mismatch.

A proposed calibration effect must exceed natural run-to-run variability before it is considered measurable.

## Evidence decision rules

### ASDdc hypothesis supported when
- runtime pre/post ASD torque channels show a repeatable negative intervention coincident with the sluggish response;
- magnitude is greater than uncertainty/run-to-run spread;
- FMTC-converted IQ deficit is directionally consistent with acceleration/road-torque deficit.

### ASDdc hypothesis rejected as primary cause when
- post-ASD torque follows pre-ASD torque closely during the symptom, within uncertainty;
- or the intervention ends well before the observed deficit while the deficit remains.

### Dynamic-smoke hypothesis supported when
- runtime dynamic-smoke output removes/delays IQ during the symptom;
- final IQ follows that dynamic limit;
- intervention timing/magnitude tracks measured torque deficit.

### Boost-transient hypothesis supported when
- runtime requested boost is materially above actual during the symptom;
- actuator/control behavior is consistent with a real air-path limitation/control lag;
- air mass and torque response recover when boost error closes.

### Injection-selector/MAP0 hypothesis supported when
- exact selector transition reproduces the Duration change;
- OEM-duration-equivalent IQ falls in the same RPM region as the high-rpm torque residual;
- runtime request remains high while realized torque falls;
- independent road/dyno behavior supports the magnitude/direction.

## Release gate for future calibration

No calibration-cell change should be generated until:

- the symptom is repeatable;
- a causal path is numerically identified;
- the predicted change exceeds uncertainty;
- at least one independent measurement/model cross-check supports the direction;
- thermal/turbo/drivetrain constraints are documented;
- validation and abort criteria are defined;
- rollback is defined.

Until then: `HOLD`.
