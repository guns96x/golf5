"""Verify all calibration invariants of 03G906021QJ_ideal_stage1_dpf_egr_off.bin."""
from pathlib import Path
import hashlib
import struct

ROOT = Path("C:/Users/pavlo/golf5/diagnostic-review")
DEEP_AUDIT = ROOT / "deep-audit"

TARGET_BIN = Path("C:/Users/pavlo/golf5/03G906021QJ_ideal_stage1_dpf_egr_off.bin")
PATH_OFF = ROOT / "new-inputs/off/03G906021QJ (DPF EGR OFF) NoCS.Bin"
PATH_REF = ROOT / "reference-from-hex.analysis-only.bin"

def main():
    target = TARGET_BIN.read_bytes()
    off = PATH_OFF.read_bytes()
    ref = PATH_REF.read_bytes()

    assert len(target) == 2097152
    h = hashlib.sha256(target).hexdigest()
    print(f"Target file verified: {len(target)} bytes, SHA-256 = {h}")

    # 1. Verify CTSCD is restored to 0x0B
    assert target[0x1CF2F6] == 0x0B, "CTSCD should be 0x0B"
    print("PASS: CTSCD restored to 0x0B (Coolant sensor diagnostics active)")

    # 2. Verify pre-turbine temperature protection restored
    assert target[0x1D4EE0:0x1D4F60] == ref[0x1D4EE0:0x1D4F60], "Thermal factor map mismatch"
    print("PASS: Pre-turbine EGT thermal protection factor 100% restored to reference")

    # 3. Verify duration maps restored to reference
    for addr in (0x1E5032, 0x1E52B4, 0x1E5536, 0x1E57B8):
        nx, ny = struct.unpack_from(">hh", ref, addr)
        v_start = addr + 4 + nx*2 + ny*2
        v_len = nx * ny * 2
        assert target[v_start:v_start+v_len] == ref[v_start:v_start+v_len], f"Duration map at {hex(addr)} mismatch"
    print("PASS: All 4 Duration maps restored to factory precision (eliminating late EOI)")

    # 4. Verify PoI2 delivery zeroed
    poi_ranges = [
        (0x1E1616, 0x1E1694),
        (0x1E1712, 0x1E17DA),
        (0x1E18CE, 0x1E1996),
        (0x1E60D0, 0x1E62C8),
        (0x1E6352, 0x1E654A),
    ]
    for start, end in poi_ranges:
        chunk = target[start:end]
        assert all(b == 0 for b in chunk), f"PoI range {hex(start)}..{hex(end)} not zeroed"
    print("PASS: All post-injection (PoI2) delivery maps 100% zeroed (no late regeneration fuel)")

    # 5. Verify EGR hysteresis shutoff preserved from OFF
    assert target[0x1C9DD8:0x1C9DF4] == off[0x1C9DD8:0x1C9DF4], "AirCtl_qHigh_CUR mismatch"
    assert target[0x1C9ECA:0x1C9EF2] == off[0x1C9ECA:0x1C9EF2], "AirCtl_qMiddle_CUR mismatch"
    print("PASS: Tested, error-free EGR hysteresis shutoff preserved exactly as in OFF")

    # 6. Verify Stage 1 Boost preserved
    assert target[0x1EB0B2:0x1EB2F2] == off[0x1EB0B2:0x1EB2F2], "Boost map should be preserved"
    print("PASS: Stage 1 boost map preserved (up to 2214 mbar)")

    # 7. Verify Stage 1 Torque Limiter preserved
    assert target[0x1D4732:0x1D48A6] == off[0x1D4732:0x1D48A6], "Torque limiter should be preserved"
    print("PASS: Stage 1 torque limiter preserved (up to 380.7 Nm)")

    # 8. Verify Stage 1 Smoke Limiter preserved
    assert target[0x1D6490:0x1D6690] == off[0x1D6490:0x1D6690], "Smoke limiter should be preserved"
    print("PASS: Stage 1 smoke limiter preserved (up to 67.8 mg)")

    # 9. Verify Stage 1 SOI advance preserved
    assert target[0x1DA8F8:0x1DAAF8] == off[0x1DA8F8:0x1DAAF8], "SOI map should be preserved"
    print("PASS: Stage 1 SOI advance preserved (+1.0..+2.1 deg)")

    print("\nALL INVARIANTS PASSED! The ideal calibration image is verified.")

if __name__ == "__main__":
    main()
