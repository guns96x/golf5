# A/B test protocol: current Stage 1 vs vNext6.1 (agreed 2026-09-17)

Candidate: `firmware-candidates/03G906021QJ_vNext6.1_fuel-3000-4000-gated_CS_OK.bin`, sha256 `f9d05f8318ca587da63c85c5d9d76e6131b5024ec49c2ffb0599403ea09a0248`.
Baseline: `03G906021QJ_stage1_full_power_dpf_egr_off.bin`.

One variable per experiment: this test changes fuel only. Boost/N75 is analysed separately and is not changed here.

## Where
- **4th gear WOT 2750→4000** (~98→143 km/h): only on a safe, legal, closed or empty section.
- **5th gear WOT 2750→4000** (~128→186 km/h): **dyno or closed track only, never a public road**. Until then, gear 5 at 3000–4000 stays HOLD.

## How (road-dyno)
- Same road section, **both directions**, identical series for each firmware:
  1. current A→B
  2. current B→A
  3. flash vNext6.1
  4. vNext6.1 A→B
  5. vNext6.1 B→A
- At least 2 pulls per direction. Engine warm (coolant ≥ 80 °C). Similar weather and load (passengers, fuel level).
- About 1 minute of steady driving between pulls, so the turbo and intercooler recover.

## VCDS logging
- **Group 011 at the highest possible rate.** Do not trade 011 sample rate for a third group.
  - Pass 1: **011 + 008**. Boost requested/actual, N75 duty, smoke/torque limitation.
  - Pass 2: **011 + 003**. Boost and MAF.
  - A single 011+003+008 log is acceptable only if its real sample interval, checked in the CSV, is short enough for boost dynamics.
- Log the whole pull, from before full throttle to after the lift.

## Abort (lift immediately)
- Actual boost rising fast **and** actual − requested error growing, with N75 already pulling duty down to correct it. Lift early; do not wait for an absolute value.
- In any case at ≥ 2450 mbar.
- Visible smoke, knock or harsh combustion, or any MIL/DTC.

## Compared per rpm bin (analysis after upload)
- Pull time and rpm rate (road torque) for each direction, then averaged.
- Boost requested/actual, N75, smoke and torque limitation (008).
- MAF (003), IAT.
- Decision on the 49.55 mg @ 4000 node only after this data. Boost/N75 overshoot is a separate follow-up experiment.
