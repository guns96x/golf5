# Smoke Limiter Strategy: MAP-Based Calibration

## Exact Definition in SW 1037391847

In factory 1.9 TDI BLS configurations equipped with DPF, Bosch utilizes a **MAP-based (manifold pressure) smoke limitation system** as the primary active smoke limiter:

- **A2L Symbol**: `FlMng_qPresSmoke_MAP` (line 462199 in A2L)
- **Description**: *Rauchbegrenzungskennfeld abhängig vom Ladedruck* (Smoke limitation map dependent on charge pressure)
- **Address in Flash**: `0x1D6490` (NOT `0x1E4280`!)
- **Actual Dimensions**: **16 × 12** (NOT 16×16!)
- **RPM Nodes (16)**: `700, 800, 900, 1000, 1100, 1400, 1500, 1600, 1700, 1800, 2000, 2250, 2500, 3000, 4000, 5355`
- **Pressure Nodes (12)**: Corrected pressure hPa (`FlMng_pIATCorr_mp`)
- **Resolution**: 0.01 mg/stroke

> [!IMPORTANT]
> **No 2750 RPM Node Exists**:
> The axis jumps directly from 2500 RPM to 3000 RPM. Any proposal to create a flat "2500–2750 plateau" must understand that 2750 RPM is calculated via linear interpolation between the 2500 and 3000 RPM columns.

## Status in Current Stage 1

- The 1800 and 2000 hPa rows are already modified by approximately +13% over stock reference.
- At 2500 RPM / 2000 hPa: 50.0 mg (ref) → **56.5 mg** (current).
- At 3000 RPM / 2000 hPa: 60.0 mg (ref) → **67.8 mg** (current).
- Deep-audit proposed micro-experiment `SMK-2500` would edit only offset `0x1D6602` (2500 RPM / 2000 hPa: 56.5 mg → 58.5 mg) conditionally after logging confirms it is the binding limiter.
