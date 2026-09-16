# Active A2L Map Catalog — SW 1037391847

Curated list of verified active calibration maps in Bosch EDC16U34 SW `1037391847`:

| Map Name | Hex Offset | Dimensions | Description | Conversion / Unit | Verified Status |
|---|---|---|---|---|---|
| `PCR_pBDesBas_MAP` | `0x1E9A40` | 16 × 16 | Base Boost Target | mbar absolute | **ACTIVE (Stage 1)** |
| `PCR_rBPCtlBas_MAP` | `0x1E9FD0` | 16 × 16 | N75 Pre-Control / Feed-Forward | % Duty Cycle | **ACTIVE (Investigating)** |
| `PCR_pBDesAtm_MAP` | `0x1E9630` | 8 × 8 | Atmospheric Boost Derating | mbar absolute | **ACTIVE** |
| `FlMng_qPresSmoke_MAP`| `0x1E4280` | 16 × 16 | MAP-Based Smoke Limiter | mg/stroke fuel | **ACTIVE (Stage 1)** |
| `TrqLim_trqEng_MAP` | `0x1D9C90` | 21 × 3 | Main Engine Torque Limiter | Nm indicated | **ACTIVE (Stage 1)** |
| `DrvDem_tq_MAP` | `0x1D2A40` | 12 × 16 | Driver Wish Torque Request | Nm requested | **ACTIVE (Stage 1)** |
| `EngM_qStart_MAP` | `0x1E2D60` | 10 × 10 | Cranking Start Fuel Quantity | mg/stroke fuel | **ACTIVE (Hot Start)** |
| `AirCtl_qHigh_CUR` | `0x1C9DAA` | 20 × 1 | EGR Hysteresis High Boundary | mg/stroke | **ACTIVE (EGR OFF)** |
| `AirCtl_qMiddle_CUR`| `0x1C9EA0` | 20 × 1 | EGR Hysteresis Middle Boundary | mg/stroke | **ACTIVE (EGR OFF)** |
