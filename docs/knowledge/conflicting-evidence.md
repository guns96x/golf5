# Conflicting Evidence & Dispute Resolution

## Conflict Case 1: N75 Actuator Duty Polarity in VCDS

- **Claim A (Common Forum Convention)**: "Higher duty percentage means opening the vanes to decrease boost."
- **Claim B (Pneumatic Mechanics / SSP 304)**: "Higher duty percentage energizes the solenoid to apply vacuum, pulling the actuator rod to close the vanes for maximum spool."
- **Audit Ground Truth**: In this specific EDC16U34 SW 1037391847, numerical table direction is **UNPROVEN statically**. A controlled runtime sign-test must be performed before altering `PCR_rBPCtlBas_MAP`.

---

## Conflict Case 2: Smoke Limiter Selection on BLS

- **Claim A**: BLS uses MAF-based smoke limitation (`FlMng_qAirSmoke_MAP`).
- **Claim B**: BLS factory DPF software uses MAP-based smoke limitation (`FlMng_qPresSmoke_MAP`).
- **Resolution**: **Verified**. A2L inspection and binary comparison confirm `FlMng_qPresSmoke_MAP` at `0x1D6490` is actively modified (+13%) in the DPF software branch.
