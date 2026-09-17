# Follow-up review of vNext6.1 — 2026-09-17

vNext6.1 addresses the previous review well. Two items remain before treating it as anything beyond an A/B experiment.

## 1. Add gear-5 evidence to the torque-preservation gate, or mark it explicitly HOLD

Current `burned_p95_constraints()` pools VCDS rows plus phone rows only for gears 3/4. The vNext6.1 validation protocol, however, calls for 3rd/4th/5th WOT pulls, and the higher-load 5th-gear case is important because this calibration has already shown different boost behaviour there.

Requested change:

- If the 2026-09-17 phone log has a sufficiently reliable speed/RPM trace for 5th, include gear 5 in the per-rpm P95 burned-fuel constraints and report its contribution explicitly.
- Do not silently mix poor-quality 5th-gear samples into the gate. Add a quality gate for gear classification / derivative stability and reject the pull if it fails.
- If 5th cannot currently be modelled to the same standard, keep the current 3/4 gate but label `gear5_torque_preservation = HOLD` in `candidate-vnext6.1.json` and require 5th as an empirical validation gate before promotion.

Acceptance criterion: the report must make it impossible to interpret the current P95 gate as having been validated in gear 5 when it has not.

## 2. Make the air/lambda side of the gate robust to pull-to-pull variation

Current code uses median gear-4 MAF at each rpm to compute the lambda-1.15 fuel floor. That is acceptable as a central estimate but not a robustness floor: air can be lower on another pull because of IAT, boost, weather, heat soak, or measurement spread.

Requested change:

- Keep the torque P95 gate as the primary no-torque-loss constraint.
- For the lambda/air constraint, report at least median and a conservative low-air statistic from valid established-WOT samples at each rpm (prefer a distribution-aware bound such as P10/P05, or a clearly justified worst-valid-pull value; do not use an arbitrary multiplier).
- Re-evaluate the fitted 3000/4000 smoke nodes against that lower-air case and report predicted lambda per individual pull, not only against the median.
- Do not force the candidate richer/leaner solely to satisfy an arbitrary lambda target if that would conflict with torque preservation. The lambda term remains a calibration guard, not proof of combustion efficiency.

Acceptance criterion: `candidate-vnext6.1.json` should include enough per-pull/per-gear evidence to show the minimum predicted lambda and which pull/gear defines it.

## Small wording fix

The status currently says the gate keeps delivered fuel `>= P95 burned estimate and >= lambda 1.15 fuel`. The actual formula is:

`delivered_new >= min(delivered_current, max(P95_burned, lambda115_fuel))`

This matters at 2750/3000 rpm where P95 is slightly above current delivered fuel. Please use the exact formula in the status/docs.

## Scope

Do not reopen the accepted fixes from the previous review. Keep vNext6.1 fuel-only, do not touch <=2500 rpm, the 1800 hPa column, 5355 rpm, SOI, Stage 0, or boost/N75 in this revision. If these two follow-up items change the fitted nodes, regenerate the BIN, checksum verification, SHA-256, byte diff, and tests; otherwise document why the existing BIN remains unchanged.
