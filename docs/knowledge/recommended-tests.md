# Recommended Test Protocols for Vehicle Validation

## Test Protocol 1: High-Rate Boost Closed-Loop Run (MVB 011 Only)

- **Diagnostic Tool**: VCDS (VAG-COM)
- **Engine Control Module**: `01 - Engine`
- **Measurement Selection**: **Select Group 011 ONLY** (do not select Groups 003 or 008 simultaneously).
  - *Reason*: Selecting 1 group increases VCDS sample frequency from ~1.2 Hz to ~3.8–4.5 Hz, capturing the exact shape of the transient peak without alias error.
- **Channels**:
  - `011.1`: Engine Speed (RPM)
  - `011.2`: Boost Specified (mbar)
  - `011.3`: Boost Actual (mbar)
  - `011.4`: N75 Duty Cycle (%)
- **Driving Maneuver**: 3rd gear straight flat road, stabilize at 1400 RPM, floor accelerator pedal to 100% until 3800 RPM, lift off.

---

## Test Protocol 2: Fueling & Limiter Arbitration Run (MVB 008 Only)

- **Measurement Selection**: **Select Group 008 ONLY**.
- **Channels**:
  - `008.1`: Engine Speed (RPM)
  - `008.2`: Driver Wish IQ (mg/stroke)
  - `008.3`: Torque Limiter IQ (mg/stroke)
  - `008.4`: Smoke Limiter IQ (mg/stroke)
- **Driving Maneuver**: Identical 3rd gear WOT pull from 1400 to 3800 RPM.
