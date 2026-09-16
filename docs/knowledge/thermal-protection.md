# Thermal Protection & Component Safety (Bauteilschutz)

## Modeled Exhaust Gas Temperature (EGT)

The 1.9 TDI BLS is not fitted with a physical pre-turbine EGT thermocouple in all market revisions. Instead, EDC16 runs a complex real-time thermodynamic thermal model:

- **EGT Calculation**: Function of engine speed, injected quantity, start of injection (SOI), boost pressure, and intake air temperature.
- **Limit Threshold**: Pre-turbine EGT must not exceed **850°C continuous** or **880°C peak transient** on the BorgWarner BV39 turbocharger.
- **Thermal Limiter Map**: When modeled temperature exceeds threshold, the ECU progressive derates fuel injection quantity to cool the exhaust gas.
