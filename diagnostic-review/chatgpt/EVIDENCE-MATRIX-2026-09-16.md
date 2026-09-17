# Evidence matrix — 2026-09-16

Branch: `chatgpt-analysis-2026-09-16`
Calibration modification status: **HOLD**

This matrix uses independent evidence families. Two calculations derived from the same family do not count twice. Missing critical runtime evidence forces `HOLD`.

| Hypothesis | Evidence families | Status | Why |
|---|---|---|---|
| Low-RPM tip-in contains a real transient torque/air restriction | runtime torque + air/boost | **CROSS_VALIDATED** | Group 008 smoke limitation ramps ~188→310 Nm while driver request is ~380 Nm; Group 011 simultaneously shows requested-minus-actual boost error peaking ~+520 mbar before MAP catches up. |
| Steady 1750–2500 rpm is capped by the smoke path near 310 Nm | runtime torque + static calibration | **CROSS_VALIDATED** | Runtime Smoke Limitation is the minimum logged torque constraint; existing inverse-FMTC calculation of the 56.5 mg static smoke value matches runtime ~309.9 Nm within VCDS resolution. |
| ASDdc is the primary cause of sluggish tip-in | system definition + missing runtime ASD | **HOLD** | Exact A2L contains the active damper path, but current logs do not contain `ASDdc_trq` or pre/post-ASD torque. Presence is not runtime proof. |
| `FlMng_qDynSmoke` is the primary cause of the tip-in ramp | runtime final smoke + missing dynamic-smoke channel | **HOLD** | Final smoke limitation clearly ramps, but `FlMng_qDynSmoke_mp` is not logged, so the dynamic sub-path cannot be separated from corrected-pressure/static-smoke logic. |
| MAP0/Duration is the primary physical cause of the 3000–4000 rpm torque fall | static injection + vehicle response + missing runtime injection | **HOLD** | Static selector/Duration calculation and road-torque fall point in the same direction, but no direct runtime Duration/selector/physical fuel measurement proves causality. |

## What is already ruled down

### Persistent low-RPM steady-state boost shortage

Current day16 high-load data do not support this as the primary low-RPM problem once spool is established:

- 2000 rpm: actual ≈2325 vs requested ≈2184 mbar;
- 2250: 2315 vs 2203;
- 2500: 2305 vs 2203;
- 2750: 2322 vs 2203;
- 3000: approximately equal.

This does **not** reject a transient boost contribution. The same current log shows a large initial boost error immediately after load application.

## System-level interpretation

The current data support a two-layer low-RPM behavior:

1. **Transient layer:** after a rapid torque request, air/boost has not yet caught up and the logged smoke torque limit ramps upward over roughly the first second.
2. **Steady layer:** after the transient has settled, the logged smoke path remains the minimum torque constraint at roughly 310 Nm through the analyzed 1750–2500 rpm region.

The exact internal split between ASDdc, dynamic smoke, corrected-pressure smoke logic and other torque interventions remains unresolved because the required runtime channels are absent.

The high-RPM 3000–4000 rpm issue remains a separate work package centered on injection-selector/Duration/SOI and torque realization.

## Next evidence required

Highest-value missing runtime channels:

- `ASDdc_trq`
- `CoEng_trqInrLtdDrv`
- `CoEng_trqSetASDUnLim`
- `CoEng_trqLimASDdc_mp`
- `FMTC_qAct`
- `FlMng_qDynSmoke_mp`
- `FlMng_pIATCorr_mp`
- runtime SOI / Duration / selector if accessible

Until these are available, the analysis continues read-only and no calibration-cell edit is authorized by this workstream.
