# CONTROL-PATH-STOCK — шлях палива та крутного моменту

**Область дії.** VW Golf 5 1.9 TDI BLS, Bosch EDC16U34-3.42, HW `03G 906 021 QJ`,
**SW `1037391847`**, проєкт `P447_HAXN`. Джерело фактів про прошивку —
`diagnostic-review/definitions/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.a2l`,
sha256 `04ab636a3f56…`, 16 772 об'єкти (11 537 CHARACTERISTIC, 5 220 MEASUREMENT, 15 AXIS_PTS).

**Це опис СТОКУ.** Тут немає жодної рекомендації щодо тюнінгу чи зміни прошивки. Мета цього
вертикального зрізу — зафіксувати точну послідовність проходження сигналу від натискання педалі
акселератора через структуру крутного моменту, димові обмеження та до кутів початку і тривалості
впорскування в насос-форсунках (Pumpe-Düse / UIS).

---

## Як читати статуси

| Статус | Що означає тут |
|---|---|
| **PROVEN** | існування об'єкта, його адреса, тип і осі прочитані з A2L цієї прошивки (`MAP_FACT` / `project_matched`) |
| **MODELED** | величина в ECU обчислюється моделлю, а не міряється датчиком |
| **UNKNOWN** | з наявних доказів не випливає; у базі заведено `gap` |

---

## Ланцюг проходження сигналу палива та моменту

```
   Педаль акселератора        AccPed_rAPP          0x7F962C  [%]
       │
       │  AccPed_trqEng0..6_MAP  (n × педаль), вибір передачі AccPed_stGearSel_CUR
       ▼
   Запит моменту водія        AccPed_trqEng        0x7F9632  [Nm]
       │
       │  Арбітраж обмежень моменту:
       │  - Ліміти трансмісії / передач: Gearbx_trqMaxGear1..6_CUR
       │  - Захист наддуву: EngPrt_trqLimPBoost_MAP (0x1C9902)
       │  - Тепловий захист турбіни (EGT): EngPrt_facTempPreTrbn_MAP (0x1C9B7E)
       ▼
   Заданий внутрішній момент   CoEng_trqInrSet      0x7F97B6  [Nm]
   (inneres Moment Sollwert > Mengenberechnung)
       │
       │  Конвертація момент → паливо:
       │  FMTC_trq2qBas_MAP (0x1D729C) (n × момент)
       │  Врахування ККД: FMTC_etaCurr (0x7F9922)
       ▼
   Бажана маса палива          FMTC_qDes / InjCtl_qDes  0x7F9AB2  [mg/str]
       │
       │  Димові обмеження (Smoke Limiters / Luftmengenbegrenzung):
       │  - По витратоміру (MAF): FlMng_qAFSCDSmoke_MAP (0x1D61D2) (n × FlMng_mAirPerCyl)
       │  - По тиску наддуву (MAP): FlMng_qPresSmoke_MAP (0x1D6490) (n × BPSCD_pFltVal)
       │  - Динамічна корекція: FlMng_facDynSmoke_CUR (0x1D5FDC)
       ▼
   Результуючий ліміт палива   InjCtl_qLim          0x7F9AB4  [mg/str]
       │
       │  Мінімум (InjCtl_qDes, InjCtl_qLim) → InjCtl_qCurr (0x7F9AAE)
       ▼
   Фактична циклова подача     InjCtl_qCurr         0x7F9AAE  [mg/str]
       │
       ├─────────────────────────────────────────┐
       ▼                                         ▼
   Кут випередження (SOI / Förderbeginn)      Тривалість подачі (Duration / Förderdauer)
   InjCrv_phiBas0..5_GMAP (0x1D9778)          InjVlv_phiInjMI1_MAP0..6 (0x1E4F3E)
   (n × InjCtl_qCurr) [°CA bTDC]              (n × InjCtl_qCurr) [°CA]
       │                                         │
       │  Корекція по BIP (Begin of Injection)   │
       │  BIP_facInjBegCor_MAP (0x1CC2EA)        │
       ▼                                         ▼
   Формування електричного імпульсу соленоїда насос-форсунки (N240..N243)
```

---

## 1. Педаль → Запит моменту водія (`AccPed`)

**Функція:** `AccPed` (Pedalwertgeber / Driver Demand).  
**Принцип:** В архітектурі Bosch EDC16 натискання педалі визначає не кількість палива напряму (як це було в EDC15), а бажаний крутний момент двигуна.

| Об'єкт | Адреса | Осі | Роль | Статус |
|---|---|---|---|---|
| `AccPed_rAPP` | `0x7F962C` | — | Відфільтроване положення педалі (%) | PROVEN |
| `AccPed_trqEng0_MAP` | `0x1C2CCE` | `Eng_nAvrg` × `AccPed_rAPP` | Базовий момент / 1-ша передача (Nm) | PROVEN |
| `AccPed_trqEng1..6_MAP`| `0x1C2E24`…`0x1C34D2` | `Eng_nAvrg` × `AccPed_rAPP` | Момент за передачами (2..6) (Nm) | PROVEN |
| `AccPed_trqEng0Cold_MAP`| `0x1C2B78` | `Eng_nAvrg` × `AccPed_rAPP` | Момент на холодному двигуні (Nm) | PROVEN |
| `AccPed_stGearSel_CUR`| `0x1C2B30` | `AccPed_rVnTrqEngActv_mp` | Перемикання/інтерполяція мап передач | PROVEN |

*Цитата першоджерела (VW SSP 304, стор. 4, 9):*
> "Bosch EDC 16 is a torque-orientated engine management system which is featured for the first time in diesel engines... The specified torque is calculated from the internal and external torque demands. To reach this torque specification, a set quantity of fuel is required."

---

## 2. Координація та обмеження моменту (`CoEng`, `EngPrt`)

**Функція:** `CoEng` (Coordination Engine Torque) та `EngPrt` (Engine Protection).  
Запит водія обмежується лімітами механічної міцності трансмісії, граничного наддуву та захисту від перегріву турбіни (EGT derating).

| Об'єкт | Адреса | Осі | Роль | Статус |
|---|---|---|---|---|
| `EngPrt_trqLimPBoost_MAP` | `0x1C9902` | `Eng_nAvrg` × `BPSCD_pFltVal` | Обмеження крутного моменту за тиском наддуву | PROVEN |
| `EngPrt_facTempPreTrbn_MAP`| `0x1C9B7E` | `Eng_nAvrg` × `Exh_tPreTrbnEst` | Фактор обмеження моменту за розрахунковою EGT турбіни | PROVEN |
| `CoEng_trqInrSet` | `0x7F97B6` | — | Заданий внутрішній крутний момент (inneres Moment) | PROVEN |

---

## 3. Конвертація моменту в кількість палива (`FMTC`)

**Функція:** `FMTC` (Fuel Mass Torque Conversion).  
Перетворює внутрішній крутний момент ($M_i$, Nm) на базову циклову подачу ($q_{des}$, mg/str).

| Об'єкт | Адреса | Осі | Роль | Статус |
|---|---|---|---|---|
| `FMTC_trq2qBas_MAP` | `0x1D729C` | `Eng_nAvrg` × `CoEng_trqInr` | Базова конвертація: Nm -> mg/str | PROVEN |
| `FMTC_trq2qRgn1_MAP`| `0x1D7524` | `Eng_nAvrg` × `CoEng_trqInr` | Конвертація під час активної регенерації DPF (режим 1) | PROVEN |
| `FMTC_etaCurr` | `0x7F9922` | — | Поточний розрахунковий ККД двигуна | PROVEN |

---

## 4. Обмеження димності та повітряні лімітери (`FlMng`)

**Функція:** `FlMng` (Fuel Management / Rauchbegrenzung).  
Запобігає утворенню сажі шляхом обмеження циклової подачі залежно від фактично доступного кисню (повітря).

| Об'єкт | Адреса | Осі | Роль | Статус |
|---|---|---|---|---|
| `FlMng_qAFSCDSmoke_MAP` | `0x1D61D2` | `Eng_nAvrg` × `FlMng_mAirPerCyl` | Обмеження димності за масою повітря (MAF) [mg/str] | PROVEN |
| `FlMng_qPresSmoke_MAP` | `0x1D6490` | `Eng_nAvrg` × `BPSCD_pFltVal` | Обмеження димності за тиском наддуву (MAP) [mg/str] | PROVEN |
| `FlMng_facDynSmoke_CUR` | `0x1D5FDC` | `Veh_v` | Динамічна корекція димового обмеження при розгоні | PROVEN |
| `InjCtl_qLim` | `0x7F9AB4` | — | Результуючий ліміт подачі після всіх обмежувачів | PROVEN |
| `InjCtl_qCurr` | `0x7F9AAE` | — | Фактична циклова подача палива (mg/str) | PROVEN |

*Цитата першоджерела (VW SSP 304, стор. 9):*
> "However, to protect the engine against mechanical damage and to prevent black smoke, there should be limitations on the quantity of fuel injected. For this reason, the engine control unit calculates a limit value for this quantity. The limit value depends on the engine speed, the air mass and the air pressure."

---

## 5. Кут початку та тривалість подачі (`InjCrv`, `InjVlv`, `BIP`)

**Функція:** `InjCrv` (Injection Curve / Förderbeginn), `InjVlv` (Injection Valve / Förderdauer) та `BIP` (Begin of Injection Period).

У системі Pumpe-Düse тиск створюється плунжером від розподільного вала, але момент і тривалість подачі визначаються відкриттям/закриттям швидкодіючого соленоїдного клапана форсунки.

| Об'єкт | Адреса | Осі | Роль | Статус |
|---|---|---|---|---|
| `InjCrv_phiBas0..5_GMAP` | `0x1D9778`… | `Eng_nAvrg` × `InjCtl_qCurr` | Базовий кут випередження основного впорскування (°CA bTDC) | PROVEN |
| `InjVlv_phiInjMI1_MAP0..6`| `0x1E4F3E`… | `Eng_nAvrg` × `InjCtl_qCurr` | Тривалість основного впорскування в градусах ПКВ (°CA) | PROVEN |
| `InjVlv_phiInjPoI2_MAP0..1`| `0x1E59C8`… | `Eng_nAvrg` × `InjCtl_qCurr` | Тривалість післявпорскування для прогріву DPF (°CA) | PROVEN |
| `BIP_facInjBegCor_MAP` | `0x1CC2EA` | `Eng_nAvrg` × `InjCtl_qCurr` | Корекція кута початку подачі за сигналом зворотного зв'язку BIP | PROVEN |

### Фізичний зв'язок кута та часу:
Тривалість впорскування в мікросекундах ($\Delta t$, $\mu s$) прямо пов'язана з кутом повороту колінчастого вала ($\Delta \phi$, °CA) та обертами двигуна ($n$, об/хв):
$$\Delta t = \frac{\Delta \phi}{6 \cdot n} \cdot 10^6$$

*Цитата першоджерела (VW SSP 315, стор. 30):*
> "The BIP of the unit injector valve is identifiable by a noticeable kink in the current curve."

*Цитата першоджерела (VW SSP 209, стор. 15, 16):*
> "At approx. 300 bar, the fuel pressure is greater than the force exerted by the pre-loaded injector spring. The injector needle is again lifted and the main injection quantity is injected. The pressure rises to 2050 bar, because more fuel is displaced in the high-pressure chamber than can escape through the nozzle holes... The injection cycle ends when the engine control unit stops activating the injector solenoid valve."

---

## 6. Відкриті прогалини (Gaps) по шляху палива

1. **Декодування числових значень решіток:** Зняти та перевірити точні значення комірок для `FMTC_trq2qBas_MAP`, `FlMng_qAFSCDSmoke_MAP`, `InjVlv_phiInjMI1_MAP0` та `InjCrv_phiBas0_GMAP` з заводського BIN.
2. **Логіка перемикання димових карт:** Встановити біти конфігурації, які визначають, чи активний лімітер по MAF (`FlMng_qAFSCDSmoke_MAP`), чи по тиску наддуву MAP (`FlMng_qPresSmoke_MAP`) у версії прошивки P447_HAXN.
3. **Температурні лімітери:** Дослідити мапи дератизації за температурою охолоджуючої рідини (`Coolant Temp Derating`) та палива (`Fuel Temp Derating`).