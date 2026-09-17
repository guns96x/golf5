# A/B comparison — 2026-09-17T15:33:11Z

Gear assumed: 4. Pulls pooled over both directions (median).

| | current | candidate |
|---|---|---|
| n_pulls | 4 | 4 |
| n_full_pulls | 2 | 2 |
| median_time_2750_to_end_s | 12.34 | 12.34 |
| median_peak_map_mbar | 2387 | 2387 |
| median_peak_boost_error_mbar | 194 | 194 |
| median_sample_interval_011_s | 0.35 | 0.35 |
| pulls_crossing_abort_map | 0 | 0 |

| rpm | pulls cur/cand | road torque P50 Nm cur → cand | boost spec / actual cur → cand | N75 % cur → cand | smoke lim Nm cur → cand | MAF mg cur → cand |
|---|---|---|---|---|---|---|
| 2750 | 4/4 | 280 → 280 | 2193/2362 → 2193/2362 | 26.4 → 26.4 | 333 → 333 | 977 → 977 |
| 3000 | 4/4 | 269 → 269 | 2193/2297 → 2193/2297 | 22.0 → 22.0 | 334 → 334 | 942 → 942 |
| 3250 | 4/4 | 225 → 225 | 2193/2113 → 2193/2113 | 25.5 → 25.5 | 334 → 334 | 830 → 830 |
| 3500 | 3/3 | 217 → 217 | 2193/2156 → 2193/2156 | 26.0 → 26.0 | 334 → 334 | 835 → 835 |
| 3750 | 2/2 | 199 → 199 | 2193/2162 → 2193/2162 | 28.5 → 28.5 | 334 → 334 | 829 → 829 |
| 4000 | 2/2 | 182 → 182 | 2193/2162 → 2193/2162 | 31.4 → 31.4 | 334 → 334 | 806 → 806 |

Pulls:

- current: LOG-01-011-003-xxx.CSV day17 18:14:23@3.2s, groups 011+003, 011 interval 0.35 s, 2750->4116 rpm in 12.18 s, peak MAP 2377, peak error 184
- current: LOG-01-011-008-xxx.CSV day17 18:15:20@0.2s (partial), groups 011+008, 011 interval 0.35 s, 2750->3339 rpm in - s, peak MAP 2397, peak error 204
- current: LOG-01-011-008-xxx.CSV day17 18:15:20@23.4s (partial), groups 011+008, 011 interval 0.35 s, 2750->3612 rpm in - s, peak MAP 2305, peak error 112
- current: LOG-01-011-008-xxx.CSV day17 18:15:20@86.7s, groups 011+008, 011 interval 0.35 s, 2750->4137 rpm in 12.49 s, peak MAP 2397, peak error 204
- candidate: LOG-01-011-003-xxx.CSV day17 18:14:23@3.2s, groups 011+003, 011 interval 0.35 s, 2750->4116 rpm in 12.18 s, peak MAP 2377, peak error 184
- candidate: LOG-01-011-008-xxx.CSV day17 18:15:20@0.2s (partial), groups 011+008, 011 interval 0.35 s, 2750->3339 rpm in - s, peak MAP 2397, peak error 204
- candidate: LOG-01-011-008-xxx.CSV day17 18:15:20@23.4s (partial), groups 011+008, 011 interval 0.35 s, 2750->3612 rpm in - s, peak MAP 2305, peak error 112
- candidate: LOG-01-011-008-xxx.CSV day17 18:15:20@86.7s, groups 011+008, 011 interval 0.35 s, 2750->4137 rpm in 12.49 s, peak MAP 2397, peak error 204
