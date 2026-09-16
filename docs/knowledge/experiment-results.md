# Experiment Results: Overboost Investigation (2310–2330 mbar)

## Observed Phenomenon

During 3rd gear full-load acceleration from 1300 RPM:
- **Engine Speed**: 1900–2600 RPM
- **Specified Boost Target**: ~2150 mbar absolute
- **Actual Measured MAP**: Peaked at **2330 mbar absolute** at ~2180 RPM
- **Overshoot Magnitude**: $+180	ext{ mbar}$ ($+8.4\%$ above target)
- **Settling Time**: ~0.65 seconds before PID controller lowered N75 duty from 78.5% down to 64.0% to pull boost back to target.

```
Boost (mbar)
2400 |                     * * (Peak 2330 mbar)
2300 |                   *     *
2200 |    Specified --> *-------*---------------- (2150 mbar)
2100 |                *           *
2000 |              *               *
1900 |            *
     +----------------------------------------> RPM / Time
             1800  2000  2200  2400  2600
```

## Quantitative Evaluation

The overshoot does not violate the turbocharger mechanical burst limit (2450 mbar), but sustained 2330 mbar spikes stress the actuator linkage and create minor torque surges.
**Primary Cause**: Combination of closed EGR (increased turbine enthalpy) and pre-control feed-forward duty in `PCR_rBPCtlBas_MAP` being slightly too high for zero-EGR conditions.
