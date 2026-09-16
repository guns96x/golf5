# Stage 1 low-rpm safety audit — Golf 5 1.9 TDI BLS / EDC16U34 / 03G906021QJ

Date: 2026-09-11

Scope: static calibration and engineering-risk review only. This is not flash approval. No compressor map for the exact installed turbo, no measured engine torque, no turbo-speed trace, no cylinder-pressure trace, and no vehicle log were supplied.

## Verdict

- **Proposal 1 — 62–63 mg at the 2000 hPa smoke-map row, 2000–2500 rpm:** reject as a direct change; conditionally test only in smaller increments after confirming that the pressure smoke limiter is actually active.
- **Proposal 2 — move the turbine-temperature limiter to 830–840 °C:** reject. It does not address 1800–2200 rpm response and weakens a restored OEM protection.
- **62 mg / 360 Nm at 1900–2200 rpm in 4th/5th:** reject for a stock-bottom-end, unknown-age DMF daily-driver calibration. The ECU's modeled torque limit is not measured crank torque, and the local torque-to-fuel table does not support treating 62 mg as 360 Nm.

## Calibration facts established from the supplied files

- `PCR_pBDesBas_MAP` reaches 2214 mbar absolute from about 2058 rpm at 40–45 mg. More fuel does not request more boost in this region; it initially supplies more exhaust energy and heat.
- `FlMng_qPresSmoke_MAP` axes are 16 rpm points by 12 corrected-pressure points. The pressure axis ends at 2000 hPa. At that top row, the current values are 56.5 mg through 2500 rpm and 67.8 mg from 3000 rpm. The 1800 hPa row is only about 51–52 mg around 1800–2500 rpm.
- `FMTC_trq2qBas_MAP` has a torque axis ending at 336 Nm. At 2000 rpm, its 314 Nm and 336 Nm cells are 57.56 and 63.14 mg respectively. Thus 62 mg corresponds to roughly 332 Nm in this table by interpolation, not 360 Nm. Behavior for requests above the 336 Nm axis must not be assumed without code/runtime proof.
- The active SOI maps end at 60 mg. Restored main-duration maps 1–3 end at 60 mg; map 4 ends at 55 mg. A 62–63 mg request is outside those calibrated axes.
- The restored `EngPrt_facTempPreTrbn_MAP` temperature axis is approximately 650/700/750/790/805/820/840/860 °C. At 2000 rpm it is 1.0 through 820 °C, then 0.95 at 840 °C and 0.90 at 860 °C. At 3000 rpm and above it reaches about 0.92 at 840 °C. Interpolation means derating already begins between 820 and 840 °C.
- The 4th- and 5th-gear driver-wish maps are byte-identical in the supplied Stage 1, as are the Gear34 and Gear56 base SOI maps. A symptom isolated to higher gears is therefore more consistent with sustained low-speed load or runtime control than with a unique 4th/5th static request.

## A. Drivetrain and engine-load assessment

Volkswagen lists the Golf V 1.9 TDI 77 kW engine at 250 Nm/1900 rpm. For 1.896 L displacement, four-stroke BMEP is `4*pi*T/Vd`:

| Torque | BMEP | Increase over 250 Nm |
|---:|---:|---:|
| 250 Nm | 16.6 bar | baseline |
| 320 Nm | 21.2 bar | +28% |
| 336 Nm | 22.3 bar | +34% |
| 360 Nm | 23.9 bar | +44% |
| 380.7 Nm | 25.2 bar | +52% |

Gear selection does not change the engine's instantaneous BMEP at the same rpm and torque. Fourth/fifth gear keep the engine in that high-BMEP, low-speed condition longer, increasing heat exposure, torsional excitation time, and bearing-load duration. The DMF also sees stronger low-frequency torque pulses at low rpm. ZF identifies bucking/rattling under high load and extremely low engine speed as relevant DMF/driveline symptoms.

No universal DMF torque rating can be assigned without its exact part number, wear state, clutch condition, injector balance, and crankshaft torsional behavior. Any shudder, bucking, or rattle is a failed acceptance test, not something to tune through.

Conservative daily-driver shape pending measurements:

- no full-load request below 1800 rpm;
- target no more than about 300–310 Nm at 1800 rpm, 315–320 Nm at 1900 rpm, 325–330 Nm at 2000 rpm, and 330–336 Nm from 2250 rpm;
- keep modeled demand within the calibrated 336 Nm FMTC axis until lookup behavior above the axis is proved;
- do not release 360 Nm at 1900–2200 rpm on the present evidence.

These values are validation guardrails, not certified component limits.

## B. Turbo surge/overspeed assessment

At sea-level pressure, 2214 mbar absolute is a compressor pressure ratio of roughly 2.21 before inlet losses; at 850 mbar ambient it is roughly 2.60. At 1800–2200 rpm and 2214 mbar manifold pressure, a simple 1.896 L, 50 °C, 85–95% volumetric-efficiency estimate gives about 7.6–10.4 lb/min engine airflow. Exact corrected flow depends on inlet pressure/temperature, EGR state, volumetric efficiency, and pressure losses.

This is the low-flow/high-pressure-ratio corner where compressor surge margin matters. Garrett and BorgWarner both define the left edge of the compressor map as the surge limit; BorgWarner specifically notes that high load at low engine speed moves the point toward surge. Audible absence of surge is encouraging but not proof of margin.

No public manufacturer compressor map for the exact installed GT1646V/BV39 part number was established. The turbo identity must be read from its tag. Without that map or turbo-speed data, the proposal cannot be certified against surge or overspeed.

Adding fuel can increase turbine power and accelerate boost, but may raise pressure ratio faster than engine airflow, reduce surge margin, increase exhaust manifold pressure, and raise turbine temperature. At higher rpm, the relevant risk may change from surge to choke/overspeed/backpressure. A flat 2214 mbar request must therefore be checked as actual pressure ratio, not treated as intrinsically safe.

## C. Combustion and spool dynamics

The smoke limiter is not a turbo-spool map. During a transient, insufficient air relative to fuel produces opacity/soot and heat; turbo lag is a known cause of transient emissions peaks. More fuel can improve turbine acceleration only if combustion phasing and available oxygen allow useful exhaust enthalpy rather than mostly smoke and late heat.

Raising only the 2000 hPa row has limited authority before corrected pressure reaches that row. If the engine is still at 1600–1800 hPa during the lazy phase, the unchanged lower rows remain controlling. Once pressure approaches 2000 hPa, a 56.5 to 62–63 mg step is a 9.7–11.5% fuel-limit increase and can create a nonlinear torque/soot/EGT step. It also goes beyond current duration/SOI axes.

First determine which limiter is active. If the smoke limiter is confirmed active and boost/MAF are healthy, test no more than a roughly +1.5–2.0 mg step per revision, with a smooth pressure and rpm gradient. Keep the first candidate at or below 60 mg because the active duration/SOI axes end there. Do not jump directly to 62–63 mg.

The fade above 3000 rpm is not evidence for delaying thermal protection. Plausible alternatives include the torque taper, active temperature derate, duration-axis saturation, air-path restriction, increasing exhaust backpressure, VNT control, or compressor choke/overspeed. The current smoke limit already rises to 67.8 mg at 3000 rpm, so adding more high-rpm fuel is particularly poorly supported.

## Required staged validation

1. **Baseline, unchanged calibration:** warm engine, no active DTCs; verify vacuum supply/N75/actuator travel, boost leaks, MAF plausibility, intake/exhaust restriction, injector balance, synchronization/torsion, and actual turbo part number.
2. **Log at high sample rate:** rpm, gear, accelerator, ambient pressure, requested/actual MAP, boost-control duty or VNT command, MAF actual/requested, requested/corrected/actual main IQ, all available fuel-limit outputs including `FlMng_qLimSmk` and its base/air/bypass components, driver/requested/current internal torque, SOI and main duration, IAT, coolant temperature, raw EGT sensors, modeled `EngPrt_tPreTrbn`, and the applied turbine-temperature factor. Add external pre-turbine thermocouple, opacity/lambda, and exhaust-manifold pressure if possible.
3. **Controlled pulls:** instrumented dyno/private closed course; begin in 3rd/4th from 1800 rpm, not 5th-gear WOT lugging. Abort for shudder/rattle, boost oscillation, uncontrolled overshoot, smoke spike, unexpected N75 saturation, or rapid EGT rise.
4. **Only if smoke limitation is proven:** apply one small, smooth <=60 mg revision and compare time-to-90%-boost, torque rise, opacity, EGT, boost error/oscillation, and driveline vibration against baseline.
5. **Thermal map:** leave OEM. If the fade coincides with the factor falling, fix the heat/airflow/combustion cause instead of postponing the protection.

## Primary references

- Volkswagen Newsroom, Golf V engine specifications: https://www.volkswagen-newsroom.com/en/motor-versions-5-golf-profile-19482
- Garrett Motion, compressor-map and surge guidance: https://www.garrettmotion.com/knowledge-center-category/oem/expert/
- BorgWarner, compressor-map interpretation: https://www.borgwarner.com/aftermarket/boosting-technologies/news/2022/05/23/understanding-compressor-maps-sizing-a-turbocharger
- BorgWarner paper on high-load/low-speed movement toward the surge line: https://www.borgwarner.com/docs/default-source/default-document-library/2015_whitepaper_intake-throttle-and-pre-swirl-device-for-lp-egr-systems_en.pdf
- ZF Aftermarket, DMF noise/bucking diagnosis: https://aftermarket.zf.com/app/controller/ti/download/Binary/b3a61f70-1004-11ec-a2de-00505690da53.pdf
- SAE 2010-01-1287, turbocharger lag and transient diesel emissions: https://saemobilus.sae.org/papers/experimental-assessment-turbocharged-diesel-engine-transient-emissions-acceleration-load-change-starting-2010-01-1287
- SAE 2004-01-0600, peak cylinder pressure and connecting-rod bearing loading: https://saemobilus.sae.org/papers/numerical-simulation-profile-influence-conrod-bearings-performance-2004-01-0600

