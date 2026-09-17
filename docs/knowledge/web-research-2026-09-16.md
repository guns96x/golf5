# External research: EDC16U34 1.9 TDI PD (BLS/BKC) tuning practice, bugs and diagnostics

Collected 2026-09-16. Generated from `knowledge/13_reports/` JSON by `tools/ingest_findings.py`; also stored in `knowledge/edc16_knowledge.db` (tables `sources`, `claims`, `conflicts`).

Status legend: `OEM_SPEC` factory documentation · `PROJECT_VERIFIED` confirmed with this car's BIN/A2L/logs · `CORROBORATED` ≥2 independent external sources · `LEAD` single external source, unverified · `CONTRADICTED` conflicts with project data.

## Duration maps and selector

| status | claim | source | relevance to this car |
|---|---|---|---|
| `CORROBORATED` | A Stage 1 for EDC16 PD 1.9 105 hp extended Duration Map 0 for 60 mg (linear extrapolation), extended SOI maps via EOI calculation with the duration selector, and recalibrated the SOI limiter. — «Duration Map 0 - extended axis for 60 iq using linear extrapolation ... Start of Injection Limiter - calibrated to allow new 60 iq deegrees» | [1st tune stoic linear EDC16 PD 1.9 tdi (Seat Leon 2, 105 hp)](https://www.ecuedit.com/1st-tune-stoic-linear-edc16-pd-1-9-tdi-t17197) (forum, authority 2) | Our Stage 1 left MAP0 stock (axis ends 55 mg) and the SOI limiter stock: delivered fuel eq. drops 66 -> 56 mg from 3000 to 4000 rpm. |
| `CORROBORATED` | If duration maps are not extended for a higher IQ, the ECU cannot physically inject the requested quantity beyond what the duration maps cover. — «if I change my max fuel injection to 70mg/str in Torque limiter and Smoke limiter ... so I need to update my duration maps as well» | [GOLF PD 150 ARL - DURATION and SOI maps](https://www.ecuedit.com/golf-pd-150-arl-duration-and-soi-maps-t5658) (forum, authority 2) | Explains the MAP0 fuel cap at 3500-4000 rpm. |
| `CORROBORATED` | PD duration map selection uses the requested SOI and linearly interpolates between two neighbouring duration maps; SOI itself shifts with coolant, atmospheric pressure and intake temperature. — «Required SOI 24 deg -> selected duration indexes 1 and 0 -> final duration (30.0+29.8)/2» | [krook1024/edc15-eoi - Diesel engine fuel timing calculations](https://github.com/krook1024/edc15-eoi) (community_guide, authority 3) | Same structure verified in our A2L: InjVlv_numMI1_CUR selects MAP0..MAP6 by InjCrv_phiMI1Des. |

## SOI and end of injection

| status | claim | source | relevance to this car |
|---|---|---|---|
| `CORROBORATED` | Injection ending after ~10 deg ATDC gives little extra power but sharply raises EGT; a PD130 tune with 43 deg duration and SOI 25 deg (EOI 18 ATDC) destroyed the turbo within minutes. — «injection after 10 deg ATDC doesn't make significant power increase, but egt starts to be very high» | [SOI AND DURATION (General tuning)](https://www.ecuedit.com/soi-and-duration-t4113) (forum, authority 2) | Current BIN map-EOI 14-17 deg ATDC at 2750-4000 rpm vs stock 5.3-6.2 deg. |
| `CORROBORATED` | Rule of thumb: EOI best near TDC, target before ~6 deg ATDC; ~10 deg ATDC still acceptable; ~2 mg per degree of crank rotation. — «EOI has to be around 6 ATDC or before - best 0 TDC» | [GOLF PD 150 ARL - DURATION and SOI maps](https://www.ecuedit.com/golf-pd-150-arl-duration-and-soi-maps-t5658) (forum, authority 2) | Stock BLS calibration keeps map-EOI 5.3-8.5 deg ATDC at WOT, consistent with this rule. |
| `LEAD` | When duration or IQ is increased, SOI must be advanced correspondingly to keep EOI in place. — «if you incrise injection duration or IQ you have to increase too SOi» | [SOI AND DURATION (General tuning)](https://www.ecuedit.com/soi-and-duration-t4113) (forum, authority 2) | Stage 1 added +10..13 deg duration but only +1..2 deg SOI. |
| `CORROBORATED` | EDC16U34 SOI limiter map caps SOI at 28 deg crank angle; tuners must rework it when advancing SOI. — «SOI limit is 28 Crank angle in SOI Limiter map. I will rework.» | [VW Golf 1.9 TDI PD 102 hp EDC16U34 ori, mappack and stage 1](https://www.ecuedit.com/vw-golf-1-9-tdi-pd-102-hp-edc16u34-ori-mappcak-and-stage-1-t20994) (forum, authority 2) | Our InjCrv_phiMIMax_MAP is stock (28.01 deg from 3500 rpm, 16.0-18.0 deg at 1750-2500); Stage 1 SOI is clipped at 2250, 2500 and 4000 rpm. |

## Smoke limiter

| status | claim | source | relevance to this car |
|---|---|---|---|
| `PROJECT_VERIFIED` | EDC16U34 limits fuel by boost pressure (FlMng_qPresSmoke_MAP) corrected for IAT (FlMng_pIATCorr_MAP); a MAF smoke map exists but is empty/unused. — «ECU limits fuel based on boost/MAP, which is corrected for IAT ... A map for MAF based smoke limiter is empty in my ECU» | [How Bosch EDC16(U34) works - basic functionality explained](https://hr.hajes.org/car-hackers-guide-bosch-edc16u34-basic-functionality-explained/) (community_guide, authority 3) | Verified: switches FlMng_swtSmokeVariant_C=1, swtqLimSmkQ_C=1; FlMng_qAFSCDSmoke_MAP all 10.0; VCDS 008 smoke limitation 309.9 Nm = inverse FMTC of 56.5 mg. |
| `PROJECT_VERIFIED` | Factory lambda smoke-limit map (inactive in this calibration) targets lambda 1.17-1.25 at 2000-4242 rpm - an OEM anchor for full-load lambda. — «FlMng_rLmbdSmkLim0_MAP rows 2000: 1.10-1.20, 3000: 1.15-1.25, 3759-4242: 1.20-1.25» | [Project analysis: current BIN / stock HEX / ON file decoded via matching A2L](repo://diagnostic-review/math-engine/DECISION-2026-09-16.md) (project_measurement, authority 4) | Use as target lambda instead of arbitrary constants. |

## BLS-specific tuning advice

| status | claim | source | relevance to this car |
|---|---|---|---|
| `LEAD` | Experienced PL tuner advice for BLS: ~330 Nm from 2250 rpm held to 3000 rpm, boost max ~2250 mbar, keep lambda maps original; author's log-based estimate ~125-130 hp at 4000 rpm. — «maki4evers: changed your lambda maps to ori ... boost ceiling 2250 instead of 2330» | [First Try: VW Golf Variant 2009 1.9 TDI BLS (Rate My Tune)](https://www.ecuedit.com/first-try-vw-golf-variant-2009-1-9-tdi-bls-t12300) (forum, authority 2) | Our file requests up to 375 Nm and targets 2214 mbar with transients to 2417 mbar. |
| `LEAD` | Reviewer reports 142 hp on an Octavia 1.9 PD over 450,000 km with 2350 mbar maximum boost; criticised a BLS tune for missing driver wish, lambda and limiter maps and a wrong checksum. — «achieved 142 HP ... using 2350 mBar maximum turbo pressure» | [Rate Tune - Golf V 1.9 TDI BLS EDC16U34](https://www.ecuedit.com/rate-tune-golf-v-1-9-tdi-bls-edc16u34-t11854) (forum, authority 2) | Upper boost reference; not measured on this car. |
| `LEAD` | A boost limiter of 2300 mbar at 860 mbar atmospheric pressure was criticised as turbo-killing at altitude; experienced tuner advised keeping stock values near 5200-5300 rpm. — «will kill your turbo if you drive on high mountains» | [VW Golf 1.9 TDI PD 102 hp EDC16U34 ori, mappack and stage 1](https://www.ecuedit.com/vw-golf-1-9-tdi-pd-102-hp-edc16u34-ori-mappcak-and-stage-1-t20994) (forum, authority 2) | PCR_pBDesMaxAP_MAP in our file raised ~8%; check at low ambient pressure. |

## Expected results (PD105 Stage 1)

| status | claim | source | relevance to this car |
|---|---|---|---|
| `LEAD` | Darkside remap for PD105 (BKC/BJB/BXE/BLS): 140-150 bhp from 105 bhp. — «Stock Power: 105bhp Darkside Remap: 140-150bhp» | [Darkside Developments - Dyno Graph Results](https://www.darksidedevelopments.co.uk/dyno-graph-results/) (tuner_site, authority 2) | This car measures ~116 PS P50 (100-135 PS P05-P95) on the current file. |
| `LEAD` | Tuner claim for Golf 5 1.9 TDI 105: 140 PS / 320 Nm. — «105 PS auf 140 PS (+33%) ... 250 Nm auf 320 Nm» | [Golf 5 1.9 TDI 105hp Chiptuning 105 -> 140 PS](https://www.hirsch-racing.de/chiptuning/volkswagen/golf/golf-5-2003-2008/19-tdi-105hp/) (tuner_site, authority 2) |  |
| `LEAD` | Tuner page for Touran 1.9 PD 105: 132 hp / 302 Nm (page states the chart is an estimate, not measured). — «Power 105 -> 132 ... Torque 250 -> 302» | [Volkswagen Touran TDI 1.9 PD 105 ECU Tuning](https://alttune.com/tuning/volkswagen-touran-19736/) (tuner_site, authority 2) |  |
| `LEAD` | Owner report: smooth-curve Storm Development remap of a PD105 peaked at 135 hp with constant pull. — «the peak HP was only increased to 135. The pull through out the rev was constant» | [Remap for 1.9 PD 105BHP 2006](https://www.briskoda.net/forums/topic/488179-remap-for-19-pd-105bhp-2006/) (forum, authority 2) |  |
| `LEAD` | Healthy BKC tolerates Stage 1 up to 130-140 hp at 280-300 Nm if injector corrections stay within +/-2.5 mg/stroke, turbo geometry is free, no smoke under load; stock 228 mm clutch holds 320-340 Nm long-term; specified vs actual boost should differ by at most 100 mbar. — «korekty wtryskow w zakresie +/-2,5 mg/skok ... Solladedruck vs. Istladedruck powinien sie roznic o maks. 100 mbar» | [BKC vs BXE vs BLS porownanie awaryjnosci i trwalosci](https://tdi-tuning.pl/bkc-vs-bxe-vs-bls-porownanie-awaryjnosci-i-trwalosci/) (tuner_site, authority 2) | Our VCDS shows +122..+214 mbar overshoot and -71..-143 mbar undershoot. |

## Fuel supply and mechanical checks

| status | claim | source | relevance to this car |
|---|---|---|---|
| `OEM_SPEC` | Tandem pump test: at least 3.5 bar at idle and 7.5 bar at 4000 rpm (VAS 5187, coolant >= 85 C). If 7.5 bar is reached only with the return line clamped, replace unit-injector O-rings; otherwise replace the tandem pump. — «Specified value: at least 7.5 bar (0.75 MPa) ... Replace O-rings for unit injectors» | [Octavia II 1.9/77 kW TDI PD - Inspecting tandem pump](https://workshop-manuals.com/skoda/octavia-mk2/drive_unit/1.9/77_kw_tdi_pd_engine/fuel_supply_gas_operation/removing_and_installing_parts_of_the_fuel_supply_system/inspecting_tandem_pump_(superb_ii_octavia_ii_fabia_ii_roomster)/) (oem_manual, authority 5) | Cheap test for the fuel-delivery hypothesis at high rpm. |
| `LEAD` | A drifting MAF reads low and the car goes soft without a fault; PD cam/follower wear and exhaust restriction produce losses that build with rpm and load. — «A drifting MAF reads low, the ECU reduces fueling to match, and the car goes soft with no fault stored» | [1.9L TDI Loss of Power: Causes and a Diagnosis Checklist](https://www.coredieselparts.com/blogs/news/1-9l-tdi-loss-of-power-causes-and-a-diagnosis-checklist) (community_guide, authority 2) | On this ECU fuel is limited by boost, not MAF, so a low MAF does not cut WOT fuel here (verified switches). |
| `LEAD` | Hot-film MAF sensors drift: author measured about -10 % error at 220k km. — «My 12 years old MAF sensor with 220k km had -10% reading error» | [How Bosch EDC16(U34) works - basic functionality explained](https://hr.hajes.org/car-hackers-guide-bosch-edc16u34-basic-functionality-explained/) (community_guide, authority 3) | Consistent with apparent VE 0.71-0.94 in our logs; kept as MAF uncertainty 0.95-1.12. |
| `LEAD` | A healthy MAF on a TDI reports over 1000 mg/stroke at full power in group 003; a faulty one stays static or below 500 mg/stroke. — «A healthy like-new MAF will report airflow over 1,000 mg/str at full power» | [Testing for a Faulty MAF w/ VCDS on a TDI](https://idparts.instantdocsbase.com/help/testing-for-a-faulty-maf-w-vcds-on-a-tdi) (community_guide, authority 3) | Our group 003: 960-1025 mg at 2000-2500 rpm, 785-813 mg at 3750-4000 rpm. |

## DPF/EGR delete side effects

| status | claim | source | relevance to this car |
|---|---|---|---|
| `LEAD` | On BLS DPF delete pipes only the lambda sensor boss is kept; pre-turbo EGT sensor stays in the manifold; other EGT and pressure sensors are removed only if the software removes their faults, otherwise leave them plugged in. — «If your tuner cannot remove these faults, the sensors should be left plugged in and wrapped out of the way» | [Darkside 2.5in DPF Delete Downpipe for 1.9 8v TDI BLS](https://darksidedevelopments.com/products/darkside-2-5-stainless-dpf-delete-downpipe-for-1-9-8v-tdi-bls-brm-2-0-8v-tdi-bmp-bmm.html) (tuner_site, authority 2) | Current file has LSU_swtVal_C=0 and EGT_swtEGTActv_C=0; physical sensor state on this car unknown. |
| `PROJECT_VERIFIED` | Fuel, torque, boost, duration and SOI maps are byte-identical between the pre-delete Stage 1 (DPF/EGR ON) and the current OFF file; functional differences are LSU/EGT switches, EGR AirCtl thresholds, PoI2, DSM classes, PFlt init and the restored 805-820 C thermal-factor rows (<= 4 %). — «a2l.load() comparison of new-inputs/on vs 03G906021QJ_stage1_full_power_dpf_egr_off.bin» | [Project analysis: current BIN / stock HEX / ON file decoded via matching A2L](repo://diagnostic-review/math-engine/DECISION-2026-09-16.md) (project_measurement, authority 4) | Calibration differences do not explain a 20-30 % loss above 3000 rpm. |

## Stage 1 structural bugs found in this file

| status | claim | source | relevance to this car |
|---|---|---|---|
| `PROJECT_VERIFIED` | Stage 1 scaled InjVlv_phiInjMI1_MAP1..4 by x1.08 at 55/60 mg but left MAP0 stock (axis to 55 mg); as SOI rises with rpm the selector moves to MAP0 and delivered fuel (stock-equivalent) falls from 66.2 mg at 3000 to 56.3 mg at 4000 rpm at constant request. — «selector 0.97 @3000 -> 0.14 @4000; stock-equivalent q 66.2 -> 56.3 mg» | [Project analysis: current BIN / stock HEX / ON file decoded via matching A2L](repo://diagnostic-review/math-engine/DECISION-2026-09-16.md) (project_measurement, authority 4) |  |
| `PROJECT_VERIFIED` | Stage 1 advanced SOI maps but left the SOI limiter InjCrv_phiMIMax_MAP stock; runtime SOI is clipped at 2250 (-0.26 deg), 2500 (-0.87 deg) and 4000 rpm (-1.15 deg). — «SOI map 17.25/18.87/29.16 vs limiter 16.99/18.00/28.01» | [Project analysis: current BIN / stock HEX / ON file decoded via matching A2L](repo://diagnostic-review/math-engine/DECISION-2026-09-16.md) (project_measurement, authority 4) |  |
| `PROJECT_VERIFIED` | Stage 1 lengthened WOT duration by +6..+13 deg but advanced SOI only +0.5..+2 deg: map-EOI moved from stock 5.3-8.5 deg ATDC to 13.6-16.9 deg ATDC. — «3000 rpm: stock dur 26.37 SOI 20.60 EOI 5.77; current dur 39.16 SOI 22.24 EOI 16.92» | [Project analysis: current BIN / stock HEX / ON file decoded via matching A2L](repo://diagnostic-review/math-engine/DECISION-2026-09-16.md) (project_measurement, authority 4) | Late injection = low torque conversion, high EGT, little black smoke: matches measured realization 0.77-0.89 without smoke. |

## Conflicts

| topic | A | B | explanation | experiment | verdict |
|---|---|---|---|---|---|
| Expected PD105 Stage 1 power vs this car | Darkside remap for PD105 (BKC/BJB/BXE/BLS): 140-150 bhp from 105 bhp. | Stage 1 lengthened WOT duration by +6..+13 deg but advanced SOI only +0.5..+2 deg: map-EOI moved from stock 5.3-8.5 deg ATDC to 13.6-16.9 deg ATDC. | Tuner figures are marketing/dyno-corrected and assume a coherent calibration; this file has three structural inconsistencies (MAP0, SOI limiter, EOI) and is measured by road dyno with P05-P95 100-135 PS. | Rolling-road dyno or repeat VCDS 011/003/008 road pulls after a coherent SOI/duration fix. | Not a contradiction of physics: the gap is explained by calibration coherence, not by the engine's potential. |

## Sources

- [First Try: VW Golf Variant 2009 1.9 TDI BLS (Rate My Tune)](https://www.ecuedit.com/first-try-vw-golf-variant-2009-1-9-tdi-bls-t12300) — forum, ecuedit.com, 2016-02
- [1st tune stoic linear EDC16 PD 1.9 tdi (Seat Leon 2, 105 hp)](https://www.ecuedit.com/1st-tune-stoic-linear-edc16-pd-1-9-tdi-t17197) — forum, ecuedit.com, 2018
- [VW Golf 1.9 TDI PD 102 hp EDC16U34 ori, mappack and stage 1](https://www.ecuedit.com/vw-golf-1-9-tdi-pd-102-hp-edc16u34-ori-mappcak-and-stage-1-t20994) — forum, ecuedit.com, 2019-09
- [Rate Tune - Golf V 1.9 TDI BLS EDC16U34](https://www.ecuedit.com/rate-tune-golf-v-1-9-tdi-bls-edc16u34-t11854) — forum, ecuedit.com, 2016-01
- [SOI AND DURATION (General tuning)](https://www.ecuedit.com/soi-and-duration-t4113) — forum, ecuedit.com, 2013-11..2014-01
- [GOLF PD 150 ARL - DURATION and SOI maps](https://www.ecuedit.com/golf-pd-150-arl-duration-and-soi-maps-t5658) — forum, ecuedit.com, 2014-04
- [How Bosch EDC16(U34) works - basic functionality explained](https://hr.hajes.org/car-hackers-guide-bosch-edc16u34-basic-functionality-explained/) — community_guide, Hajes Racing (hajes.org)
- [krook1024/edc15-eoi - Diesel engine fuel timing calculations](https://github.com/krook1024/edc15-eoi) — community_guide, GitHub
- [Octavia II 1.9/77 kW TDI PD - Inspecting tandem pump](https://workshop-manuals.com/skoda/octavia-mk2/drive_unit/1.9/77_kw_tdi_pd_engine/fuel_supply_gas_operation/removing_and_installing_parts_of_the_fuel_supply_system/inspecting_tandem_pump_(superb_ii_octavia_ii_fabia_ii_roomster)/) — oem_manual, Skoda workshop manual (mirror)
- [PD tandem pump pressure, what is normal?](https://forums.tdiclub.com/index.php?threads/pd-tandem-pump-pressure-what-is-normal.350512/) — forum, TDIClub, 2012-04
- [Darkside Developments - Dyno Graph Results](https://www.darksidedevelopments.co.uk/dyno-graph-results/) — tuner_site, Darkside Developments
- [Darkside 2.5in DPF Delete Downpipe for 1.9 8v TDI BLS](https://darksidedevelopments.com/products/darkside-2-5-stainless-dpf-delete-downpipe-for-1-9-8v-tdi-bls-brm-2-0-8v-tdi-bmp-bmm.html) — tuner_site, Darkside Developments
- [BKC vs BXE vs BLS porownanie awaryjnosci i trwalosci](https://tdi-tuning.pl/bkc-vs-bxe-vs-bls-porownanie-awaryjnosci-i-trwalosci/) — tuner_site, TDI-TUNING.PL
- [Volkswagen Touran TDI 1.9 PD 105 ECU Tuning](https://alttune.com/tuning/volkswagen-touran-19736/) — tuner_site, Alt Tune
- [Golf 5 1.9 TDI 105hp Chiptuning 105 -> 140 PS](https://www.hirsch-racing.de/chiptuning/volkswagen/golf/golf-5-2003-2008/19-tdi-105hp/) — tuner_site, Hirsch Racing
- [Remap for 1.9 PD 105BHP 2006](https://www.briskoda.net/forums/topic/488179-remap-for-19-pd-105bhp-2006/) — forum, BRISKODA, 2020-12
- [1.9L TDI Loss of Power: Causes and a Diagnosis Checklist](https://www.coredieselparts.com/blogs/news/1-9l-tdi-loss-of-power-causes-and-a-diagnosis-checklist) — community_guide, CoreDieselParts
- [Testing for a Faulty MAF w/ VCDS on a TDI](https://idparts.instantdocsbase.com/help/testing-for-a-faulty-maf-w-vcds-on-a-tdi) — community_guide, IDParts
- [VCDS: Checking injector values](https://www.vag-coding.net/tutorials-information/vcds-checking-injector-values/) — community_guide, VAG Coding
- [Project analysis: current BIN / stock HEX / ON file decoded via matching A2L](repo://diagnostic-review/math-engine/DECISION-2026-09-16.md) — project_measurement, guns96x/golf5, 2026-09-16
