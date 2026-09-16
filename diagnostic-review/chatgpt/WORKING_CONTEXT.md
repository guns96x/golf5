# ChatGPT Working Context — isolated branch

Branch: `chatgpt-analysis-2026-09-16`
Base commit: `0568ea2aaf92dae182667538d884f49ee17b4870`
Purpose: continue independent analysis without touching Claude's work on `main`.

## Verified current state

- Active firmware under analysis: `03G906021QJ_stage1_full_power_dpf_egr_off.bin`
- Known SHA-256: `d8296554b0342a9a4eb1ca0af0a17ccbbecc066349907448213ea6179ad2bfe0`
- Math engine exists under `tools/calmath*` with A2L-driven map decoding, telemetry alignment, virtual dyno / Monte Carlo, VCDS parsing and tests.
- `candidate-v1.json` currently still contains the older smoke-limiter proposal and must not be treated as the latest plan.
- Latest decision note identifies a stronger candidate: `InjVlv_phiInjMI1_MAP0` remained stock while MAP1..4 were scaled in Stage 1.
- Selector behavior moves from almost MAP1 at ~3000 rpm toward MAP0 by ~4000 rpm.
- Current numerical claim from Claude's decision note:
  - 3000 rpm: requested ~62.6 mg, selector ~0.97, OEM-duration-equivalent ~66.2 mg
  - 3250 rpm: requested ~63.2 mg, selector ~0.64, ~62.4 mg-equivalent
  - 3500 rpm: requested ~64.0 mg, selector ~0.44, ~60.1 mg-equivalent
  - 3750 rpm: requested ~63.9 mg, selector ~0.21, ~57.2 mg-equivalent
  - 4000 rpm: requested ~62.1 mg, selector 0.00, ~55.0 mg-equivalent
- Treat those numbers as `OEM-duration-equivalent`, not directly measured physical injected mass.
- Runtime VCDS evidence reportedly confirms smoke limitation around 309.9 Nm agrees with inverse FMTC for the static 56.5 mg smoke node within about 2.1 Nm.
- FMTC >336 Nm ambiguity is no longer central for the observed WOT points because runtime torque remains inside the axis.
- No new BIN was created by Claude in the reviewed commits.

## Current priority

Independently verify the MAP0-duration hypothesis before any firmware generation:

1. Reproduce MAP0/MAP1..4 scaling from A2L + stock/current BIN.
2. Reproduce `InjVlv_numMI1_CUR` selector vs SOI over 3000–4500 rpm.
3. Recompute duration using exact interpolation and axis policy.
4. Convert current duration to OEM-duration-equivalent IQ by inverting the OEM duration maps.
5. Compare the predicted IQ-equivalent fall against measured road-torque fall and VCDS runtime quantities.
6. Quantify uncertainty and residuals.
7. Replace the obsolete smoke candidate only if the duration hypothesis survives independent verification.
8. Do not create or modify a firmware BIN until the plan is numerically cross-validated.

## Safety / epistemic rules

- Distinguish static calibration, runtime measurement, mathematical inference and hypothesis.
- Never label `PCR_pBDesBas_MAP` static values as runtime requested boost without synchronized runtime evidence.
- Never treat electrical command-end proxy as physical EOI or combustion end.
- Keep unknowns as `UNKNOWN` rather than inventing values.
- One coherent change at a time; preserve rollback path and checksum validation.
