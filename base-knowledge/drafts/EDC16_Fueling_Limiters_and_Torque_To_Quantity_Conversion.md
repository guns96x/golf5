# Fueling Architecture & Limiter Hierarchy

## Fuel Quantity Selection Logic

In Bosch EDC16U34, the final injected quantity ($q_{\text{final}}$ in mg/stroke) delivered to the Pumpe-Düse unit injectors is arbitrated through a strict cascade of limiters:

$$q_{\text{final}} = \min(q_{\text{driver\_wish}}, q_{\text{torque\_limiter}}, q_{\text{smoke\_limiter}}, q_{\text{component\_protection}})$$

```
                                  +-----------------------+
                                  | Driver Wish IQ        |
                                  | (DrvDem_q_MAP)        |
                                  +-----------------------+
                                              |
                                              v
+-----------------------+         +-----------------------+
| Torque Limiter IQ     |-------->| Arbitrated Minimum IQ |
| (TrqLim_q_MAP)        |         | = min(...)            |
+-----------------------+         +-----------------------+
                                              ^
+-----------------------+                     |
| Smoke Limiter IQ      |---------------------+
| (FlMng_qPresSmoke_MAP)|                     |
+-----------------------+                     |
                                              |
+-----------------------+                     |
| Thermal / Derating IQ |---------------------+
+-----------------------+
```

## Diagnostic Verification via VCDS (Measuring Block 008)

During full-throttle acceleration (3rd gear WOT), log **Measuring Block 008**:
- `Field 1`: Engine Speed (RPM)
- `Field 2`: Driver Wish IQ (mg/stroke) — should be highest (~60–70 mg)
- `Field 3`: Torque Limit IQ (mg/stroke) — calibrated mechanical limit
- `Field 4`: Smoke Limit IQ (mg/stroke) — smoke limiter active value

Whichever field (3 or 4) has the **lower value** is the active governing limiter at that exact RPM.
