# A/B comparison — 2026-09-17T15:42:27Z

Gear assumed: 4. Pulls pooled over both directions (median).

| | current | candidate |
|---|---|---|
| n_pulls | 4 | 2 |
| n_full_pulls | 2 | 2 |
| median_time_2750_to_end_s | 12.34 | 13.40 |
| median_peak_map_mbar | 2387 | 2407 |
| median_peak_boost_error_mbar | 194 | 214 |
| median_sample_interval_011_s | 0.35 | 0.18 |
| pulls_crossing_abort_map | 0 | 0 |

| rpm | pulls cur/cand | road torque P50 Nm cur → cand | boost spec / actual cur → cand | N75 % cur → cand | smoke lim Nm cur → cand | MAF mg cur → cand |
|---|---|---|---|---|---|---|
| 2750 | 4/2 | 280 → - | 2193/2362 → 2193/2385 | 26.4 → 27.2 | 333 → 324 | 977 → 955 |
| 3000 | 4/2 | 269 → 250 | 2193/2297 → 2193/2311 | 22.0 → 22.4 | 334 → 334 | 942 → 897 |
| 3250 | 4/2 | 225 → 210 | 2193/2113 → 2193/2081 | 25.5 → 28.2 | 334 → 322 | 830 → 822 |
| 3500 | 3/2 | 217 → 198 | 2193/2156 → 2193/2171 | 26.0 → 28.2 | 334 → 310 | 835 → 817 |
| 3750 | 2/2 | 199 → 198 | 2193/2162 → 2193/2176 | 28.5 → 30.2 | 334 → 300 | 829 → 813 |
| 4000 | 2/2 | 182 → 184 | 2193/2162 → 2193/2173 | 31.4 → 32.2 | 334 → 290 | 806 → 798 |

Pulls:

- current: LOG-01-011-003-xxx.CSV day17 18:14:23@3.2s, groups 011+003, 011 interval 0.35 s, 2750->4116 rpm in 12.18 s, peak MAP 2377, peak error 184
- current: LOG-01-011-008-xxx.CSV day17 18:15:20@0.2s (partial), groups 011+008, 011 interval 0.35 s, 2750->3339 rpm in - s, peak MAP 2397, peak error 204
- current: LOG-01-011-008-xxx.CSV day17 18:15:20@23.4s (partial), groups 011+008, 011 interval 0.35 s, 2750->3612 rpm in - s, peak MAP 2305, peak error 112
- current: LOG-01-011-008-xxx.CSV day17 18:15:20@86.7s, groups 011+008, 011 interval 0.35 s, 2750->4137 rpm in 12.49 s, peak MAP 2397, peak error 204
- candidate: LOG-01-011-003-v61.CSV day17 18:38:23@0.1s, groups 011+003, 011 interval 0.18 s, 2750->4095 rpm in 14.08 s, peak MAP 2417, peak error 224
- candidate: LOG-01-011-008-v61.CSV day17 18:39:16@0.1s, groups 011+008, 011 interval 0.18 s, 2750->4074 rpm in 12.71 s, peak MAP 2397, peak error 204
