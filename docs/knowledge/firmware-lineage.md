# Firmware Lineage & Version Control

## Baseline Firmware Images

1. **Factory OEM Baseline**:
   - **File**: `diagnostic-review/reference-from-hex.analysis-only.bin`
   - **Origin**: Extracted from official factory HEX dataset `03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.HEX`
   - **Size**: 2,097,152 bytes (2.0 MB)
   - **Stock High-Load Boost Target**: **2050 mbar**
   - **Status**: Pure stock calibration reference.

2. **Stage 1 Full Power (CURRENTLY FLASHED IN VEHICLE)**:
   - **File**: `03G906021QJ_stage1_full_power_dpf_egr_off.bin`
   - **SHA-256**: `d8296554b0342a9a4eb1ca0af0a17ccbbecc066349907448213ea6179ad2bfe0`
   - **High-Load Boost Request**: **2214 mbar**
   - **Features**: PoI2 zeroed (no unburned fuel smoke), CTSCD restored to 0x0B (no 87°C derate), EGT protection active.
   - **Status**: Currently installed and running in the vehicle.

3. **Stage 1 Refined CS_OK (Candidate Build)**:
   - **File**: `03G906021QJ_stage1_refined_CS_OK.bin`
   - **SHA-256**: `a517affa3f89bf2ba188a84c6b6810b20f61fa297de4917e99cba5f1f18e2b44`
   - **High-Load Boost Request**: **2214 mbar**
   - **Features**: Adds `HS-250` hot start fix and Gear 5/6 cruise SOI (+0.703° CA); checksums verified.
   - **Status**: Static audit complete; NOT flash approved without logging plan.

4. **Stage 1 Ideal DPF & EGR OFF (REJECTED BUILD)**:
   - **File**: `03G906021QJ_ideal_stage1_dpf_egr_off.bin`
   - **Status**: **REJECTED**. Retained stock duration maps and drove too sluggishly.
