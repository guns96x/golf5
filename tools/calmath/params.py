"""Uncertain parameters. Each entry: distribution bounds, status, provenance.

status values:
  MEASURED        - taken from this car's logs
  PUBLISHED       - manufacturer/standard figure, range covers trim/tolerance spread
  ENGINEERING_RANGE - physically reasonable bracket, NOT verified for this car; results must show sensitivity
  UNKNOWN_RANGE   - genuinely unknown for the test road/day; bracket chosen wide on purpose
"""

VEHICLE = {
    'mass_kg': {'min': 1360, 'max': 1520, 'status': 'ENGINEERING_RANGE',
                'source': 'Golf V 1.9 TDI curb mass ~1.28-1.35 t by trim/body, plus driver, fuel and cargo. '
                          'Replace with a weighbridge figure to shrink the dominant uncertainty.'},
    'cda_m2': {'min': 0.66, 'max': 0.76, 'status': 'PUBLISHED',
               'source': 'Golf V Cd ~0.32 x frontal area ~2.2 m2; +/-7 % for mirrors, roof, ride height.'},
    'crr': {'min': 0.008, 'max': 0.013, 'status': 'ENGINEERING_RANGE',
            'source': 'Passenger-car tyres on asphalt, warm, typical label classes B-E.'},
    'eta_driveline': {'min': 0.90, 'max': 0.95, 'status': 'ENGINEERING_RANGE',
                      'source': 'Manual FWD transaxle incl. CV joints, direct/indirect gears 3-4.'},
    'inertia_engine_kgm2': {'min': 0.15, 'max': 0.30, 'status': 'ENGINEERING_RANGE',
                            'source': '1.9 TDI crank train + dual-mass flywheel + clutch.'},
    'inertia_wheels_kgm2': {'min': 2.4, 'max': 4.0, 'status': 'ENGINEERING_RANGE',
                            'source': 'Four 16" wheel/tyre assemblies incl. discs and drive shafts.'},
    'wheel_radius_m': {'min': 0.300, 'max': 0.315, 'status': 'PUBLISHED',
                       'source': '205/55 R16 dynamic rolling radius; only used for wheel inertia term.'},
    'ambient_temp_k': {'min': 283.0, 'max': 303.0, 'status': 'UNKNOWN_RANGE',
                       'source': 'Ambient temperature on 2026-09-16 not logged (IAT is post-intercooler).'},
    'grade_frac': {'min': -0.015, 'max': 0.015, 'status': 'UNKNOWN_RANGE',
                   'source': 'Road gradient not logged. +/-1.5 % mean grade over a pull. Dominant for absolute torque.'},
    'speed_scale': {'min': 0.97, 'max': 1.03, 'status': 'ENGINEERING_RANGE',
                    'source': 'OBD PID 0x0D vs true speed; tyre wear and ECU speed scaling.'},
}

FUEL = {
    'lhv_j_kg': {'min': 42.6e6, 'max': 43.1e6, 'status': 'PUBLISHED',
                 'source': 'EN 590 diesel lower heating value, typical 42.6-43.1 MJ/kg.'},
    'afr_stoich': {'min': 14.4, 'max': 14.6, 'status': 'PUBLISHED',
                   'source': 'Diesel stoichiometric air/fuel mass ratio ~14.5 (composition dependent).'},
    'eta_brake_full_load': {'min': 0.35, 'max': 0.41, 'status': 'ENGINEERING_RANGE',
                            'source': 'Brake efficiency of a small turbo-DI diesel near full load (BSFC ~205-245 g/kWh). '
                                      'Not measured on this engine.'},
}

ENGINE = {
    'displacement_m3': {'value': 1.896e-3, 'status': 'PUBLISHED', 'source': 'BLS 1.9 TDI: 1896 cm3, 4 cylinders.'},
    'n_cyl': {'value': 4, 'status': 'PUBLISHED', 'source': 'BLS inline-4.'},
    'coolant_c_for_friction': {'value': 90.0, 'status': 'MEASURED',
                               'source': 'Coolant 91 C in session snapshot of 2026-09-16 logs.'},
}

# Air-density model for speed-density plausibility check (not used as ground truth)
AIR = {
    'charge_temp_c': {'min': 35.0, 'max': 65.0, 'status': 'UNKNOWN_RANGE',
                      'source': 'Logged IAT 35 C was a stale snapshot (age > 8 s); WOT charge temperature bracketed.'},
    've_expected': {'min': 0.80, 'max': 0.95, 'status': 'ENGINEERING_RANGE',
                    'source': 'Volumetric efficiency of an 8-valve turbo diesel referenced to manifold conditions.'},
    'maf_scale': {'min': 0.95, 'max': 1.12, 'status': 'ENGINEERING_RANGE',
                  'source': 'True air / OBD PID 0x10 reading. Hot-film MAF sensors drift low with age; apparent VE '
                            '0.71-0.94 from these logs cannot separate sensor drift from real VE. Asymmetric on purpose.'},
}
