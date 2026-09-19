# EDC16 Torque-Oriented Engine Management

## Architectural Principle

As defined in **VW SSP 304**, EDC16 is a **torque-oriented** engine control system. Unlike older EDC15 systems where the accelerator pedal directly mapped to fuel quantity (mg/stroke), EDC16 treats **torque (Nm)** as the universal internal currency.

```
[Driver Wish / Pedal]  --> [Outer Torque Request]
[Cruise Control / AC]  --> [Outer Torque Request]
                                |
                                v
                   [Torque Coordinator & Filters]
                                |
                                v
               [Friction & Parasitic Subtraction]
                                |
                                v
                   [Indicated / Inner Torque]
                                |
           +--------------------+--------------------+
           |                                         |
           v                                         v
   [Torque Limiter Map]                     [Smoke Limiter]
   (TrqLim_trqEng_MAP)                     (Air/Fuel Lambda)
           |                                         |
           +--------------------+--------------------+
                                |
                                v
                    [Arbitrated Minimum Torque]
                                |
                                v
           [Torque-to-Quantity Conversion Map]
           (TrqConv_qInd_MAP / TrqConv_qEng_MAP)
                                |
                                v
                    [Injected Fuel Quantity (mg/stroke)]
                                |
           +--------------------+--------------------+
           |                                         |
           v                                         v
   [Duration Maps]                           [Start of Injection]
   (InjCrv_phiDur_MAP)                       (InjCrv_phiMI1Des_MAP)
```

## Step-by-Step Torque Flow

1. **Outer Torque Generation**:
   - `DrvDem_tq_MAP`: Inputs are Engine RPM and Accelerator Pedal %; output is requested driver torque in Nm.
2. **Torque Coordinator**:
   - Arbitrates between driver wish, cruise control (GRA), ESP/traction intervention (ASR/MSR), and engine drag torque control.
3. **Inner Torque Conversion**:
   - Accounts for internal mechanical friction, oil pump, alternator, and coolant pump drag (`TrqLoss_trqLoss_MAP`).
4. **Limitation Layer**:
   - `TrqLim_trqEng_MAP`: Primary mechanical torque limiter as a function of RPM and atmospheric pressure. Protects the dual-mass flywheel (DMF), clutch, conrods, and transmission.
5. **Conversion to Injected Quantity**:
   - `TrqConv_qInd_MAP`: Converts indicated torque (Nm) to injected fuel mass (mg/stroke).
