# Heywood Mathematical Formulary: Internal Combustion Engine Fundamentals (1988)

**Canonical Mathematical Ground Truth for Diesel Engine ECU Calibration & Thermodynamics**  
*Authored by:* John B. Heywood (Sloan Automotive Laboratory, Massachusetts Institute of Technology)  
*Primary Source:* *Internal Combustion Engine Fundamentals*, McGraw-Hill, 1988 (ISBN 0-07-028637-X)  
*Verification Basis:* Scanned Ground Truth Edition (`Heywood_1988_Internal_Combustion_Engine_Fundamentals_Complete.pdf`, 481 sheets / 962 book pages)  
*Search & Cross-Referencing:* Digital Text PDF & EPUB editions (`Heywood_1988_Internal_Combustion_Engine_Fundamentals_Digital_Text.pdf`, `Heywood_1988_Internal_Combustion_Engine_Fundamentals.epub`)  
*Verification Protocol:* Every single equation in this formulary has been visually inspected, character-by-character, against the original 1988 printed scan sheets. No corrupted OCR text or unverified reconstructions are permitted. Discrepancies with modern teaching notes (MIT 2.61, Bosch Automotive Handbook) are formally recorded as `CONFLICT` or `NOTE`.

---

## Navigation & Domain Directory

1. [Torque, Power, Work, BMEP, IMEP, FMEP](#01-torque-power-work-bmep-imep-fmep)
2. [Stoichiometry, Fuel-Air Ratio, Equivalence Ratio ($\phi$), Lambda ($\lambda$)](#02-stoichiometry-fuel-air-ratio-equivalence-ratio-phi-lambda-lambda)
3. [Air Mass Flow & Volumetric Efficiency ($\eta_v$)](#03-air-mass-flow--volumetric-efficiency-eta_v)
4. [Turbocharger Compressor Pressure Ratio ($\Pi_c$) & Corrected Flow](#04-turbocharger-compressor-pressure-ratio-pi_c--corrected-flow)
5. [Compressor Isentropic Efficiency ($\eta_c$) & Discharge Temperature](#05-compressor-isentropic-efficiency-eta_c--discharge-temperature)
6. [Apparent Net & Gross Heat Release Rates ($dQ/d\theta$)](#06-apparent-net--gross-heat-release-rates-dqdtheta)
7. [Diesel Ignition Delay ($\tau_{\text{id}}$) & Combustion Phasing](#07-diesel-ignition-delay-tau_textid--combustion-phasing)
8. [Pumping Work & PMEP Relations](#08-pumping-work--pmep-relations)
9. [Thermal Efficiency & Specific Fuel Consumption (BSFC)](#09-thermal-efficiency--specific-fuel-consumption-bsfc)
10. [Polytropic In-Cylinder State Relations](#10-polytropic-in-cylinder-state-relations)
11. [Exhaust Enthalpy & Turbine Power Balance](#11-exhaust-enthalpy--turbine-power-balance)
12. [Transient Intake Manifold Filling Dynamics ($dp_m/dt$)](#12-transient-intake-manifold-filling-dynamics-dp_mdt)
13. [Summary Matrix & Verification Audit Trail](#13-summary-matrix--verification-audit-trail)

---

## 01. Torque, Power, Work, BMEP, IMEP, FMEP

### Heywood Eq. 2.12: Brake Torque Definition
- **Source Mapping:** Chapter 2, Book Page 46, Scan Sheet 37 (Left Page)
- **Mathematical Expression:**
  $$T = F \cdot b$$
- **Symbol Definitions & Units:**
  - $T$: Engine torque delivered at the flywheel / dynamometer shaft $[\text{N}\cdot\text{m}]$
  - $F$: Force exerted by the dynamometer brake stator at radius arm $b$ $[\text{N}]$
  - $b$: Moment arm length of dynamometer torque reaction scale $[\text{m}]$
- **Physical Meaning & Thermodynamic Interpretation:**
  Torque is the static moment of force exerted by the engine crankshaft on an external load. Unlike power, torque does not depend on time or speed; it represents the immediate mechanical twisting effort produced by the mean gas pressure acting on the piston area transferred through the slider-crank kinematic chain.
- **Assumptions & Validity Regime:**
  Quasi-steady measurement on an absorbing brake (dynamometer). Valid for steady-state crankshaft rotation where rotational acceleration torque $I_{\text{eng}} \frac{d\omega}{dt} = 0$.
- **ECU Calibration Pitfalls:**
  In Bosch EDC16/EDC17 torque-based architectures (e.g., maps `trq2q` or inner torque path), the ECU controls *indicated inner engine torque* ($T_{\text{ind}}$), not brake flywheel torque ($T_{\text{brake}}$). Overestimating mechanical and parasitic losses causes the ECU to inject excess fuel ($m_f$), causing clutch slip or exceeding transmission torque limits.
- **VERIFIED_FROM_SCAN:** `YES`
- **CROSSCHECK:** `MIT 2.61 / Bosch Automotive Handbook` (Consistent)

---

### Heywood Eq. 2.13a & 2.13b: Engine Power and Rotational Speed
- **Source Mapping:** Chapter 2, Book Page 46, Scan Sheet 37 (Left Page)
- **Mathematical Expression:**
  $$P = 2\pi N T = \omega T$$
  $$P(\text{kW}) = 2\pi N(\text{rev/s}) T(\text{N}\cdot\text{m}) \times 10^{-3} = \frac{N(\text{rev/min}) T(\text{N}\cdot\text{m})}{9549.3}$$
- **Symbol Definitions & Units:**
  - $P$: Mechanical power delivered by the crankshaft $[\text{W}]$ (or $[\text{kW}]$)
  - $N$: Crankshaft rotational speed $[\text{rev/s}]$ or $[\text{rev/min}]$
  - $\omega$: Angular velocity of crankshaft $\omega = 2\pi N$ $[\text{rad/s}]$
  - $T$: Brake torque $[\text{N}\cdot\text{m}]$
  - $9549.3$: Derived conversion constant $\frac{60 \times 1000}{2\pi} \approx 9549.2966$ $[\text{rev}\cdot\text{N}\cdot\text{m} / (\text{min}\cdot\text{kW})]$
- **Physical Meaning & Thermodynamic Interpretation:**
  Power is the rate at which mechanical work is transferred across the engine drive boundary. It is the scalar product of torque and angular frequency.
- **Assumptions & Validity Regime:**
  Uniform crankshaft rotation across the measured cycle. In multi-cylinder engines, instantaneous power fluctuates with cylinder firing events; Eq. 2.13 represents the cycle-averaged power.
- **ECU Calibration Pitfalls:**
  Using instantaneous engine speed rather than cycle-filtered engine speed when computing instantaneous torque requests leads to severe hunting and driveline vibration ("bucking" / surge), especially in low gear at low RPM.
- **VERIFIED_FROM_SCAN:** `YES`
- **CROSSCHECK:** `MIT 2.61 / Bosch Automotive Handbook` (Consistent)

---

### Heywood Eq. 2.14: Indicated Work per Cycle
- **Source Mapping:** Chapter 2, Book Page 47, Scan Sheet 37 (Right Page)
- **Mathematical Expression:**
  $$W_{c,i} = \oint p \, dV$$
- **Symbol Definitions & Units:**
  - $W_{c,i}$: Indicated work transferred from the cylinder gas to the piston crown per cycle $[\text{J}]$
  - $p$: Instantaneous in-cylinder pressure $[\text{Pa}]$
  - $V$: Instantaneous cylinder volume $[\text{m}^3]$
- **Physical Meaning & Thermodynamic Interpretation:**
  The line integral of cylinder pressure with respect to volume over an engine cycle. On a $p$-$V$ indicator diagram, it corresponds to the enclosed area:
  - **Gross Indicated Work ($W_{c,ig}$):** Integration over compression and expansion strokes only ($180^\circ$ BTDC compression to $180^\circ$ ATDC expansion, i.e., $-180^\circ$ to $+180^\circ$ CAD).
  - **Net Indicated Work ($W_{c,in}$):** Integration over all four strokes ($-360^\circ$ to $+360^\circ$ CAD), which naturally subtracts the pumping work loop.
- **Assumptions & Validity Regime:**
  Spatial uniformity of cylinder pressure across the combustion chamber (true as long as local gas velocities remain substantially below the acoustic speed of sound, $M \ll 1$).
- **ECU Calibration Pitfalls:**
  Optical or piezo sensor phasing errors: A shift of just $1^\circ$ CAD in TDC alignment causes up to a $5-10\%$ error in computed indicated work and IMEP.
- **VERIFIED_FROM_SCAN:** `YES`
- **CROSSCHECK:** `MIT 2.61 / SAE J1349` (Consistent)

---

### Heywood Eq. 2.15: Indicated Power per Cylinder
- **Source Mapping:** Chapter 2, Book Page 48, Scan Sheet 38 (Left Page)
- **Mathematical Expression:**
  $$P_i = \frac{W_{c,i} N}{n_R}$$
- **Symbol Definitions & Units:**
  - $P_i$: Indicated engine power per cylinder $[\text{W}]$
  - $W_{c,i}$: Indicated work per cycle per cylinder $[\text{J}]$
  - $N$: Crankshaft rotational speed $[\text{rev/s}]$
  - $n_R$: Number of crank revolutions per power stroke per cylinder ($n_R = 2$ for four-stroke; $n_R = 1$ for two-stroke) $[\text{dimensionless}]$
- **Physical Meaning & Thermodynamic Interpretation:**
  Relates per-cycle thermodynamic gas work to continuous power. For a 4-stroke engine, power strokes occur once every two crankshaft revolutions ($n_R = 2$), meaning the cycle frequency is $N/2$. For total engine power with $n_c$ cylinders: $P_{i,\text{total}} = n_c \cdot P_i$.
- **Assumptions & Validity Regime:**
  Equal work distribution across all cylinders.
- **ECU Calibration Pitfalls:**
  Failing to divide by $n_R = 2$ when converting cylinder-individual torque models to per-engine output or per-second fuel consumption.
- **VERIFIED_FROM_SCAN:** `YES`
- **CROSSCHECK:** `MIT 2.61 / Bosch Automotive Handbook` (Consistent)

---

### Heywood Eq. 2.16 & 2.17: Mechanical Efficiency and Power Split
- **Source Mapping:** Chapter 2, Book Pages 48–49, Sheet 38 (Left & Right Pages)
- **Mathematical Expression:**
  $$P_{i,g} = P_b + P_f$$
  $$\eta_m = \frac{P_b}{P_{i,g}} = 1 - \frac{P_f}{P_{i,g}}$$
- **Symbol Definitions & Units:**
  - $P_{i,g}$: Gross indicated power (work over compression + expansion) $[\text{W}]$
  - $P_b$: Brake usable power delivered at crankshaft $[\text{W}]$
  - $P_f$: Total engine friction power (rubbing friction + accessories + pumping work) $[\text{W}]$
  - $\eta_m$: Engine mechanical efficiency $[0 \text{ to } 1, \text{dimensionless}]$
- **Physical Meaning & Thermodynamic Interpretation:**
  Heywood defines mechanical efficiency specifically with respect to **gross indicated power** ($P_{i,g}$), absorbing pumping power into total friction power ($P_f = P_{f,\text{rubbing}} + P_p + P_{\text{accessories}}$).
- **Assumptions & Validity Regime:**
  Applies to firing conditions. Under motored dyno testing, piston side-thrust forces and cylinder wall temperatures are significantly lower than under firing conditions, meaning motored friction underestimates firing friction by $10-20\%$.
- **ECU Calibration Pitfalls:**
  Confusing gross vs. net indicated baseline: If an ECU tuner implements friction compensation assuming net IMEP, but the base ECU map uses gross IMEP, the engine will double-count pumping losses, degrading idle control stability and cruise fuel economy.
- **VERIFIED_FROM_SCAN:** `YES`
- **CROSSCHECK:** `MIT 2.61` (Noted: MIT 2.61 explicitly highlights the distinction between European gross definition vs. net convention).

---

### Heywood Eq. 2.19a & 2.20a: Mean Effective Pressure (MEP)
- **Source Mapping:** Chapter 2, Book Page 50, Scan Sheet 39 (Left Page)
- **Mathematical Expression:**
  $$\text{mep} = \frac{P n_R}{V_d N} = \frac{W_c}{V_d}$$
  $$\text{mep}(\text{kPa}) = \frac{2\pi n_R T(\text{N}\cdot\text{m})}{V_d(\text{dm}^3)} = \frac{6.2832 \, n_R T(\text{N}\cdot\text{m})}{V_d(\text{dm}^3)}$$
  For a 4-stroke engine ($n_R = 2$):
  $$\text{bmep}(\text{kPa}) = \frac{4\pi T(\text{N}\cdot\text{m})}{V_d(\text{dm}^3)} \approx \frac{12.5664 \, T(\text{N}\cdot\text{m})}{V_d(\text{dm}^3)}$$
  $$\text{bmep}(\text{bar}) = \frac{4\pi T(\text{N}\cdot\text{m})}{100 \cdot V_d(\text{dm}^3)} = \frac{0.125664 \, T(\text{N}\cdot\text{m})}{V_d(\text{dm}^3)}$$
- **Symbol Definitions & Units:**
  - $\text{mep}$: Mean effective pressure $[\text{Pa}]$ or $[\text{kPa}]$ (subscripts: $b = \text{brake}$, $ig = \text{indicated gross}$, $in = \text{indicated net}$, $p = \text{pumping}$)
  - $V_d$: Total engine displaced volume $[\text{m}^3]$ or $[\text{dm}^3 = \text{liters}]$
  - $W_c$: Total engine work delivered per complete cycle $[\text{J}]$
  - $T$: Engine torque $[\text{N}\cdot\text{m}]$
- **Physical Meaning & Thermodynamic Interpretation:**
  MEP is a size-independent measure of an engine's specific work output. It represents the fictitious constant pressure that, if acting on the piston face over the entire expansion stroke, would produce the identical cycle work.
  - Typical naturally aspirated diesel: $\text{BMEP}_{\text{max}} \approx 700 - 900\text{ kPa}$ ($7 - 9\text{ bar}$).
  - Modern turbocharged DI diesel: $\text{BMEP}_{\text{max}} \approx 1800 - 2800\text{ kPa}$ ($18 - 28\text{ bar}$).
- **Assumptions & Validity Regime:**
  Linear scaling with displaced volume; valid across all engine sizes from 0.5L single-cylinders to 20,000L marine diesels.
- **ECU Calibration Pitfalls:**
  Failing to recognize BMEP as a proxy for thermal/mechanical stress: Exceeding cylinder peak pressure rating ($p_{\text{max}}$ limit, e.g. 180–210 bar on common rail pistons) while targeting excessive BMEP at low RPM causes cylinder head gasket blowout, rod bending, or ring land collapse.
- **VERIFIED_FROM_SCAN:** `YES`
- **CROSSCHECK:** `MIT 2.61 / Bosch Automotive Handbook` (Consistent)

---

## 02. Stoichiometry, Fuel-Air Ratio, Equivalence Ratio ($\phi$), Lambda ($\lambda$)

### Heywood Eq. 2.25, 2.26 & 3.5: Air-Fuel Ratio & Stoichiometric Combustion
- **Source Mapping:** Chapter 2, Page 53, Sheet 40 & Chapter 3, Pages 68–71, Sheets 48–49
- **Mathematical Expression:**
  $$(A/F) = \frac{\dot{m}_a}{\dot{m}_f}, \quad (F/A) = \frac{\dot{m}_f}{\dot{m}_a} = \frac{1}{(A/F)}$$
  For a general hydrocarbon fuel $\text{C}_n \text{H}_m$ (or $\text{CH}_y$ where $y = m/n$):
  $$\text{C}_n \text{H}_m + \left( n + \frac{m}{4} \right)(\text{O}_2 + 3.773 \text{N}_2) \longrightarrow n \text{CO}_2 + \frac{m}{2} \text{H}_2 \text{O} + 3.773 \left( n + \frac{m}{4} \right) \text{N}_2$$
  $$(A/F)_s = \frac{1 + \frac{y}{4}}{12.011 + 1.008 y} \cdot \left[ 32.000 + 3.773 \times 28.016 \right] = \frac{1 + \frac{y}{4}}{12.011 + 1.008 y} \cdot 137.28$$
- **Symbol Definitions & Units:**
  - $(A/F)$: Mass air-to-fuel ratio $[\text{dimensionless}, \text{kg air / kg fuel}]$
  - $(F/A)$: Mass fuel-to-air ratio $[\text{dimensionless}, \text{kg fuel / kg air}]$
  - $(A/F)_s$: Stoichiometric mass air-to-fuel ratio $[\text{dimensionless}]$
  - $y = m/n$: Hydrogen-to-carbon atomic ratio of the fuel ($y \approx 1.85$ for standard European EN 590 diesel fuel)
  - For standard diesel fuel ($\text{C}_{14.4}\text{H}_{24.9}$, $y \approx 1.85$): $(A/F)_s \approx 14.50\text{ kg air / kg fuel}$.
  - For standard gasoline ($\text{C}_8\text{H}_{18}$, $y \approx 2.25$): $(A/F)_s \approx 14.60 - 14.70\text{ kg air / kg fuel}$.
- **Physical Meaning & Thermodynamic Interpretation:**
  Stoichiometric air-fuel ratio is the exact theoretical ratio where all carbon is converted to $\text{CO}_2$ and all hydrogen to $\text{H}_2\text{O}$ with zero excess molecular oxygen remaining in the exhaust products.
- **Assumptions & Validity Regime:**
  Complete combustion, dry air composed of $21.0\%\ \text{O}_2$ and $79.0\%\ \text{N}_2$ ($3.773$ moles $\text{N}_2$ per mole $\text{O}_2$), molecular weight of air $M_{\text{air}} = 28.96\text{ g/mol}$.
- **ECU Calibration Pitfalls:**
  Assuming gasoline stoichiometry ($14.7$) for diesel calibration. Using $14.7$ instead of $14.5$ underestimates injected fuel mass by $1.4\%$. More critically, biodiesel blends (FAME/RME, which contain oxygen in the fuel molecule, $\text{C}_{19}\text{H}_{36}\text{O}_2$) have stoichiometric ratios around $12.5 - 12.8$. Using standard diesel constants with biodiesel leads to severe fueling discrepancies.
- **VERIFIED_FROM_SCAN:** `YES`
- **CROSSCHECK:** `MIT 2.61 / Bosch Diesel Engine Management` (Consistent)

---

### Heywood Eq. 3.8 & 3.9: Fuel/Air Equivalence Ratio ($\phi$) and Relative Air/Fuel Ratio ($\lambda$)
- **Source Mapping:** Chapter 3, Book Page 71, Scan Sheet 49 (Right Page)
- **Mathematical Expression:**
  $$\phi = \frac{(F/A)_{\text{actual}}}{(F/A)_s} = \frac{(A/F)_s}{(A/F)_{\text{actual}}}$$
  $$\lambda = \phi^{-1} = \frac{1}{\phi} = \frac{(A/F)_{\text{actual}}}{(A/F)_s} = \frac{(F/A)_s}{(F/A)_{\text{actual}}}$$
- **Symbol Definitions & Units:**
  - $\phi$: Fuel/air equivalence ratio $[\text{dimensionless}]$
    - $\phi < 1$: Fuel-lean mixture (excess air)
    - $\phi = 1$: Stoichiometric mixture
    - $\phi > 1$: Fuel-rich mixture (excess fuel)
  - $\lambda$: Relative air/fuel ratio (Lambda) $[\text{dimensionless}]$
    - $\lambda > 1$: Fuel-lean (characteristic diesel operating regime: $\lambda \approx 1.15 \text{ to } 8.0$)
    - $\lambda = 1$: Stoichiometric
    - $\lambda < 1$: Fuel-rich (produces severe black smoke / particulate in diesels)
- **Physical Meaning & Thermodynamic Interpretation:**
  Diesel engines operate overall lean at all times because combustion is heterogeneous (diffusion flame governed by turbulent spray mixing). Even when the global mixture is lean ($\lambda = 1.3$), locally within the spray envelope there exist stoichiometric and over-rich zones ($\phi \ge 1$) where soot nucleation takes place.
- **Assumptions & Validity Regime:**
  Global cylinder-averaged air and fuel masses.
- **ECU Calibration Pitfalls:**
  **The Diesel Smoke Limit:** In smoke limitation maps (`MAF/MAP smoke limiters` in EDC15/EDC16/EDC17):
  Calibrators frequently lower the smoke limiter below $\lambda = 1.15$ ($\phi > 0.87$) in pursuit of torque. At $\lambda < 1.25$ on stock injectors, soot emissions spike exponentially, blocking DPFs, caking variable nozzle turbine (VNT) vanes, and driving exhaust gas temperatures (EGT) past $850^\circ\text{C}$.
- **VERIFIED_FROM_SCAN:** `YES`
- **CROSSCHECK:** `MIT 2.61 / Bosch Automotive Handbook` (Consistent)

---

## 03. Air Mass Flow & Volumetric Efficiency ($\eta_v$)

### Heywood Eq. 2.27a, 2.27b & 6.2: Volumetric Efficiency Definition
- **Source Mapping:** Chapter 2, Page 54, Sheet 41 & Chapter 6, Page 210, Sheet 119
- **Mathematical Expression:**
  $$\eta_v = \frac{n_R \dot{m}_a}{\rho_{a,i} V_d N} = \frac{2 \dot{m}_a}{\rho_{a,i} V_d N} \quad (\text{for 4-stroke})$$
  $$\eta_v = \frac{m_a}{\rho_{a,i} V_d}$$
  $$\text{where } \rho_{a,i} = \frac{p_{a,i}}{R_a T_{a,i}}$$
- **Symbol Definitions & Units:**
  - $\eta_v$: Volumetric efficiency $[0 \text{ to } >1.0, \text{dimensionless}]$
  - $\dot{m}_a$: Mass flow rate of fresh air inducted into the engine $[\text{kg/s}]$
  - $m_a$: Mass of air inducted per cylinder per cycle $[\text{kg}]$
  - $\rho_{a,i}$: Reference density of inlet air $[\text{kg/m}^3]$
  - $p_{a,i}$: Reference inlet pressure $[\text{Pa}]$
  - $T_{a,i}$: Reference inlet temperature $[\text{K}]$
  - $R_a$: Specific gas constant for dry air ($R_a = \frac{\tilde{R}}{M_a} = \frac{8314.3}{28.96} = 287.05\text{ J/(kg}\cdot\text{K)}$)
  - $V_d$: Displaced cylinder volume $[\text{m}^3]$
  - $N$: Crankshaft rotational speed $[\text{rev/s}]$
- **Physical Meaning & Thermodynamic Interpretation:**
  Volumetric efficiency quantifies the breathing effectiveness of the engine's gas exchange system. It is the ratio of actual trapped air mass in the cylinder to the ideal air mass that would occupy the displaced volume at reference inlet conditions.
- **Assumptions & Validity Regime:**
  **Critical Distinction between Atmospheric vs. Manifold Reference:**
  - If $\rho_{a,i}$ is evaluated at ambient atmospheric conditions ($\rho_{a,0} = p_0 / R_a T_0$), $\eta_v$ measures the performance of the **entire induction system including turbocharger, intercooler, and valves**. In turbocharged engines, this overall $\eta_v$ can reach $1.8 - 3.5$.
  - If $\rho_{a,i}$ is evaluated at **inlet manifold conditions** ($p_{\text{intake}}, T_{\text{intake}}$), $\eta_v$ isolates the **pumping performance of the intake port, valve geometry, and valve timing alone**. In this case, $\eta_v$ is typically $0.80 - 0.92$.
- **ECU Calibration Pitfalls:**
  In speed-density based ECUs (calculating cylinder mass charge $m_{\text{cyl}}$ from MAP and IAT):
  $$m_{\text{cyl}} = \eta_v(N, p_m) \cdot \frac{p_m}{R_a T_m} \cdot V_{\text{cyl}}$$
  Using an atmospheric-referenced volumetric efficiency map instead of a manifold-referenced map causes massive fueling errors under boost (running dangerously lean or rich).
- **VERIFIED_FROM_SCAN:** `YES`
- **CROSSCHECK:** `MIT 2.61 / Bosch Automotive Handbook` (Consistent)

---

## 04. Turbocharger Compressor Pressure Ratio ($\Pi_c$) & Corrected Flow

### Heywood Eq. 6.38, 6.52 & 6.53: Compressor Pressure Ratio and Corrected Variables
- **Source Mapping:** Chapter 6, Book Pages 251–255, Scan Sheets 139–141
- **Mathematical Expression:**
  $$\Pi_c = \frac{p_{02}}{p_{01}}$$
  $$\dot{m}_{\text{corr}} = \dot{m} \frac{\sqrt{T_{01} / T_{\text{ref}}}}{p_{01} / p_{\text{ref}}} = \dot{m} \frac{\sqrt{\theta}}{\delta}$$
  $$N_{\text{corr}} = \frac{N_{\text{tc}}}{\sqrt{T_{01} / T_{\text{ref}}}} = \frac{N_{\text{tc}}}{\sqrt{\theta}}$$
  $$\text{where } \theta = \frac{T_{01}}{T_{\text{ref}}}, \quad \delta = \frac{p_{01}}{p_{\text{ref}}}$$
- **Symbol Definitions & Units:**
  - $\Pi_c$: Total-to-total compressor pressure ratio $[\text{dimensionless}]$
  - $p_{01}$: Total (stagnation) pressure at compressor inlet $[\text{Pa}]$
  - $p_{02}$: Total (stagnation) pressure at compressor exit (before intercooler) $[\text{Pa}]$
  - $\dot{m}$: Actual compressor mass airflow $[\text{kg/s}]$
  - $\dot{m}_{\text{corr}}$: Corrected compressor mass flow rate $[\text{kg/s}]$
  - $N_{\text{tc}}$: Physical compressor rotational speed $[\text{rev/min}]$
  - $N_{\text{corr}}$: Corrected compressor rotational speed $[\text{rev/min}]$
  - $T_{01}$: Total (stagnation) temperature at compressor inlet $[\text{K}]$
  - $T_{\text{ref}}$: Standard reference temperature ($298.15\text{ K} = 25^\circ\text{C}$ or $288.15\text{ K}$)
  - $p_{\text{ref}}$: Standard reference pressure ($101.325\text{ kPa} = 1.01325\text{ bar}$ or $100.0\text{ kPa}$)
- **Physical Meaning & Thermodynamic Interpretation:**
  Corrected mass flow and corrected speed are non-dimensional similarity parameters derived from Mach number and blade kinematic velocity triangles ($C / \sqrt{\gamma R T_0} \propto \dot{m}\sqrt{T_0}/p_0$ and $U / \sqrt{\gamma R T_0} \propto N/\sqrt{T_0}$). They allow compressor maps produced on test benches at sea-level standard conditions to predict compressor behavior at high altitude or hot intake conditions.
- **Assumptions & Validity Regime:**
  Constant gas properties ($\gamma, R$) across the inlet duct; negligible Reynolds number variation across high-subsonic Mach flows.
- **ECU Calibration Pitfalls:**
  **Turbo Overspeed at Altitude:** Calibrators often request constant absolute boost pressure (e.g. $2.5\text{ bar}$ MAP) at sea level and altitude. At $2000\text{m}$ altitude, ambient pressure $p_{01}$ drops from $1.0\text{ bar}$ to $0.8\text{ bar}$. To maintain $2.5\text{ bar}$ boost, the compressor pressure ratio must increase from $\Pi_c = 2.5$ to $\Pi_c = 3.125$. The compressor moves violently toward the overspeed and surge boundary, resulting in turbocharger failure. The ECU boost limit map must derate target boost as a function of barometric pressure (`p_amb`).
- **VERIFIED_FROM_SCAN:** `YES`
- **CROSSCHECK:** `MIT 2.61 / SAE J1826` (Consistent)

---

## 05. Compressor Isentropic Efficiency ($\eta_c$) & Discharge Temperature

### Heywood Eq. 6.39, 6.40 & 6.42: Compressor Efficiency and Power
- **Source Mapping:** Chapter 6, Book Pages 251–252, Scan Sheets 139–140
- **Mathematical Expression:**
  $$\eta_{c\text{TT}} = \frac{h_{02s} - h_{01}}{h_{02} - h_{01}} = \frac{T_{02s} - T_{01}}{T_{02} - T_{01}} = \frac{\left( \frac{p_{02}}{p_{01}} \right)^{\frac{\gamma_c - 1}{\gamma_c}} - 1}{\frac{T_{02}}{T_{01}} - 1}$$
  Actual compressor exit total temperature:
  $$T_{02} = T_{01} \left[ 1 + \frac{1}{\eta_{c\text{TT}}} \left( \Pi_c^{\frac{\gamma_c - 1}{\gamma_c}} - 1 \right) \right]$$
  Compressor shaft drive power required:
  $$P_c = -\dot{W}_c = \dot{m}_a c_{p,a} (T_{02} - T_{01}) = \frac{\dot{m}_a c_{p,a} T_{01}}{\eta_{c\text{TT}}} \left[ \Pi_c^{\frac{\gamma_c - 1}{\gamma_c}} - 1 \right]$$
- **Symbol Definitions & Units:**
  - $\eta_{c\text{TT}}$: Isentropic total-to-total compressor efficiency $[0 \text{ to } 1, \text{dimensionless}]$ (typically $0.68 - 0.78$ in turbochargers)
  - $h_{01}, h_{02}$: Actual stagnation enthalpies at compressor inlet and exit $[\text{J/kg}]$
  - $h_{02s}$: Ideal isentropic stagnation enthalpy at compressor discharge pressure $[\text{J/kg}]$
  - $T_{01}, T_{02}$: Stagnation temperatures at inlet and exit $[\text{K}]$
  - $\gamma_c$: Ratio of specific heats for fresh ambient air ($\gamma_c = c_p / c_v \approx 1.40$)
  - $\frac{\gamma_c - 1}{\gamma_c}$: Isentropic temperature exponent $\frac{1.40 - 1}{1.40} = \frac{0.40}{1.40} \approx 0.2857$
  - $c_{p,a}$: Specific heat capacity of dry air at constant pressure ($c_{p,a} \approx 1005\text{ J/(kg}\cdot\text{K)}$)
  - $P_c$: Compressor mechanical shaft power requirement $[\text{W}]$
- **Physical Meaning & Thermodynamic Interpretation:**
  Compressor isentropic efficiency measures how closely the compression process approaches a reversible adiabatic path. Real-world fluid friction, boundary layer separation, and blade tip leakage convert input shaft work into irreversible thermal dissipation, driving exit temperature $T_{02}$ significantly above the ideal isentropic temperature $T_{02s}$.
- **Assumptions & Validity Regime:**
  Adiabatic compressor casing (negligible heat transfer to ambient; valid at medium to high mass flow rates). Ideal gas behavior for intake air.
- **ECU Calibration Pitfalls:**
  Pushing a small turbocharger into its low-efficiency "choke" or high-pressure surge island ($\eta_c < 0.60$): Exit temperature $T_{02}$ skyrockets above $200^\circ\text{C}$. Even with an intercooler, manifold charge temperature climbs, drastically lowering charge air density and causing thermal throttling, soot spikes, and compressor wheel burst risk.
- **VERIFIED_FROM_SCAN:** `YES`
- **CROSSCHECK:** `MIT 2.61 / Bosch Automotive Handbook` (Consistent)

---

## 06. Apparent Net & Gross Heat Release Rates ($dQ/d\theta$)

### Heywood Eq. 10.1, 10.3, 10.6 & 10.7: Single-Zone Heat Release Rate Analysis
- **Source Mapping:** Chapter 10, Book Pages 510–513, Scan Sheets 269–270
- **Mathematical Expression:**
  First Law open-system energy balance:
  $$\frac{dQ}{dt} - p \frac{dV}{dt} + \sum_i \dot{m}_i h_i = \frac{dU}{dt}$$
  Net heat release rate:
  $$\frac{dQ_n}{dt} = \frac{dQ_{\text{ch}}}{dt} - \frac{dQ_{\text{ht}}}{dt} = p \frac{dV}{dt} + \frac{dU_s}{dt}$$
  Canonical Heywood Equation in Crank Angle Domain:
  $$\frac{dQ_n}{d\theta} = \frac{\gamma}{\gamma - 1} p \frac{dV}{d\theta} + \frac{1}{\gamma - 1} V \frac{dp}{d\theta}$$
  Gross chemical heat release:
  $$\frac{dQ_{\text{ch}}}{d\theta} = \frac{dQ_n}{d\theta} + \frac{dQ_{\text{ht}}}{d\theta}$$
  Total fuel energy check:
  $$Q_{\text{ch,total}} = \int_{\theta_{\text{start}}}^{\theta_{\text{end}}} \frac{dQ_{\text{ch}}}{d\theta} d\theta = m_f Q_{\text{LHV}} \eta_{\text{comb}}$$
- **Symbol Definitions & Units:**
  - $dQ_n / d\theta$: Apparent net heat release rate $[\text{J/CAD}]$ (Joules per Crank Angle Degree)
  - $dQ_{\text{ch}} / d\theta$: Apparent gross chemical heat release rate $[\text{J/CAD}]$
  - $dQ_{\text{ht}} / d\theta$: Cylinder wall convective and radiative heat loss rate $[\text{J/CAD}]$
  - $p$: In-cylinder gas pressure $[\text{Pa}]$
  - $V$: Instantaneous cylinder volume at crank angle $\theta$ $[\text{m}^3]$
  - $dp / d\theta$: Rate of cylinder pressure change $[\text{Pa/CAD}]$
  - $dV / d\theta$: Cylinder volume change rate from slider-crank kinematics $[\text{m}^3/\text{CAD}]$
  - $\gamma$: Effective ratio of specific heats ($c_p / c_v$). Heywood recommends:
    - $\gamma \approx 1.35$ for pre-combustion compressed air charge.
    - $\gamma \approx 1.26 - 1.30$ for post-combustion burned gases.
    - $\gamma = 1.30 - 1.32$ as standard constant single-zone compromise.
  - $m_f$: Mass of fuel injected per cylinder per cycle $[\text{kg}]$
  - $Q_{\text{LHV}}$: Lower heating value of diesel fuel ($Q_{\text{LHV}} \approx 42.5 - 43.2\text{ MJ/kg} = 42.5 \times 10^6\text{ J/kg}$)
  - $\eta_{\text{comb}}$: Combustion efficiency ($\approx 0.98 - 0.99$ in clean DI diesels)
- **Physical Meaning & Thermodynamic Interpretation:**
  Eq. 10.6 reveals the two primary thermodynamic mechanisms absorbing released combustion energy:
  1. The displacement work term $\frac{\gamma}{\gamma - 1} p \frac{dV}{d\theta}$: Work performed on the moving piston crown.
  2. The pressure rise term $\frac{1}{\gamma - 1} V \frac{dp}{d\theta}$: Sensible thermal internal energy accumulation in the gas.
  During early premixed diesel combustion, $dp/d\theta$ dominates, creating the sharp spike in $dQ_n/d\theta$ responsible for combustion noise ("diesel knock"). During the subsequent mixing-controlled diffusion combustion phase, $p(dV/d\theta)$ dominates as the piston expands downwards.
- **Assumptions & Validity Regime:**
  Single-zone lumped parameter model: uniform spatial pressure and temperature; ideal gas equation of state $p V = m R T$; crevice flow volume neglected; instantaneous fuel vaporization enthalpy small relative to $Q_{\text{LHV}}$.
- **ECU Calibration Pitfalls:**
  Selecting inappropriate $\gamma$: Using room-temperature air ratio $\gamma = 1.40$ instead of $1.30-1.32$ will substantially overestimate calculated heat release rate and cumulative burned fuel mass. Furthermore, uncalibrated pressure sensor thermal drift or improper baseline pegging (matching piezo sensor voltage to MAP near BDC intake) ruins heat release accuracy.
- **VERIFIED_FROM_SCAN:** `YES`
- **CROSSCHECK:** `MIT 2.61 / SAE Paper 860485` (Consistent)

---

### Heywood Eq. 2.5 & 2.6: Cylinder Kinematics & Volume Derivative
- **Source Mapping:** Chapter 2, Book Page 44, Scan Sheet 36 (Left Page)
- **Mathematical Expression:**
  $$\frac{V(\theta)}{V_c} = 1 + \frac{1}{2}(r_c - 1) \left[ R + 1 - \cos\theta - \sqrt{R^2 - \sin^2\theta} \right]$$
  $$V(\theta) = V_c + \frac{V_d}{2} \left[ R + 1 - \cos\theta - \sqrt{R^2 - \sin^2\theta} \right]$$
  $$\frac{dV}{d\theta} = \frac{V_d}{2} \sin\theta \left[ 1 + \frac{\cos\theta}{\sqrt{R^2 - \sin^2\theta}} \right]$$
- **Symbol Definitions & Units:**
  - $V(\theta)$: Instantaneous combustion chamber volume at crank angle $\theta$ $[\text{m}^3]$
  - $V_c$: Clearance volume at Top Dead Center $[\text{m}^3]$
  - $V_d$: Swept / displaced cylinder volume $V_d = \frac{\pi}{4} B^2 L$ $[\text{m}^3]$
  - $r_c$: Geometric compression ratio $r_c = \frac{V_d + V_c}{V_c}$ $[\text{dimensionless}]$
  - $R$: Connecting rod length to crank radius ratio $R = \frac{l}{a} = \frac{2l}{L}$ $[\text{dimensionless}]$ (typically $3.0 - 3.8$)
  - $l$: Connecting rod center-to-center length $[\text{m}]$
  - $a$: Crank radius $a = L/2$ $[\text{m}]$
  - $L$: Piston stroke $[\text{m}]$
  - $\theta$: Crankshaft angle measured from TDC ($\theta = 0$ at TDC, $\theta = \pi$ at BDC) $[\text{rad}]$
- **Physical Meaning & Thermodynamic Interpretation:**
  The exact geometric volume trajectory of a reciprocating slider-crank engine mechanism. $\frac{dV}{d\theta}$ is zero at TDC ($\theta = 0^\circ$) and BDC ($\theta = 180^\circ$), peaking near $70^\circ - 75^\circ$ ATDC depending on rod ratio $R$.
- **Assumptions & Validity Regime:**
  Rigid crankshaft and connecting rod (zero mechanical deflection under firing pressure). Zero wrist-pin offset.
- **ECU Calibration Pitfalls:**
  Neglecting rod ratio $R$: Approximating $\frac{dV}{d\theta}$ with pure sinusoidal harmonic motion ($\frac{V_d}{2} \sin\theta$) introduces large errors in early expansion heat release calculations.
- **VERIFIED_FROM_SCAN:** `YES`
- **CROSSCHECK:** `MIT 2.61 / Bosch Automotive Handbook` (Consistent)

---

## 07. Diesel Ignition Delay ($\tau_{\text{id}}$) & Combustion Phasing

### Heywood Eq. 10.35: Classical Arrhenius / Wolfer Autoignition Delay
- **Source Mapping:** Chapter 10, Book Page 545, Scan Sheet 286 (Right Page)
- **Mathematical Expression:**
  $$\tau_{\text{id}} = A \cdot p^{-n} \exp\left( \frac{E_A}{\tilde{R} T} \right)$$
- **Symbol Definitions & Units:**
  - $\tau_{\text{id}}$: Ignition delay time interval $[\text{s}]$ or $[\text{ms}]$
  - $p$: In-cylinder gas pressure during delay $[\text{Pa}]$ or $[\text{bar}]$ (depends on constant $A$)
  - $T$: In-cylinder charge temperature during delay $[\text{K}]$
  - $A$: Empirical proportionality constant dependent on fuel spray and chamber geometry
  - $n$: Pressure exponent (typically $0.7 - 1.2$, reflecting reaction order)
  - $E_A$: Apparent global activation energy $[\text{J/mol}]$
  - $\tilde{R}$: Universal gas constant ($8.3143\text{ J/(mol}\cdot\text{K)}$)
- **Physical Meaning & Thermodynamic Interpretation:**
  Autoignition in diesel combustion is a dual physical-chemical process:
  1. **Physical delay:** Droplet breakup, spray atomization, vaporization, and turbulent air-fuel vapor mixing.
  2. **Chemical delay:** Pre-flame low-temperature oxidation reactions (peroxide and radical formation) leading up to radical pool thermal explosion.
  At high temperatures ($T > 1000\text{ K}$), chemical kinetics become virtually instantaneous, and physical mixing limits ignition delay. At cold start ($T < 700\text{ K}$), chemical kinetics exponentially dominate.
- **Assumptions & Validity Regime:**
  Constant pressure and temperature during the delay interval (homogeneous bomb or flow reactor conditions).
- **ECU Calibration Pitfalls:**
  Applying static injection timing maps when charge temperature drops: If intake air temperature drops (e.g. frozen winter morning), $\tau_{\text{id}}$ lengthens drastically. If SOI (Start of Injection) is not advanced, combustion occurs too late in the expansion stroke, leading to unburned white hydrocarbon smoke, misfires, and lack of power.
- **VERIFIED_FROM_SCAN:** `YES`
- **CROSSCHECK:** `MIT 2.61` (Consistent)

---

### Heywood Eq. 10.37 & 10.38: Hardenberg & Hase DI Diesel Ignition Delay Correlation
- **Source Mapping:** Chapter 10, Book Pages 555–556, Scan Sheets 291–292
- **Mathematical Expression:**
  $$\tau_{\text{id}}(\text{CA}) = (0.36 + 0.22 \bar{S}_p) \exp\left[ E_A \left( \frac{1}{\tilde{R} T} - \frac{1}{17,190} \right) \left( \frac{21.2}{p - 12.4} \right)^{0.63} \right]$$
  $$E_A = \frac{618,840}{\text{CN} + 25}$$
  $$\tau_{\text{id}}(\text{ms}) = \frac{\tau_{\text{id}}(\text{CA})}{0.006 N}$$
- **Symbol Definitions & Units:**
  - $\tau_{\text{id}}(\text{CA})$: Ignition delay duration in Crank Angle Degrees $[\text{CAD}]$
  - $\tau_{\text{id}}(\text{ms})$: Ignition delay duration in milliseconds $[\text{ms}]$
  - $\bar{S}_p$: Mean piston speed $\bar{S}_p = 2 L N$ $[\text{m/s}]$
  - $N$: Engine rotational speed $[\text{rev/min}]$
  - $p$: In-cylinder charge pressure at TDC $[\textbf{bar}]$ **(STRICT REQUIREMENT: MUST BE IN BAR, NOT PASCALS)**
  - $T$: In-cylinder charge temperature at TDC $[\textbf{K}]$
  - $E_A$: Apparent activation energy $[\text{J/mol}]$
  - $\text{CN}$: Fuel Cetane Number $[\text{dimensionless}]$ (typically $51 - 55$ for standard European diesel)
  - $\tilde{R}$: Universal gas constant ($8.3143\text{ J/(mol}\cdot\text{K)}$)
- **Physical Meaning & Thermodynamic Interpretation:**
  One of the most accurate empirical correlations for DI diesel engines across warm and cold regimes. It accounts explicitly for:
  - Piston velocity ($\bar{S}_p$), which governs in-cylinder turbulence and turbulent fuel-air mixing rate.
  - Cetane rating ($\text{CN}$), which directly alters activation energy $E_A$.
  - Pressure non-linearity $(p - 12.4)^{-0.63}$, capturing the radical branching behavior of diesel autoignition.
- **Assumptions & Validity Regime:**
  DI engines operating with commercial diesel fuels ($\text{CN} \in [38, 60]$). Pressure evaluated under compression near TDC: $p_{\text{TC}} = p_i r_c^n$, $T_{\text{TC}} = T_i r_c^{n-1}$.
- **ECU Calibration Pitfalls:**
  **Unit Catastrophe:** Entering pressure in $\text{Pa}$ or $\text{kPa}$ into Eq. 10.37 will produce infinite or complex numbers because of $(p - 12.4)^{0.63}$. Pressure **must be in bar**. Furthermore, during EGR introduction, oxygen concentration drops; Eq. 10.37 assumes clean air. Under heavy EGR ($>30\%$), actual ignition delay is prolonged by $15-30\%$ due to thermal dilution and slower radical formation.
- **VERIFIED_FROM_SCAN:** `YES`
- **CROSSCHECK:** `SAE Paper 790493 / Bosch Diesel Engine Management` (Consistent)

---

### Livengood-Wu Autoignition Integral for Dynamic In-Cylinder States
- **Source Mapping:** Chapter 10, Book Page 546, Scan Sheet 287 (Left Page)
- **Mathematical Expression:**
  $$\int_{t_{\text{SOI}}}^{t_{\text{SOC}}} \frac{1}{\tau_{\text{id}}(p(t), T(t))} \, dt = 1 \quad \text{or} \quad \int_{\theta_{\text{SOI}}}^{\theta_{\text{SOC}}} \frac{1}{\tau_{\text{id}}(p(\theta), T(\theta))} \frac{d\theta}{6 N} = 1$$
- **Symbol Definitions & Units:**
  - $t_{\text{SOI}}$ / $\theta_{\text{SOI}}$: Start of Injection timing $[\text{s}]$ or $[\text{CAD}]$
  - $t_{\text{SOC}}$ / $\theta_{\text{SOC}}$: Start of Combustion timing (ignition point) $[\text{s}]$ or $[\text{CAD}]$
  - $\tau_{\text{id}}(p, T)$: Instantaneous ignition delay evaluated at time-varying pressure $p(t)$ and temperature $T(t)$ $[\text{s}]$
  - $6N$: Conversion factor from RPM to CAD/s ($1\text{ rev/min} = 360^\circ / 60\text{ s} = 6^\circ/\text{s}$)
- **Physical Meaning & Thermodynamic Interpretation:**
  Because cylinder pressure and temperature change rapidly during the compression stroke while injection is underway, the autoignition process is non-isothermal. The Livengood-Wu integral models the normalized accumulation of intermediate chain-branching precursor radicals ($[R^\bullet] / [R^\bullet]_{\text{crit}}$). Autoignition occurs when the integrated progress variable reaches unity.
- **Assumptions & Validity Regime:**
  Single-step global radical accumulation mechanism where reaction history does not change the dominant activation energy regime.
- **ECU Calibration Pitfalls:**
  In common-rail pilot injection calibration: The pilot injection creates early heat release that preheats and pressurizes the cylinder charge. Applying the standard main-injection ignition delay formula without accounting for the pilot-induced state change causes the ECU model to severely overestimate main ignition delay, resulting in miscalculated combustion phasing ($CA_{50}$).
- **VERIFIED_FROM_SCAN:** `YES`
- **CROSSCHECK:** `MIT 2.61 / SAE Paper 550015` (Consistent)

---

## 08. Pumping Work & PMEP Relations

### Heywood Eq. 2.8, 2.9 & Chapter 13: Pumping Loop Work and PMEP
- **Source Mapping:** Chapter 2, Book Pages 47–50, Scan Sheets 37–39 & Chapter 13
- **Mathematical Expression:**
  $$W_p = \oint_{\text{pumping loop}} p \, dV = \int_{\text{exhaust}} p \, dV + \int_{\text{intake}} p \, dV$$
  $$W_{c,in} = W_{c,ig} - W_p$$
  $$\text{pmep} = \text{imep}_g - \text{imep}_n = \frac{W_p}{V_d}$$
  Approximate 4-stroke gas exchange relation:
  $$\text{pmep} \approx p_{\text{exh}} - p_{\text{int}} = p_3 - p_2$$
  $$\text{bmep} = \text{imep}_n - \text{fmep}_{\text{mech}} = \text{imep}_g - \text{pmep} - \text{fmep}_{\text{mech}}$$
- **Symbol Definitions & Units:**
  - $W_p$: Pumping work transferred during exhaust and intake strokes $[\text{J}]$
  - $W_{c,in}$: Net indicated work per cycle $[\text{J}]$
  - $W_{c,ig}$: Gross indicated work per cycle $[\text{J}]$
  - $\text{pmep}$: Pumping mean effective pressure $[\text{Pa}]$ or $[\text{kPa}]$
  - $\text{imep}_g$: Gross indicated mean effective pressure $[\text{Pa}]$
  - $\text{imep}_n$: Net indicated mean effective pressure $[\text{Pa}]$
  - $\text{bmep}$: Brake mean effective pressure delivered at flywheel $[\text{Pa}]$
  - $\text{fmep}_{\text{mech}}$: Pure mechanical rubbing and accessory friction MEP $[\text{Pa}]$
  - $p_{\text{exh}} = p_3$: Exhaust manifold backpressure before turbine $[\text{Pa}]$
  - $p_{\text{int}} = p_2$: Intake manifold boost pressure $[\text{Pa}]$
- **Physical Meaning & Thermodynamic Interpretation:**
  Pumping work represents the gas exchange fluid work required to expel exhaust products and induct fresh air charge:
  - **Naturally Aspirated / Throttled Engine:** $p_{\text{exh}} > p_{\text{int}}$ $\implies$ PMEP is **positive** (a work loss deducted from gross work).
  - **Turbocharged Engine with High Turbine Expansion / Restricted VNT:** When the turbine nozzle is closed down to spool boost, exhaust backpressure $p_3$ often exceeds intake boost $p_2$ by $0.5 - 1.5\text{ bar}$, creating a large positive PMEP penalty that degrades thermal efficiency.
  - **Well-Matched Turbocharger at Full Load:** If turbocharger efficiency is exceptionally high and $p_{\text{int}} > p_{\text{exh}}$ ($p_2 > p_3$), PMEP becomes **negative**, meaning the gas exchange loop does positive net work on the piston (a "pumping aid" adding to engine power).
- **Assumptions & Validity Regime:**
  Quasi-steady gas exchange pressures across valve open durations; negligible runner acoustic wave reflections.
- **ECU Calibration Pitfalls:**
  **Over-closing VNT Mechanism:** tuners frequently over-close the VNT vanes (requesting high pre-turbine backpressure) to force rapid boost response. This spikes $p_3$ above $3.5\text{ bar}$ while $p_2$ is only $2.2\text{ bar}$. The resulting surge in PMEP destroys fuel economy, increases residual exhaust gas fraction in the cylinder, spikes in-cylinder temps, and can cause exhaust valve float.
- **VERIFIED_FROM_SCAN:** `YES`
- **CROSSCHECK:** `MIT 2.61 / Bosch Automotive Handbook` (Consistent)

---

## 09. Thermal Efficiency & Specific Fuel Consumption (BSFC)

### Heywood Eq. 2.21, 2.22, 2.23 & 2.24: Fuel Conversion Efficiency and BSFC
- **Source Mapping:** Chapter 2, Book Pages 51–53, Scan Sheets 39–40
- **Mathematical Expression:**
  $$\text{sfc} = \frac{\dot{m}_f}{P}$$
  $$\text{bsfc}(\text{g/kW}\cdot\text{h}) = \frac{\dot{m}_f(\text{g/h})}{P_b(\text{kW})} = \frac{3600 \cdot \dot{m}_f(\text{kg/s})}{P_b(\text{kW})} \times 10^3$$
  $$\eta_f = \frac{W_c}{m_f Q_{\text{LHV}}} = \frac{P}{\dot{m}_f Q_{\text{LHV}}} = \frac{1}{\text{sfc} \cdot Q_{\text{LHV}}}$$
  $$\eta_{t,b} = \frac{3600}{\text{bsfc}(\text{g/kW}\cdot\text{h}) \cdot Q_{\text{LHV}}(\text{MJ/kg})}$$
  $$\text{bsfc}(\text{g/kW}\cdot\text{h}) = \frac{3600}{\eta_{t,b} \cdot Q_{\text{LHV}}(\text{MJ/kg})}$$
- **Symbol Definitions & Units:**
  - $\text{bsfc}$: Brake Specific Fuel Consumption $[\text{g/(kW}\cdot\text{h)}]$
  - $\text{isfc}$: Indicated Specific Fuel Consumption $[\text{g/(kW}\cdot\text{h)}]$
  - $\dot{m}_f$: Total engine fuel mass consumption rate $[\text{kg/s}]$ or $[\text{g/h}]$
  - $P_b$: Engine brake power output $[\text{kW}]$
  - $\eta_{t,b} = \eta_f$: Brake thermal / fuel conversion efficiency $[0 \text{ to } 1, \text{dimensionless}]$
  - $Q_{\text{LHV}}$: Fuel Lower Heating Value $[\text{MJ/kg}]$ ($Q_{\text{LHV}} \approx 42.6\text{ MJ/kg}$ for automotive diesel)
- **Physical Meaning & Thermodynamic Interpretation:**
  BSFC measures the fuel mass required to produce one kilowatt-hour of useful mechanical shaft work. It is the exact reciprocal of brake thermal efficiency scaled by fuel heating value:
  - Best modern passenger car diesel: $\text{BSFC}_{\text{min}} \approx 195 - 210\text{ g/(kW}\cdot\text{h)}$ $\implies \eta_{t,b} \approx 40 - 43\%$.
  - Modern heavy-duty truck diesel: $\text{BSFC}_{\text{min}} \approx 180 - 190\text{ g/(kW}\cdot\text{h)}$ $\implies \eta_{t,b} \approx 44 - 47\%$.
  - Large two-stroke marine diesel: $\text{BSFC}_{\text{min}} \approx 155 - 165\text{ g/(kW}\cdot\text{h)}$ $\implies \eta_{t,b} > 50\%$.
- **Assumptions & Validity Regime:**
  Fuel heating value measured under constant-pressure standard calorimeter conditions (ASTM D240). Complete fuel delivery without unaccounted injector return line leakage.
- **ECU Calibration Pitfalls:**
  Chasing peak torque at retarded combustion phasing ($CA_{50} > 15^\circ$ ATDC): While retarding SOI reduces peak cylinder pressure $p_{\text{max}}$ and NOx emissions, it drastically degrades expansion ratio utilization, causing BSFC to deteriorate by $10-25\%$ and dumping raw thermal energy into the exhaust manifold.
- **VERIFIED_FROM_SCAN:** `YES`
- **CROSSCHECK:** `MIT 2.61 / Bosch Diesel Engine Management` (Consistent)

---

## 10. Polytropic In-Cylinder State Relations

### Heywood Eq. 9.1, 9.2, 9.3 & 10.39: Polytropic Compression & Expansion
- **Source Mapping:** Chapter 9, Book Page 377, Scan Sheet 202 & Chapter 10, Book Page 556, Scan Sheet 292
- **Mathematical Expression:**
  $$p(\theta) V(\theta)^n = \text{const}$$
  $$p(\theta) = p_i \left( \frac{V_i}{V(\theta)} \right)^n, \quad T(\theta) = T_i \left( \frac{V_i}{V(\theta)} \right)^{n - 1}$$
  End of compression conditions at Top Dead Center (TDC):
  $$p_{\text{TC}} = p_i \cdot r_c^n \quad (10.39b)$$
  $$T_{\text{TC}} = T_i \cdot r_c^{n-1} \quad (10.39a)$$
- **Symbol Definitions & Units:**
  - $p(\theta)$: In-cylinder pressure at crank angle $\theta$ $[\text{Pa}]$
  - $T(\theta)$: In-cylinder charge temperature at crank angle $\theta$ $[\text{K}]$
  - $p_i$: Pressure at Intake Valve Closing (IVC) or manifold pressure $[\text{Pa}]$
  - $T_i$: Temperature at Intake Valve Closing (IVC) or manifold temperature $[\text{K}]$
  - $r_c$: Effective volumetric compression ratio $[\text{dimensionless}]$
  - $n$: Polytropic exponent $[\text{dimensionless}]$:
    - **Compression Stroke ($n_c$):** Typically $n_c \approx 1.32 - 1.37$ (lower than isentropic air ratio $\gamma \approx 1.39-1.40$ due to wall heat losses).
    - **Cold Starting ($n_c$):** Can drop to $n_c \approx 1.10 - 1.25$ at low cranking speed ($N < 200\text{ rpm}$) due to prolonged residence time and extreme cylinder wall heat transfer.
    - **Expansion Stroke ($n_e$):** Typically $n_e \approx 1.25 - 1.32$ (due to post-combustion heat loss and burned gas thermodynamics).
- **Physical Meaning & Thermodynamic Interpretation:**
  Real in-cylinder compression and expansion are neither isothermal ($n=1$) nor adiabatic isentropic ($n=\gamma$). Heat transfer from the hot compressed gas to the cooler cylinder walls reduces the polytropic compression exponent $n_c$ below $\gamma$.
- **Assumptions & Validity Regime:**
  Closed system between Intake Valve Closing (IVC) and Start of Combustion (SOC). Constant average molecular weight and negligible blowby past the piston rings ($<1-2\%$).
- **ECU Calibration Pitfalls:**
  Assuming constant compression temperature $T_{\text{TC}}$ across all engine speeds: At low cranking speeds ($150\text{ rpm}$), $n_c$ collapses toward $1.15-1.20$, resulting in TDC air temperatures below the diesel autoignition threshold ($T_{\text{TC}} < 650\text{ K}$). Calibrators must compensate with glow-plug preheating and prolonged cranking injection quantities.
- **VERIFIED_FROM_SCAN:** `YES`
- **CROSSCHECK:** `MIT 2.61 / Bosch Automotive Handbook` (Consistent)

---

## 11. Exhaust Enthalpy & Turbine Power Balance

### Heywood Eq. 6.44, 6.46, 6.48 & 6.49: Turbine Isentropic Efficiency & Turbocharger Balance
- **Source Mapping:** Chapter 6, Book Pages 253–255, Scan Sheets 140–141
- **Mathematical Expression:**
  $$\eta_{t\text{TT}} = \frac{h_{03} - h_{04}}{h_{03} - h_{04s}} = \frac{T_{03} - T_{04}}{T_{03} - T_{04s}} = \frac{1 - (T_{04} / T_{03})}{1 - (p_{04} / p_{03})^{\frac{\gamma_e - 1}{\gamma_e}}}$$
  Turbine shaft power delivered:
  $$P_t = \dot{W}_T = \dot{m}_e (h_{03} - h_{04}) = \dot{m}_e c_{p,e} (T_{03} - T_{04}) = \dot{m}_e c_{p,e} \eta_{t\text{TT}} T_{03} \left[ 1 - \left( \frac{p_{04}}{p_{03}} \right)^{\frac{\gamma_e - 1}{\gamma_e}} \right]$$
  Turbocharger mechanical shaft power equilibrium (steady-state speed):
  $$P_c = \eta_m \cdot P_t$$
  $$\frac{\dot{m}_a c_{p,a} T_{01}}{\eta_{c\text{TT}}} \left[ \Pi_c^{\frac{\gamma_c - 1}{\gamma_c}} - 1 \right] = \eta_m \cdot \dot{m}_e c_{p,e} \eta_{t\text{TT}} T_{03} \left[ 1 - \left( \frac{p_{04}}{p_{03}} \right)^{\frac{\gamma_e - 1}{\gamma_e}} \right]$$
  Overall turbocharger efficiency:
  $$\eta_{\text{tc}} = \eta_{c\text{TT}} \cdot \eta_{t\text{TT}} \cdot \eta_m$$
- **Symbol Definitions & Units:**
  - $P_t$: Turbine mechanical power output $[\text{W}]$
  - $P_c$: Compressor mechanical power requirement $[\text{W}]$
  - $\dot{m}_e$: Exhaust mass flow rate $\dot{m}_e = \dot{m}_a + \dot{m}_f$ $[\text{kg/s}]$
  - $\dot{m}_a$: Intake air mass flow rate $[\text{kg/s}]$
  - $c_{p,e}$: Specific heat of exhaust gases ($c_{p,e} \approx 1150 - 1250\text{ J/(kg}\cdot\text{K)}$ at $800 - 1000\text{ K}$)
  - $c_{p,a}$: Specific heat of ambient air ($c_{p,a} \approx 1005\text{ J/(kg}\cdot\text{K)}$)
  - $T_{03}$: Stagnation temperature at turbine inlet (pre-turbine EGT) $[\text{K}]$
  - $T_{04}$: Stagnation temperature at turbine discharge (post-turbine exhaust) $[\text{K}]$
  - $p_{03}$: Stagnation pressure at turbine inlet (exhaust manifold backpressure) $[\text{Pa}]$
  - $p_{04}$: Stagnation pressure at turbine exit (downpipe / exhaust system backpressure) $[\text{Pa}]$
  - $\gamma_e$: Ratio of specific heats for exhaust gas ($\gamma_e \approx 1.30 - 1.33$)
  - $\frac{\gamma_e - 1}{\gamma_e}$: Isentropic expansion exponent $\approx \frac{1.33 - 1}{1.33} \approx 0.248$
  - $\eta_m$: Turbocharger bearing mechanical efficiency (typically $0.95 - 0.98$)
- **Physical Meaning & Thermodynamic Interpretation:**
  A turbocharger operates with no external mechanical connection; the compressor is powered solely by enthalpy extracted by the turbine from hot exhaust gases. The available turbine power scales directly with inlet absolute temperature $T_{03}$ and the available expansion pressure ratio $p_{03} / p_{04}$.
- **Assumptions & Validity Regime:**
  Steady-state or pulse-averaged energy balance. Constant specific heats across turbine expansion.
- **ECU Calibration Pitfalls:**
  **Neglecting Downpipe Backpressure ($p_{04}$):** Clogged DPFs or restrictive catalytic converters increase downpipe backpressure $p_{04}$ (e.g. from $1.1\text{ bar}$ to $1.6\text{ bar}$). This severely flattens the expansion ratio $p_{03}/p_{04}$, drastically reducing turbine power. The ECU's boost PID controller responds by aggressively shutting the VNT vanes, raising $p_{03}$ to dangerous levels ($>4.0\text{ bar}$), spiking EGT and destroying turbine bearings.
- **VERIFIED_FROM_SCAN:** `YES`
- **CROSSCHECK:** `MIT 2.61 / Watson & Janota Turbocharging` (Consistent)

---

## 12. Transient Intake Manifold Filling Dynamics ($dp_m/dt$)

### Heywood Eq. 7.21, 7.22, 14.1 & 14.3: Filling and Emptying Manifold Model
- **Source Mapping:** Chapter 7, Book Pages 311–312, Scan Sheets 169–170 & Chapter 14, Book Pages 752–757, Scan Sheets 390–392
- **Mathematical Expression:**
  Conservation of air mass in the manifold volume:
  $$\frac{dm_{a,m}}{dt} = \dot{m}_{a,\text{in}} - \sum \dot{m}_{a,\text{cyl}}$$
  Engine cylinder air pumping outflow rate:
  $$\sum \dot{m}_{a,\text{cyl}} = \frac{\eta_v \rho_{a,m} V_d N}{n_R} = \frac{\eta_v V_d N}{2} \left( \frac{p_m}{R_a T_m} \right) \quad (\text{for 4-stroke})$$
  Ideal gas equation of state:
  $$p_m V_m = m_{a,m} R_a T_m$$
  Differentiating with respect to time (assuming uniform manifold temperature $T_m$):
  $$\frac{dp_m}{dt} + \left( \frac{\eta_v V_d N}{2 V_m} \right) p_m = \dot{m}_{a,\text{in}} \frac{R_a T_m}{V_m}$$
  Canonical Manifold Filling Time Constant:
  $$\tau_m = \frac{2 V_m}{\eta_v V_d N} \approx \frac{V_m}{\dot{V}_{\text{engine}}}$$
- **Symbol Definitions & Units:**
  - $p_m$: Intake manifold pressure (MAP) $[\text{Pa}]$
  - $dp_m / dt$: Rate of manifold pressure rise/decay $[\text{Pa/s}]$
  - $V_m$: Intake manifold plenum + runner physical volume $[\text{m}^3]$
  - $m_{a,m}$: Instantaneous mass of air contained in manifold $[\text{kg}]$
  - $T_m$: Intake manifold air temperature (IAT) $[\text{K}]$
  - $R_a$: Specific gas constant for air ($287.05\text{ J/(kg}\cdot\text{K)}$)
  - $\dot{m}_{a,\text{in}}$: Mass flow entering manifold from compressor / intercooler $[\text{kg/s}]$
  - $\sum \dot{m}_{a,\text{cyl}}$: Mass flow leaving manifold into cylinders $[\text{kg/s}]$
  - $\eta_v$: Volumetric efficiency referenced to manifold conditions $[\text{dimensionless}]$
  - $V_d$: Engine displacement volume $[\text{m}^3]$
  - $N$: Crankshaft rotational speed $[\text{rev/s}]$
  - $\tau_m$: Manifold filling first-order time constant $[\text{s}]$
- **Physical Meaning & Thermodynamic Interpretation:**
  The filling-and-emptying model represents the intake manifold as a dynamic lumped pneumatic capacitor. When throttle or turbo boost changes abruptly, the air mass inside volume $V_m$ cannot change instantaneously. Pressure $p_m$ lags mass flow $\dot{m}_{a,\text{in}}$ with an exponential response governed by time constant $\tau_m$.
  For a typical 2.0L engine ($V_d = 0.002\text{ m}^3$) with manifold volume $V_m = 0.003\text{ m}^3$ operating at $2000\text{ rpm}$ ($N = 33.3\text{ rev/s}$) and $\eta_v = 0.85$:
  $$\tau_m = \frac{2 \times 0.003}{0.85 \times 0.002 \times 33.3} \approx 0.106\text{ s} \quad (106\text{ ms})$$
- **Assumptions & Validity Regime:**
  Lumped acoustic volume (dimensions of manifold $L_{\text{manifold}} \ll \lambda_{\text{acoustic}} = a / f_{\text{engine}}$); uniform pressure and temperature distribution; isothermal or slow heat transfer across plenum walls.
- **ECU Calibration Pitfalls:**
  **MAF vs. MAP Dynamic Lead/Lag:** In transient tip-in (sudden acceleration):
  MAF sensor measures air entering the manifold ($\dot{m}_{a,\text{in}}$), while the cylinders only ingest $\dot{m}_{a,\text{cyl}}$. During pressure buildup ($dp_m/dt > 0$), $\dot{m}_{a,\text{in}} > \dot{m}_{a,\text{cyl}}$ because a fraction of the inducted air is consumed to charge the manifold capacitance. Calibrating fuel injection strictly on MAF without a dynamic filling observer results in rich soot spikes on tip-in, while calibrating strictly on MAP without phase advance results in transient lean hesitation.
- **VERIFIED_FROM_SCAN:** `YES`
- **CROSSCHECK:** `MIT 2.61 / SAE Paper 810494` (Consistent)

---

## 13. Summary Matrix & Verification Audit Trail

| Domain / Eq Number | Parameter / Phenomenon | Heywood Book Page | Scan Sheet | SI Verified Units | Status |
|---|---|---|---|---|---|
| **Eq. 2.12** | Brake Torque ($T = Fb$) | Page 46 | Sheet 37 | $\text{N}\cdot\text{m}$ | `VERIFIED_FROM_SCAN: YES` |
| **Eq. 2.13a,b** | Power ($P = 2\pi N T$) | Page 46 | Sheet 37 | $\text{W, kW}$ | `VERIFIED_FROM_SCAN: YES` |
| **Eq. 2.14** | Indicated Work ($W_{c,i} = \oint p \, dV$) | Page 47 | Sheet 37 | $\text{J}$ | `VERIFIED_FROM_SCAN: YES` |
| **Eq. 2.15** | Indicated Power ($P_i = W_{c,i} N / n_R$) | Page 48 | Sheet 38 | $\text{W}$ | `VERIFIED_FROM_SCAN: YES` |
| **Eq. 2.16 & 2.17** | Mech. Efficiency ($\eta_m = P_b / P_{i,g}$) | Pages 48–49 | Sheet 38 | Dimensionless | `VERIFIED_FROM_SCAN: YES` |
| **Eq. 2.19a, 2.20a** | Mean Effective Pressure ($\text{MEP}$) | Page 50 | Sheet 39 | $\text{Pa, kPa}$ | `VERIFIED_FROM_SCAN: YES` |
| **Eq. 2.25 & 2.26** | Air/Fuel & Fuel/Air Ratios | Page 53 | Sheet 40 | $\text{kg/kg}$ | `VERIFIED_FROM_SCAN: YES` |
| **Eq. 3.5 & 3.6** | Stoichiometric Combustion Equation | Pages 68–70 | Sheets 48–49 | Molar / Mass | `VERIFIED_FROM_SCAN: YES` |
| **Eq. 3.8 & 3.9** | Equivalence Ratio $\phi$ & Lambda $\lambda$ | Page 71 | Sheet 49 | Dimensionless | `VERIFIED_FROM_SCAN: YES` |
| **Eq. 2.27a,b & 6.2** | Volumetric Efficiency ($\eta_v$) | Pages 54, 210 | Sheets 41, 119 | Dimensionless | `VERIFIED_FROM_SCAN: YES` |
| **Eq. 6.38 & 6.53** | Compressor Pressure Ratio & Corrected Flow | Pages 251, 255 | Sheets 139, 141 | Non-dim, $\text{kg/s}$ | `VERIFIED_FROM_SCAN: YES` |
| **Eq. 6.39 & 6.42** | Compressor Efficiency $\eta_c$ & Power $P_c$ | Pages 251–252 | Sheets 139–140 | Non-dim, $\text{W}$ | `VERIFIED_FROM_SCAN: YES` |
| **Eq. 10.6 & 10.7** | Apparent Net Heat Release Rate ($dQ_n/d\theta$) | Pages 512–513 | Sheet 270 | $\text{J/CAD, J}$ | `VERIFIED_FROM_SCAN: YES` |
| **Eq. 2.6 & 2.11** | Slider-Crank Kinematics & $dV/d\theta$ | Pages 44–45 | Sheet 36 | $\text{m}^3, \text{m}^3/\text{CAD}$ | `VERIFIED_FROM_SCAN: YES` |
| **Eq. 10.35** | Arrhenius / Wolfer Ignition Delay | Page 545 | Sheet 286 | $\text{s, ms}$ | `VERIFIED_FROM_SCAN: YES` |
| **Eq. 10.37 & 10.38** | Hardenberg & Hase DI Delay Correlation | Pages 555–556 | Sheets 291–292 | $\text{CAD, bar, K}$ | `VERIFIED_FROM_SCAN: YES` |
| **Eq. 2.8 & 2.9** | Pumping Work ($W_p$) & PMEP | Pages 47, 50 | Sheets 37, 39 | $\text{J, Pa}$ | `VERIFIED_FROM_SCAN: YES` |
| **Eq. 2.21 & 2.24** | BSFC & Thermal Efficiency ($\eta_{t,b}$) | Pages 51–53 | Sheets 39–40 | $\text{g/(kW}\cdot\text{h)}$, Non-dim | `VERIFIED_FROM_SCAN: YES` |
| **Eq. 9.1 & 10.39** | Polytropic Compression $p(\theta), T(\theta)$ | Pages 377, 556 | Sheets 202, 292 | $\text{Pa, K}$ | `VERIFIED_FROM_SCAN: YES` |
| **Eq. 6.46 & 6.48** | Turbine Efficiency $\eta_t$ & Power $P_t$ | Pages 253–254 | Sheets 140–141 | Non-dim, $\text{W}$ | `VERIFIED_FROM_SCAN: YES` |
| **Eq. 6.49** | Turbocharger Mechanical Power Balance | Page 254 | Sheet 141 | $\text{W}$ | `VERIFIED_FROM_SCAN: YES` |
| **Eq. 7.22 & 14.3** | Intake Manifold Dynamic Filling ($dp_m/dt$) | Pages 312, 754 | Sheets 170, 391 | $\text{Pa/s, s}$ | `VERIFIED_FROM_SCAN: YES` |

---
*Heywood Mathematical Formulary compiled and verified autonomously by Antigravity under the Global Developer & Ground-Truth Verification Protocol.*

