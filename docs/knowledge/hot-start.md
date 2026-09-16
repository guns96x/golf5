# Hot-Start Hesitation & Cranking Torque Architecture

## The Bosch EDC16 Hot Start Problem

A widespread issue in VAG 1.9 TDI Pumpe-Düse engines running EDC16 is prolonged cranking when the engine is at normal operating temperature (75–90°C coolant).

### Root Cause in Calibration (Ground Truth)

The primary cranking torque map is **`StSys_trqStrtBas_MAP`**:
- **Address in Flash**: `0x1F070C`
- **Actual Dimensions**: **9 × 9** (RPM × Coolant °C)
- **RPM Nodes**: `0, 200, 250, 280, 450, 600, 900, 1550, 1600`
- **Coolant Nodes**: Approximately `−24, −18, −10, 0, 20, 40, 60, 80, 100°C`

At 250 RPM, `StSys_trqStrtBas_MAP` delivers **0.0 Nm** across 40°C, 60°C, 80°C, and 100°C. Both base and terminal-50 maps match completely at 280 RPM (108–125 Nm).
As the starter motor and battery age, hot cranking RPM plateaus between 240 and 275 RPM, causing extended dry cranking without fuel delivery.

### The Verified `HS-250` Patch

> [!IMPORTANT]
> **Do Not Perform a Bulk Copy**:
> A bulk copy from `StSys_trqStrt_MAP` alters 14 cells down to 0 RPM, potentially defeating deliberate cranking protection.
> Instead, populate ONLY the 4 missing cells at 250 RPM:

| RPM | Coolant | Current Value | `HS-250` Patch | Flash Offset | Big-Endian S16 Byte Diff |
|---:|---:|---:|---:|---:|---|
| 250 | 39.96°C | 0 Nm | **125 Nm** | `0x1F0762` | `0000 → 04E2` |
| 250 | 59.96°C | 0 Nm | **112 Nm** | `0x1F0764` | `0000 → 0460` |
| 250 | 79.96°C | 0 Nm | **108 Nm** | `0x1F0766` | `0000 → 0438` |
| 250 | 99.96°C | 0 Nm | **108 Nm** | `0x1F0768` | `0000 → 0438` |

This exact patch is implemented in `03G906021QJ_stage1_refined_CS_OK.bin`.
