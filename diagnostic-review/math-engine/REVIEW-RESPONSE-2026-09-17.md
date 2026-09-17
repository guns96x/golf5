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

Byte diff against `03G906021QJ_stage1_full_power_dpf_egr_off.bin` (independently recomputed from disk):
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
