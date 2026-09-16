# Firmware Lineage & Version Control

## Baseline Firmware Images

1. **Factory OEM Baseline**:
   - **File**: `diagnostic-review/reference-from-hex.analysis-only.bin`
   - **Origin**: Extracted from official factory HEX dataset `03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.HEX`
   - **Size**: 2,097,152 bytes (2.0 MB)
   - **SHA-256**: `b3f36070a7b4582f3efce39ff6d46487e45218d6e3cbebe4fbe8cbdbdffca577`
   - **Integrity**: Pure stock calibration reference.

2. **Stage 1 Refined CS_OK**:
   - **File**: `03G906021QJ_stage1_refined_CS_OK.bin`
   - **Modifications**: Optimized torque request, boost ceiling raised to 2350 mbar, smoke limits aligned, checksum verified via EVC OLS242.
   - **Status**: Flash-ready.

3. **Stage 1 Ideal DPF & EGR OFF**:
   - **File**: `03G906021QJ_ideal_stage1_dpf_egr_off.bin`
   - **Modifications**: Stage 1 calibration combined with DPF deactivation switch and EGR zero hysteresis curve.
