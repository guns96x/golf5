# Tuning Disciplines and Emissions Modifications

## Constrained Calibration

Define tuning as constrained calibration. There is no universal "Stage 1 percentage."

For a percentage change:
$$p' = p(1 + \delta)$$

Applying percentage directly to raw storage gives:
$$a[r(1+\delta)] + b$$

This differs from $p(1+\delta)$ when the conversion has a nonzero offset ($b \neq 0$). Percentage operations are also inappropriate for:
- Signed quantities (negative values invert the direction)
- Categorical values (on/off switches, mode selectors)
- Nonlinear conversions (table lookups, rational formulas)
- Near-zero quantities (small absolute changes become huge percentages)

## Duration Scaling Risks

> [!CAUTION]
> Blind duration scaling can increase delivered fuel without updating the ECU's quantity model. It can extend injection later in the cycle and cause smoke or excessive exhaust temperature.

Crank angle vs time relationship:
$$\Delta\theta_{\text{crank}} = 0.006 \cdot RPM \cdot t_{\text{ms}}$$

At 4,000 RPM, 1 ms spans **24 crank degrees**.

With a signed crank-angle coordinate increasing through TDC:
$$EOI = SOI + \Delta\theta$$

Important distinctions:
- Respect the ECU's sign convention for injection timing
- Distinguish electrical energizing time from actual hydraulic injection duration
- Axis relabeling alone does NOT recalibrate the injector

## Air/Fuel Consistency

Simplified air/fuel consistency check:
$$m_f = \frac{m_{\text{fresh air}}}{\lambda \cdot AFR_{\text{stoich}}}$$

Both masses must use the same cylinder/cycle basis. Limitations:
- Fuel composition affects stoichiometric ratio
- EGR displaces fresh air without appearing in MAF reading
- Residual gases affect effective charge
- Transient mixing differs from steady-state

## Turbo Evaluation

Pressure ratio:
$$PR = \frac{p_{\text{compressor outlet,abs}}}{p_{\text{compressor inlet,abs}}}$$

Use absolute pressures and account for intake/intercooler losses. Check operating points against:
- Compressor flow and speed limits
- Efficiency contours
- Surge line (low flow, high PR → instability)
- Choke line (high flow → sonic limitation)

Reference: [Garrett Performance Catalog](https://www.garrettmotion.com/wp-content/uploads/2023/03/Garrett_Performance_Catalog_Volume_9_2023_3_22.pdf)

## Safety Limits

Every tuning brief must supply justified limits for:

| Parameter | Why |
|---|---|
| Exhaust gas temperatures | Turbine, exhaust manifold, catalyst, DPF thermal limits |
| Cylinder pressure | Piston, connecting rod, head gasket mechanical limits |
| Turbo speed | Bearing and wheel burst limits |
| Fuel delivery | Injector flow capacity, pump capacity |
| Driveline torque | Clutch, gearbox, driveshaft ratings |

> [!WARNING]
> Preserving a limiter table is necessary but **insufficient** if altered sensor or torque models make its inputs inaccurate. A smoke limiter that receives wrong MAF values protects nothing.

## Emissions Modifications Analysis

Resolve the requested meaning before proposing changes:

### DPF OFF
| Aspect | Required Analysis |
|---|---|
| Sensor diagnostics | Differential pressure sensor, exhaust temperature sensors |
| Pressure monitoring | Soot load model, backpressure calculation |
| Soot model | Accumulated soot mass, distance since regen |
| Regeneration triggers | Temperature targets, injection timing, post-injection |
| Additive dosing | Cerine/iron-based fuel additive (if equipped) |
| Temperature management | Pre-catalyst, post-catalyst, DPF inlet/outlet temps |
| DTCs | All DPF-related fault codes and their reactions |

### EGR OFF
| Aspect | Required Analysis |
|---|---|
| Valve position control | Target position, PWM duty, feedback |
| Recirculation rate model | Mass flow calculation, dilution ratio |
| Intake temperature | EGR heating effect on charge temperature |
| NOx model | NOx-dependent EGR targets (if present) |
| Turbo interaction | VNT/N75 compensation for EGR flow changes |
| Lambda effects | Mixture changes from removing exhaust gas dilution |

### Adblue/SCR OFF
| Aspect | Required Analysis |
|---|---|
| Injection control | Dosing valve, injector, spray quality |
| Catalyst monitoring | NOx conversion efficiency, NH₃ slip |
| Dosing control | Demand calculation, quality monitoring |
| Quality sensing | NOx sensor, temperature sensors |
| Tank heating | Urea thawing system |
| NOx reduction | Upstream/downstream NOx comparison |

### Lambda OFF
| Aspect | Required Analysis |
|---|---|
| Sensor diagnostics | Heater control, signal plausibility, aging |
| Closed-loop correction | Short-term and long-term fuel trim |
| Target lambda | Enrichment, lean cruise, catalyst protection |
| Catalyst monitoring | Light-off, efficiency, oxygen storage |
| Component protection | Over-temperature enrichment |

## Enable Switch vs Threshold

> [!IMPORTANT]
> The reference must distinguish an **enable switch** from a **threshold**, hysteresis pair, state-machine transition, or diagnostic mask. Threshold changes can make a transition unreachable without deactivating the surrounding function.

## DTC Handling

"DTC zeroing" requires exact semantics: zero may alter reporting, classification, or another field depending on the diagnostic architecture.

> [!WARNING]
> Suppressing a DTC code does **not** prove that the fault reaction, substitute value, regeneration request, or torque intervention is inactive.

For each affected function, require the full chain:

```
trigger → detection → debounce → diagnostic event → reaction → recovery
```

Record the actual changed branch and test relevant operating states. Preserve unrelated diagnostics and protections.

## Legal Considerations

Record jurisdiction and intended use before deployment.

> [!CAUTION]
> An "off-road" label is **insufficient** evidence of legal eligibility. Applicable rules need independent verification.

Reference: [EPA fact sheet on defeat devices and tampering](https://www.epa.gov/enforcement/epa-fact-sheet-re-aftermarket-defeat-devices-and-tampering)
