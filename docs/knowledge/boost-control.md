# EDC16 Boost Pressure Control Architecture

## Boost Target Formation

In the Bosch EDC16U34 system for the 1.9 TDI BLS, the target manifold absolute pressure (MAP) is governed by the **PCR (Pressure Charge Regulation)** functional subsystem.

$$	ext{Final Boost Target} = \min\Big(	ext{PCR\_pBDesBas\_MAP}(	ext{RPM}, 	ext{IQ}) + \Delta p_{	ext{ambient}} + \Delta p_{	ext{temp}}, 	ext{PCR\_pBDesMax\_CUR}(	ext{RPM})\Big)$$

### 1. Base Boost Target Map (`PCR_pBDesBas_MAP`)
- **A2L Symbol**: `PCR_pBDesBas_MAP`
- **Offset in SW 1037391847**: `0x1E9A40`
- **Axes**: Engine Speed (RPM, 16 points) × Injected Quantity (mg/stroke, 16 points)
- **Units**: mbar absolute
- **Stage 1 Calibration Peak**: **2350 mbar** at 2250–3500 RPM, 55 mg/stroke.

### 2. Atmospheric & Environmental Corrections
- Altitude compensation (`PCR_pBDesAtm_MAP`): Derates boost request as ambient barometric pressure decreases below 1000 mbar to prevent turbocharger overspeed in thin air.
- Charge temperature compensation (`PCR_pBDesT_MAP`): Derates target if intake air temperature (IAT) exceeds calibrated thermal thresholds.

---

## Closed-Loop Boost Regulation Architecture

```
                    +---------------------------+
                    |  PCR_rBPCtlBas_MAP        |
                    |  (Feed-Forward / Pre-Ctrl)|
                    +---------------------------+
                                  |
                                  v
+-------------------+        [ + / Sum ] -------> [ Actuator Output: N75 PWM % ]
| Boost Error (e)   |             ^
| = Actual - Target |             |
+-------------------+             |
          |             +-------------------+
          +------------>| Closed-Loop PID   |
                        | (P + I + D Terms) |
                        +-------------------+
```

1. **Feed-Forward Control**:
   - Predicts the exact vane position (duty cycle) required to generate the requested boost at the current mass flow and engine speed.
   - Allows instant response without waiting for error to accumulate in the manifold.
2. **Feedback Correction (PID)**:
   - **Proportional (P)**: Immediate counter-reaction proportional to instantaneous boost error.
   - **Integral (I)**: Eliminates steady-state error over time.
   - **Derivative (D)**: Dampens rapid boost rise rate to prevent overshoot.
