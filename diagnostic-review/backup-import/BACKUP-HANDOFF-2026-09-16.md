# Complete project backup handoff — 2026-09-16

> Purpose: make the uploaded local project backup auditable and usable by Claude/other agents without overwriting newer work on `main`.

## Source archive

- Uploaded archive: `golf5_complete_project_backup.zip`
- SHA-256: `f1f072e965a4ebbbee38bbaff21c6d68341b91b01576419a089d847c31167a59`
- Extracted file count: `3159`

| project | files | bytes |
|---|---:|---:|
| `brain_artifacts` | 427 | 22456717 |
| `golf5` | 690 | 261095235 |
| `golf5-android-flasher` | 1798 | 33604115 |
| `vcds-android` | 244 | 26317086 |

## Import policy

- `golf5/` is the calibration project relevant to this repository.
- Existing `main` files are authoritative when they are newer than the backup. The backup must **not** blindly overwrite Claude outputs.
- Backup provenance is captured in `BACKUP-2026-09-16-MANIFEST.csv` with raw SHA-256 for all 690 `golf5` files.
- The Android app/flasher and `brain_artifacts` are listed above but are not mixed into this calibration repository.

## Verified identity checks against GitHub main

- `03G906021QJ_stage1_full_power_dpf_egr_off.bin`: raw bytes match GitHub; SHA-256 `d8296554b0342a9a4eb1ca0af0a17ccbbecc066349907448213ea6179ad2bfe0`.
- A2L/HEX/S19 appear larger in the Windows backup only because of CRLF line endings. After `CRLF -> LF`, their Git blob SHA values exactly match `main`:
  - A2L: `2a78a6c2ed3ba7ec9a009a45ce38e74cdd4b186b`
  - HEX: `5c04c0a21baccabede7c5ac9985a2f522ae365aa`
  - S19: `bbc256dbd5e6e36a34796e87b833116ec26854d1`
- Therefore do not create duplicate “backup A2L” solely because raw byte counts differ on Windows.

## Ground-truth paths already visible to Claude on main

- Active BIN: `03G906021QJ_stage1_full_power_dpf_egr_off.bin`
- Exact A2L: `diagnostic-review/definitions/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.a2l`
- OEM/reference HEX and S19 in the same definitions directory
- Current/old firmware evidence under `diagnostic-review/`, `gdrive_downloads/` and root BINs
- VCDS and phone logs under `logs/`
- Project conversation history under `conversation_history/`
- Claude math-engine state under `diagnostic-review/math-engine/`
- Shared research note: `docs/knowledge/transient-torque-asddc-dynamic-smoke-2026-09-16.md`

## Agent rules

1. Use the manifest to resolve provenance before assuming two similarly named files are identical.
2. Prefer SHA-256 identity over filename identity.
3. Do not replace newer `main` analysis with older backup text.
4. BIN modifications remain prohibited unless backed by calculation, checksum/readback plan and validation criteria.
5. Treat the uploaded backup as a **source snapshot**, not as a command to roll the repository back.

## High-value firmware / definition artifacts in backup

| path | bytes | SHA-256 |
|---|---:|---|
| `03G906021QJ_ideal_stage1_dpf_egr_off.bin` | 2097152 | `55c80596de4d8b622d0c1227e03e30e4b99ef22d3b9a3e0078ce6b5f0d84e3b7` |
| `03G906021QJ_stage1_full_power_dpf_egr_off.bin` | 2097152 | `d8296554b0342a9a4eb1ca0af0a17ccbbecc066349907448213ea6179ad2bfe0` |
| `03G906021QJ_stage1_refined_CS_OK.bin` | 2097152 | `a517affa3f89bf2ba188a84c6b6810b20f61fa297de4917e99cba5f1f18e2b44` |
| `03G906021QJ_stage1_refined_dpf_egr_off.bin` | 2097152 | `48c8f368b5ce26cd920e3e2dcc7be20762d0ab69684504843f2e23ebb0c56fe8` |
| `diagnostic-review/deep-audit/03G906021QJ_stage1-preserving-dpf-egr-off.review.bin` | 2097152 | `29b5f585c78973046a9cf2161c86eda9f1541d8066e481c93ce4eda746c2e492` |
| `diagnostic-review/deep-audit/03G906021QJ_stage1-preserving-restore-duration.review.bin` | 2097152 | `c41a1b3eb0b50d8944a0932f2cf0bb904548e0b416559c0232d5f9c17c086b81` |
| `diagnostic-review/definitions/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.a2l` | 12602543 (Windows CRLF source) | `04ab636a3f564031cfc9ed0a4178d5e1c3795e6f37e42236c71eda786c16050a` |
| `diagnostic-review/new-inputs/on/03G906021QJ.Bin` | 2097152 | `a1fc76a6ca961604999980733f89f13a77aa903af52b1ca43567be3dc76e5bc4` |
| `diagnostic-review/reference-from-hex.analysis-only.bin` | 2097152 | `cf891152a97fb63609b40fc590fd86f38b034119b516e936eb8c0173e2551d26` |
