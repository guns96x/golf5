# Thermal Protection & Component Safety (Bauteilschutz)

## Modeled Exhaust Gas Temperature (EGT)

The 1.9 TDI BLS uses an onboard thermodynamic model to estimate pre-turbine exhaust gas temperature.

- **Limit Threshold**: Pre-turbine EGT must not exceed **805°C continuous** on the BorgWarner BV39 turbocharger.
- **Protection Map**: `EngPrt_facTempPreTrbn_MAP` progressively derates torque when temperature exceeds safe thresholds.
- **Status in Current Vehicle**: Restored and active in `stage1_full_power_dpf_egr_off.bin`.
