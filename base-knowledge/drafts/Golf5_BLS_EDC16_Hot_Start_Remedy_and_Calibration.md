# Hot-Start Hesitation & Cranking Torque Architecture

## The Bosch EDC16 Hot Start Problem

A widespread issue in VAG 1.9 TDI Pumpe-Düse engines running EDC16 is prolonged cranking when the engine is at normal operating temperature (75–90°C coolant).

### Root Cause in Calibration (Ground Truth)

The primary cranking torque map is **`StSys_trqStrtBas_MAP`**:
- **Address in Flash**: `0x1F070C`
- **Actual Dimensions**: **9 × 9** (RPM × Coolant °C)
- **Static Status**: `STATICALLY_MATCHED` (A2L line 268931)

At 250 RPM, `StSys_trqStrtBas_MAP` delivers **0.0 Nm** across 40°C, 60°C, 80°C, and 100°C. Both base and terminal-50 maps match completely at 280 RPM (108–125 Nm).
As the starter motor and battery age, hot cranking RPM plateaus between 240 and 275 RPM, causing extended dry cranking without fuel delivery.

### The Verified `HS-250` Patch

| RPM | Coolant | Current Value | `HS-250` Patch | Flash Offset | Big-Endian S16 Byte Diff |
|---:|---:|---:|---:|---:|---|
| 250 | 39.96°C | 0 Nm | **125 Nm** | `0x1F0762` | `0000 → 04E2` |
| 250 | 59.96°C | 0 Nm | **112 Nm** | `0x1F0764` | `0000 → 0460` |
| 250 | 79.96°C | 0 Nm | **108 Nm** | `0x1F0766` | `0000 → 0438` |
| 250 | 99.96°C | 0 Nm | **108 Nm** | `0x1F0768` | `0000 → 0438` |

> [!NOTE]
> **Static Identification vs Vehicle Validation**:
> - `TASK-HOTSTART-MAP-IDENTITY`: **COMPLETED** (offsets, dimensions, and values statically verified).
> - `TASK-HOTSTART-HS250-VALIDATION`: **PENDING** (requires in-vehicle warm restart log to validate starting time without shudder).
