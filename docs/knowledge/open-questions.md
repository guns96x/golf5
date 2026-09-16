# Project Open Questions & Competing Hypotheses

## The 15 Core Project Questions

1. What functional block generates final boost request on SW 1037391847?
2. Which environmental corrections alter `PCR_pBDesBas_MAP` output?
3. What is the exact feed-forward role of `PCR_rBPCtlBas_MAP`?
4. How does the IQ axis extrapolate above the final defined axis value?
5. Which PID closed-loop terms dominate transient boost regulation?
6. Which limiter governs fuel at each 100 RPM increment from 1500 to 4000 RPM?
7. Is `FlMng_qPresSmoke_MAP` actively limiting fuel in the 1800–2200 RPM window?
8. What governs actual injected quantity during rapid pedal tip-in?
9. Which SOI maps execute for gear 3 vs gear 5?
10. Which thermal protection maps derate torque under high continuous load?
11. Which exact map controls hot start cranking fuel?
12. What was the OEM post-injection thermal management strategy for DPF regeneration?
13. Which calibration differences in stage 1 are functional vs software version artifacts?
14. Which duplicate map banks are actively called at runtime?
15. What exact pre-control adjustment eliminates the 2330 mbar boost overshoot?

---

## Competing Hypotheses for 2310–2330 mbar Boost Spike

- **Hypothesis A (High Target)**: Specified boost request itself is set high in this range. *(Contradicted by logs: specified is ~2150 mbar)*.
- **Hypothesis B (Feed-Forward Duty Too High)**: Zero EGR flow increases turbine mass flow; feed-forward table holds vanes too closed. *(Strongly Supported)*.
- **Hypothesis C (PID Transient Tuning)**: Derivative/Proportional gain is too slow to catch rapid spool-up. *(Corroborated)*.
- **Hypothesis D (Mechanical Sticking)**: VNT vanes or vacuum actuator linkage has mechanical friction. *(Low probability: vehicle returns cleanly to target)*.
