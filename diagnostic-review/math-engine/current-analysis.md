# Calibration math engine — current analysis

Generated from `current-analysis.json` (2026-09-16T13:46:21Z). Current BIN sha256 `d8296554b0342a9a…`, stock reference `cf891152a97fb636…`.

Values in brackets are Monte Carlo P05–P95 (10000 draws). Uncertain inputs and their provenance are listed at the end.

## Pulls used

| pull | gear | rpm | km/h per rpm (MAD) | speed pairs | rpm samples |
|---|---|---|---|---|---|
| 20260916_102349@11.9s | 3 | 1670→3270 | 0.0255 (0.0000) | 2 | 11 |
| 20260916_102349@24.3s | 3 | 1998→3344 | 0.0254 (0.0000) | 1 | 9 |
| 20260916_110755@0.4s | 3 | 1869→3988 | 0.0255 (0.0000) | 1 | 14 |
| 20260916_111930@2.1s | 4 | 1411→4084 | 0.0357 (0.0000) | 5 | 40 |
| 20260916_112035@2.1s | 4 | 1386→4072 | 0.0358 (0.0001) | 5 | 38 |

## Gear 3 — measured vs models

| rpm | MAP mbar | air mg/str | road torque Nm | PS | q cmd mg (limiter) | λ of cmd fuel | fuel-model Nm | implied burned q mg | ECU brake model Nm |
|---|---|---|---|---|---|---|---|---|---|
| 2250 | 2352.0 | 987.0 | 214 [180–247] | 58–79 | 56.5 (smoke) | 1.20 [1.10–1.30] | 304 [280–330] | 41.3 [34.4–48.4] | 282 |
| 2500 | 2328.0 | 984.0 | 273 [231–338] | 82–120 | 56.5 (smoke) | 1.20 [1.10–1.30] | 305 [279–330] | 52.8 [43.9–66.2] | 280 |
| 2750 | 2370.0 | 969.0 | 307 [270–346] | 106–135 | 62.0 (torque_path) | 1.11 [1.02–1.20] | 323 [297–350] | 59.2 [51.3–68.3] | 302 |
| 3000 | 2378.0 | 948.0 | 297 [264–336] | 113–144 | 62.6 (torque_path) | 1.18 [1.08–1.28] | 296 [273–321] | 57.3 [49.9–66.2] | 300 |
| 3250 | 2302.0 | 913.0 | 262 [232–293] | 107–136 | 63.2 (torque_path) | 1.14 [1.04–1.24] | 296 [272–321] | 50.6 [44.0–57.8] | 298 |
| 3500 | 2204.0 | 848.0 | 231 [203–266] | 101–132 | 64.0 (torque_path) | 1.06 [0.97–1.15] | 297 [272–320] | 44.6 [38.4–52.4] | 296 |

## Gear 4 — measured vs models

| rpm | MAP mbar | air mg/str | road torque Nm | PS | q cmd mg (limiter) | λ of cmd fuel | fuel-model Nm | implied burned q mg | ECU brake model Nm |
|---|---|---|---|---|---|---|---|---|---|
| 1750 | 2174.0 | 920.0 | 314 [277–354] | 69–88 | 56.5 (smoke) | 1.12 [1.02–1.22] | 304 [279–329] | 60.5 [52.6–69.7] | 283 |
| 2000 | 2292.0 | 976.0 | 314 [274–357] | 78–102 | 56.5 (smoke) | 1.18 [1.09–1.29] | 305 [279–330] | 60.5 [51.7–70.4] | 284 |
| 2250 | 2297.0 | 986.0 | 307 [257–364] | 82–116 | 56.5 (smoke) | 1.20 [1.10–1.30] | 305 [280–330] | 59.2 [48.6–71.3] | 282 |
| 2500 | 2295.0 | 976.0 | 302 [266–342] | 95–122 | 56.5 (smoke) | 1.18 [1.09–1.29] | 304 [280–330] | 58.4 [50.5–67.5] | 280 |
| 2750 | 2315.0 | 947.0 | 288 [249–330] | 98–129 | 62.0 (torque_path) | 1.08 [0.99–1.18] | 323 [297–350] | 55.7 [47.5–65.0] | 302 |
| 3000 | 2202.0 | 906.0 | 252 [218–288] | 93–123 | 62.6 (torque_path) | 1.13 [1.04–1.23] | 296 [272–321] | 48.5 [41.4–56.8] | 300 |
| 3250 | 2180.0 | 868.0 | 238 [204–279] | 95–129 | 63.2 (torque_path) | 1.08 [0.99–1.18] | 296 [272–321] | 46.0 [38.8–54.7] | 298 |
| 3500 | 2163.0 | 846.0 | 232 [200–272] | 100–135 | 64.0 (torque_path) | 1.06 [0.97–1.15] | 296 [272–321] | 44.8 [38.0–53.2] | 296 |
| 3750 | 2175.0 | 828.0 | 207 [178–241] | 95–129 | 63.9 (torque_path) | 1.03 [0.95–1.12] | 296 [272–321] | 40.0 [33.7–47.9] | 287 |
| 4000 | 2167.0 | 812.0 | 183 [156–212] | 89–121 | 62.1 (torque_path) | 1.01 [0.93–1.10] | 296 [273–321] | 35.2 [29.5–41.9] | 270 |

## Firmware chain (gear 4, static, current vs stock)

| rpm | DW Nm | trqLimP Nm cur/stock | request Nm | q FMTC clamp/extrap mg | smoke last col mg cur/stock | q cmd | SOI hyp ° | dur hyp ° | dur ms | dur ratio cur/stock | elec end proxy ° |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1500 | 374 | 338 / 250 | 338 | 66.1 / 66.5 | 56.5 / 50.0 | 56.5 | 12.91 | 26.46 | 2.94 | 1.079 | 13.55 |
| 1750 | 369 | 367 / 272 | 367 | 64.2 / 72.5 | 56.5 / 50.0 | 56.5 | 14.32 | 27.96 | 2.66 | 1.079 | 13.64 |
| 2000 | 364 | 375 / 278 | 364 | 63.1 / 70.2 | 56.5 / 50.0 | 56.5 | 15.96 | 30.04 | 2.50 | 1.079 | 14.08 |
| 2250 | 359 | 374 / 277 | 359 | 62.6 / 67.9 | 56.5 / 50.0 | 56.5 | 17.25 | 31.17 | 2.31 | 1.079 | 13.92 |
| 2500 | 354 | 364 / 270 | 354 | 61.8 / 65.1 | 56.5 / 50.0 | 56.5 | 18.87 | 32.69 | 2.18 | 1.079 | 13.82 |
| 2750 | 350 | 358 / 265 | 350 | 62.0 / 64.9 | 62.1 / 55.0 | 62.0 | 20.58 | 37.25 | 2.26 | 1.080 | 16.67 |
| 3000 | 345 | 348 / 258 | 345 | 62.6 / 64.8 | 67.8 / 60.0 | 62.6 | 22.24 | 39.16 | 2.18 | 1.079 | 16.92 |
| 3250 | 342 | 342 / 253 | 342 | 63.2 / 64.5 | 67.8 / 60.0 | 63.2 | 24.52 | 39.87 | 2.04 | 1.079 | 15.35 |
| 3500 | 339 | 336 / 249 | 336 | 64.0 / 64.0 | 67.8 / 60.0 | 64.0 | 25.90 | 40.65 | 1.94 | 1.080 | 14.75 |
| 3750 | 336 | 331 / 245 | 331 | 63.9 / 63.9 | 67.8 / 60.0 | 63.9 | 27.53 | 41.35 | 1.84 | 1.079 | 13.82 |
| 4000 | 333 | 319 / 236 | 319 | 62.1 / 62.1 | 67.8 / 60.0 | 62.1 | 29.16 | 42.14 | 1.76 | 1.079 | 12.98 |

## Air-limited torque (gear 4, measured air, η range)

| rpm | air mg | λ=1.05 | λ=1.10 | λ=1.15 | λ=1.20 | λ=1.25 | λ=1.30 | road Nm |
|---|---|---|---|---|---|---|---|---|
| 1750 | 920 | 288–338 | 275–323 | 263–309 | 252–296 | 242–284 | 233–273 | 314 [277–354] |
| 2000 | 976 | 306–358 | 292–342 | 279–327 | 268–314 | 257–301 | 247–289 | 314 [274–357] |
| 2250 | 986 | 309–362 | 295–346 | 282–331 | 271–317 | 260–304 | 250–293 | 307 [257–364] |
| 2500 | 976 | 306–358 | 292–342 | 279–327 | 268–314 | 257–301 | 247–289 | 302 [266–342] |
| 2750 | 947 | 297–348 | 283–332 | 271–317 | 260–304 | 249–292 | 240–281 | 288 [249–330] |
| 3000 | 906 | 284–333 | 271–318 | 259–304 | 249–291 | 239–280 | 229–269 | 252 [218–288] |
| 3250 | 868 | 272–319 | 260–304 | 248–291 | 238–279 | 229–268 | 220–257 | 238 [204–279] |
| 3500 | 846 | 265–311 | 253–296 | 242–284 | 232–272 | 223–261 | 214–251 | 232 [200–272] |
| 3750 | 828 | 259–304 | 248–290 | 237–278 | 227–266 | 218–255 | 210–246 | 207 [178–241] |
| 4000 | 812 | 255–298 | 243–285 | 232–272 | 223–261 | 214–251 | 206–241 | 183 [156–212] |

## Smoke limiter input check

```
{
 "raw_pressure_hpa_where_corrected_reaches_last_smoke_column": {
  "35C": 1915,
  "50C": 2005,
  "65C": 2095,
  "70C": 2130
 },
 "note": "FlMng_pIATCorr_MAP axis input is FlMng_pBPAPCorr_mp; identity with logged MAP is assumed (both are boost pressure in hPa abs)."
}
```

## Automatic findings

**F1 (CALCULATED)** Commanded fuel exceeds what the measured air can burn cleanly (median lambda < 1.10).
- G3 3500 rpm: lambda_cmd 1.06 [0.97-1.15], air 848 mg
- G4 2750 rpm: lambda_cmd 1.08 [0.99-1.18], air 947 mg
- G4 3250 rpm: lambda_cmd 1.08 [0.99-1.18], air 868 mg
- G4 3500 rpm: lambda_cmd 1.06 [0.97-1.15], air 846 mg
- G4 3750 rpm: lambda_cmd 1.03 [0.95-1.12], air 828 mg
- G4 4000 rpm: lambda_cmd 1.01 [0.93-1.10], air 812 mg

**F2 (CALCULATED)** Measured torque is more than 15 % below the energy model of the commanded fuel.
- G3 2250 rpm: road 214 [180-247] Nm vs fuel model 304 Nm
- G3 3500 rpm: road 231 [203-266] Nm vs fuel model 297 Nm
- G4 3000 rpm: road 252 [218-288] Nm vs fuel model 296 Nm
- G4 3250 rpm: road 238 [204-279] Nm vs fuel model 296 Nm
- G4 3500 rpm: road 232 [200-272] Nm vs fuel model 296 Nm
- G4 3750 rpm: road 207 [178-241] Nm vs fuel model 296 Nm
- G4 4000 rpm: road 183 [156-212] Nm vs fuel model 296 Nm

## Candidate plan (PROVISIONAL — no BIN generated)

λ target 1.184 — median commanded-fuel lambda of gear-4 pulls at (2000, 2250, 2500) rpm (measured air, current smoke map).

| map | rpm node | hPa node | address | current mg | candidate mg | raw s16 (hex) | air mg/str |
|---|---|---|---|---|---|---|---|
| FlMng_qPresSmoke_MAP | 3000 | 2000 | 0x1D661A | 67.80 | 54.00 | 5400 (1518) | 906 |
| FlMng_qPresSmoke_MAP | 4000 | 2000 | 0x1D6632 | 67.80 | 47.50 | 4750 (128E) | 812 |

| rpm | q cmd now → new mg | λ cmd now → new | Δ torque Nm | elec end proxy now → new ° | duration ms now → new |
|---|---|---|---|---|---|
| 2750 | 62.0 → 55.2 | 1.08 → 1.18 | 0 [-37–0] | 16.67 → 13.29 | 2.26 → 2.05 |
| 3000 | 62.6 → 54.0 | 1.13 → 1.15 | 0 [-1–0] | 16.92 → 13.62 | 2.18 → 1.98 |
| 3250 | 63.2 → 52.4 | 1.08 → 1.14 | 0 [0–0] | 15.35 → 11.89 | 2.04 → 1.84 |
| 3500 | 64.0 → 50.8 | 1.06 → 1.15 | 0 [0–0] | 14.75 → 10.91 | 1.94 → 1.71 |
| 3750 | 63.9 → 49.1 | 1.03 → 1.16 | 0 [0–0] | 13.82 → 10.47 | 1.84 → 1.64 |
| 4000 | 62.1 → 47.5 | 1.01 → 1.17 | 0 [0–0] | 12.98 → 9.84 | 1.76 → 1.56 |

Validation: gear-4 WOT 2750-4000 rpm: road torque P50 must not fall by more than the pull-to-pull spread; logged IQ (VCDS) must equal the new smoke column within 1 mg where it binds

Abort if:
- road torque P50 at any 3000-3750 rpm bin drops > 15 Nm vs this analysis
- visible smoke unchanged AND logged IQ already below the new cap (cap had no effect)
- any new DTC

Rollback: `03G906021QJ_stage1_full_power_dpf_egr_off.bin`

## Parameters and provenance

| parameter | range / value | status | source |
|---|---|---|---|
| mass_kg | 1360 – 1520 | ENGINEERING_RANGE | Golf V 1.9 TDI curb mass ~1.28-1.35 t by trim/body, plus driver, fuel and cargo. Replace with a weighbridge figure to shrink the dominant uncertainty. |
| cda_m2 | 0.66 – 0.76 | PUBLISHED | Golf V Cd ~0.32 x frontal area ~2.2 m2; +/-7 % for mirrors, roof, ride height. |
| crr | 0.008 – 0.013 | ENGINEERING_RANGE | Passenger-car tyres on asphalt, warm, typical label classes B-E. |
| eta_driveline | 0.9 – 0.95 | ENGINEERING_RANGE | Manual FWD transaxle incl. CV joints, direct/indirect gears 3-4. |
| inertia_engine_kgm2 | 0.15 – 0.3 | ENGINEERING_RANGE | 1.9 TDI crank train + dual-mass flywheel + clutch. |
| inertia_wheels_kgm2 | 2.4 – 4.0 | ENGINEERING_RANGE | Four 16" wheel/tyre assemblies incl. discs and drive shafts. |
| wheel_radius_m | 0.3 – 0.315 | PUBLISHED | 205/55 R16 dynamic rolling radius; only used for wheel inertia term. |
| ambient_temp_k | 283.0 – 303.0 | UNKNOWN_RANGE | Ambient temperature on 2026-09-16 not logged (IAT is post-intercooler). |
| grade_frac | -0.015 – 0.015 | UNKNOWN_RANGE | Road gradient not logged. +/-1.5 % mean grade over a pull. Dominant for absolute torque. |
| speed_scale | 0.97 – 1.03 | ENGINEERING_RANGE | OBD PID 0x0D vs true speed; tyre wear and ECU speed scaling. |
| lhv_j_kg | 42600000.0 – 43100000.0 | PUBLISHED | EN 590 diesel lower heating value, typical 42.6-43.1 MJ/kg. |
| afr_stoich | 14.4 – 14.6 | PUBLISHED | Diesel stoichiometric air/fuel mass ratio ~14.5 (composition dependent). |
| eta_brake_full_load | 0.35 – 0.41 | ENGINEERING_RANGE | Brake efficiency of a small turbo-DI diesel near full load (BSFC ~205-245 g/kWh). Not measured on this engine. |
| displacement_m3 | 0.001896 | PUBLISHED | BLS 1.9 TDI: 1896 cm3, 4 cylinders. |
| n_cyl | 4 | PUBLISHED | BLS inline-4. |
| coolant_c_for_friction | 90.0 | MEASURED | Coolant 91 C in session snapshot of 2026-09-16 logs. |
| charge_temp_c | 35.0 – 65.0 | UNKNOWN_RANGE | Logged IAT 35 C was a stale snapshot (age > 8 s); WOT charge temperature bracketed. |
| ve_expected | 0.8 – 0.95 | ENGINEERING_RANGE | Volumetric efficiency of an 8-valve turbo diesel referenced to manifold conditions. |
| maf_scale | 0.95 – 1.12 | ENGINEERING_RANGE | True air / OBD PID 0x10 reading. Hot-film MAF sensors drift low with age; apparent VE 0.71-0.94 from these logs cannot separate sensor drift from real VE. Asymmetric on purpose. |
