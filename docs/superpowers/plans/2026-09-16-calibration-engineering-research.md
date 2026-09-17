# EDC16U34 Calibration Engineering Research Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a read-only, evidence-driven analysis pipeline that locates torque loss from driver request through transient torque control, air/boost, injection command and measured vehicle response before any firmware modification is considered.

**Architecture:** Extend the existing `tools/calmath` work with small focused validators rather than expanding one monolithic CLI. The first deliverable is a transient torque validator centered on ASDdc/ASDrf and dynamic-smoke paths; later packages add boost-transient and injection-selector validation, and a final cross-validation report combines their outputs without writing BIN files.

**Tech Stack:** Python 3 standard library, existing `tools/calmath/a2l.py`, existing telemetry/VCDS readers, JSON + deterministic Markdown reports, `unittest`.

**Spec:** `diagnostic-review/chatgpt/CALIBRATION_ENGINEERING_DESIGN.md`

## Global Constraints

- Work only on branch `chatgpt-analysis-2026-09-16` unless explicitly instructed otherwise.
- Never create or modify a firmware BIN in this plan.
- Exact A2L identity/scaling is required for calibration claims.
- Static calibration values must not be described as runtime-active values without runtime evidence.
- Raw MAP must not be substituted for `FlMng_pIATCorr_mp` without an explicit proxy status.
- Electrical duration/end proxy must not be described as physical injected mass, physical EOI, combustion end or CA50.
- Unknown inputs remain `UNKNOWN`/`null`.
- Candidate calibration output is prohibited until cross-validation gates pass.

---

### Task 1: Pure transient-torque math model

**Files:**
- Create: `tools/calmath/transient_torque.py`
- Create: `tests/test_transient_torque.py`

**Interfaces:**
- Produces: `torque_delta(before_nm: float, after_nm: float) -> float`
- Produces: `iq_delta(fmtc_map, rpm: float, before_nm: float, after_nm: float) -> dict`
- Produces: `integrated_deficit(samples: list[dict]) -> dict`
- Produces: `intervention_status(delta_nm: float, uncertainty_nm: float) -> str`

- [ ] **Step 1: Write failing tests for signed torque deficit**

```python
from calmath.transient_torque import torque_delta


def test_torque_delta_positive_when_intervention_removes_torque():
    assert torque_delta(340.0, 292.0) == 48.0


def test_torque_delta_negative_when_intervention_adds_torque():
    assert torque_delta(280.0, 300.0) == -20.0
```

- [ ] **Step 2: Run the tests and verify they fail because the module does not exist**

Run: `python -m unittest tests.test_transient_torque -v`
Expected: import failure for `calmath.transient_torque`.

- [ ] **Step 3: Implement `torque_delta` minimally**

```python
def torque_delta(before_nm, after_nm):
    return float(before_nm) - float(after_nm)
```

- [ ] **Step 4: Add failing tests for FMTC-based IQ delta using a deterministic fake map**

```python
class FakeFMTC:
    def lookup(self, rpm, torque, policy='clamp'):
        return torque / 5.0


def test_iq_delta_maps_torque_intervention_to_iq():
    r = iq_delta(FakeFMTC(), 1800, 340, 290)
    assert r['q_before_mg'] == 68.0
    assert r['q_after_mg'] == 58.0
    assert r['delta_q_mg'] == 10.0
```

- [ ] **Step 5: Implement `iq_delta` with explicit map policy and no hidden extrapolation**

The returned object must include `rpm`, `before_nm`, `after_nm`, `q_before_mg`, `q_after_mg`, `delta_q_mg`, and `fmtc_policy`.

- [ ] **Step 6: Add failing tests for integrated transient deficit**

Use samples with timestamps and `delta_nm`; integrate by trapezoidal rule to produce `nm_s`, `peak_deficit_nm`, `duration_s`.

- [ ] **Step 7: Implement integration and uncertainty status**

`intervention_status` returns `CALCULATED` only when `abs(delta_nm) > uncertainty_nm`; otherwise `WITHIN_UNCERTAINTY`.

- [ ] **Step 8: Run focused and full existing tests**

Run: `python -m unittest tests.test_transient_torque -v`
Run: `python -m unittest discover -s tests -v`
Expected: zero failures.

- [ ] **Step 9: Commit**

Commit message: `feat(chatgpt): add pure transient torque intervention math`

---

### Task 2: A2L inventory for ASDdc/ASDrf and dynamic smoke

**Files:**
- Create: `tools/calmath/transient_inventory.py`
- Modify: `tests/test_transient_torque.py`

**Interfaces:**
- Consumes: `calmath.a2l.db()` parsed database.
- Produces: `inventory_transient_objects(db: dict) -> dict`
- Produces categories: `measurements`, `characteristics`, `missing_required`, `optional`.

Required runtime names:
`ASDdc_trq`, `CoEng_trqInrLtdDrv`, `CoEng_trqSetASDUnLim`, `CoEng_trqLimASDdc_mp`, `FMTC_qAct`, `FlMng_qDynSmoke_mp`, `FlMng_pIATCorr_mp`.

Required calibration prefixes/names:
`ASDdc_`, `ASDrf_`, `FlMng_qDynSmoke_MAP`, `FlMng_facDynSmoke_CUR`, `FlMng_facDynSmkAP_CUR`, `FlMng_facDynSmkTemp_CUR`.

- [ ] **Step 1:** Add a synthetic A2L database test that proves exact required names are detected and missing names are reported.
- [ ] **Step 2:** Run test and verify failure.
- [ ] **Step 3:** Implement inventory using only parsed A2L metadata, not hard-coded addresses.
- [ ] **Step 4:** Add classification fields `role`, `evidence_level`, `runtime_required` for each required object.
- [ ] **Step 5:** Run focused and full tests.
- [ ] **Step 6:** Commit as `feat(chatgpt): inventory transient torque and dynamic smoke A2L paths`.

---

### Task 3: Current/stock/old-ON calibration comparison

**Files:**
- Create: `tools/transient_torque_validator.py`
- Modify: `tests/test_transient_torque.py`

**Interfaces:**
- CLI inputs default to existing project files:
  - current: `03G906021QJ_stage1_full_power_dpf_egr_off.bin`
  - stock/reference: `diagnostic-review/reference-from-hex.analysis-only.bin`
  - prior ON: `diagnostic-review/new-inputs/on/03G906021QJ.Bin`
- Produces: `diagnostic-review/chatgpt/transient-calibration-diff.json`
- Produces: `diagnostic-review/chatgpt/transient-calibration-diff.md`

- [ ] **Step 1:** Add tests for deterministic diff schema using fake decoded characteristics.
- [ ] **Step 2:** Verify failure.
- [ ] **Step 3:** Implement read-only decoding and comparison of all inventory characteristics.
- [ ] **Step 4:** Include SHA-256 of every input binary and exact A2L path.
- [ ] **Step 5:** For each object report `identical_current_vs_stock`, `identical_current_vs_on`, dimensions/units/address, and numeric min/max delta where meaningful.
- [ ] **Step 6:** Explicitly prohibit file writes outside report paths and test that no `.bin` output path exists.
- [ ] **Step 7:** Run all tests and execute the validator against project files.
- [ ] **Step 8:** Commit as `feat(chatgpt): compare transient calibration paths across firmware lineage`.

---

### Task 4: Runtime ASDdc intervention analyzer

**Files:**
- Create: `tools/calmath/transient_runtime.py`
- Modify: `tools/transient_torque_validator.py`
- Modify: `tests/test_transient_torque.py`

**Interfaces:**
- Produces: `analyze_runtime(samples, fmtc_map, uncertainty_nm) -> dict`.
- Accepts time-aligned sample dictionaries with runtime channels; missing channels remain null and produce `HOLD`, not inferred values.

Per-sample outputs:
`rpm`, `gear/state`, `torque_before_asd_nm`, `asd_correction_nm`, `torque_after_asd_nm`, `delta_t_asd_nm`, `q_before_asd_mg`, `q_after_asd_mg`, `delta_q_asd_mg`, `dynamic_smoke_mg`, `status`.

Segment outputs:
`peak_asd_deficit_nm`, `integrated_asd_deficit_nm_s`, `time_to_90pct_post_asd_torque_s`, intervention start/end timestamps.

- [ ] **Step 1:** Write synthetic runtime tests with a known 50 Nm ASD intervention and known recovery time.
- [ ] **Step 2:** Verify failure.
- [ ] **Step 3:** Implement runtime analyzer with explicit time alignment.
- [ ] **Step 4:** Add tests for missing ASD channels returning `HOLD`.
- [ ] **Step 5:** Add tests showing dynamic-smoke correction is reported separately from ASD correction.
- [ ] **Step 6:** Run full suite and analyze any compatible existing logs; never invent absent channels.
- [ ] **Step 7:** Commit as `feat(chatgpt): quantify runtime ASD and dynamic smoke interventions`.

---

### Task 5: Boost-transient validator

**Files:**
- Create: `tools/calmath/boost_transient.py`
- Create: `tests/test_boost_transient.py`
- Modify: `tools/transient_torque_validator.py`

**Interfaces:**
- Produces metrics from synchronized `boost_requested`, `map_actual`, `n75`, `rpm`, `pedal/load`.
- Metrics: rise time, `dMAP/dt`, peak error, RMS error, actuator saturation fraction, signed area of boost error.

- [ ] **Step 1:** Write synthetic step-response tests.
- [ ] **Step 2:** Verify failure.
- [ ] **Step 3:** Implement request/actual metrics without using static map values as runtime request.
- [ ] **Step 4:** Add test that analysis returns `HOLD` when runtime boost request is absent.
- [ ] **Step 5:** Run tests and existing compatible VCDS logs.
- [ ] **Step 6:** Commit as `feat(chatgpt): add synchronized boost transient metrics`.

---

### Task 6: Injection selector / duration independent validator

**Files:**
- Create: `tools/calmath/injection_selector.py`
- Create: `tests/test_injection_selector.py`
- Create: `tools/injection_selector_validator.py`

**Interfaces:**
- Produces `selector_components(selector: float, map_count: int) -> (lo, hi, weight)`.
- Produces exact current/stock blended duration at a given RPM/IQ/SOI.
- Produces OEM-duration-equivalent IQ by inverse interpolation on the stock blended duration surface.

- [ ] **Step 1:** Write selector boundary/interpolation tests including selector 0.0, 0.5, 0.97 and integer boundaries.
- [ ] **Step 2:** Verify failure.
- [ ] **Step 3:** Implement selector logic.
- [ ] **Step 4:** Write tests for monotonic inverse duration-to-IQ and explicit out-of-axis status.
- [ ] **Step 5:** Implement OEM-equivalent inversion; no extrapolation unless explicitly selected and labeled.
- [ ] **Step 6:** Run against current/stock project files over 2500–4500 rpm and generate `diagnostic-review/chatgpt/injection-selector-validation.{json,md}`.
- [ ] **Step 7:** Quantify whether the MAP0 transition predicts the observed high-rpm torque residual within uncertainty.
- [ ] **Step 8:** Commit as `feat(chatgpt): independently validate duration selector and MAP0 transition`.

---

### Task 7: Cross-validation evidence matrix

**Files:**
- Create: `tools/calmath/evidence_matrix.py`
- Create: `tests/test_evidence_matrix.py`
- Create: `tools/calibration_evidence_report.py`

**Interfaces:**
- Consumes JSON outputs from Tasks 3–6 plus existing `current-analysis.json` and `vcds-analysis.json`.
- Produces: `diagnostic-review/chatgpt/EVIDENCE-MATRIX-2026-09-16.json`
- Produces: `diagnostic-review/chatgpt/EVIDENCE-MATRIX-2026-09-16.md`

Statuses are limited to `MEASURED`, `CALCULATED`, `CROSS_VALIDATED`, `PROVISIONAL`, `CONFLICT`, `UNKNOWN`, `HOLD`.

- [ ] **Step 1:** Write tests that prevent a single static-map inference from becoming `CROSS_VALIDATED`.
- [ ] **Step 2:** Write tests requiring at least two independent evidence families for cross-validation.
- [ ] **Step 3:** Implement evidence matrix and residual comparison.
- [ ] **Step 4:** Generate one table across 1500–4000 rpm with no fabricated values.
- [ ] **Step 5:** Run full suite.
- [ ] **Step 6:** Commit as `feat(chatgpt): combine ECU air injection and road evidence without premature calibration`.

---

### Task 8: Research/source ledger and measurement protocol

**Files:**
- Create: `diagnostic-review/chatgpt/SOURCES.md`
- Create: `diagnostic-review/chatgpt/MEASUREMENT-PROTOCOL.md`

**Interfaces:**
- `SOURCES.md` records source, authority tier, exact claim supported, applicability and limitations.
- `MEASUREMENT-PROTOCOL.md` specifies synchronized channels, test segments, repeat count, acceptance and abort criteria.

Required primary references to document:
- VW SSP 304 EDC16 torque orientation, metering, active pulse damping.
- VW SSP 209 PD solenoid duration/quantity and BIP/COI feedback.
- exact project A2L.
- ASAM MCD-2 MC for A2L semantics.
- Ross-Tech TDI logging guidance for group 011 where applicable.
- BorgWarner VTG documentation for general vane-control physics; exact BV39 limits remain unknown unless exact-part documentation is found.

- [ ] **Step 1:** Add source ledger with explicit Tier A/B/C labels.
- [ ] **Step 2:** Write measurement protocol covering steady WOT and pedal-step transients; do not require a specific gear as the only diagnostic condition.
- [ ] **Step 3:** Define minimum channels and fallback channel sets.
- [ ] **Step 4:** Define reproducibility metrics and environmental metadata.
- [ ] **Step 5:** Commit as `docs(chatgpt): add calibration source ledger and measurement protocol`.

---

## Completion gate

This plan is complete only when:
- all new unit tests have been run with zero failures;
- report generation has been run on actual project inputs where supported;
- all claims in generated reports have an evidence status;
- no firmware BIN was created or modified;
- no candidate calibration is emitted unless the evidence matrix independently supports it and the user explicitly requests that next phase.
