# Hot-Start Hesitation & Cranking Fuel Architecture

## The Bosch EDC16 Hot Start Problem

A widespread issue in VAG 1.9 TDI Pumpe-Düse engines running EDC16 is prolonged cranking when the engine is at normal operating temperature (75–90°C coolant).

### Root Cause in Calibration

In factory map `EngM_qStart_MAP` (Cranking fuel quantity):
- At cold temperatures (e.g. 0–20°C), the ECU injects fuel immediately even at low cranking speeds (100–150 RPM).
- At warm temperatures (> 70°C), the OEM calibration deliberately sets injected quantity to **0.0 mg** until the starter motor spins the engine above **250 RPM**.
- As the starter motor, battery, and cabling age, maximum warm cranking RPM drops to 220–240 RPM. The engine cranks continuously without firing until RPM barely crosses the 250 RPM threshold.

### Engineering Solution

Smoothly interpolate the warm temperature columns down to 150–180 RPM, delivering 25–35 mg/stroke of starting fuel, resolving the extended cranking hesitation permanently while preserving dual-mass flywheel protection.
