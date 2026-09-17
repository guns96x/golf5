# Review request — Stage 1 vNext5 (2026-09-17)

Car: VW Golf 5 1.9 TDI BLS, Bosch EDC16U34, HW `03G906021QJ` / SW `1037391847`, BV39 turbo, DPF physically removed, EGR blanked, stock MANN air filter.
Currently flashed: `03G906021QJ_stage1_full_power_dpf_egr_off.bin` (bought with this Stage 1).
Owner priorities: strong pull, engine/turbo life, fuel economy. No smoke.

## What to review

**Recommended candidate:** `firmware-candidates/03G906021QJ_vNext5_stage1-balanced_CS_OK.bin` (sha256 `23c32e88002ea57d2490962fa8f3b4590d5f08f5c626383fc673573991d922ea`), built by `python tools/calmath_engine.py build-vnext5`.

Changes vs the flashed file:
1. Stage 0: `StSys_trqStrtBas_MAP` (hot start) and `InjCrv_phiBasGear56_MAP` light-load cruise SOI, copied from `03G906021QJ_stage1_refined_CS_OK.bin`.
2. SOI `InjCrv_phiBasGear34_MAP` / `InjCrv_phiBasGear56_MAP`, 3000–5000 rpm, q columns 45/55/60 mg: advanced so each cell ≤ OEM limiter `InjCrv_phiMIMax_MAP` − 0.25° (limiter itself unchanged) and ≤ OEM cell + 2.5°.
3. Smoke limiter `FlMng_qPresSmoke_MAP` 1800 / 2000 hPa columns: fuel for λ 1.15 at measured WOT air; cells only lowered.

Please challenge in particular:
- **Evidence that late combustion costs power above 3000 rpm:** end-of-command proxy (duration − SOI) is 14–17° ATDC now vs 5–8° OEM, and fuel equivalent of road torque is 37–51 mg vs 56–66 mg injected (`diagnostic-review/math-engine/vcds-analysis.json`).
- **Whether advancing SOI up to (OEM limiter − 0.25°) is safe** for peak cylinder pressure on this PD engine.
- **The air model:** WOT air per rpm pooled from VCDS group 003 (2026-09-16) and OBD MAF+MAP+IAT road log (`logs/20260917/`), `wot_air_evidence()` and `tools/maf_speed_density_check.py`. Implied VE rises with flow at fixed rpm, so no flow-dependent MAF under-read was found. A uniform MAF scale error is NOT excluded.
- **Smoke-map pressure axis handling:** at established boost the IAT-corrected pressure is ≥2000 hPa, so the last column applies; the 1800 column governs spool.
- **Stock-equivalent delivery model** (`stock_equivalent_q`): delivered fuel is expressed through OEM duration maps, and SOI moves the duration selector `InjVlv_numMI1_CUR`.
- **The checksum rule** (`fix_checksums`, two blocks summing to `0xD01FE500`), which was validated on 3 independent known-good files (`tests/test_calmath.py`).

Known open issue, deliberately not changed: boost overshoot to 2420–2470 hPa in 5th gear at 2750–3230 rpm (target 2214). This needs a fast VCDS group 011 log first.

## Where things are

- Plan and all decisions: `diagnostic-review/math-engine/STAGE1-ENGINEERING-PLAN.md` (§4b vNext3, §4c vNext4, §4d vNext5)
- Earlier findings: `diagnostic-review/math-engine/DECISION-2026-09-16.md`
- Candidate reports: `diagnostic-review/math-engine/candidate-vnext{3,4,5}.json`, `candidate-stage0.json`
- Engine: `tools/calmath_engine.py`; tests: `python -m unittest discover -s tests` (62 tests)
- Alternatives: `03G906021QJ_vNext4_stage1-edge_CS_OK.bin` (λ 1.10, +fuel at 2000–2500), `03G906021QJ_stage0_hotstart-ecocruise_CS_OK.bin` (no WOT change)
- Logger app used for the road logs: https://github.com/guns96x/vcds-android
