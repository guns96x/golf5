# VNT / N75 Actuator Mechanics & Pre-Control

## Turbocharger Specification

- **Turbocharger Model**: BorgWarner / KKK BV39
- **OEM Part Reference**: `5439 988 0072` / `03G253014M`
- **Type**: Variable Nozzle Turbine (VNT) with pneumatic vacuum actuator and N75 electro-pneumatic solenoid.

---

## Pre-Control Map (`PCR_rBPCtlBas_MAP`)

- **A2L Symbol**: `PCR_rBPCtlBas_MAP` (line 394165 in A2L)
- **Description**: *Basissteuerkennfeld für Ladedruck* (Base control map for charge pressure)
- **Address**: `0x1E9FD0`
- **Actual Dimensions**: **16 × 13** (NOT 16×16!)
- **Axes**: Engine Speed (RPM, 16 points) × Injected Quantity (mg/stroke, 13 points)
- **Data Format**: 16-bit signed, factor 0.01 (% duty)
- **Status in Stage 1**: **Identical to stock reference** (zero changes).

---

## Actuator Duty Cycle Polarity — Statically Unproven

> [!WARNING]
> **Static Data Cannot Prove Actuator Polarity**:
> In VAG EDC16 implementations:
> - Physical vacuum pulls the actuator rod against internal spring pressure to move vanes toward the narrow/closed position (maximum turbine drive).
> - However, whether higher numeric percentage in `PCR_rBPCtlBas_MAP` commands more vacuum or less vacuum in SW 1037391847 is **NOT PROVED from static data alone**.
> - The repository's deep-audit explicitly states:
>   > *"The numerical duty direction is not proved from static data. Use the small N75-A surface only if a sign test proves that lower Prc increases initial boost slope."*
> 
> Therefore, no arbitrary pre-control edits should be applied without first executing a controlled single-group sign-test.

---

## The `N75-A` Micro-Experiment Specification

If a sign-test proves that lower table numbers increase turbine spool drive, the deep-audit defined a conservative **0.2–0.75 percentage-point** test pocket:

| RPM \ IQ | 30 mg | 32 mg | 35 mg | 38 mg | 40 mg | 45 mg | Offset Range |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1750 | 56.53→56.28 | 51.00→50.50 | 49.45→48.95 | 47.14→46.64 | 47.43→47.03 | 47.00→46.80 | `0x1EA0B8–0x1EA0C2` |
| 1900 | 47.42→47.02 | 47.00→46.25 | 44.13→43.38 | 44.34→43.59 | 43.87→43.27 | 45.06→44.76 | `0x1EA0D2–0x1EA0DC` |
| 2000 | 46.00→45.75 | 46.00→45.50 | 43.21→42.71 | 43.03→42.53 | 43.34→42.94 | 43.96→43.76 | `0x1EA0EC–0x1EA0F6` |

Status: **HOLD** until sign-test logging is completed.
