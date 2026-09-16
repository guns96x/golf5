# Smoke Limiter Strategy: MAP-Based vs MAF-Based

## BLS Engine OEM Architecture

In factory 1.9 TDI BLS configurations equipped with DPF, Bosch utilizes a **MAP-based (manifold pressure) smoke limitation system** as the primary active smoke limiter:

- **A2L Symbol**: `FlMng_qPresSmoke_MAP`
- **Description**: *Rauchbegrenzungskennfeld abhängig vom Ladedruck* (Smoke limitation map dependent on charge pressure)
- **Offset in SW 1037391847**: `0x1E4280`
- **Axes**: Engine Speed (RPM) × Manifold Absolute Pressure (mbar)
- **Output**: Maximum allowable injected fuel quantity (mg/stroke)

## Comparison with MAF-Based Strategy (BKC / BXE)

| Characteristic | BLS (with DPF) | BKC / BXE (Euro 3/4 non-DPF) |
|---|---|---|
| Primary Sensor | MAP (Intake Manifold Pressure Sensor G31) | MAF (Mass Air Flow Sensor G70) |
| A2L Map Name | `FlMng_qPresSmoke_MAP` | `FlMng_qAirSmoke_MAP` |
| Fast Response | Instantaneous manifold pressure measurement | Slight sensor film thermal delay |
| Air Leak Impact | Boost leak can cause over-fueling if MAP reads high | Boost leak causes safe fuel derating |
