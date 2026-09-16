# Telemetry & Diagnostic Log Index

## Log Inventory

| Log File | Format | Sampling Rate | Channels Logged | Primary Objective |
|---|---|---|---|---|
| `VCDS_WOT_Log_20260914_114936.csv` | VCDS CSV | ~1.2 Hz (multi-group) | RPM, Specified Boost, Actual Boost, N75 Duty, Driver Wish, Torque Limit, Smoke Limit, MAF | Multi-group log capturing 2310–2320 mbar boost peak vs 2214 mbar request |
| `Turbo_Fast_Log_20260914_210903.csv` | High-Rate OBD CSV | ~4.2 Hz | RPM, MAP absolute, Baro, Boost gauge, MAF, Speed, Engine Load | High-frequency MAP rise time and transient oscillation analysis |
