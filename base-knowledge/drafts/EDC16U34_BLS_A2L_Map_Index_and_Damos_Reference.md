# Statically Matched A2L Map Catalog — SW 1037391847

> [!IMPORTANT]
> **Static Match vs Runtime Execution**:
> Agreement between A2L symbol names, addresses, and dimensions proves **static structure**, but does **NOT** prove which duplicate or variant map bank actively executes at runtime in the vehicle.
> All maps below carry `static_match_proven = true` and `runtime_active_proven = false` until runtime component logging demonstrates execution.

| Map Name | Flash Address | Actual Dimensions | Axes | Unit / Resolution | Match Status | Runtime Active |
|---|---|---|---|---|---|:---:|
| `PCR_rBPCtlBas_MAP` | `0x1E9FD0` | **16 × 13** | RPM × mg/stroke | 0.01 % | `STATICALLY_MATCHED` | `unproven` |
| `PCR_pBDesBas_MAP` | `0x1EB0B2` | **16 × 10** | RPM × mg/stroke | mbar abs | `STATICALLY_MATCHED` | `unproven` |
| `FlMng_qPresSmoke_MAP` | `0x1D6490` | **16 × 12** | RPM × corrected hPa | 0.01 mg/stroke | `STATICALLY_MATCHED` | `unproven` |
| `StSys_trqStrtBas_MAP` | `0x1F070C` | **9 × 9** | RPM × coolant °C | 0.1 Nm | `STATICALLY_MATCHED` | `unproven` |
| `StSys_trqStrt_MAP` | `0x1F07EA` | **9 × 9** | RPM × coolant °C | 0.1 Nm | `STATICALLY_MATCHED` | `unproven` |
| `InjCrv_phiBasGear56_MAP` | `0x1DACF8` | **16 × 14** | RPM × mg/stroke | 0.0234375° CA | `STATICALLY_MATCHED` | `unproven` |
| `TrqLim_trqEng_MAP` | `0x1D9C90` | 21 × 3 | RPM × atmospheric | Nm indicated | `STATICALLY_MATCHED` | `unproven` |
| `DrvDem_tq_MAP` | `0x1D2A40` | 12 × 16 | RPM × pedal % | Nm requested | `STATICALLY_MATCHED` | `unproven` |
| `AirCtl_qHigh_CUR` | `0x1C9DAA` | 20 × 1 | Temp | mg/stroke | `STATICALLY_MATCHED` | `unproven` |
| `AirCtl_qMiddle_CUR` | `0x1C9EA0` | 20 × 1 | Temp | mg/stroke | `STATICALLY_MATCHED` | `unproven` |
