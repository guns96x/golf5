# Research Changelog & Bootstrap History

## Version 1.2.0 — 2026-09-16 (Epistemic Hardening Pass)
- **Schema & Database Hardening**:
  - `claims` table: Default project identifiers changed to `NULL` to prevent generic Tier A/B literature bleeding into vehicle-specific claims.
  - `map_definitions` table: Replaced `is_verified_active` with explicit `static_match_proven` and `runtime_active_proven`.
- **Map Catalog Status**: Changed catalog status to `STATICALLY_MATCHED (A2L)` with explicit disclaimer that static agreement does not prove runtime duplicate table selection.
- **Telemetry Disentanglement**:
  - Separated 14.09.2026 legacy logs from 16.09.2026 telemetry.
  - Recorded: `calibration_map_high_load = 2214 mbar`, `runtime_specified = UNKNOWN`, `runtime_actual_peak = 2310–2330 mbar`, `overshoot_vs_runtime_request = UNKNOWN`.
- **Task Splitting**: Split hot-start into `TASK-HOTSTART-MAP-IDENTITY` (completed) and `TASK-HOTSTART-HS250-VALIDATION` (pending).
- **Hardware Corrections**: Corrected MPC562 internal CALRAM specification to 32 KB per NXP datasheet.
