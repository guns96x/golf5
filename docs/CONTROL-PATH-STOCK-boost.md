# CONTROL-PATH-STOCK — шлях наддуву

**Область дії.** VW Golf 5 1.9 TDI BLS, Bosch EDC16U34-3.42, HW `03G 906 021 QJ`,
**SW `1037391847`**, проєкт `P447_HAXN`. Джерело фактів про прошивку —
`diagnostic-review/definitions/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.a2l`,
sha256 `04ab636a3f56…`, 16 772 об'єкти (11 537 CHARACTERISTIC, 5 220 MEASUREMENT,
15 AXIS_PTS).

**Це опис СТОКУ.** Тут немає жодної рекомендації що змінювати. Мета першого
зрізу — зрозуміти, як заводська логіка веде педаль до N75, і чесно позначити,
де закінчується доведене.

**Нічого з цього не є межею компонента.** Усі числа й стелі нижче — уставки ECU.
`PCR_pBDesMaxAP_MAP` — це лімітер прошивки, а не допустимий тиск BV39.

## Як читати статуси

| Статус | Що означає тут |
|---|---|
| **PROVEN** | існування об'єкта, його адреса, тип і осі прочитані з A2L цієї прошивки (`MAP_FACT` / `project_matched`) |
| **MODELED** | величина в ECU обчислюється моделлю, а не міряється (наприклад, оберти турбіни) |
| **UNKNOWN** | з наявних доказів не випливає; у базі заведено `gap` із тим, що саме потрібно |

Окремо: **PROVEN ≠ значення відомі напевно.** Для частини мап значення тепер
декодовані з `reference-from-hex.analysis-only.bin` через
`tools/decode_boost_path_stock.py` (адреса, RECORD_LAYOUT і COMPU_METHOD беруться
з A2L, нічого не вгадується). Але цей BIN сам **РЕКОНСТРУЙОВАНИЙ з hex, а не
знятий з машини** — тому такі значення позначені `MAP_FACT` / `raw`, а не
`verified`: вони описують те, що прошите в ЦЬОМУ конкретному образі, а не
обов'язково поточний стан машини. Прогалина P1 тепер `PARTIAL`, не `OPEN` —
структура і числа з реконструкції є, живого readback немає (окрема прогалина).

Кожне твердження нижче лежить у `ecu-kb`; цитати документів перевірені дослівно
(`python kb.py check` — 0 порушень), декодовані значення перевірені прогоном
скрипта проти A2L і сирих байтів. Вихідні файли:
`ecu-kb/claims/boost-path-stock.json`, `ecu-kb/claims/boost-path-values.json`,
`ecu-kb/claims/turbo-bv39-scope.json`, повні решітки —
`diagnostic-review/math-engine/boost-path-stock-values.json`.

---

## Ланцюг

```
   педаль                AccPed_rAPP          0x7F962C
      │  AccPed_trqEng0..6_MAP  (n × педаль),  вибір AccPed_stGearSel_CUR
      ▼
   запит моменту водія
      │  Gearbx_trqMaxGear1..6_CUR · EngPrt_trqNLim_CUR · EngPrt_trqLimPBoost_MAP
      │  CoVeh_trqLim_CUR · CoEng_trqLimErr_CUR        ← порядок арбітражу UNKNOWN
      ▼
   внутрішній момент     CoEng_trqInrSet      0x7F97B6   «inneres Moment Sollwert (>Mengenberechnung)»
      │  FMTC_trq2qBas_MAP   (n × момент)
      ▼
   маса палива
      │  димова межа: FlMng_qAFSCDSmoke_MAP (n × повітря/цикл), FlMng_qPresSmoke_MAP
      ▼
   InjCtl_qCurr 0x7F9AAE ──► PCR_qDes 0x7F9BCC  (для уставки)
                        └──► PCR_qCtl 0x7F9BCA  (для попереднього керування)
      │
      ├─ уставка:       PCR_pBDesBas_MAP (n × PCR_qDes) × корекції → PCR_pBDes 0x7F9BC0
      │                 стеля PCR_pBDesMaxAP_MAP (n × атм. тиск)
      │
      ├─ feedforward:   PCR_rBPCtlBas_MAP (n × PCR_qCtl) × корекції
      │
      └─ регулятор:     PCR_facP/I/D_MAP (n × InjCtl_qCurr), DT1, пороги вмик./вимик.
                        зворотний зв'язок BPSCD_pFltVal 0x7F96B4
                                  │
                                  ▼
                        PCR_rBPGov 0x7F9BD6 → межі PCR_rBPGovMax/Min_MAP
                                  │  лінеаризація PCR_rBPGovLin_CUR
                                  ▼
                        PCR_rBPACD 0x7F9BCE «Stellgröße für den Ladedrucksteller»
                                  │  BPACD_rCnv_CUR: ступінь відкриття → шпаруватість
                                  ▼
                        N75 (вакуумний клапан) → вакуумна камера → лопатки VTG
```

---

## Стрілка 1. Педаль → запит моменту водія

**Функція:** `AccPed` (197 об'єктів, 20 мап і кривих).
**Статус: PROVEN (структура).**

| Об'єкт | Адреса | Осі | Роль |
|---|---|---|---|
| `AccPed_trqEng0_MAP` | `0x1C2CCE` | `Eng_nAvrg` × `AccPed_rAPP` | 1-ша передача / загальний випадок |
| `AccPed_trqEng1..6_MAP` | `0x1C2E24`…`0x1C34D2` | те саме | по передачах (до 6-ї) |
| `AccPed_trqEng0Cold_MAP` | `0x1C2B78` | — | холодний двигун |
| `AccPed_stGearSel_CUR` | `0x1C2B30` | `AccPed_rVnTrqEngActv_mp` | вибір та інтерполяція між мапами передач |
| `AccPed_trqEngLim_MAP` | `0x1C3628` | — | максимальна тягова частка бажання водія |
| `AccPed_trqEngLow_MAP` | `0x1C369A` | — | мінімальне значення бажання водія |

Опис `AccPed_trqEng3_MAP` в A2L: «4.Gang: (voreilendes) Zugwunschmoment aus
Mot.-Drehz. und AccPed_rChkdVal». Тобто вихід — **момент**, а не паливо, і вже
на цьому етапі він залежить від передачі.

**Чого бракує:** значення комірок; умови перемикання холодної мапи.

## Стрілка 2. Запит моменту → лімітери

**Статус: PROVEN (перелік), UNKNOWN (арбітраж).**

| Об'єкт | Адреса | Осі | Що обмежує |
|---|---|---|---|
| `Gearbx_trqMaxGear1..6_CUR` | `0x1D84E2`…`0x1D8618` | — | момент по передачі (захист КПП) |
| `EngPrt_trqNLim_CUR` | `0x1D495E` | `Eng_nAvrg` | обмеження за обертами, у внутрішньому моменті |
| `EngPrt_trqLimPBoost_MAP` | `0x1D471E` | `APSCD_pVal` × `Eng_nAvrg` | захист двигуна «при активному наддуві» |
| `EngPrt_qLimPBoost_MAP` | `0x1D45EE` | `APSCD_pVal` × `Eng_nAvrg` | те саме, але в масі палива |
| `CoVeh_trqLim_CUR` | `0x1CCEAA` | — | системна помилка |
| `CoEng_trqLimErr_CUR` | `0x1CCC08` | — | системна помилка |

Пара `EngPrt_trqLimPBoost` / `EngPrt_qLimPBoost` цікава тим, що обмеження
задане **одночасно в моменті й у паливі** — тобто в прошивці є обидва шари, і
плутати їх не можна.

**UNKNOWN:** як саме вони комбінуються — min-select, пріоритет, рампа? З A2L це
не випливає. Заведено прогалину «Встановити порядок арбітражу лімітерів моменту».

## Стрілка 3. Момент → маса палива

**Функція:** `FMTC`. **Статус: PROVEN (структура).**

| Об'єкт | Адреса | Осі |
|---|---|---|
| `FMTC_trq2qBas_MAP` | `0x1D729C` | `Eng_nAvrg` × `CoEng_trqInrSet` |
| `FMTC_trq2qRgn1..4_MAP` | `0x1D7524`…`0x1D7560` | окремі мапи для режимів регенерації DPF |

Змінна `CoEng_trqInrSet` (`0x7F97B6`) в A2L підписана «inneres Moment Sollwert
(>Mengenberechnung)» — стрілка «момент → розрахунок кількості» названа самим
документом прошивки.

## Стрілка 4. Димова межа

**Функція:** `FlMng`. **Статус: PROVEN (структура).**

| Об'єкт | Адреса | Осі | Роль |
|---|---|---|---|
| `FlMng_qAFSCDSmoke_MAP` | `0x1D61D2` | `Eng_nAvrg` × `FlMng_mAirPerCyl_mp` | димова межа за повітрям на циліндр |
| `FlMng_qPresSmoke_MAP` | `0x1D6490` | `Eng_nAvrg` × `FlMng_pIATCorr_mp` | димова межа за тиском |
| `FlMng_dSmokeMapNr_CUR` | `0x1D5F10` | температура двигуна | вибір мапи з набору |
| `FlMng_facCorAP_CUR` | `0x1D5F4C` | атм. тиск | корекція |
| `FlMng_facCorAirTemp_CUR` | `0x1D5F1A` | темп. повітря | корекція |
| `FlMng_facCorEngTemp_CUR` | `0x1D5F7E` | темп. двигуна | корекція |
| `FlMng_qDynSmoke_MAP` | `0x1D63EC` | — | динамічне підвищення на перехідних |

Це місце, де повітря обмежує паливо. Наддув сюди входить опосередковано — через
`FlMng_mAirPerCyl_mp` і `FlMng_pIATCorr_mp`.

## Стрілка 5. Паливо → уставка наддуву

**Функція:** `PCR` (355 об'єктів: 228 CHARACTERISTIC + 127 MEASUREMENT; 73 мапи
і криві). **Статус: PROVEN (структура).**

Ключовий факт: **уставка наддуву будується від обертів і ПАЛИВА, не від моменту.**

| Об'єкт | Адреса | Осі | Роль |
|---|---|---|---|
| `PCR_pBDesBas_MAP` | `0x1EB0B2` | `Eng_nAvrg` × `PCR_qDes` | базова уставка |
| `PCR_pBDesBas2_MAP` | `0x1EAF3A` | те саме | друга система (див. UNKNOWN) |
| `PCR_facAT_CUR` | `0x1EAD28` | `IATSCD_tAir` | поправка за темп. впускного повітря |
| `PCR_facEAT_CUR` | `0x1EAE56` | `EATSCD_tAir` | поправка за темп. довкілля |
| `PCR_facCtQ_MAP` | `0x1EAD6A` | `CTSCD_tClnt` × `PCR_qDes` | поправка за темп. ОР |
| `PCR_pAPQCmpn_MAP` | `0x1EAE70` | `APSCD_pVal` × `PCR_qDes` | поправка за атм. тиском |
| `PCR_pNQCtCmpn_MAP` | `0x1EBCFA` | `Eng_nAvrg` × `PCR_qDes` | поправка |
| **`PCR_pBDesMaxAP_MAP`** | `0x1EB22A` | `Eng_nAvrg` × `APSCD_pVal` | **стеля уставки** |
| `PCR_facShftUpCor_MAP` | `0x1E9204` | `Eng_nAvrg` × `BPSCD_pFltVal` | корекція при перемиканні вгору |

Результат — `PCR_pBDes` (`0x7F9BC0`, «Ladedrucksollwert»).

**Статус: PROVEN (значення, з застереженням).** У `reference-from-hex.analysis-only.bin`
`PCR_pBDesBas_MAP` сягає стелі **2050 гПа абс.** у зоні `rpm≈2247–3990` при
`PCR_qDes≥40 мг/хід`; на холостому ході (rpm=0) стоїть **198 гПа** для будь-якого
палива — це, найімовірніше, значення-заглушка для вимкненого двигуна, а не
реальна уставка. `PCR_pBDesMaxAP_MAP` при атмосферному тиску ≥900 гПа дає стелю
**2200 гПа** — ВИЩЕ за стелю самої базової мапи. Тобто на рівні моря обмежувальним
фактором є не висотна таблиця, а сама базова мапа `PCR_pBDesBas_MAP`; висотна
таблиця стає активним обмежувачем лише коли атмосферний тиск падає (на висоті —
при 600 гПа стеля падає до 1500 гПа, що числами підтверджує якісне твердження
SSP 304 нижче).

OEM-підтвердження логіки на рівні сімейства, **VW SSP 304, стор. 15**:

> Charge pressure control works depending on the torque demand. To control the
> charge pressure, signals from the charge pressure sender are used. The signals
> from the intake air temperature sender, coolant temperature sender and the
> altitude sensor are used as correction factors.

Зверни увагу на розбіжність рівнів: документ каже «залежить від запиту моменту»,
а прошивка бере віссю мапи **паливо** (`PCR_qDes`). Це не суперечність — паливо
саме й отримане з моменту на стрілці 3, — але доказ у нас саме на паливо.

## Стрілка 6. Висота і модель обертів турбіни

**Статус: MODELED.**

| Об'єкт | Адреса | Осі | Роль |
|---|---|---|---|
| `PCR_nTrbn_MAP` | `0x1E97B0` | `PCR_facBPAltCorr_mp` × `PCR_dmAirAltCorrFl_mp` | «Verdichterkennfeld zu Ermittlung der Laderdrehzahl» |
| `PCR_nTrbn2_MAP` | `0x1E92FC` | — | «Verdichterkennfeld» (друга система) |
| `PCR_nTrbnMax_CUR` | `0x1E978E` | `Eng_nAvrg` | максимальні оберти нагнітача |
| `PCR_facBPAltMax_MAP` | `0x1E8EDA` | `PCR_nTrbnMax_mp` × `PCR_dmAirAltCorr_mp` | допустиме відношення тисків на висоті |
| `PCR_facBPAltCorr_C` | `0x1E8C90` | — | нормований перепад на інтеркулері |

**У прошивці є компресорна карта.** Це означає, що ECU оцінює оберти турбіни за
відношенням тисків і витратою повітря — і обмежує наддув, щоб не перевищити
`PCR_nTrbnMax_CUR`. Оберти при цьому **не міряються**: ототожнювати модель із
реальними обертами BV39 не можна.

**Знахідка: сама межа обертів у цьому образі не задана.** Сирі байти
`PCR_nTrbnMax_CUR` у `reference-from-hex.analysis-only.bin` — `0x7FFF` (32767)
у всіх 8 точках осі rpm без винятку. Це максимальне представиме 16-бітне
знакове число, класичний сентинел «не задано». Після переведення в фізичні
одиниці (×10) це дає безглузді 327670 об/хв — не реальну межу. Перевірено на
сирих байтах, а не лише через decoder:

```
адреса 0x1E978E: 00 08 0000 02bc 0578 0834 0af0 0dac 1068 1388
                 7fff 7fff 7fff 7fff 7fff 7fff 7fff 7fff
                 ^^^^ n=8 точок осі rpm ^^^^  ^^^^ 8× значення = усі 0x7FFF ^^^^
```

Дві гіпотези лишаються нерозрізненими без живого readback: (а) цей конкретний
ліміт свідомо не задіяний у калібровці — обмеження обертів турбіни робиться
десь-інде; (б) це артефакт реконструкції з hex. Для практики висновок
однаковий: **ЦЯ крива в ЦЬОМУ образі нічого не обмежує.**

OEM-підтвердження призначення групи, **VW SSP 304, стор. 15 і 27**:

> The charge pressure is reduced gradually when the vehicle is travelling at
> high altitudes to protect the charger.

> The signal is used to determine a correction value for charge pressure control
> and exhaust gas recirculation.

## Стрілка 7. Попереднє керування (feedforward)

**Статус: PROVEN (структура).**

| Об'єкт | Адреса | Осі |
|---|---|---|
| `PCR_rBPCtlBas_MAP` | `0x1E9FD0` | `Eng_nAvrg` × `PCR_qCtl` |
| `PCR_rBPCtlGear_MAP` | `0x1EA1AE` | — (холостий хід) |
| `PCR_facCtlBas_CUR` | `0x1E9DB6` | `APSCD_pVal` |
| `PCR_facCtlAT_CUR` | `0x1E9D50` | темп. повітря |
| `PCR_rCtlAPCmpn_MAP` | `0x1EAC34` | `APSCD_pVal` × `PCR_qCtl` |

Окрема гілка палива для керування (`PCR_qCtl`, «für die Steuerung benutztes
Einspritzmengensignal») і для уставки (`PCR_qDes`, «Einspritzmenge für
Sollwertbildung») — тобто feedforward і setpoint живляться **різними**
сигналами кількості. Це важливо: міняти «мапу наддуву» і думати, що це одне й
те саме місце, — помилка.

## Стрілка 8. Регулятор

**Статус: PROVEN (структура), UNKNOWN (сама структура регулятора).**

| Об'єкт | Адреса | Осі | Роль |
|---|---|---|---|
| `PCR_facP_MAP` | `0x1EC0C6` | `Eng_nAvrg` × `InjCtl_qCurr` | адаптація P |
| `PCR_facI_MAP` | `0x1EBFD2` | те саме | адаптація I |
| `PCR_facD_MAP` | `0x1EBEDE` | те саме | адаптація D |
| `PCR_DT1_MAP` | `0x1EBDEA` | — | стала часу DT1-ланки |
| `PCR_qRgtOn_CUR` | `0x1EC2EA` | `Eng_nAvrg` | поріг вмикання регулятора за кількістю |
| `PCR_qRgtOff_CUR` | `0x1EC242` | `Eng_nAvrg` | поріг вимикання |
| `PCR_pBGDevMax_CUR` | `0x1EC994` | темп. ОР/оливи | максимальне допустиме відхилення |
| `PCR_tiCoStrt_CUR` | `0x1EC9CC` | — | час, на який регулятор вимкнений після старту |

Зворотний зв'язок — `BPSCD_pFltVal` (`0x7F96B4`, «gefilterter Wert des
Ladedrucks»).

**UNKNOWN:** ці мапи дають **множники адаптації**, а не самі Kp/Ki/Kd. Базові
коефіцієнти і структура (PI + DT1 чи повний PID) з A2L не випливають.

**Статус: PROVEN (значення множників, з застереженням).** У
`reference-from-hex.analysis-only.bin`: `PCR_facP_MAP` плоский по площині —
**0.4** на низьких-середніх обертах (до ~2400), **0.3** вище; P практично не
залежить від навантаження, лише злегка від обертів. `PCR_facI_MAP` навпаки
зростає з обертами й навантаженням: **0.1** на холостому й малому
навантаженні, до **0.4** на високих обертах і повній кількості палива.
`PCR_facD_MAP` веде себе схоже на I — **0** на малому навантаженні незалежно
від обертів, до **0.2–0.3** на високому навантаженні. Тобто множники I і D
зростають разом, а P — практично сталий: адаптація в цій калібровці підсилює
інтегральну й диференціальну складові на високому навантаженні, а не
пропорційну.

OEM-підтвердження замкненого контуру для 1.9 TDI PD, **VW SSP 209, стор. 35**:

> The engine control unit compares the actual measured value with the setpoint
> from the charge pressure map. If the actual value deviates from the setpoint,
> then the engine control unit adjusts the charge pressure via the solenoid
> valve for charge pressure control.

## Стрілка 9. Обмеження виходу і лінеаризація

**Статус: PROVEN (структура).**

| Об'єкт | Адреса | Осі |
|---|---|---|
| `PCR_rBPGovMax_MAP` | `0x1EC52C` | `Eng_nAvrg` × `InjCtl_qCurr` |
| `PCR_rBPGovMin_MAP` | `0x1EC6A4` | `Eng_nAvrg` × `InjCtl_qCurr` |
| `PCR_rBPGovLin_CUR` | `0x1EC4D6` | `PCR_rBPGovUnLin_mp` (%) |

Плюс окремі стелерні значення для особливих режимів: `PCR_rBPGearChng_MAP`
(`0x1EC41C`, перемикання передач), `PCR_rBPOvrRun_MAP` (`0x1EC89A`, примусовий
холостий хід), `PCR_rBPAPRatMin_MAP` (`0x1EC352`, поріг розпізнавання скидання
газу) — усе під підписом «noise suppression» / «Anti-Kaudern».

**Статус: PROVEN (значення, з застереженням).** У `reference-from-hex.analysis-only.bin`
`PCR_rBPGovMax_MAP` тримає стелю **80 %** у більшій частині площини (низькі й
середні оберти та кількість палива) і плавно спадає до **51 %** у зоні
`rpm=5000 × InjCtl_qCurr=35 мг/хід` — тобто виходу регулятора на високих
обертах ECU довіряє менше. `PCR_rBPGovMin_MAP` — плоска підлога **5 %** на всіх
виміряних вузлах, без винятків. `PCR_rBPGovLin_CUR` (лінеаризація) у цьому
образі закодована як **тотожність**: вихід дорівнює входу в усіх 21 точці
(0–100 %, крок 5 %) — додаткової корекції нелінійності на цьому каналі
в поточній калібровці немає.

## Стрілка 10. → N75

**Статус: PROVEN (структура), UNKNOWN (знак).**

| Об'єкт | Адреса | Роль |
|---|---|---|
| `PCR_rBPACD` | `0x7F9BCE` | «Stellgröße für den Ladedrucksteller» |
| `BPACD_rCnv_CUR` | `0x1CC642` | ступінь відкриття (`PCR_rBPACD`, %) → шпаруватість |
| `BPACD_rCnv_mp` | `0x9FE9BC` | «Tastverhältnis basierend auf dem Ausgang des Ladedruckreglers» |

OEM-опис приводу для 1.9 TDI Pumpe-Düse, **VW SSP 209, стор. 44**:

> The solenoid valve for charge pressure control is activated by the engine
> control unit. The vacuum in the vacuum box for vane adjustment is set
> depending on the pulse duty factor.

**UNKNOWN:** чи більша шпаруватість означає більший наддув. З A2L знак не
випливає; без нього будь-яка правка керування — здогадка про напрямок.
Заведено прогалину, закривається одним логом VCDS.

---

## Що з SSP 304 брати можна, а що ні

Це найавторитетніший EDC16-документ у корпусі — і він **частково про інший
двигун**. Розділ про привід наддуву (стор. 15 і 33) описує електричні позиційні
моторчики, якими ECU керує по CAN:

> The engine control unit sends a signal via the CAN drive train databus to the
> turbocharger positioning motors.

а електромагнітний клапан у тому ж документі підписаний:

> Charge pressure limitation solenoid valve N75 (R5-TDI-engine)

BLS має вакуумний N75 без CAN. Отже:

| Розділ SSP 304 | Застосовність до BLS |
|---|---|
| логіка уставки: залежність від моменту, корекції за температурами й висотою | **так**, як опис сімейства EDC16 |
| зниження наддуву на висоті для захисту турбіни | **так** |
| привід: позиційні моторчики V280/V281 по CAN | **ні** — інший двигун |
| N75 із підписом «(R5-TDI-engine)» | обережно: опис клапана стосується R5 |

У базі це записано як конфлікт (`conflicts`), а не як «суперечність джерел»:
різна область застосовності всередині одного сімейства.

**Окремо про файл `Pierburg_N75_Valve_Internal_Anatomy_and_Operation.pdf`.**
Назва наводить на думку про офіційний документ виробника, але за власним
текстом це допис приватної особи на форум:

> I submitted this to tdiclub.com, because the information I found there was
> very helpful in tracking down the problem with my Tdi.

Тому все з нього — `COMMUNITY_CLAIM`, а не `OEM_DOCUMENTED`. Зокрема
твердження «пружини повернення золотника немає, закриває клапан сам вакуум»
лишається неперевіреним. (Сам реєстр `library_registry.json` при цьому вже
коректний — видавець там і так `TDIClub Technical Archive`, `Tier C`. Перша
версія цього документа стверджувала протилежне; це була моя власна
неперевірена помилка, і вона відкликана в базі — `claim #22`, статус
`deprecated`, з `retraction_reason`.)

---

## Відкрите: гілки, яких може не бути

**Позиційний зворотний зв'язок приводу (`BPASCD`).** У прошивці є повний набір:
лінеаризація `BPASCD_rLinRelPos_CUR` (`0x1CC6C8`) за напругою, перемикач джерела
сигналу ADC/CAN `BPASCD_swtSigRelPos_C` (`0x1CC71E`), змінні
`BPASCD_rRelPos` (`0x7F96AA`) і `BPACD_rIn1` (`0x7F969C`,
«Positionsistwert des Ladedruckstellers»), адаптація зсуву. Це рівно та
архітектура, яку описує SSP 304. На BLS привід вакуумний і датчика положення
лопаток немає. **Наявність об'єктів у A2L не означає, що гілка активна.**

Що електричний привід у EDC16 справді існує — але на інших двигунах — показує
й другий документ, VW SSP 325 (Transporter T5, 3.0 л V6 TDI Common Rail),
стор. 15:

> air guide vane adjustment has been implemented using an electric adjuster

**Регенерація DPF.** `PCR_pBDesRgn1a…3b_MAP` (`0x1EB3A6`…`0x1EBA7A`),
`PCR_rBPCtlRgn1a…3b_MAP` (`0x1EA328`…`0x1EAA80`), корекції `PCR_*RgnCor*`,
криві `PCR_facCtlRgn1/2/3_CUR` і `PCR_facDesRgn1/2/3_CUR`, а також окремі
`FMTC_trq2qRgn1..4_MAP`. **DPF на машині фізично відсутній.** Чи досяжні ці
гілки і що вони роблять з наддувом, якщо досяжні, — не з'ясовано.

**Друга система.** `…Bas2`, `…Ctl2`, `PCR_rBPACD2`, `BPACD_rCnv2_CUR`,
`PCR_nTrbn2_MAP`, «linkes/rechtes Sy(stem)» в описах. Прошивка розрахована на
конфігурацію з двома контурами наддуву. На одноконтурному BLS ця гілка,
найімовірніше, мертва — але це `HYPOTHESIS`, не факт, і декод даних це
трохи ускладнює: `PCR_pBDesBas2_MAP` (`0x1EAF3A`) у `reference-from-hex.analysis-only.bin`
**не порожня і не ідентична** `PCR_pBDesBas_MAP` — інша стеля (1950–1951 гПа
проти 2050), інший вузол осі rpm (4020 замість 3990), розбіжності в кількох
клітинках на 50–150 гПа. Це не доводить, що гілка активна на BLS — заповнена
таблиця в спільній для сімейства прошивці нічого не каже про те, чи код BLS-
варіанту її читає, — але спростовує просту версію «це порожня чи скопійована
таблиця». Дані реальні й самостійні. Питання «чи читає код цю гілку на BLS»
лишається `UNKNOWN`.

---

## Чого бракує (прогалини в базі)

| P | Статус | Питання | Чим закривається |
|---|---|---|---|
| 1 | `PARTIAL` | Декодувати значення мап шляху наддуву з reference BIN | зроблено зі структурою через `tools/decode_boost_path_stock.py`; лишається живий readback |
| 1 | `OPEN` | Незайманий заводський readback ECU | повний дамп до будь-яких змін — саме він перетворить `PARTIAL` вище на `RESOLVED` |
| 1 | `OPEN` | Визначити напрямок шпаруватості N75 | лог VCDS: шпаруватість проти наддуву на розгоні |
| 1 | `OPEN` | Підтвердити BV39 фотом таблички | фото парт-номера турбіни |
| 1 | `OPEN` | Чи досяжні уставки наддуву режиму регенерації DPF | аналіз коду + телеметрія |
| 1 | `OPEN` | Розділити в SSP 304 те, що стосується BLS | порозділова розмітка застосовності |
| 1 | `OPEN` | Дані BorgWarner саме на виконання `54399880072` | компресорна карта / технічні межі від виробника |
| 2 | `OPEN` | Порядок арбітражу лімітерів моменту | аналіз коду або лог `CoEng_trqInrSet` |
| 2 | `OPEN` | Чи активна гілка `BPASCD` на BLS | значення `BPASCD_swtSigRelPos_C` з BIN + DTC |
| 2 | `RESOLVED` | ~~Виправити запис реєстру для «Pierburg»-документа~~ | не було потрібно — реєстр уже коректний, помилка була в моєму твердженні (`claim #22`, `deprecated`) |

**Безпечна межа наддуву для BV39 — UNKNOWN.** Жоден інгестований документ не
містить допустимого тиску чи обертів для виконання `54399880072`, а сама
ідентифікація турбіни має статус `INFERRED` (каталог, без фото таблички).
Значення мап `PCR_*` межею компонента не є.

### Пастка «2.3 бар»

У корпусі є число, яке легко прийняти за відповідь. BorgWarner TurboNews 2004/1,
стор. 8:

> The gain in power and torque enjoyed by the engine is predominantly thanks to
> the new BV39 turbocharger by BorgWarner Turbo Systems with variable turbine
> geometry and 2.3 bar (absolute) boost pressure.

Це **не межа BV39 і не число для цієї машини**. Мова про Audi A2 1.4 TDI,
трициліндровий, 90 к.с.; виконання турбіни в документі не назване; 2.3 бар там —
робоча точка застосування, а не допустимий максимум. Переносити його на 1.9 TDI
BLS означало б зробити одразу дві заборонені підміни: чуже застосування замість
свого і спостережене значення замість фізичної межі.

У базі це записано двома твердженнями: документованим фактом про A2 і окремим
`INFERRED` про заборону переносу.

---

## Як перевірити це самому

```bat
cd D:\CLAUDE\golf5\ecu-kb
python kb.py a2l PCR_pBDesBas_MAP
python kb.py a2l --limit 80 PCR
python kb.py search "charge pressure control"
python kb.py check
python kb.py gaps

cd ..
python tools\decode_boost_path_stock.py
```

Останній рядок передруковує на екран ті самі числа, що лягли в
`diagnostic-review/math-engine/boost-path-stock-values.json`: жодне значення в
цьому документі не набрано вручну.
