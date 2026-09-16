# Start of Injection (SOI) & Temperature Compensation

## Start of Injection (SOI) Overview

- **A2L Base Map**: `InjCrv_phiMI1Des_MAP`
- **Gear 5-6 Cruise Map**: `InjCrv_phiBasGear56_MAP` at `0x1DACF8` (16 × 14, RPM × mg/stroke)
- **Units**: Degrees Crank Angle Before Top Dead Center (°BTDC) with resolution 0.0234375° CA

## Eco Cruise Advance

In candidate build `stage1_refined_CS_OK`, cruise SOI in Gear 5/6 is advanced by exactly **+0.703125° CA** (30 LSBs) across 1750–2250 RPM and 15–25 mg/stroke to optimize combustion phasing with EGR closed.
