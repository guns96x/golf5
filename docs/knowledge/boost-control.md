# EDC16 Boost Pressure Control Architecture

## Boost Target Formation

In the Bosch EDC16U34 system for the 1.9 TDI BLS, the target manifold absolute pressure (MAP) is governed by the **PCR (Pressure Charge Regulation)** functional subsystem.

$$\text{Final Boost Target} = \min\Big(\text{PCR\_pBDesBas\_MAP}(\text{RPM}, \text{IQ}) + \Delta p_{\text{ambient}} + \Delta p_{\text{temp}}, \text{PCR\_pBDesMax\_CUR}(\text{RPM})\Big)$$

### 1. Base Boost Target Map (`PCR_pBDesBas_MAP`)
- **Stock Reference High-Load Request**: **2050 mbar** absolute.
- **Stage 1 Active Request**: **2214 mbar** absolute (104 values modified versus stock reference; verified by deep-audit).
- **Units**: mbar absolute.

> [!IMPORTANT]
> **Static Target vs Runtime Request**:
> - `calibration_map_high_load = 2214 mbar` is the static value in the calibration map.
> - In any specific vehicle run, `runtime_specified` may differ due to transient filtering, cold/hot temperature scaling, or atmospheric derating.
> - In the 16.09.2026 OBD pair log (`Turbo_Pair_20260916_112035.csv`), `runtime_specified` was **UNKNOWN** because that specific PID channel was not polled.

### 2. Atmospheric & Environmental Corrections
- Altitude compensation (`PCR_pBDesAtm_MAP`): Derates boost request as ambient barometric pressure decreases below 1000 mbar to prevent turbocharger overspeed in thin air.
- Charge temperature compensation (`PCR_pBDesT_MAP`): Derates target if intake air temperature (IAT) exceeds calibrated thermal thresholds.
