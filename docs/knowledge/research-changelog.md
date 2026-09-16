# Research Changelog & Bootstrap History

## Version 1.1.0 — 2026-09-16 (Ground-Truth Alignment Pass)
- **Addresses & Dimensions Aligned with Deep-Audit**:
  - `PCR_rBPCtlBas_MAP`: corrected dimensions to **16×13** at `0x1E9FD0`.
  - `FlMng_qPresSmoke_MAP`: corrected address to **`0x1D6490`** and dimensions to **16×12** (RPM × corrected pressure hPa).
  - `StSys_trqStrtBas_MAP`: confirmed address at **`0x1F070C`** (9×9) and exact `HS-250` cells at `0x1F0762–0x1F0768`.
- **Target Boost Calibration**: Corrected high-load Stage 1 target from draft 2350 mbar to verified **2214 mbar** (stock reference: 2050 mbar).
- **Epistemic Status Sanitization**: Downgraded unverified assertions (overboost root cause, N75 numerical duty direction) from verified to `raw` / `hypothesis`.
- **Firmware Lineage Correction**: Explicitly noted that `stage1_full_power` is active in car, `stage1_refined_CS_OK` is candidate build, and `ideal_stage1` was rejected as sluggish.
- **Database Synchronization**: Re-seeded and re-indexed `knowledge/edc16_knowledge.db` with ground-truth records.
