# Ross-Tech VCDS & VAS Diagnostic Engineering Guide: VAG 1.9 TDI PD (EDC16U34)

**Document ID**: VCDS-EDC16U34-DIAG-GUIDE  
**Authority Tier**: Tier A (OEM Specification & Diagnostic Standard)  
**Target ECU**: Bosch EDC16U34 (e.g., VW Golf 5, Passat B6, Touran 1.9 TDI BLS/BXE/BKC)  
**Applicability**: VCDS (VAG-COM Diagnostic System), VAS 5051/5052, ODIS  

---

## 1. Executive Summary & Diagnostic Philosophy

In the Bosch EDC16U34 engine management system, diagnostic communication via K-Line (KWP2000) or CAN Bus (UDS/ISO 14229 gatewayed via J533) provides real-time access to internal ECU calculation registers via **Measuring Value Blocks (MVB)**. 

Unlike conventional OBD-II generic data (SAE J1979 Mode $01), VAG Measuring Blocks expose internal arbitrated values—such as indicated torque, torque friction loss, individual injector solenoid BIP (Beginning of Injection Period) deviations, and multi-channel temperature models.

This guide provides the complete engineering reference for logging, interpreting, and troubleshooting EDC16U34 engine control using VCDS.

---

## 2. Core Measuring Value Blocks (MVB) Reference Table

| Group | Field 1 | Field 2 | Field 3 | Field 4 | Primary Diagnostic Purpose |
|---|---|---|---|---|---|
| **001** | Engine Speed (`RPM`) | Injected Quantity (`mg/str`) | Injection Duration (`°CA`) | Coolant Temp G62 (`°C`) | Base fueling, idle consumption, injection duration verification |
| **003** | Engine Speed (`RPM`) | MAF Specified (`mg/str`) | MAF Actual (`mg/str`) | EGR Duty Cycle (`%`) | Air mass tracking, EGR flow, boost leaks, MAF aging |
| **004** | Engine Speed (`RPM`) | Start of Injection (`°BTDC`) | Injection Duration (`°CA`) | Synchro Angle / Torsion (`°KW`) | Camshaft timing, torsion angle calibration, SOI verification |
| **007** | Fuel Temp G81 (`°C`) | Fuel Temp Status | Intake Air Temp G42 (`°C`) | Coolant Temp G62 (`°C`) | Temperature sensor plausibility, thermal derating checks |
| **008** | Engine Speed (`RPM`) | Driver Wish (`mg/str` or `Nm`) | Torque Limiter (`mg/str` or `Nm`) | Smoke Limiter (`mg/str` or `Nm`) | Fueling limitation hierarchy: determine which limiter governs |
| **010** | MAF Actual (`mg/str`) | Barometric Pressure (`mbar`) | Boost Pressure Actual (`mbar`) | Throttle / Pedal (`%`) | Sensor zero-offset checks, MAP plausibility, full load air delivery |
| **011** | Engine Speed (`RPM`) | Boost Specified (`mbar`) | Boost Actual (`mbar`) | N75 VNT Duty Cycle (`%`) | Turbo response, boost overshoot/undershoot, vane sticking |
| **013** | Smooth Running Cyl 1 (`mg/str`) | Smooth Running Cyl 2 (`mg/str`) | Smooth Running Cyl 3 (`mg/str`) | Smooth Running Cyl 4 (`mg/str`) | Idle cylinder balancing, injector nozzle clogging, compression |
| **015** | Engine Speed (`RPM`) | Actual Engine Torque (`Nm`) | Fuel Consumption (`l/h`) | Torque Request (`Nm`) | Internal indicated torque calculation vs. external loads |
| **018** | Injector 1 Status (`Code`) | Injector 2 Status (`Code`) | Injector 3 Status (`Code`) | Injector 4 Status (`Code`) | Solenoid valve electrical & BIP window validity |
| **023** | BIP Deviation Cyl 1 (`µs`) | BIP Deviation Cyl 2 (`µs`) | BIP Deviation Cyl 3 (`µs`) | BIP Deviation Cyl 4 (`µs`) | Solenoid valve response time, tandem pump delivery pressure |
| **067** | Temp before Turbo G235 (`°C`) | Temp in DPF G448 (`°C`) | Differential Pressure (`mbar`) | Offset Diff. Press (`mbar`) | DPF exhaust temperature, delta-P sensor calibration |
| **068** | Particle Filter Carbon Mass | Particle Filter Soot Mass (`g`) | Ash Mass (`g`) | Regeneration Status | DPF soot load model, ash accumulation limits |

---

## 3. Deep Dive: Key Diagnostic Groups for Calibration & Troubleshooting

### 3.1 Group 004: Torsion Angle (Synchro Angle) & Dynamic SOI

- **Field 4: Synchro Angle / Torsion Value (`Synchro. Angle`)**:
  - **Engineering Meaning**: Phase angle between the crankshaft sensor (G28, 60-2 tooth impulse wheel) and the camshaft Hall sensor (G40) on the camshaft sprocket.
  - **Specification Window**: $-3.0^\circ \text{KW} \le \theta_{\text{synchro}} \le +3.0^\circ \text{KW}$.
  - **Ideal Calibration Target (1.9 TDI BLS)**: $+0.0^\circ \text{KW} \text{ to } +0.5^\circ \text{KW}$ at hot idle ($85^\circ\text{C}+$ coolant).
  - **Physical Impact**:
    - **Retarded (negative, e.g. $-2.5^\circ$)**: Slightly easier cranking, quieter idle, higher exhaust gas temperature, increased low-end spool delay.
    - **Advanced (positive, e.g. $+2.0^\circ$)**: Sharper transient throttle response, lower EGT, higher idle fuel consumption (Group 015 l/h), stiffer engine tone.
    - If reading fluctuates by more than $\pm 0.5^\circ$ during steady idle, inspect timing belt tensioner damping or camshaft sprocket runout.

### 3.2 Group 008: Fuel Limiter Arbitration Hierarchy

Under wide-open throttle (WOT, 100% pedal), Group 008 reveals the ECU's inner arbitration logic:

$$\text{Injected Quantity (Actual)} = \min\left( \text{Driver Wish}, \, \text{Torque Limiter}, \, \text{Smoke Limiter} \right)$$

- **Field 2 (Driver Wish)**: Requested fuel derived from `DrvDem_tq_MAP` via `TrqConv_qInd_MAP`. At 100% pedal, typically 65–70 mg/str (or 320–350 Nm).
- **Field 3 (Torque Limiter)**: Governed by `TrqLim_trqEng_MAP` as a function of RPM and barometric pressure. On stock BLS, peaks at approx. 48–52 mg/str at 2000–2500 RPM.
- **Field 4 (Smoke Limiter)**: Governed by `FlMng_qPresSmoke_MAP` (MAP-based) or `FlMng_qAirSmoke_MAP` (MAF-based). Restricts fuel until boost/air mass builds up.
- **Diagnostic Rule**:
  - If the engine feels sluggish during spool-up, observe Field 4. If Smoke Limiter remains low (<35 mg/str) while Boost Actual is slow to rise, the symptom is caused by turbo spool latency or a boost leak, not a software fueling restriction.

### 3.3 Group 011: Turbo VNT Closed-Loop Regulation & N75 Duty Cycle

Group 011 is the single most critical group for calibrating and diagnosing the variable geometry turbocharger (BorgWarner BV39 on BLS):

- **Field 2: Specified Boost (`p_charge_des`)**: Manifold absolute pressure target in mbar. (Stock BLS max: $\approx 2050\text{ mbar}$ abs / $1.05\text{ bar}$ gauge).
- **Field 3: Actual Boost (`p_charge_act`)**: Measured by MAP sensor G31 in mbar.
- **Field 4: N75 Duty Cycle (`VNT D.Cycle`)**: Solenoid duty cycle percentage sent to the vacuum actuator.
  - **Inverted Logic Standard**: In EDC16 VAG software:
    - High Duty Cycle ($75\% - 95\%$): High vacuum applied $\to$ VNT vanes **closed** (maximum exhaust gas velocity directed onto turbine wheel $\to$ fast spool-up).
    - Low Duty Cycle ($20\% - 40\%$): Vacuum vented to atmosphere $\to$ VNT vanes **open** (bypass / low backpressure $\to$ prevent overboost).
- **Evaluating WOT Logging (3rd or 4th gear, 1500 to 4200 RPM)**:
  - **Spool Phase (1500–2000 RPM)**: N75 duty cycle should rise to $80\% - 90\%$ until boost approaches target.
  - **Regulation Phase (2200–4000 RPM)**: N75 duty cycle should settle smoothly between **$60\%$ and $75\%$**.
  - **Pathology A: Duty Cycle $> 80\%$ at high RPM**: Turbo is struggling to reach target boost. Causes: boost leak, clogged air filter, low vacuum supply (<0.6 bar vacuum), cracked actuator diaphragm, leaking charge piping.
  - **Pathology B: Duty Cycle $< 30\%$ with Boost Spike $> 250\text{ mbar}$ over target**: VNT vanes sticking, actuator rod misadjusted (too short / stop screw improper), vacuum solenoid N75 sticking mechanically.

---

## 4. Injector Health & Actuation Diagnostics

### 4.1 Group 013: Idle Smooth Running Compensation (Quantity Deviation)

EDC16 computes the rotational acceleration of the crankshaft impulse wheel for each firing stroke at idle ($850 - 900\text{ RPM}$). If a cylinder delivers less power, the ECU injects additional fuel into that cylinder to maintain zero crankshaft jerk:

- **Tolerance Range**: $-2.80\text{ mg/str} \le \Delta Q \le +2.80\text{ mg/str}$.
- **Healthy Threshold**: All cylinders within **$\pm 0.50\text{ mg/str}$**.
- **Interpretation**:
  - **Positive deviation ($+1.2\text{ to }+2.8\text{ mg/str}$)**: That cylinder is weak and needs extra fuel to balance. Causes: low compression (worn rings, bent conrod, leaking valve), partially clogged injector nozzle, worn camshaft lobe on that unit injector.
  - **Negative deviation ($-1.2\text{ to }-2.8\text{ mg/str}$)**: That cylinder is over-performing or compensating for a neighbouring dead cylinder; or injector nozzle is leaking/dripping.

### 4.2 Group 018: Unit Injector Electrical & Operating Status Codes

Group 018 monitors the hardware status of the high-pressure solenoid valves (N240, N241, N242, N243):

| Status Code | Meaning | Diagnostic Action |
|---|---|---|
| **000** | Normal, error-free operation | System fully functional |
| **002** | Control start phase | Normal during transition |
| **004** | Small injection quantity active | Pilot injection phase |
| **008** | Maximum solenoid current reached | Normal electrical latch verification |
| **016** | BIP (Beginning of Injection Period) out of tolerance window | Check camshaft rocker adjustment, fuel feed pressure |
| **032** | Sampling error | Check electrical wiring harness inside cylinder head |
| **064** | Conversion error / signal corrupted | Injector wiring short / open circuit |
| **128** | BIP not recognized / no closure detected | Solenoid failure, broken injector harness, dead solenoid |

> [!IMPORTANT]
> A momentary flash of code `002`, `004`, or `008` during sudden revving is normal. Under steady load or idle, all cylinders must display **`000`**.

### 4.3 Group 023: BIP (Beginning of Injection Period) Switching Time Deviation

When the EDC16 energizes the unit injector solenoid valve, it monitors the current waveform. As the valve needle hits its end stop, a distinctive inflection point occurs in the current derivative ($dI/dt$). The time difference between the electrical start command and this physical closure point is the **BIP deviation** ($\Delta t_{\text{BIP}}$):

- **Specification Window**: $-100\,\mu\text{s} \le \Delta t_{\text{BIP}} \le +100\,\mu\text{s}$.
- **Healthy Target**: Within **$\pm 30\,\mu\text{s}$**.
- **Diagnostic Interpretation**:
  - **High positive value ($+60\text{ to }+100\,\mu\text{s}$)**: The valve is closing too slowly. Primary cause: **insufficient fuel supply pressure from the tandem pump** (tandem pump pressure must exceed $3.5\text{ bar}$ at idle and $7.5\text{ bar}$ at $4000\text{ RPM}$), clogged fuel filter, or fuel aeration.
  - **High negative value ($-60\text{ to }-100\,\mu\text{s}$)**: The valve closes prematurely. Primary cause: hydraulic cavitation, fuel temperature too high, or worn return valve spring inside the unit injector.

---

## 5. Functional Testing via VCDS "Basic Settings" (Mode 04)

### 5.1 Basic Settings Group 011: VNT Turbocharger Actuator Cycling

1. Connect VCDS, enter **[01 - Engine]**.
2. Warm engine to $> 80^\circ\text{C}$ coolant.
3. Switch to **[Basic Settings - 04]**, enter Group **011**, click **[Go!]**.
4. The ECU raises engine idle speed automatically to approx. $1400\text{ RPM}$ and alternates the N75 solenoid duty cycle every 10 seconds:
   - **Phase ON (Vanes Closed)**: Duty cycle $90\% - 99\%$. Boost should rise to $\approx 1050 - 1150\text{ mbar}$.
   - **Phase OFF (Vanes Open)**: Duty cycle $0\% - 10\%$. Boost should drop to atmospheric $\approx 960 - 1000\text{ mbar}$.
5. **Physical Inspection**:
   - Inspect the turbocharger vacuum actuator rod. It must move smoothly through its full **$10\text{ to }12\text{ mm}$ stroke** between stops without binding, hesitation, or notchiness.
   - Boost difference between ON and OFF must be at least **$100 - 150\text{ mbar}$**. If the delta is $< 60\text{ mbar}$, the vanes are clogged with carbon or the vacuum system has a leak.

### 5.2 Basic Settings Group 003: EGR Valve Operation Test

1. Engine at hot idle ($80^\circ\text{C}+$ coolant).
2. Enter **[Basic Settings - 04]**, enter Group **003**, click **[Go!]**.
3. ECU raises idle speed to $\approx 1400\text{ RPM}$ and toggles the EGR valve every 10 seconds:
   - **EGR Active (Open)**: Air mass drops to $\approx 180 - 240\text{ mg/str}$ (exhaust gas displaces fresh air).
   - **EGR Inactive (Closed)**: Air mass rises to $\approx 420 - 480\text{ mg/str}$ (100% fresh air inducted).
4. If air mass does not change, the EGR valve is mechanically jammed, vacuum line is disconnected, or the intake manifold is clogged with carbon deposits.

---

## 6. Adaptation Channels & Hot Start Calibration Reference

In **[Adaptation - 10]** on EDC16U34:
- **Channel 01**: Injected Quantity offset (idle trimming, limited range $\pm 2.0\text{ mg/str}$).
- **Channel 02**: Idle Speed Adjustment (standard $830 - 900\text{ RPM}$, adjustable within small safety limits).
- **Channel 03**: EGR Rate Adaptation (reduction of EGR duty within legal boundaries).
- **Hot Start Vulnerability**:
  - In OEM EDC16U34 calibration, the starting fuel delivery table (`InjCrv_qStart_MAP`) sets injected fuel to **$0.0\text{ mg/str}$** at coolant temperatures $\ge 70^\circ\text{C}$ for starter speeds $< 250\text{ RPM}$.
  - When the starter motor ages or battery voltage drops slightly during hot cranking, starter speed peaks at $210 - 240\text{ RPM}$, resulting in protracted cranking (5–10 seconds) until the engine crosses the $250\text{ RPM}$ threshold.
  - Software recalibration lowers the cranking fuel threshold to $100\text{ RPM}$ across all temperature columns, enabling instantaneous hot starts.

---

## 7. High-Rate Data Logging Best Practices for Calibration Validation

When logging transient runs for WinOLS calibration verification:
1. Select **no more than 2 groups simultaneously** (e.g. Group 008 + Group 011, or Group 003 + Group 011) to maintain a sample rate $> 3.5\text{ samples/sec}$.
2. If using VCDS HEX-NET or HEX-V2, enable **[Advanced Measuring Values]** and select only the 6 required PIDs to achieve up to $10 - 15\text{ Hz}$ data acquisition rates:
   - `Engine Speed` (`nmot_w`)
   - `Driver Requested Torque` (`trq_des`)
   - `Torque Limiter Output` (`trq_lim`)
   - `Charge Pressure Target` (`p_charge_des`)
   - `Charge Pressure Actual` (`p_charge_act`)
   - `N75 Duty Cycle` (`duty_cycle_vnt`)
3. Execute logs in **3rd or 4th gear** from $1400\text{ RPM}$ up to $4200\text{ RPM}$ at 100% accelerator pedal on a flat, safe test road.
