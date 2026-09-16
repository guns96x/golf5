# Experiment Results: Boost Telemetry Analysis (16.09.2026 Run)

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
