# Map Identification and A2L Integration

## A2L Object Resolution

A2L integration should resolve at least:

- `CHARACTERISTIC`, `AXIS_DESCR`, `AXIS_PTS` and referenced axes
- `RECORD_LAYOUT`, datatype, alignment, storage order and active dimensions
- `COMPU_METHOD`, conversion tables, units and conversion direction
- Byte-order overrides, address extensions and memory segments
- Shared, fixed, calculated and externally stored axes
- Variant selection and relevant code references

ASAM MCD-2 MC describes addresses, datatypes, layouts, conversions and calibration objects. Matching the description to the actual executable remains necessary.
Reference: [ASAM MCD-2 MC](https://www.asam.net/standards/detail/mcd-2-mc/)

DAMOS or A2L from a similar software version is supporting evidence until relocation and object compatibility are established.

## Heuristic Scanning

When A2L is unavailable, heuristic scanning may use:
- Plausible dimensions (common sizes: 8×8, 10×10, 12×12, 16×16)
- Monotonic axis values (ascending RPM, ascending load)
- Smooth surface interpolation patterns
- Repeated structures (multiple maps with same layout)
- Physical range plausibility (e.g., injection duration 0–25 ms, boost 0–3.0 bar)

> [!WARNING]
> These features identify **candidates**, not functions. Confirm actual consumers, selection logic, and active extents. Allocated storage can exceed the points used at runtime.

## Object Terminology

| Object | Mathematical form | Storage implication |
|---|---|---|
| Scalar | $z = c$ | One value |
| Curve | $z = f(x)$ | One independent axis |
| Surface | $z = f(x, y)$ | Two independent axes |
| Higher-dimensional | $z = f(x_1, \ldots, x_n)$ | Explicit dimensions and selection semantics |

Editors may call these "1D/2D/3D" inconsistently. Store `axis_count` explicitly.

## Conversion Formulas

### Affine Conversion
$$p = a \cdot r + b$$
$$r' = \text{round}\left(\frac{p' - b}{a}\right), \quad a \neq 0$$

Check representable range before encoding. Reject overflow instead of silently clipping. With nearest-integer rounding, physical quantization error is at most $|a|/2$, provided no clipping occurs.

### Signed Two's Complement (w-bit)
$$r = \begin{cases} u, & u < 2^{w-1} \\ u - 2^w, & u \geq 2^{w-1} \end{cases}$$

Nonlinear, rational, and tabulated conversions require their specified direction and inverse behavior; they must not be flattened into an assumed multiplier.

### Linear Interpolation
$$t = \frac{x - x_i}{x_{i+1} - x_i}$$
$$z = (1 - t) z_i + t \cdot z_{i+1}$$

### Bilinear Interpolation
$$z = (1-t)(1-u)z_{00} + t(1-u)z_{10} + (1-t)u \cdot z_{01} + tu \cdot z_{11}$$

The profile must establish clamping, extrapolation, repeated-breakpoint handling, integer arithmetic, and runtime rounding. Floating-point interpolation is a reference model until those details are verified.

## Primary Map Dependencies (Diesel)

| Map/Function | Typical Inputs → Output | Main Dependency |
|---|---|---|
| Driver Wish | Pedal, RPM → torque or fuel request | Torque arbitration |
| Torque limiters | RPM, environment, state → permitted torque | Engine and transmission limits |
| MAF smoke limiter | Fresh-air mass, RPM → permitted fuel | Oxygen availability, transients |
| MAP smoke limiter | Pressure/load, RPM → permitted fuel | Charge model, temperature, EGR |
| Injection duration | Fuel quantity, pressure/RPM → actuation time/angle | Injector characterization, timing |
| Start of Injection (SOI) | RPM, quantity, temps → timing | Combustion phasing, cylinder pressure |
| Boost target | RPM, load/quantity → pressure request | Air demand, turbo operating envelope |
| Boost limiter | RPM, baro, temp → pressure ceiling | Altitude, compressor capability |
| N75/VNT control | Operating point, error → duty/position | Actuator polarity, feedback, saturation |
| Rail pressure | RPM, fuel demand → pressure request | Common-rail hardware, delivery limits |

> [!NOTE]
> Rail-pressure maps apply to common-rail systems only. Distributor-pump (VP37/VP44) and unit-injector (PDE/PLD) diesels need their own fuel-system branch.

## Primary Map Dependencies (Petrol)

| Map/Function | Typical Inputs → Output | Main Dependency |
|---|---|---|
| Load/MAF model | Sensor data, RPM, temps → charge/load | Torque, fueling, ignition models |
| Target lambda | RPM, load, state → lambda | Fuel, catalyst, component protection |
| Ignition timing | RPM, load → base advance | Knock and combustion limits |
| Knock correction | Cylinder/state → timing correction | Detection, adaptive control |
| WGDC | RPM, load/request → wastegate command | Closed-loop boost control |

## Map Dependency Chain

```
Driver Wish → Torque Arbitration → Fuel Quantity Request
                                         ↓
                   ┌─────────────────────┼───────────────────────┐
                   ↓                     ↓                       ↓
            MAF Smoke Limiter    MAP Smoke Limiter    Rail Pressure Target
                   ↓                     ↓                       ↓
            Permitted Fuel ──────→ Injection Duration ←── Rail Pressure
                                         ↓
                                   Start of Injection
                                         ↓
                              Boost Target ← VNT/N75 Control
                                         ↓
                              Boost Limiter (safety ceiling)
```

Modifying one map without considering its dependencies in this chain can create physical inconsistencies (smoke, excessive temperature, turbo surge).

## Bosch Motorsport Reference
Bosch Motorsport documentation illustrates the dependency from charge/load through fuel mass to injection time, with separate physical corrections. Its labels and values must NOT be transferred directly to production EDC/MED software.
Reference: [Bosch MS 6.x manual](https://www.bosch-motorsport.com/media/downloads/engine_control_unit_ms_6-x_manual.pdf)
