"""EDC16U34 calibration math engine (pure standard-library Python).

Modules:
  a2l        - A2L-driven characteristic decoding (address, record layout, COMPU_METHOD)
  physics    - unit-checked engine/vehicle formulas
  telemetry  - OBD event loading, per-sample time alignment, WOT segmentation, gear ratio
  dyno       - Monte Carlo virtual dyno (road-load inversion)
  params     - uncertain parameters with explicit ranges and provenance
"""
