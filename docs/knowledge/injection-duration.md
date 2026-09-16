# Pumpe-Düse Injection Duration Maps

## Unit Injector Actuation Mechanics

In the 1.9 TDI BLS Pumpe-Düse system:
- High injection pressure (up to 2050 bar) is generated mechanically by the engine camshaft pressing each unit injector rocker arm.
- The ECU controls fuel delivery by energizing the fast-switching solenoid valve inside each injector.
- Duration is expressed in **Degrees of Crankshaft Angle (°CA)** required to deliver the desired fuel volume at a specific RPM and pressure.

## Duration Map Calibration Integrity

> [!CAUTION]
> **Do Not Falsify Duration Maps**:
> Common amateur tuning methods modify duration maps to inject more fuel without altering torque or IQ limiters (so-called "duration tricking").
> This breaks:
> 1. Real-time consumption calculation on the dashboard.
> 2. Onboard thermal protection models (which compute exhaust gas temperature from genuine IQ).
> 3. ESP/ASR torque coordination.
> 
> In this project, all duration maps remain strictly calibrated to genuine physical injector delivery curves.
