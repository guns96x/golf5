# Active A2L Map Catalog — SW 1037391847

Curated list of verified active calibration maps in Bosch EDC16U34 SW `1037391847` based on `calibration-enhancements-deep-audit-2026-09-11.md`:

| Map Name | Flash Address | Actual Dimensions | Axes | Unit / Resolution | Verified Role & Status |
|---|---|---|---|---|---|
| `PCR_rBPCtlBas_MAP` | `0x1E9FD0` | **16 × 13** | RPM × mg/stroke | 0.01 % | N75 Pre-control base map; 100% stock reference; polarity unproven |
| `PCR_pBDesBas_MAP` | `0x1EB0B2` | **16 × 10** | RPM × mg/stroke | mbar abs | Boost target; Stage 1 high-load request = **2214 mbar** |
| `FlMng_qPresSmoke_MAP` | `0x1D6490` | **16 × 12** | RPM × corrected hPa | 0.01 mg/stroke | MAP-based smoke limiter; 1800/2000 hPa rows modified +13% |
| `StSys_trqStrtBas_MAP` | `0x1F070C` | **9 × 9** | RPM × coolant °C | 0.1 Nm | Base cranking torque; targets 250 RPM cells in `HS-250` patch |
| `StSys_trqStrt_MAP` | `0x1F07EA` | **9 × 9** | RPM × coolant °C | 0.1 Nm | Terminal-50 cranking torque; reference for HS-250 values |
| `InjCrv_phiBasGear56_MAP` | `0x1DACF8` | **16 × 14** | RPM × mg/stroke | 0.0234375° CA | Cruise SOI 5-6 gear; +0.703° CA in candidate build |
| `TrqLim_trqEng_MAP` | `0x1D9C90` | 21 × 3 | RPM × atmospheric | Nm indicated | Main torque limiter bounding indicated engine torque |
| `DrvDem_tq_MAP` | `0x1D2A40` | 12 × 16 | RPM × pedal % | Nm requested | Driver wish torque request |
| `AirCtl_qHigh_CUR` | `0x1C9DAA` | 20 × 1 | Temp | mg/stroke | EGR hysteresis high threshold (zeroed for EGR OFF) |
| `AirCtl_qMiddle_CUR` | `0x1C9EA0` | 20 × 1 | Temp | mg/stroke | EGR hysteresis middle threshold (zeroed for EGR OFF) |
