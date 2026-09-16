# EDC16 Boost Pressure Control Architecture

## Boost Target Formation

In the Bosch EDC16U34 system for the 1.9 TDI BLS, the target manifold absolute pressure (MAP) is governed by the **PCR (Pressure Charge Regulation)** functional subsystem.

$$\text{Final Boost Target} = \min\Big(\text{PCR\_pBDesBas\_MAP}(\text{RPM}, \text{IQ}) + \Delta p_{\text{ambient}} + \Delta p_{\text{temp}}, \text{PCR\_pBDesMax\_CUR}(\text{RPM})\Big)$$

### 1. Base Boost Target Map (`PCR_pBDesBas_MAP`)
- **Stock Reference High-Load Request**: **2050 mbar** absolute.
- **Stage 1 Active Request**: **2214 mbar** absolute (104 values modified versus stock reference; verified by deep-audit).
- **Units**: mbar absolute.

> [!NOTE]
> Previous draft documentation mistakenly referenced a 2350 mbar ceiling. The actual verified Stage 1 high-load request across the 2000–3500 RPM full-load plateau is **2214 mbar**.

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

1. **Feed-Forward Control (`PCR_rBPCtlBas_MAP`)**:
   - A static 2D starting point for the closed-loop controller.
   - In SW 1037391847, this map remained **100% stock reference** in Stage 1, while boost request was raised from 2050 to 2214 mbar.
2. **Feedback Correction (PID)**:
   - Reacts to dynamic boost error ($e = p_{\text{actual}} - p_{\text{target}}$).
