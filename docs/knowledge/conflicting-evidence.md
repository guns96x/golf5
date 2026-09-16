# Conflicting Evidence & Dispute Resolution

## Conflict Case 1: N75 Actuator Duty Polarity in VCDS

- **Claim A (Tuner forum consensus)**: "80% duty cycle means the N75 valve is opening the vanes to reduce boost."
- **Claim B (Bosch & VW SSP 304)**: "80% duty cycle energizes the solenoid to apply vacuum, pulling the actuator rod to CLOSE the vanes for maximum turbine drive and boost increase."
- **Authority / Applicability**:
  - Claim A: Authority 2, Applicability 3
  - Claim B: Authority 5, Applicability 5
- **Verdict**: **Claim B is verified**. Physical logging proves that duty starts at ~80% during spool-up and drops to 60–65% as boost stabilizes.

---

## Conflict Case 2: Smoke Limiter Selection on BLS

- **Claim A**: BLS uses MAF-based smoke limitation (`FlMng_qAirSmoke_MAP`).
- **Claim B**: BLS factory DPF software uses MAP-based smoke limitation (`FlMng_qPresSmoke_MAP`).
- **Resolution**: A2L code inspection confirms that DPF software branch switches primary smoke limitation to MAP-based curve.
