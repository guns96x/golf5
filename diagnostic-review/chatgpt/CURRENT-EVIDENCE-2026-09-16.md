# Current evidence — system-wide torque-path diagnosis

Date: 2026-09-16
Branch: `chatgpt-analysis-2026-09-16`
Firmware: current installed Stage 1 (`d8296554...`)

This note separates measured runtime facts from calculated interpretation. It is not a calibration plan.

## 1. Low-RPM pedal-step / transient response

Source: `logs/vcds/LOG-01-011-003-008.CSV`, current session `day16 11:54:46`.

### MEASURED — boost response at the beginning of the load step

Selected Group 011 samples:

| t s | rpm | boost requested mbar | MAP actual mbar | request-actual mbar | N75 % |
|---:|---:|---:|---:|---:|---:|
| 0.02 | 1449 | 1091.4 | 1234.2 | -142.8 | 80.1 |
| 0.30 | 1512 | 1693.2 | 1203.6 | +489.6 | 80.5 |
| 0.55 | 1470 | 1785.0 | 1264.8 | +520.2 | 77.3 |
| 0.83 | 1470 | 1795.2 | 1407.6 | +387.6 | 69.4 |
| 1.08 | 1491 | 1815.6 | 1540.2 | +275.4 | 58.4 |
| 1.36 | 1533 | 1856.4 | 1713.6 | +142.8 | 50.9 |
| 1.60 | 1575 | 1887.0 | 1907.4 | -20.4 | 44.2 |
| 1.90 | 1617 | 1927.8 | 2070.6 | -142.8 | 44.2 |
| 2.19 | 1659 | 1968.6 | 2060.4 | -91.8 | 46.2 |
| 2.46 | 1722 | 2009.4 | 2091.0 | -81.6 | 45.0 |
| 2.72 | 1764 | 2050.2 | 2182.8 | -132.6 | 39.8 |

Interpretation status: `MEASURED` for values; `CALCULATED` for differences.

The largest positive boost error in this visible initial step is about **+520 mbar**. Actual MAP crosses the ramping requested value by t≈1.60 s, about **1.30 s after the large request step at t≈0.30 s**. Because boost request itself is ramping with operating state, this is an observed catch-up time, not a universal turbo time constant.

### MEASURED — torque arbitration during the same load application

Selected Group 008 samples:

| t s | rpm | driver request Nm | torque limitation Nm | smoke limitation Nm | binding candidate |
|---:|---:|---:|---:|---:|---|
| 0.47 | 1449 | 380.6 | 327.0 | 187.9 | smoke |
| 0.74 | 1491 | 383.1 | 331.8 | 207.4 | smoke |
| 0.99 | 1491 | 383.1 | 334.3 | 226.9 | smoke |
| 1.27 | 1533 | 380.6 | 339.2 | 273.3 | smoke |
| 1.52 | 1554 | 380.6 | 344.0 | 302.6 | smoke |
| 1.81 | 1596 | 380.6 | 346.5 | 307.4 | smoke |
| 2.09 | 1638 | 378.2 | 351.4 | 307.4 | smoke |
| 2.38 | 1701 | 375.8 | 358.7 | 307.4 | smoke |
| 2.63 | 1743 | 375.8 | 363.6 | 307.4 | smoke |
| 2.91 | 1785 | 373.3 | 368.4 | 309.9 | smoke |

At every listed sample, the VCDS `Smoke Limitation` value is below both driver request and the separate torque limitation, so it is the minimum of the three logged torque constraints.

### CALCULATED — transient part of the smoke-limiter ramp

Using 309.9 Nm as the eventual value reached by this measured smoke-limitation channel in the same acceleration, define only for diagnostic decomposition:

`transient_smoke_deficit(t) = max(309.9 - smoke_limitation(t), 0)`

Trapezoidal integration over t=0.47…2.91 s gives approximately:

- peak extra transient deficit: **122.0 Nm** at t=0.47 s;
- integrated extra transient deficit: **79.5 Nm·s**;
- smoke limitation reaches ≥95% of 309.9 Nm (294.4 Nm) at t=1.52 s, approximately **1.05 s after the high driver request is present at t=0.47 s**.

This calculation does **not** say which internal FlMng sub-path caused the ramp. The current VCDS log does not contain `FlMng_qDynSmoke_mp` or `FlMng_pIATCorr_mp`, so attribution between dynamic-smoke and corrected-pressure/static-smoke logic remains `UNKNOWN`.

## 2. Steady high-load low/mid RPM

Source: existing `diagnostic-review/math-engine/vcds-analysis.md`, current day16 pulls.

### MEASURED/CALCULATED — smoke remains the logged binding torque constraint

Existing analysis reports for 1750–2500 rpm:

- binding classification: smoke limit at all seven analyzed points;
- runtime inner torque around 310–311 Nm;
- FMTC-equivalent runtime IQ about 55.5–56.4 mg;
- stock-duration-equivalent about 58.5–60.2 mg;
- air about 960–1025 mg/stroke on the analyzed points.

Status: runtime limiter values are `MEASURED`; FMTC/IQ conversions are `CALCULATED`.

### MEASURED — once spooled, low-RPM boost is not below request

Current day16 11:54:46 pull:

| rpm | boost requested | MAP actual | actual-request |
|---:|---:|---:|---:|
| 2000 | 2184 | 2325 | +141 mbar |
| 2250 | 2203 | 2315 | +112 mbar |
| 2500 | 2203 | 2305 | +102 mbar |
| 2750 | 2203 | 2322 | +119 mbar |
| 3000 | 2203 | 2203 | ~0 mbar |

Therefore the currently logged data do **not** support a persistent low-RPM steady-state boost shortage as the primary explanation after spool is established.

This does not reject a transient air/boost contribution: the pedal-step data above show a large temporary positive requested-minus-actual boost error before MAP catches up.

## 3. Current system-level interpretation

### `CROSS_VALIDATED` direction: transient response matters

Two synchronized runtime paths change strongly during initial load application:

1. requested boost rises much faster than actual MAP initially;
2. logged Smoke Limitation rises from ~188 Nm toward ~310 Nm while driver request is already ~380 Nm.

Both effects disappear/reduce as air/boost builds. This is a quantitatively plausible mechanism for sluggish initial response even when steady-state boost later meets/exceeds request.

### `PROVISIONAL`: exact cause inside smoke/transient torque logic

Still unresolved because the current VCDS channel set does not expose:

- `ASDdc_trq`;
- `CoEng_trqInrLtdDrv`;
- `CoEng_trqSetASDUnLim`;
- `CoEng_trqLimASDdc_mp`;
- `FMTC_qAct`;
- `FlMng_qDynSmoke_mp`;
- `FlMng_pIATCorr_mp`.

Therefore the measured low-RPM torque ramp cannot yet be assigned specifically to ASDdc, dynamic smoke, corrected-pressure smoke logic, or a combination of them.

## 4. High-RPM path remains separate

The existing high-RPM evidence remains consistent with the separate Duration-selector/MAP0 hypothesis. The new transient findings do not explain away the 3000–4000 rpm torque-realization fall and should not be merged into that issue without evidence.

## 5. Immediate decision

- Do not increase boost blindly: steady low/mid-RPM MAP already meets/exceeds runtime request once spooled.
- Do not change static smoke solely from the transient ramp: exact `FlMng_qDynSmoke_mp` / `FlMng_pIATCorr_mp` contributions are not logged.
- Do not change ASDdc calibrations without runtime pre/post-ASD torque evidence.
- Continue read-only modeling and acquire the missing runtime channels if the transport/tooling permits it.

Status for calibration modification: **HOLD**.
