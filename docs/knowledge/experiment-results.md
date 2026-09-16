# Experiment Results: Overboost Investigation (2310–2320 mbar)

## Observed Phenomenon

In the 3rd gear full-throttle acceleration run:
- **Engine Speed Range**: 1900–2600 RPM
- **Specified Boost Target**: **2214 mbar absolute** (calibrated Stage 1 request)
- **Actual Measured MAP**: Peaked at **~2310–2320 mbar absolute** at ~2180 RPM
- **Overshoot Magnitude**: $+96\dots+106\text{ mbar}$ ($+4.5\dots+4.8\%$ above specified target)

```
Boost (mbar)
2350 |
2320 |                   * * (Peak 2310–2320 mbar)
2300 |                 *     *
2214 |  Specified --> *-------*---------------- (2214 mbar)
2100 |              *           *
2000 |            *               *
1900 |          *
     +----------------------------------------> RPM / Time
             1800  2000  2200  2400  2600
```

## Epistemic Evaluation: Competing Hypotheses A–G

> [!NOTE]
> In accordance with [RESEARCH_POLICY.md](RESEARCH_POLICY.md), the root cause is **NOT** declared an established fact. The following competing hypotheses are under active evaluation:

- **Hypothesis A (Specified Target Elevated)**: *Rejected*. Stage 1 request is confirmed at 2214 mbar.
- **Hypothesis B (Feed-Forward Duty Elevated Post-EGR Delete)**: *Hypothesis (RAW)*. With EGR closed, 100% of exhaust gas expands across the turbine. If stock feed-forward (`PCR_rBPCtlBas_MAP`) was tuned for 15–30% EGR bypass, it holds vanes too closed during transient spool-up. Requires sign-test to confirm.
- **Hypothesis C (PID Transient Damping)**: *Hypothesis (RAW)*. PID derivative or proportional gain may be under-damped for the rapid spool-up rate.
- **Hypothesis D (Sensor / Sampling Alias)**: *Hypothesis (RAW)*. The ~1.2 Hz sampling rate of multi-group VCDS logging obscures the true peak shape and settling time.
- **Hypothesis G (Mechanical Actuator Hysteresis)**: *Hypothesis (RAW)*. Vacuum bleed rate through N75 solenoid or actuator rod friction creates pneumatic delay.
