# Response to ChatGPT review of vNext6 (2026-09-17)

Accepted points and what changed:

| # | Review point | Verdict | Action in vNext6.1 |
|---|---|---|---|
| 1 | vNext6 edits 1750–2500 rpm and the 1800 hPa spool column despite the plan calling that zone validated, while the low-rpm tip-in restriction (smoke limitation ~188→310 Nm, boost error ~+520 mbar, EVIDENCE-MATRIX) is still HOLD | **Accepted** (confirmed in repo) | Every node ≤ 2500 rpm and the whole 1800 hPa column are untouched |
| 2 | At 2000 rpm (58.8 vs burned P50 61.6) and 2750 rpm (57.0 vs 57.7) vNext6 delivers less than the model links to current torque | **Accepted** (my own tables show it) | Torque-preservation gate restored: per bin, delivered ≥ min(current, max(P95 burned over all pulls, λ 1.15 fuel)) |
| 3 | λ 1.15 is a calibration target, not proof that more fuel cannot burn | **Accepted** | Wording is now "model indicates inefficient fuel use", not "unburnt fuel" |
| 4 | Stock-equivalent fuel and the EOI proxy are models, not injector or combustion measurements | **Accepted** | Kept as models, labelled as such |
| 5 | 5355 rpm change is an extrapolation without data | **Accepted** | 5355 untouched |
| 6 | 1800 hPa air scaling (air ∝ pressure, constant VE) is weakest in transients | **Accepted** | Not used |
| 7 | Stage 0 should be tested separately | **Accepted** | vNext6.1 contains no Stage 0 objects |
| 8 | Boost / N75 still unresolved | Agreed | Unchanged; needs a fast group 011 log |
| 9 | "Without SOI changes" is imprecise because Stage 0 includes eco-cruise SOI | **Accepted** | vNext6.1 has no SOI change at all |
| — | BIN checksum not independently recomputed by the reviewer | Noted | vNext6.1 differs from the flashed file in 12 bytes only (below), easy to diff |

## vNext6.1

`firmware-candidates/03G906021QJ_vNext6.1_fuel-3000-4000-gated_CS_OK.bin`, sha256 `4f7d9ff98e8e672226b017f283ba537e6e374cd54069a6a5e74a4f6f1a074d21`, `build-vnext6.1`.

Byte diff against `03G906021QJ_stage1_full_power_dpf_egr_off.bin` (first build, SUPERSEDED — see follow-up section below):
- `0x1D661A`: `FlMng_qPresSmoke_MAP` 3000 rpm / 2000 hPa, 67.80 → 63.55 mg (raw 6780 → 6355, factor 0.01)
- `0x1D6632`: `FlMng_qPresSmoke_MAP` 4000 rpm / 2000 hPa, 67.80 → 48.80 mg (raw 6780 → 4880)
- `0x1BFFFC..FF` and `0x1FDFFC..FF`: checksum words; both blocks sum to `0xD01FE500`

Model effect (4th gear, logged runtime q):

| rpm | delivered now | gate | delivered new | EOI proxy now → new |
|---|---|---|---|---|
| 2750 | 64.2 | 64.2 | 64.2 | 16.7 → 16.7 |
| 3000 | 66.2 | 66.2 | 66.2 | 16.9 → 16.9 |
| 3250 | 62.4 | 59.1 | 62.4 | 15.4 → 15.3 |
| 3500 | 60.1 | 53.2 | 58.6 | 14.8 → 14.1 |
| 3750 | 57.2 | 49.2 | 53.3 | 13.8 → 12.3 |
| 4000 | 56.3 | 48.8 | 48.8 | 14.3 → 10.5 |

The 3000 rpm node moves, but delivered fuel at 3000 stays the same, because runtime q ≥ 60 mg saturates the duration map axis; the move only shapes the 3000–4000 interpolation.

Status: experiment for A/B against the current file (3rd/4th/5th WOT 2000→4000, groups 011+008 or the OBD logger). Stage 0 stays available separately as `03G906021QJ_stage0_hotstart-ecocruise_CS_OK.bin`.

---

# Response to REVIEW-FOLLOWUP-2026-09-17 (commit e5239de)

All three requests are implemented. The fitted 4000 rpm node changed, so the BIN was regenerated.

## 1. Gear 5: explicitly HOLD at 3000–4000

`road_pull_evidence()` now analyses every OBD phone pull (2026-09-16 and 2026-09-17 logs, gears 3/4/5) through a quality gate. A pull is accepted only if all of these hold:
- gear classified within ±3 % of 0.0255 / 0.0357 / 0.0465 km/h per rpm;
- at least 3 speed/rpm pairs;
- ratio MAD ≤ 0.5 %;
- at least 12 rpm samples;
- only boost-established bins are used.

It rejected 8 pulls, listed in `candidate-vnext6.1.json → rejected_pulls`: three of four 5th-gear pulls and two short 4th-gear pulls, all for having only 1–2 speed pairs, plus three 3rd-gear pulls from 2026-09-16.

The single accepted 5th-gear pull (`20260917_121649@105s`) reaches only 2750 rpm. So `gear5_torque_preservation = {2750: included, 3000–4000: HOLD}`, and `gear5_note` makes a 5th-gear WOT 2750→4000 pull a required empirical gate before promotion.

## 2. Air/lambda robustness per pull

For each rpm bin the JSON now reports:
- air median, P10, min and n over all accepted pulls (VCDS + phone);
- the per-pull P95 that defines the gate (`burned_p95_defined_by`);
- predicted lambda for every individual pull (`predicted_lambda_per_pull`), with `q_basis` = logged q for VCDS pulls, or the gear-4 VCDS median for phone pulls, which have no logged q;
- `min_predicted_lambda` with the pull and gear that define it.

The torque P95 stays the primary constraint. The lambda floor uses median air, which gives the higher and therefore more torque-conservative fuel floor.

| rpm | gate (mg) | delivered new | air median / P10 / min | min predicted λ (pull, gear) |
|---|---|---|---|---|
| 2750 | 64.2 | 64.2 (unchanged) | 947 / 938 / 923 | 0.99 (20260917@105s, 5th) |
| 3000 | 66.2 | 66.2 (unchanged) | 904 / 888 / 873 | 0.91 (VCDS day16 11:54:46, 4th) |
| 3250 | 62.4 | 62.4 (unchanged) | 862 / 820 / 758 | 0.84 (20260917@322s, 4th) |
| 3500 | 54.5 | 58.7 | 845 / 835 / 832 | 0.98 (VCDS day16 11:54:46, 4th) |
| 3750 | 49.5 | 54.0 | 826 / 799 / 785 | 1.00 (VCDS day16 11:54:12, 3rd) |
| 4000 | 48.7 | 49.5 | 812 / 793 / 785 | 1.09 (VCDS day16 11:54:12, 3rd) |

The λ < 1 values at 2750–3250 come from fuel that vNext6.1 does not change: the gate equals current delivery there. They describe the current calibration on those pulls, not an effect of this candidate. The 3250 minimum comes from one 4th-gear pull with unusually low MAF (758 mg), which is itself a reason not to reduce fuel there.

New 2026-09-17 4th-gear pulls raised P95 at 3250 (68.5) and 3500 (54.5, previously 53.2). The 3750 gate is now set by λ 1.15 at median air (49.5). Together these moved the 4000 node from 48.80 to **49.55 mg**.

## 3. Formula wording

Status, docstring and docs now state the exact rule: `delivered_new >= min(delivered_current, max(P95_burned, lambda115_fuel))`.

## Regenerated vNext6.1

- sha256 `f9d05f8318ca587da63c85c5d9d76e6131b5024ec49c2ffb0599403ea09a0248` (replaces `4f7d9ff9…`)
- Byte diff against the flashed file, recomputed from disk: `0x1D661A` 6780→6355 (3000 rpm, 63.55 mg), `0x1D6632` 6780→4955 (4000 rpm, 49.55 mg), and the checksum words `0x1BFFFC..FF` and `0x1FDFFC..FF`. Both blocks sum to `0xD01FE500`.
- Tests: 64/64. The scope is unchanged: no edits ≤ 2500 rpm, to the 1800 hPa column, at 5355, to SOI, to Stage 0, or to boost/N75.
