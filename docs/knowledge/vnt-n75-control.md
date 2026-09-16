# VNT / N75 Actuator Mechanics & Pre-Control

## Turbocharger Specification

- **Turbocharger Model**: BorgWarner / KKK BV39
- **OEM Part Reference**: `5439 988 0072` / `03G253014M`
- **Type**: Variable Nozzle Turbine (VNT) with vacuum actuator and N75 electro-pneumatic solenoid.

## Actuator Duty Cycle Polarity in EDC16U34

> [!IMPORTANT]
> **Polarity Definition for EDC16U34**:
> - **Higher N75 Duty % (e.g., 80%)**: Vacuum solenoid applies higher vacuum to the actuator capsule. The VNT vanes move to the **closed position** (minimum nozzle area). This forces exhaust gas through narrow guide vanes at maximum velocity onto the turbine wheel, producing **maximum turbine drive and rapid boost rise**.
> - **Lower N75 Duty % (e.g., 30–45%)**: Solenoid vents vacuum to atmosphere. Actuator spring opens the vanes (maximum nozzle area). Exhaust velocity drops, bypassing energy around the wheel to **dump turbine drive and reduce boost**.

---

## Pre-Control Map (`PCR_rBPCtlBas_MAP`)

- **A2L Symbol**: `PCR_rBPCtlBas_MAP`
- **Description**: *Basissteuerkennfeld für Ladedruck* (Base control map for charge pressure)
- **Offset**: `0x1E9FD0`
- **Dimensions**: 16 × 16
- **Axes**: Engine Speed (RPM) × Injected Quantity (mg/stroke)

### The Overboost Mechanism Post-EGR Delete

When EGR is active in stock software, a substantial fraction of exhaust gas (15–35%) recirculates into the intake manifold before the turbine.
When **EGR is turned OFF (closed 100%)**:
1. **100% of total exhaust mass flow** is directed across the turbine wheel during spool-up.
2. If `PCR_rBPCtlBas_MAP` retains stock pre-control values (designed for reduced gas flow), the vanes are held too closed for the increased mass flow.
3. The turbine over-accelerates rapidly during 1900–2300 RPM spool-up.
4. Manifold pressure shoots up to **2310–2330 mbar** before the PID integral term can react, back off N75 duty, and stabilize boost.

**Remedy**: Relax `PCR_rBPCtlBas_MAP` by 3–6% in the spool-up region (1800–2400 RPM, 35–55 mg IQ).
