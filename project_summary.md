# Project Summary: GOLF5 (1.9 TDI BLS / EDC16U34)
**Last Updated**: 2026-09-14 | **Status**: Active Tuning & Diagnostic Verification

## 1. Hardware & Configuration
- **Vehicle**: Volkswagen Golf Mk5
- **Engine**: 1.9 TDI PD (BLS), 77 kW / 105 HP stock
- **ECU**: Bosch EDC16U34, VAG P/N `03G906021QJ`, Software `1037387342` (also dataset `1037391847P447HAXN`). (References also BKC EDC16U1).
- **Turbocharger**: KKK / BorgWarner BV39 (`03G253014M`) with vacuum actuator controlled via N75 solenoid valve.
- **Exhaust & Aftertreatment**: DPF physically removed, catalytic converter retained; EGR valve physically blanked off.
- **Flashing Interface**: MPPS v18 clone (VID `1C43`, PID `0500`, Silicon Labs C8051F320 controller).

## 2. Verified Invariants & Ground Truth (🟢)
- **N75 Control Logic**: Under boost, normal duty cycle is 40% to 75%. In Bosch EDC16U34, duty cycle is directly proportional to actuator vacuum: ~80% = max vacuum (VNT vanes closed, max spool); ~28.5% = atmospheric pressure (vanes open). Continuous duty cycle > 85% signals sticky VNT vanes or severe vacuum/boost leak.
- **Smoke Limiter**: Factory map is 16x16 MAF-based (Airflow mg/stroke vs Engine RPM).
- **Golden Calibration Binary**: `03G906021QJ_stage1_refined_CS_OK.bin` verified with valid Bosch checksums and RSA signature.
- **DPF OFF Calibration**: Matrix `PFlt_numEngPOp1_CA` (`0x1ECA6E`, engine states during regeneration) is zeroed.
- **Coolant Temp Error Class**: `DSM_ClaDfp_CTSCD_C` (`0x1CF2F6`) changed `11 -> 0` in previous OFF file; reverting to factory reference `0x0B` is verified for review.
- **Thermal Protection**: `EngPrt_facTempPreTrbn_MAP` in previous OFF had 12 values weakened up to 4.05% at 805–820 °C pre-turbine; 20-byte candidate restores factory thermal factor.
- **MPPS USB Transport**: Bulk IN endpoint `0x81` returns 2-byte FTDI status-only packets (`01 10` or `01 60`) when no payload is queued. The host must submit read requests >= 64 bytes and discard the 2-byte status header before parsing payload.

## 3. Current Project Status
- Golden Stage 1 calibration file (`03G906021QJ_stage1_refined_CS_OK.bin`) is ready and checksum-verified.
- Live WOT logging on 4th gear using `vcds-android` is prepared to diagnose intermittent turbo lag and cold-start smoke symptoms.

## 4. Key Decisions Made
- **Retain Stage 1 Calibration**: Rejected blind reduction to 310–330 Nm or 229-byte duration rollback without verified car telemetry.
- **Do Not Modify N75 Blindly**: Strictly forbidden to change N75 pre-control maps without analyzing WOT CSV logs.
- **Strict Project Isolation**: Decoupled ECU calibration (`golf5`), diagnostic logging (`vcds-android`), and hardware flashing (`golf5-android-flasher`).

## 5. Active Working Hypotheses (🟡)
- Turbo lag between 1500–2000 RPM is caused by a microcrack in the integrated vacuum reservoir inside the valve cover (known VAG BLS/BXE issue) or low vacuum supply (< 0.6 bar at N75 inlet), preventing quick VNT vane closure.
- Intermittent white smoke at cold start / tip-in after hard driving is provoked by thermal degradation or unsuppressed regeneration pathways in software.

## 6. Discarded Hypotheses (🔴 Do Not Repeat / Anti-Memory)
- **Discarded: Reducing N75 pre-control map `PCR_rBPCtlBas_MAP` (`0x1E9FD0`) by −0.40% (Astra proposal).** Reduces vacuum, opens VNT vanes, and worsens turbo lag.
- **Discarded: Switching to MAP-based smoke limiter without full linearization table.** Caused severe black smoke burst at 1800 RPM.
- **Discarded: Increasing N75 duty cycle to 90% at 1500 RPM.** Caused aggressive overboost spike (> 2.5 bar) and limp mode error 17965.
- **Discarded: Diagnosing faulty thermostat as primary root cause.** Revoked; symptoms trigger after heating/aggressive driving, not stuck open thermostat.
- **Discarded: Claiming rev limiter was altered at `0x1D4922` / `0x1D4988`.** Verified that actual table sizes are 6 and 2 points, and changes were outside active curves.
- **Discarded: Sending USB vendor request `0x92` to MPPS adapter.** This is FTDI EEPROM erase command and permanently wipes the clone adapter.
- **Discarded: Forcing emergency DPF regeneration.** High fire hazard with physically removed DPF.

## 7. Known Problems & Issues
- Turbo lag / flat acceleration between 1500 and 2000 RPM on 4th gear.
- Intermittent white smoke and raw exhaust odor on cold start and after aggressive driving.

## 8. Completed Work
- Reverse-engineered MPPS v18 USB communication and documented protocol in `mpps-usb-protocol-analysis-2026-09-11.md`.
- Static A2L analysis across factory reference, Stage 1 ON, and DPF/EGR OFF binaries.
- Produced verified flash candidate `03G906021QJ_stage1_refined_CS_OK.bin`.

## 9. Next Steps
- Connect `vcds-android` via USB-OTG and record 4th gear WOT log (1400–3500+ RPM).
- Measure mechanical vacuum supply at N75 inlet and test valve cover reservoir integrity with a vacuum gauge.
- Inspect CSV log for `Boost_Specified` vs `Boost_Actual`, `N75_Duty_pct`, and `Smoke_Limit_IQ_mg`.
