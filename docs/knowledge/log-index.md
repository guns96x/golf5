# Telemetry & Diagnostic Log Index

## Delineation of Log Datasets

Logs from 14.09.2026 and 16.09.2026 must be treated as **independent datasets** captured under different calibrations:

### 1. Active Telemetry Runs (16.09.2026) — Under `stage1_full_power`
- **File**: `logs/20260916/Turbo_Pair_20260916_112035.csv`
- **Firmware in Vehicle**: `stage1_full_power_dpf_egr_off.bin`
- **Channels Logged**: RPM, MAP absolute, Barometric pressure, Speed, Engine Load, MAF.
- **Observations**: Fast spool (1890 mbar at 1459 RPM, 2020 mbar at 1573 RPM); actual MAP plateau at **~2310–2330 mbar** across 1900–2600 RPM.
- **Limitation**: Synchronous requested boost was **NOT LOGGED** in this OBD pair stream (`runtime_specified = UNKNOWN`).

### 2. Legacy Diagnostic Runs (14.09.2026) — Under Old Garage Calibration
- **File**: `logs/VCDS_WOT_Log_20260914_114936.csv`
- **Firmware in Vehicle**: Old garage calibration (pre-repair: CTSCD bugged, PoI2 active).
- **Channels Logged**: Multi-group VCDS (~1.2 Hz) capturing RPM, Specified Boost, Actual Boost, N75 Duty, IQ channels.
- **Notes**: Demonstrates old calibration lag (-336 mbar deficit at 1400 RPM) and transient spikes under the defective baseline.
