# Незалежний review Stage 1 — 2026-09-10

## Вердикт за специфікацією

Заявлені числові висновки Stage 1 відтворюються прямим читанням `reference-from-hex.analysis-only.bin` і `new-inputs/on/03G906021QJ.Bin` за адресами A2L. Це калібрувальні значення, а не виміряний момент на стенді й не доказ того, що конкретна гілка виконується в ECU. OFF зберігає ці Stage 1 байти: для всіх перевірених ділянок `ON == OFF`.

### Декодування

- A2L задає `BYTE_ORDER MSB_FIRST` (рядок 4538) і `RECORD_LAYOUT Kf_Xs16_Ys16_Ws16` (рядки 715347–715353): два `SWORD` лічильники, осі `SWORD`, `FNC_VALUES SWORD COLUMN_DIR DIRECT`. Для цих MAP правильний плоский індекс — `i = x * ny + y`.
- Перевірені `RAT_FUNC` мають лінійні коефіцієнти: `Trq` `/10` (рядок 714910), `InjMassCyc` `/100` (рядок 711038), `AngleCrS` `/42.6666666666667` (рядок 706498), `Fact` `/8192` (рядок 707932). Від’ємні або дробові фізичні значення нижче є результатом цієї інверсії, а не signed/endianness помилкою.
- Декодер Stage 1 використовує фактичний кінець layout (`pos`) для відсікання змін; це важливо, бо A2L `DP_BLOB` часто більший за активний запис. Перевірені `reserved → actual` байти: `AccPed_*` 342→308, `EngPrt_trqLimP_MAP` 262→178, `FMTC_trq2qBas_MAP` 648→546, `FlMng_qPresSmoke_MAP` 478→444; для SOI, duration і temp MAP фактичний розмір дорівнює reserved.

### Відтворені значення

| Характеристика (A2L) | Координати `x,y` | BIN offset; bytes ref→ON | Фізично ref→ON | Висновок |
|---|---:|---|---:|---|
| `EngPrt_trqLimP_MAP` (A2L 250409–250422) | `2,7` = 900 hPa, 1900 rpm; `i=49` | `0x1D47C8`; `0B04→0EDF` | 282.0→380.7 Nm | рівно +35.00%; це внутрішній torque request/limit, не dyno torque |
| `FMTC_trq2qBas_MAP` (A2L 274149–274162) | `8,14` = 3000 rpm, 314 Nm; `i=142` | `0x1D73FA`; `142E→1666` | 51.66→57.34 mg/cyc | +10.995% |
| те саме | `8,15` = 3000 rpm, 336 Nm; `i=143` | `0x1D73FC`; `1605→1871` | 56.37→62.57 mg/cyc | +10.999% |
| `InjVlv_phiInjMI1_MAP1` (A2L 361359–361369) | `18,13/14` = 5000 rpm, 55/60 mg/hub | `0x1E52B0/52`; `06EB→0778`, `074F→07E4` | 41.5078→44.8125; 43.8516→47.3438 °CrS | +7.96%; main-injection duration, in crank-angle degrees |
| `InjVlv_phiInjMI1_MAP2` (A2L 361428–361438) | `18,13/14` = 5000 rpm, 55/60 mg/hub | `0x1E5532/34`; `06B1→0739`, `06F8→0786` | 40.1484→43.3359; 41.8125→45.1406 °CrS | +7.94–7.96% |
| `InjVlv_phiInjMI1_MAP3` (A2L 361497–361507) | `18,13/14` = 5000 rpm, 55/60 mg/hub | `0x1E57B4/B6`; `0676→06F9`, `06CD→0758` | 38.7656→41.8359; 40.8047→44.0625 °CrS | +7.92–7.98% |
| `InjVlv_phiInjMI1_MAP4` (A2L 361566–361576) | `18,13/14` = 4500 rpm, 50/55 mg/hub | `0x1E5A36/38`; `0570→05DF`, `0602→067D` | 32.625→35.2266; 36.0469→38.9297 °CrS | +7.97–8.00%; RPM виправлено повторним читанням осі |
| `InjCrv_phiBasGear12/34/56_MAP` (A2L 345191, 345260, 345329) | `13,12/13` = 4000 rpm, 55/60 mg/hub; `i=194/195` | `0x1DAABC/BE`; `0480→04DC` in each copy | 27.0→29.15625 °CrS | +7.986%; SOI/start-of-main-injection table |
| `EngPrt_facTempPreTrbn_MAP` (A2L 248747–248760) | `x=4` 804.96 °C, `y=6`; `x=5` 819.96 °C, `y=5` | `0x1D4F2C`; `1FAE→2004`; `0x1D4F3A`; `1EB8→2004` | 0.989990→1.000488; 0.959961→1.000488 | weaker modeled pre-turbine-temperature torque factor in these cells |

All selected axis bytes compare equal in reference, ON and OFF. The duration maps’ axis labels are unchanged: maps 1–3 include 55/60 mg/hub; map 4 includes 50/55 mg/hub. The SOI maps likewise have unchanged RPM and injected-mass axes.

## A2L nominal limits — important non-fault qualification

Do not classify values as newly faulty merely because they exceed a characteristic’s nominal `LOWER_LIMIT/UPPER_LIMIT`, or because duration is negative. The reference already contains such values:

- `InjVlv_phiInjMI1_MAP1` declares −6…40.00781 °CrS, while reference includes −6.75 and 43.8516 °CrS.
- Maps 2–4 declare −6…30 °CrS, while reference maxima are 41.8125, 40.8047 and 36.0469 °CrS respectively.

The valid Stage 1 statement is the reference→ON delta at unchanged axes. A2L nominal limits are metadata/range hints here, not a pass/fail safety specification; the extended limits are wider still.

## Byte classification

The independent accounting agrees with `stage1-physical-audit.json`:

`4851 total = 1949 direct named bytes + 395 additional deduplicated exact-copy bytes + 2231 structural-alternate bytes + 276 opaque trailer bytes`.

The two opaque ranges are `0x1BFF74–0x1C0000` (140 bytes) and `0x1FDF78–0x1FE000` (136 bytes). The 23 structural candidates are structurally consistent with the proxy MAPs, but their symbol identity and runtime selection are explicitly **not verified**. Exact byte identity is not proof of runtime role either. Therefore `2344` is the direct-plus-exact-copy coverage, while `4575` is coverage only after including the unverified structural candidates.

## Якість і межі висновку

**Якість декодування: PASS з caveats.** The record layout, MSB-first UWORD/SWORD reads, `COLUMN_DIR` indexing, RAT_FUNC inversion, actual extents, unchanged axes and byte accounting are internally consistent and reproducible. The old reserved-size view (`stage1-map-review.json`) must not be used to attribute trailing bytes; the deep audit’s actual extents correct that issue.

**Якість діагностичного висновку: NOT PROVEN.** The strongest material mistakes to avoid are:

1. Calling +35% “35% more real engine power/torque”; it is a table value with unchanged axes.
2. Treating the 2231 structural bytes as identified active maps, or treating exact copies as proof of runtime selection.
3. Calling negative duration or A2L nominal-limit exceedance a new Stage 1 fault when the same condition exists in the reference.
4. Calling the temperature-factor edit a global EGT-protection disablement. It changes one pre-turbine torque-factor table at ~805/820 °C; execution, sensor validity and all other protection paths are unverified.
5. Treating the hot-after-aggressive-driving / recovery-after-gentle-cooling symptom as proof that these Stage 1 tables cause the fault. The current OFF image retains them, and there is no ECU readback, Bosch checksum validation, datalog or physical acceptance.

Thus the edits are credible calibration-risk contributors worth isolating in a controlled comparison, but this static audit does not establish the causal fault or make any image flash-ready.
