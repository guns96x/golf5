# Calibration enhancement audit — VW Golf 5 1.9 TDI BLS / EDC16U34 / 03G906021QJ

## Executive decision

This is a static calibration and engineering-risk audit, not flash approval. No current ECU readback, hot-start log, boost transient log, turbo part-number/compressor map, exhaust-manifold-pressure trace, turbo-speed trace, cylinder-pressure trace, opacity measurement, or checksum verification was supplied.

| Proposal | Decision | Exact conclusion |
|---|---|---|
| 1. Copy `StSys_trqStrt_MAP` warm values into `StSys_trqStrtBas_MAP` | **Reject as a bulk copy; conditionally test a 4-cell 250-rpm patch only** | The zeros form a deliberate RPM/temperature staircase: both maps match completely at 280 rpm. A full copy changes 14 cells at 0–250 rpm and may defeat a cranking-speed gate or duplicate the terminal-50 contribution. |
| 2. Slight `PCR_rBPCtlBas_MAP` N75/VNT pre-control change | **Feasible only as a logged, sign-verified A/B experiment** | The 2214 mbar request was raised from 2050 mbar in the Stage 1, while this pre-control map stayed reference. The numerical duty direction is not proved from static data. Use the small `N75-A` surface below only if a sign test proves that lower `Prc` increases initial boost slope. |
| 3. `FlMng_qPresSmoke_MAP` smoothing | **Conditionally accept one 2500-rpm cell at 58.5 mg; reject the claimed 2500–2750 plateau as stated** | There is no 2750-rpm node. With the current 3000-rpm value left at 67.8 mg, the 2750-rpm interpolation is 63.15 mg after a 58.5-mg edit. Holding 2750 rpm to 60 mg requires reducing the 3000-rpm node to 61.5 mg, which may cut Stage-1 torque/power. |
| 4. `InjCrv_phiBasGear56_MAP` cruise SOI +0.6…0.8° | **Technically plausible as a separate 9-cell A/B test; efficiency gain unproved** | Use the exactly representable +0.703125° step. EGR removal does not prove the stock cells are “legacy EGR timing”; less EGR generally shortens ignition delay, so blindly advancing commanded SOI can move actual combustion too early and increase NOx, pressure rise, and noise. |

No firmware image was changed or created by this audit.

## Evidence base and decoding

The matching A2L identifies the four maps at:

| Map | Address | Actual dimensions | Axes | Value resolution |
|---|---:|---:|---|---:|
| `StSys_trqStrtBas_MAP` | `0x1F070C` | 9×9 | RPM × coolant °C | 0.1 Nm |
| `StSys_trqStrt_MAP` | `0x1F07EA` | 9×9 | RPM × coolant °C | 0.1 Nm |
| `PCR_rBPCtlBas_MAP` | `0x1E9FD0` | 16×13 | RPM × mg/stroke | 0.01% |
| `FlMng_qPresSmoke_MAP` | `0x1D6490` | 16×12 | RPM × corrected pressure hPa | 0.01 mg/stroke |
| `InjCrv_phiBasGear56_MAP` | `0x1DACF8` | 16×14 | RPM × mg/stroke | 0.0234375° crank |

The A2L uses `MSB_FIRST`, signed 16-bit axes and values, and `COLUMN_DIR`; the flat value index is `rpm_index × y_count + y_index`.[^1] The named definitions and inputs are in the A2L at lines 268931, 345331, 394165, 462199, and 462268. Runtime measurement labels also exist for `StSys_trqStrt`, `StSys_trqStrtBas_mp`, `FlMng_qLimSmk`, `InjCrv_phiMI1Des`, `PCR_pBDes`, `PCR_rBPCtlBas_mp`, `PCR_rBPCtl`, and their component terms.[^2]

All four map regions, plus `StSys_trqStrt_MAP` and `PCR_pBDesBas_MAP`, are byte-identical among the supplied OFF image and the three later candidate images. Therefore the analysis below applies to each supplied candidate. It does **not** establish the contents of the ECU currently in the car.

The Stage-1 boost request is not stock. `PCR_pBDesBas_MAP` has 104 changed values versus the supplied reference; its high-load request rises from 2050 to 2214 mbar absolute. `FlMng_qPresSmoke_MAP` is also already modified: its 1800- and 2000-hPa rows are about 13% above reference; at 2500/2000 hPa the value is 50.0→56.5 mg, and at 3000/2000 hPa it is 60.0→67.8 mg. `PCR_rBPCtlBas_MAP` has zero changed values versus reference. The low-load 15–25 mg cells in the Gear56 SOI map are reference values; the existing Stage-1 SOI edits are confined to 55/60 mg.

The ON/OFF dumps contain `0xFF` through the program segment below `0x180000`. The separate HEX-derived reference contains code, but its installed-ECU identity has not been proved. Static A2L address agreement therefore does not prove which duplicate/variant table executes in the vehicle. A current ECU readback and runtime component logs are release gates.

## 1. Hot-start torque maps

### What the data actually show

The actual RPM axis is `0, 200, 250, 280, 450, 600, 900, 1550, 1600`; the coolant axis is approximately `−24, −18, −10, 0, 20, 40, 60, 80, 100°C`. The supplied “rows 2491, 2551, 2631” are not A2L RPM nodes; they may be row identifiers in another editor/export.

| RPM | `StSys_trqStrtBas_MAP`, 20/40/60/80/100°C | `StSys_trqStrt_MAP`, 20/40/60/80/100°C |
|---:|---|---|
| 0 | 0 / 0 / 0 / 0 / 0 | 156 / 125 / 112 / 108 / 108 Nm |
| 200 | 0 / 0 / 0 / 0 / 0 | 156 / 125 / 112 / 108 / 108 Nm |
| 250 | 156 / 0 / 0 / 0 / 0 | 156 / 125 / 112 / 108 / 108 Nm |
| 280 | 156 / 125 / 112 / 108 / 108 | 156 / 125 / 112 / 108 / 108 Nm |

This is structured calibration, not random missing data. The base map progressively enables warm starting torque as cranking speed rises, while the terminal-50 map already requests the warm torque. At 280 rpm the two maps are identical. Bosch describes starting as distinct cranking, ignition, and run-up phases and notes that starting fuel and timing must be precisely controlled at low speed; too much accumulated fuel during ignition delay increases the pressure-rise/noise event.[^3]

### Why the full copy is unsafe as a first move

A bulk copy changes 14 cells: five at 0 rpm, five at 200 rpm, and four at 250 rpm. Static data cannot show whether the two map outputs are selected, limited, ramped, or combined. If combined, copied values can duplicate torque demand; if selected, they can bypass a deliberate minimum-speed/temperature strategy. It can also mask a weak starter, voltage drop, poor crank/cam synchronization, incorrect coolant signal, torsion/synchronization issue, or injector leakage.

### Smallest defensible experiment: `HS-250`

Only if a repeated hot-start log shows all of the following:

- coolant 80–100°C and a genuine long-crank symptom;
- cranking speed plateaus in the 250–279 rpm band;
- terminal 50 and start-state signals are valid;
- `StSys_trqStrtBas_mp` remains zero while the terminal-50 start-torque path is nonzero;
- battery/starter voltage drop, starter current, crank/cam sync, torsion/synchronization, and injector balance/leakage are acceptable.

Then populate only the missing 250-rpm warm/hot cells:

| RPM | Coolant | Current | `HS-250` | BIN offset | Big-endian S16 |
|---:|---:|---:|---:|---:|---|
| 250 | 39.96°C | 0 Nm | 125 Nm | `0x1F0762` | `0000→04E2` |
| 250 | 59.96°C | 0 Nm | 112 Nm | `0x1F0764` | `0000→0460` |
| 250 | 79.96°C | 0 Nm | 108 Nm | `0x1F0766` | `0000→0438` |
| 250 | 99.96°C | 0 Nm | 108 Nm | `0x1F0768` | `0000→0438` |

Leave the 0- and 200-rpm warm cells at zero and leave the axes unchanged. If the engine cannot reach 250 rpm hot, this calibration is not the first repair. If it already exceeds 280 rpm during the delay, these four cells are unlikely to be causal.

### Validation and abort gates

Log RPM, coolant, fuel temperature, battery voltage at ECU and starter, terminal-50/start states, crank/cam synchronization, requested/actual IQ, `StSys_trqStrt`, `StSys_trqStrtBas_mp`, `StSys_trqBas`, SOI, duration, and first-fire/run-up time over at least ten comparable hot restarts per version. Abort/revert for kickback, harsher pressure-rise noise, more white/black smoke, run-up overshoot, a longer 95th-percentile start time, or any synchronization/DTC change.

## 2. N75/VNT pre-control

### Feasibility

`PCR_rBPCtlBas_MAP` is a feed-forward starting point for a closed-loop boost controller, not a boost target. Its axis ends at 45 mg/stroke while the current Stage 1 can request about 60 mg; endpoint behavior must be confirmed, because a clamped 45-mg column can govern higher fuel quantities.

The table generally falls numerically as load and requested boost rise—for example, 1750 rpm changes from 67.00% at 20 mg to 47.00% at 45 mg. Together with Volkswagen's description of the vacuum VNT system—more vacuum moves the vanes toward the narrow, fast-spool position—this suggests, but does not prove, that a **lower** table number commands more turbine drive in this implementation.[^4] Do not apply an “increase N75 duty” rule from another ECU/tool convention.

Changing feed-forward can reduce the feedback correction needed after a torque step, but it can also increase turbine inlet pressure, pumping work, compressor pressure ratio, turbo speed, surge exposure, and boost overshoot. Diesel air-path research treats feed-forward, feedback, fuel rate, thermal state, and nonlinear VGT dynamics as a coupled system rather than a scalar duty tweak.[^5]

At 2214 mbar absolute, ideal compressor pressure ratio is about 2.19 at 1013 mbar ambient and 2.60 at 850 mbar ambient, before inlet and intercooler losses. The exact turbo tag and compressor map are absent. Garrett defines the left boundary as the surge line and warns that loaded surge is the damaging case; turbo-speed limits also tighten near the map boundaries.[^6]

### Exact first experiment: `N75-A`

Use only if runtime logging proves `PCR_rBPCtlBas_mp` is derived from this named map and a controlled sign test proves that lowering `Prc` increases initial MAP slope. Keep `PCR_rBPCtlBas2_MAP`, all correction/limit maps, axes, boost request, and PID/governor maps unchanged.

Cells are `current→N75-A`, in percent. All unlisted cells remain unchanged.

| RPM \ IQ | 30 mg | 32 mg | 35 mg | 38 mg | 40 mg | 45 mg | Offset range |
|---:|---:|---:|---:|---:|---:|---:|
| 1750 | 56.53→56.28 | 51.00→50.50 | 49.45→48.95 | 47.14→46.64 | 47.43→47.03 | 47.00→46.80 | `0x1EA0B8–0x1EA0C2` |
| 1900 | 47.42→47.02 | 47.00→46.25 | 44.13→43.38 | 44.34→43.59 | 43.87→43.27 | 45.06→44.76 | `0x1EA0D2–0x1EA0DC` |
| 2000 | 46.00→45.75 | 46.00→45.50 | 43.21→42.71 | 43.03→42.53 | 43.34→42.94 | 43.96→43.76 | `0x1EA0EC–0x1EA0F6` |

This is a 0.2–0.75 percentage-point pocket, tapered by the unchanged 1500- and 2250-rpm rows. It is deliberately much smaller than typical feedback authority. If the sign test does not prove the assumed polarity, `N75-A` is **HOLD**; do not auto-invert it from static reasoning.

### Acceptance and abort gates

Run baseline and candidate with the same gear, start RPM, pedal step, coolant/IAT range, ambient pressure, and fuel. Log at the highest available rate: requested/actual MAP, ambient pressure, N75 command, `PCR_rBPCtlBas_mp`, final `PCR_rBPCtl`, feedback/governor component, requested/actual/corrected IQ, MAF, IAT, coolant, modeled pre-turbine temperature and its limiter factor. Add external pre-turbine EGT, turbo speed, exhaust-manifold pressure, and compressor-inlet pressure where possible.

Accept only if time to 95% of boost target improves beyond test repeatability, while overshoot is no more than baseline +30 mbar and no more than request +100 mbar for 0.5 s. Abort immediately for request +150 mbar, sustained/oscillatory boost error over ±100 mbar, surge/flutter, VNT/N75 saturation, driveline shudder, smoke increase, or modeled/external EGT entering the restored thermal-derate region. These are conservative test guards, not Volkswagen-certified limits.

## 3. Pressure smoke limiter

### Axis and interpolation correction

The RPM nodes are `700, 800, 900, 1000, 1100, 1400, 1500, 1600, 1700, 1800, 2000, 2250, 2500, 3000, 4000, 5355`. There is no 2750-rpm node. The pressure input is `FlMng_pIATCorr_mp`, a corrected pressure signal, not necessarily raw manifold pressure.

Current values in the relevant pressure rows are:

| RPM | 1600 hPa | 1800 hPa | 2000 hPa |
|---:|---:|---:|---:|
| 2000 | 40.50 | 50.98 | 56.50 mg |
| 2250 | 41.50 | 51.60 | 56.50 mg |
| 2500 | 41.80 | 52.09 | 56.50 mg |
| 3000 | 41.16 | 51.49 | 67.80 mg |

With current linear interpolation, the top-row limit is 62.15 mg at 2750 rpm. Raising only 2500 rpm to 58.5 mg makes it 63.15 mg at 2750. Therefore the proposal can either preserve the 3000-rpm Stage-1 fuel ceiling or enforce `≤60 mg` through 2750, but not both.

### Recommended first experiment: `SMK-2500`

Only after logging proves that `FlMng_qLimSmk`/`FlMng_qLimSmkBas_mp` is the binding limiter during the flat spot and `FlMng_pIATCorr_mp` is near the 2000-hPa row:

| RPM | Corrected pressure | Current | `SMK-2500` | BIN offset | Big-endian S16 |
|---:|---:|---:|---:|---:|---|
| 2500 | 2000 hPa | 56.50 mg | **58.50 mg** | `0x1D6602` | `1612→16DA` |

Do not alter the axis. Leave 3000/2000 hPa at 67.8 mg in the first experiment. This is a +3.54% local change from the current value, but the resulting 58.5 mg is already +17% over the 50.0-mg reference cell.

If `≤60 mg at 2750 rpm` is a hard requirement, the exact paired endpoint is 3000/2000 hPa = 61.5 mg (`0x1D661A`, `1A7C→1806`) because `(58.5 + 61.5)/2 = 60.0`. That alternative is **not recommended as the first flat-spot test**: it removes 6.3 mg of current authority at 3000 rpm and may reduce torque/power if the smoke limiter is active.

At 1900 hPa, the 2500-rpm interpolation is only 54.295 mg now and 55.295 mg after `SMK-2500`; at 1800 hPa it remains 52.09 mg. If corrected pressure is below about 1950 hPa during the symptom, a top-row-only edit has little authority and the cause should be sought in air-path response, active limiter selection, or lower pressure rows. Do not compensate for an air leak, MAF error, VNT problem, or excessive backpressure by adding fuel.

Turbo lag creates an air/fuel mismatch and transient smoke peaks; experimental work identifies turbo lag as the dominant cause of transient emissions peaks, including during acceleration and starting.[^7] More fuel can add turbine energy, but before air arrives it also lowers lambda, increases soot/opacity and exhaust heat. This is why `SMK-2500` and `N75-A` must not be tested together initially.

Acceptance requires a repeatable reduction in the flat-spot torque/acceleration deficit with no worse opacity, lambda, boost overshoot, EGT, or driveline vibration. An external fast lambda/opacity instrument is strongly preferred because the supplied OFF calibration disables the LSU gate and the DPF is physically removed. Visible smoke alone is not a quantitative pass.

## 4. Gear 5/6 cruise SOI

### Current map and combustion interpretation

The relevant current cells are:

| RPM | 15 mg | 20 mg | 25 mg |
|---:|---:|---:|---:|
| 1750 | 0.328125° | 3.000000° | 4.0078125° BTDC |
| 2000 | 1.312500° | 3.000000° | 4.0078125° BTDC |
| 2250 | 2.343750° | 3.000000° | 4.1484375° BTDC |

These are base SOI/start-of-delivery values, not measured start of combustion. The A2L exposes additive, PCR, EGT, altitude, temperature, and desired/final SOI terms; actual phasing depends on those corrections, unit-injector hydraulics, torsion/synchronization, fuel temperature, and ignition delay.

The four current main-duration maps at 2000 rpm span roughly 9.47–12.09° at 15 mg, 12.26–14.60° at 20 mg, and 14.53–17.44° at 25 mg. A simple `duration − SOI` arithmetic illustration therefore places electrical end-of-command well after TDC. Advancing base SOI by 0.703° moves that endpoint earlier by the same nominal amount if every other term is unchanged; it does not prove physical end of injection or CA50.

Thermodynamically, a small advance can improve indicated work and lower exhaust temperature if combustion is currently too late by moving heat release toward the efficient expansion window. Too much advance creates negative work before TDC, higher peak pressure and pressure-rise rate, more combustion noise, higher chamber temperature, and generally more NOx. Bosch gives 0–8° BTDC as an example low-consumption combustion-start region but explicitly warns that even small timing errors materially affect consumption, emissions, and noise and that timing must be load/speed/temperature specific.[^8]

The “legacy EGR timing” premise is not established. Experimental diesel work reports that EGR commonly increases ignition delay and combustion duration.[^9] With EGR physically blanked, the same commanded SOI can already produce earlier/faster actual heat release. A clean-looking exhaust is not proof of lower NOx; an SOI advance usually pushes the soot/NOx trade-off toward more NOx.

### Exact A/B candidate: `SOI56-A`

Use the nearest exact map quantum within the requested range: raw `+30`, equal to **+0.703125° crank**, at nine cells. Leave Gear12, Gear34, all 55/60-mg Stage-1 cells, duration maps, axes, and correction maps unchanged.

| RPM | IQ | Current→candidate | BIN offset | Big-endian S16 |
|---:|---:|---:|---:|---|
| 1750 | 15 | 0.328125→1.031250° | `0x1DADCE` | `000E→002C` |
| 1750 | 20 | 3.000000→3.703125° | `0x1DADD0` | `0080→009E` |
| 1750 | 25 | 4.007812→4.710938° | `0x1DADD2` | `00AB→00C9` |
| 2000 | 15 | 1.312500→2.015625° | `0x1DADEA` | `0038→0056` |
| 2000 | 20 | 3.000000→3.703125° | `0x1DADEC` | `0080→009E` |
| 2000 | 25 | 4.007812→4.710938° | `0x1DADEE` | `00AB→00C9` |
| 2250 | 15 | 2.343750→3.046875° | `0x1DAE06` | `0064→0082` |
| 2250 | 20 | 3.000000→3.703125° | `0x1DAE08` | `0080→009E` |
| 2250 | 25 | 4.148438→4.851563° | `0x1DAE0A` | `00B1→00CF` |

The unchanged 1500/2500-rpm and 12.5/30-mg neighbors provide interpolation ramps around the target island. Gear12/34/56 maps are currently byte-identical; changing only Gear56 deliberately creates a high-gear calibration difference. Confirm the ECU's recognized gear and `InjCrv_phiBasGear56_mp` at runtime.

### Validation

Test this candidate by itself at fixed road load or, preferably, steady-state dyno points near 1750/2000/2250 rpm and 15/20/25 mg. Log recognized gear, desired/actual IQ, `InjCrv_phiBasGear56_mp`, `InjCrv_phiMI1Bas_mp`, all SOI corrections, `InjCrv_phiMI1Des`, final SOI, duration, MAF, MAP, IAT, coolant, fuel temperature, torsion/synchronization, and EGT. Measure repeatable fuel mass or BSFC; tank-to-tank economy cannot resolve the likely small effect reliably.

Accept only if consumption improves beyond measurement uncertainty with no increase in harshness/combustion noise, NOx, smoke, EGT, or torque fluctuation. Cylinder-pressure instrumentation should show no adverse peak-pressure or pressure-rise change; without it, the result cannot be certified for mechanical peak-pressure safety. Revert if actual SOI moves by more than the intended base delta because another correction branch changes.

## Interaction and rollout order

| Pair | Interaction | Rule |
|---|---|---|
| Hot start + any running map | Separate operating state | Test hot start alone first; no reason to bundle. |
| N75 + smoke | Both alter spool: vane energy vs fuel/exhaust enthalpy | **Never first-test together.** Baseline → `N75-A` or `SMK-2500`, compare, revert, then test the other. |
| N75 + SOI | SOI can change exhaust enthalpy while N75 changes turbine extraction | Stabilize boost control before cruise SOI work. |
| Smoke + SOI | Fuel ceiling changes load; timing changes pressure/EGT/NOx | Keep SOI test at stable 15–25 mg where the smoke proposal should not bind. |

Recommended sequence:

1. Obtain a fresh ECU readback; verify SW identity, map-region equality, physical DPF/EGR configuration, and ECU-specific checksum support.
2. Baseline mechanical health and repeatable logs. Do not tune through DTCs, poor synchronization, vacuum/actuator faults, boost leaks, MAF implausibility, intake/exhaust restriction, or starter voltage drop.
3. If hot-start evidence matches the 250–279 rpm gate, test `HS-250` alone.
4. For the high-gear flat spot, identify the active limiter and corrected-pressure operating point. Test either `N75-A` or `SMK-2500` first, not both.
5. After air-path/fueling transients are stable, test `SOI56-A` as a steady-state economy experiment.
6. Only then consider a combined candidate, using the winning individual revisions and repeating every thermal/boost/smoke/start acceptance test.

## Release status

| Gate | Status |
|---|---|
| A2L map identity, dimensions, axes, scaling, and current bytes | **PASS (static)** |
| Proposed address/value tables | **PASS (static arithmetic)** |
| Current ECU readback matches supplied OFF/candidate images | **NOT RUN** |
| Named duplicate/variant maps proven active at runtime | **NOT RUN** |
| Bosch/ECU checksum after edits | **NOT RUN** |
| Hot-start physical acceptance | **NOT RUN** |
| Boost/smoke physical acceptance | **NOT RUN** |
| SOI fuel-economy, NOx, noise, and cylinder-pressure acceptance | **NOT RUN** |
| Flash-ready recommendation | **FAIL / HOLD** |

The four ideas are not equally mature. `SMK-2500` and `SOI56-A` are precise, bounded experiments once their runtime inputs are proved. `N75-A` needs a polarity/active-map gate. The proposed full hot-start copy is over-broad and should be replaced by the conditional 250-rpm-only candidate.

## Sources

[^1]: Bosch/VW A2L supplied locally, `03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.a2l`, `BYTE_ORDER MSB_FIRST` at line 4538; `Kf_Xs16_Ys16_Ws16` record layout at lines 715347–715353; conversions `AngleCrS`, `EngN`, `InjMass`, `Prc`, `Pres_hPa`, `Temp_Cels`, and `Trq` at lines 706496–706506, 707809–707819, 711012–711022, 712331–712341, 712535–712545, 714296–714306, and 714908–714918.
[^2]: Bosch/VW A2L supplied locally, runtime measurements around lines 611064–611330, 644564–645605, 671779–674227, and 695127–696202.
[^3]: Robert Bosch GmbH, *Diesel-Engine Management*, “Operating statuses—Starting” and “Start of injection and delivery,” mirrored at [StudyLib](https://studylib.net/doc/25652593/bosch---diesel-engine-management).
[^4]: Volkswagen AG, *Self-Study Programme 190: Adjustable Turbocharger—Design and Function*, pp. 8, 11–13, 18, 23 and 27, mirrored at [VAGLinks](https://www.vaglinks.com/Docs/SSP/VWUSA.COM_SSP_190_TurboCharger.pdf).
[^5]: Jiadi Zhang et al., “[Benefits of Feedforward for Model Predictive Airpath Control of Diesel Engines](https://arxiv.org/abs/2205.05630),” 2022; and “[Development of a Model Predictive Airpath Controller for a Diesel Engine on a High-Fidelity Engine Model with Transient Thermal Dynamics](https://arxiv.org/abs/2202.12803),” 2022.
[^6]: Garrett Motion, “[How a Turbo Works—Turbo Compressor Map](https://www.garrettmotion.com/knowledge-center-category/oem/expert/)”; BorgWarner, “[Understanding Compressor Maps: Sizing a Turbocharger](https://www.borgwarner.com/aftermarket/boosting-technologies/news/2022/05/23/understanding-compressor-maps-sizing-a-turbocharger),” 2022.
[^7]: C. Rakopoulos et al., “[Experimental Assessment of Turbocharged Diesel Engine Transient Emissions during Acceleration, Load Change and Starting](https://saemobilus.sae.org/papers/experimental-assessment-turbocharged-diesel-engine-transient-emissions-acceleration-load-change-starting-2010-01-1287),” SAE 2010-01-1287.
[^8]: Robert Bosch GmbH, *Diesel-Engine Management*, “Start of injection and delivery,” especially the example ranges and advanced/retarded timing discussion, mirrored at [StudyLib](https://studylib.net/doc/25652593/bosch---diesel-engine-management).
[^9]: M. Zheng et al., “[Influence of EGR on Combustion and Exhaust Emissions of Heavy Duty DI-Diesel Engines Equipped with Common-Rail Injection Systems](https://saemobilus.sae.org/papers/influence-egr-combustion-exhaust-emissions-heavy-duty-di-diesel-engines-equipped-common-rail-injection-systems-2001-01-3497),” SAE 2001-01-3497; Alain Maiboom et al., “[Various Effects of EGR on Combustion and Emissions on an Automotive DI Diesel Engine](https://saemobilus.sae.org/papers/various-effects-egr-combustion-emissions-automotive-di-diesel-engine-numerical-experimental-study-2007-01-1834),” SAE 2007-01-1834.
