# Аудит усіх 311 байтів ON → OFF

Дата: 2026-09-10. Аудит виконано лише читанням. BIN, A2L/HEX/S19, SGM та наявні JSON-звіти не змінювалися.

## Короткий висновок

У `new-inputs/on/03G906021QJ.Bin` → `new-inputs/off/03G906021QJ (DPF EGR OFF) NoCS.Bin` змінено 311 байтів у 29 ділянках. Розподіл:

| Група | Діапазони | Байти | Висновок |
|---|---:|---:|---|
| Дублікати payload AirCtl у `0x189xxx` | `0x189E34–0x189E4F`, `0x189F26–0x189F4D` | 68 | Побайтово дорівнюють зміненим payload двох підписаних кривих у `0x1C9xxx`; A2L-символа для `0x189xxx` немає, активність не доведена |
| Підписані AirCtl-криві | `0x1C9DD8–0x1C9DF3`, `0x1C9ECA–0x1C9EF1` | 68 | Фактичні 20-точкові значення `AirCtl_qHigh_CUR`/`AirCtl_qMiddle_CUR` занулено; це пороги моніторингу EGR/TVA, не пряме занулення виходів клапанів |
| Класи DSM | `0x1CF2BD–0x1CF406` (окремі піддіапазони) | 58 | 58 класів діагностичних шляхів змінено на `0`; можуть бути приглушені DTC/повідомлення, але A2L не доводить, що вимкнено самі регулятори |
| EGT/LSU gates | `0x1D4274`, `0x1E8598` | 2 | `EGT_swtEGTActv_C` і `LSU_swtVal_C`: `1→0` |
| Матриця регенерації | `0x1ECA82–0x1ECABD` | 29 | Ненульові значення payload `PFlt_numEngPOp1_CA` занулено; усі 64 value-byte OFF = `0` |
| Ініціалізація моделі DPF | `0x1EF60E–0x1EF60F` | 2 | `PFlt_tSurfInit_C`: raw `0x01F4→0xFFFA` |
| Хвости зарезервованих кривих | `0x1D4922–0x1D4947`, `0x1D4988–0x1D49B5` | 84 | Усі змінені байти після = повторюваний патерн `0x20`; призначення невідоме. Ділянки поза фактичними таблицями за динамічними лічильниками осей, тому це не підтверджена зміна робочого RPM limiter |

Сума: `68+68+58+2+29+2+84 = 311`.

## 1. `0x1D4922` і `0x1D4988`: що саме змінено

У A2L обидві ділянки потрапляють лише в зарезервований розмір характеристик:

* `EngPrt_trqNLimSpr_CUR` @ `0x1D48F8`, reserved `102` bytes. За фактичним заголовком у всіх трьох образах — 6 точок, active `26` bytes, values `0x1D4906–0x1D4911`. Зміна `0x1D4922–0x1D4947` починається на offset `+42`, тобто після active end `0x1D4912`.
* `EngPrt_trqNLim_CUR` @ `0x1D495E`, reserved `102` bytes. Фактичний заголовок — 2 точки, active `10` bytes, values `0x1D4964–0x1D4967`. Зміна `0x1D4988–0x1D49B5` починається на offset `+42`, також поза active end `0x1D4968`.

До: обидва хвости містять структуроподібні S16-послідовності (зокрема `14 82 15 7C 16 76 17 70 18 6A`, потім `27 10` та інші значення). Після: кожен змінений байт дорівнює `0x20`; це повторюваний патерн, але його призначення (заповнювач, очищення чи інше) з наданих матеріалів не встановлюється. Якби помилково трактувати `0x20 0x20` як S16 `8224`, це дало б штучне torque-значення, але такий розрахунок тут не має фізичного сенсу: байти не належать активній таблиці.

Перевірка `active-map-verification.json` підтверджує: осі та значення обох реальних кривих ON/OFF однакові; active-зміни = `0`. Отже, ці 84 байти не доводять зміну робочої відсічки ні в нормальному режимі, ні в режимі system error. A2L — опис калібрувань, а не доказ того, що зарезервований хвіст читається runtime-кодом.

## 2. `0x189xxx`: сильний кандидат на копії, але не доведений runtime-символ

У ON:

* `0x189E34–0x189E4F` побайтово дорівнює `0x1C9DD8–0x1C9DF3` — саме 14 зміненим значенням `AirCtl_qHigh_CUR` (26.00 mg, 3 точки; 33.00 mg, 11 точок).
* `0x189F26–0x189F4D` побайтово дорівнює `0x1C9ECA–0x1C9EF1` — усім 20 зміненим значенням `AirCtl_qMiddle_CUR` (`-0.01`, `22.00`, `31.00` у A2L display-domain).
* У OFF обидві ділянки повністю `00`, як і відповідні `0x1C9xxx` payload; осі та заголовки в `0x1C9xxx` не змінені.

Це робить гіпотезу «копія/тіньовий payload тих самих двох кривих» набагато сильнішою, ніж трактування `0x189xxx` як випадкового шуму. Проте в A2L немає CHARACTERISTIC на цих адресах, немає вказівника або call graph, а `0x189xxx` може бути окремим варіантом/резервом даних. SGM дає лише адресні блоки програмування: `dav_pfu_05` охоплює `0x180000–0x1BFFFF` (рядки 32763–32775), а `dav_pfu_04` — `0x1C0000–0x1FFFFF` (рядки 28033–28045); SGM не є таблицею символів і не підтверджує relocation/runtime-використання `0x189xxx`.

Тому правильний статус: **підтверджена побайтовa копія payload; активність — невизначена**. Не приписувати їй окремий AirCtl-калібрувальний символ і не рахувати її як самостійну робочу карту.

## 3. AirCtl, EGR і TVA

A2L прямо відносить `AirCtl_Monitor` @ line 716327 до «моніторингу та вимкнення керування EGR», а `Exhaust_Gas_Recirculation` @ line 719235 включає `AirCtl_CtlValCalc`, `AirCtl_DesValCalc`, `AirCtl_Governor`, `AirCtl_Monitor`, `EGRCD_Co` і `TVACD_Co`. Окремо `AirCtl_ControlMonitor` описаний як monitoring/switching для EGR/TVA feedforward control.

### `AirCtl_qHigh_CUR` @ `0x1C9DAA`

* A2L: `CURVE`, 20 точок, `Kl_Xs16_Ws16`, `InjMass`; active bytes `82`, values `0x1C9DD4–0x1C9DFB`.
* Змінені лише value indices 2–15 (`0x1C9DD8–0x1C9DF3`). Вісь RPM: `710, 800, 1050, 1260, 1470, 1680, 1890, 2100, 2310, 2520, 2730, 2980, 3000, 3185`.
* ON → OFF у display-domain A2L `InjMass`: `26.00→0.00` для перших 3 точок і `33.00→0.00` для наступних 11. Raw: `0x0A28→0x0000`, `0x0CE4→0x0000`. Масштаб `InjMass` підтверджений `INJ_MASS_RES=0.01` у A2L system constants.
* Опис — верхня гістерезисна межа вимкнення при великій кількості впорскування.

### `AirCtl_qMiddle_CUR` @ `0x1C9EA0`

* A2L: `CURVE`, 20 точок, `InjMass`; values `0x1C9ECA–0x1C9EF1`.
* Вісь RPM: `0, 710, 720, 800, 1050, 1260, 1470, 1680, 1890, 2100, 2310, 2520, 2750, 2760, 3085, 3100, 3500, 3750, 3990, 4200`.
* ON display-domain: `-0.01` (2 точки), `22.00` (3), `31.00` (10), `-0.01` (5). OFF: усі 20 = `0.00`. Raw: `0xFFFF`, `0x0898`, `0x0C1C` → `0x0000`.
* Опис — нижній гістерезисний поріг контролю кількості.

Це зміна порогів у `AirCtl_Monitor`, а не пряме занулення `AirCtl_rEGR_MAP`, `AirCtl_rTVA` чи actuator-driver defaults. A2L не містить comparator/call graph, тому з байтів не можна чесно вирішити, чи нульовий поріг у цій SW-версії: (а) примусово переводить EGR/TVA в shutdown, (б) обходить monitor через умову `threshold>0`, або (в) змінює лише окрему hysteresis-state machine. З урахуванням того, що EGR фізично заглушений, можливий залишковий вплив TVA/дросельної заслінки не виключається: TVA має власні карти/драйвер (`TVACD_Co`) і може використовувати координацію AirCtl під час decel, shutdown або aftertreatment. Це гіпотеза для runtime-логування, не встановлений факт причини гулу/втрати тяги.

## 4. DSM: що приглушено і що може бути замасковано

Усі 58 змінених `DSM_ClaDfp_*` — однобайтові `Kw_Wu8` «Fehlerklasse für Fehlerpfad Dfp_…» за A2L. Усі ON→OFF мають `nonzero→00`:

* Окремі, переважно не пов'язані з DPF, діагностичні шляхи: `AOHtCDHt1/2/3`, `CTSCD`, `AirCtl_GovDevMax/Min`, `AirCtl_GovDevRgnMax/Min`.
* EGR/air/exhaust path: `EGPpCDTPreTrbn`, `EGRCD_CBV`, `EGRCD_Max/Min`, `EGRCD_Sig`, `EGRCD_SigNpl`, `EGRSCD`, `EGRSCD_JamVlv`, `EGRSCD_LgTimeDrft`, `EGRSCD_ShTimeDrft`, `EGRVlv_JamVlv`, `Shtrp_EGRBA`.
* LSU/O2 sensor and monitor path: `LSUCDCircNernst0`, `LSUCDCircPumpCur0`, `LSUCDCircVirtGnd0`, `LSUCDHeater0`, `LSUCDHtCoup0`, `LSUCDO20`, `LSUCDWireIP0`, `LSUCtlRiExc0`, `LSUMonDyn0`, `LSUMonFullLd0`, `LSUMonOvrRun0`, `LSUMonPartLd0`.
* Oxidation/pressure/DPF sensing and protection: `OxiCCDTPre`, `PFltCDPDiff`, `PFltCDTempPre`, `PFltEngPrt`, `PFltPresDynPlaus`, `PFltPresHsChng`, `PFltPresSens`, `PFltPresSensFrz`, `PFltPresSensHsLn`, `PFltPresSensSot`.
* Regeneration/temperature branches: `PFltRgnLckPerm`, `PFltRgnPerm`, `PFltSotSimPresPerm`, `PFltTempDwnStrm`, `PFltTempDwnStrmMax/Min`, `PFltTempPreOxiC`, `PFltTempPrePFlt`, `PFltTempPreTrbn`, `PFltTempPst`, `PFltTempPstPFlt`, `PFltTempSens`, `PFltTempSens2`, `PFltTempUpStrm`, `PFltTempUpStrmMax/Min`.

The names show breadth, not exact implementation. `DSM_ClaDfp_*` is a class/route assignment for a diagnostic fault path; the A2L does not define that class `0` means «disable control». In particular, the same OFF can hide unrelated failures: EGR valve/position/wiring, EGR cooler bypass, air-control governor deviation, exhaust pressure/temperature sensors, LSU heater/pump/Nernst/O2 plausibility, DPF differential-pressure plausibility, and DPF temperature/permission/lockout paths. Therefore «no DTC» or missing VCDS emissions parameters cannot be read as evidence that these components or physical protections are healthy.

Два класи особливо важливо не приписувати DPF без застереження: `DSM_ClaDfp_AOHtCDHt1_C`, `_Ht2_C`, `_Ht3_C` @ `0x1CF2BD–0x1CF2BF` (`01→00`) належать A2L-функції `AOHtCD_Co` — компонентному драйверу `Zuheizer` (дизельний додатковий нагрівач), а не температурі повітря чи DPF. Їх занулення може приховати несправності силових виходів/нагрівачів, зокрема коротке замикання, обрив/відсутність навантаження або перегрів, але не доводить, що нагрівач реально працює чи впливає на симптоми. `DSM_ClaDfp_CTSCD_C` @ `0x1CF2F6` (`0B→00`) належить `CTSCD_Co` — драйверу датчика температури охолоджувальної рідини (`Wassertemperaturfühler Komponententreiber`); A2L має measurement `CTSCD_tClnt` для coolant temperature. Отже, OFF може маскувати дефект/неправдоподібність CTS або його CAN/ADC-сигналу — це окремий, потенційно важливий для heat/load-діагностики шлях, але не доказ зміни самої температури.

## 5. Other direct OFF gates

* `EGT_swtEGTActv_C` @ `0x1D4274`: A2L `VALUE`, `Kw_Wu8`, `OneToOne`; raw `01→00`. The adjacent byte remains `00`, so a BE word viewer may show `0x0100→0`, but the A2L object itself is one byte. Its A2L description is a switch for EGT functions; this is compatible with a wider aftertreatment coordinator, but not proof that every EGT/temperature branch is unreachable.
* `LSU_swtVal_C` @ `0x1E8598`: raw `01→00`; A2L explicitly says LSU functions `1=ON, 0=OFF`. This is a calibration gate, not proof of sensor state or proof that all fuel/aftertreatment logic is gone.
* `PFlt_numEngPOp1_CA` @ `0x1ECA6E`: dynamic A2L extent is 8×8, 82 bytes, values `0x1ECA80–0x1ECA BF`; 29 previously nonzero value bytes changed to `00`. Header/axes are unchanged. OFF has all 64 values zero. This proves one regeneration operating-state matrix was neutralized, not all regeneration/PoI paths.
* `PFlt_tSurfInit_C` @ `0x1EF60E`: raw signed BE `500→-6`. The exact A2L `Temp_Cels` `COEFFS 0 10 2731.4 0 0 1` gives `(raw−2731.4)/10`, hence `-223.14→-273.74 °C` in the linear display domain. This is a DPF surface-model initialization value, not a runtime measured EGT; the extreme value may be a special sentinel, but that meaning is not established by A2L alone.

## 6. Relation to the user's heat/load symptoms

The current user report is that smoke/smell, hot-load droning and power loss persist after the thermostat; with emissions ON, the same loss/drone occurred during regeneration (without smoke while the DPF was installed). EGR is physically blanked. Aggressive heating/load repeatedly triggers the symptoms, while gentle driving cools the car and symptoms disappear cyclically; this is heat/load correlation, not proof of periodic regeneration. Thus a thermostat fix must not be recorded as resolution. The firmware audit supports that OFF is a broad aftertreatment/diagnostic alteration, but it does not establish whether the present event is caused by regeneration, AirCtl/TVA coordination, boost/exhaust restriction, fueling/injector behavior, coolant/temperature-sensor plausibility, or another mechanical issue. The absence of emissions parameters in VCDS is consistent with gates/diagnostic publication changes, but cannot distinguish “function not executing” from “measurement channel suppressed.”

## Evidence and limits

* Raw ranges and byte counts: `diagnostic-review/binary-comparison.json` (`differing_bytes=311`, ranges at lines 85–285).
* Dynamic extents and unchanged active RPM-limiters: `diagnostic-review/active-map-verification.json`.
* A2L characteristic/address/layout index: `diagnostic-review/a2l-characteristics-index.json`.
* A2L definitions: `diagnostic-review/definitions/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.a2l`; SGM block addresses above.
* No disassembly, relocation table, call graph, ECU readback, Auto-Scan/live log, or Bosch internal checksum validation was available. A2L is metadata, not runtime code. `reference-from-hex.analysis-only.bin` is an analysis reference only.
* Build/install/physical acceptance: **NOT RUN / not applicable to this static audit**. No firmware was generated, written, or installed.
