Так. Для твого **Project Knowledge Bootstrap** я б зробив не просто папку з PDF, а локальну технічну бібліотеку з provenance, applicability і рівнями довіри. Тоді Gemini/Codex зможуть відповідати не «десь читав, що N75 треба так», а: **ось Bosch/VW теорія → ось A2L для цього сімейства → ось конкретна карта у твоєму SW → ось лог машини → ось висновок і невизначеність**.

## 1. Що завантажити в першу чергу

### Tier A — обов'язкова база

**1. Bosch — Diesel Engine Management: Systems and Components, Konrad Reif, 2014**

Найцінніша загальна книга для твого випадку: дизельний цикл, подача повітря, injection, EDC, sensors, start-assist, diagnostics тощо. Springer відносить її до Bosch Professional Automotive Information. ([link.springer.com](https://link.springer.com/book/10.1007/978-3-658-03981-3))

[Springer — Diesel Engine Management](https://link.springer.com/book/10.1007/978-3-658-03981-3?utm_source=chatgpt.com)

**2. Bosch — Dieselmotor-Management, 4th ed., 2004**

Для твого EDC16/PD це навіть особливо цікаве видання за епохою: у змісті є charge control, diesel injection, electronic control, emission systems тощо. ([link.springer.com](https://link.springer.com/book/10.1007/978-3-322-80331-3))

[Springer — Dieselmotor-Management 4th ed.](https://link.springer.com/book/10.1007/978-3-322-80331-3?utm_source=chatgpt.com)

**3. VW SSP 304 — Electronic Diesel Control EDC16: Design and Function**

Це must-have. VW прямо описує EDC16 як torque-oriented engine management system; SSP містить metering regulation, start of injection, charge-pressure control, sensors, actuators і діагностику. ([scribd.com](https://www.scribd.com/document/563638250/SSP-304-EDC-16))

Публічний PDF-мірор:

[VW SSP 304 — EDC16 PDF](https://www.vaglinks.com/docs/ssp/VWUSA.COM_SSP_304_EDC-16.pdf?utm_source=chatgpt.com)

**4. VW SSP 209 / 841303 — 1.9 TDI Pump Injection / Pumpe-Düse**

Дає фундамент саме по PD: unit injector, injection process, engine management, air path і виконавчі механізми. ([procarmanuals.com](https://procarmanuals.com/self-study-program-209-1-9-ltr-tdi-engine-pump-injection-system-design-function/))

[Каталог VW SSP з 1.9 TDI Pump Injection](https://www.springfieldvw.com/wp-content/uploads/ssp-assistant/docs/ssp/SSP%20VW/?utm_source=chatgpt.com)

**5. VW SSP 336 — Catalytic Coated Diesel Particulate Filter**

Навіть при нинішній конфігурації авто ця документація потрібна, щоб Bootstrap розумів **оригінальну логіку ECU**: температурний менеджмент, regeneration-related functionality, aftertreatment sensors та взаємозалежності. Це не інструкція з видалення системи, а опис її штатної роботи. ([vaglinks.com](https://www.vaglinks.com/Docs/SSP/VWUSA.COM_SSP_336_VW_Diesel_particulate_filter.pdf))

[VW SSP 336 PDF](https://www.vaglinks.com/Docs/SSP/VWUSA.COM_SSP_336_VW_Diesel_particulate_filter.pdf?utm_source=chatgpt.com)

**6. VW 4-cylinder Diesel Engine workshop material — BKC/BLS/BXE**

Для механічних специфікацій твого BLS і перевірки того, що проблема справді calibration-related, а не hardware-related. Публічний каталог прямо перелічує BKC/BLS/BRM/BXE. ([vag-hub.com](https://www.vag-hub.com/vw-engine/))

[VW engine workshop manual index](https://www.vag-hub.com/vw-engine/?utm_source=chatgpt.com)

---

## 2. Стандарти ECU та A2L

**7. ASAM MCD-2 MC / ASAP2**

Критично важливо. Стандарт визначає A2L: calibration parameters, measurements, memory locations, axes, conversions, access information тощо. Поточна сторінка ASAM вказує версію 1.7.1. ([asam.net](https://www.asam.net/standards/detail/mcd-2-mc/))

[ASAM MCD-2 MC official](https://www.asam.net/standards/detail/mcd-2-mc/?utm_source=chatgpt.com)

Також:

[ASAM MCD-2 MC Wiki](https://www.asam.net/standards/detail/mcd-2-mc/wiki/?utm_source=chatgpt.com)

**8. ETAS INCA documentation**

Корисно для розуміння OEM measurement/calibration workflow. ETAS описує зв'язок A2L з calibration parameters та measurement channels, зокрема при XCP. ([docs.etas.com](https://docs.etas.com/inca/docs/V7.6.1/EN/Subsystems/hw/Content/Topics/REF_Applikation_ueber_XCP_%28CAN-Bus%29.htm))

[ETAS — Measurement and Calibration using XCP](https://docs.etas.com/inca/docs/V7.6.1/EN/Subsystems/hw/Content/Topics/REF_Applikation_ueber_XCP_%28CAN-Bus%29.htm?utm_source=chatgpt.com)

Не тому, що твій Golf треба переводити на XCP, а щоб агент правильно розумів **OEM calibration methodology**.

---

## 3. WinOLS/DAMOS/checksum

**9. EVC WinOLS Manual**

Актуальний manual містить DAMOS/ASAP2 import і важливе правило: A2L/DAMOS має відповідати конкретному project data, інакше import може бути неповним або неправильним. ([evc.de](https://www.evc.de/ftp/winols/winols%20HelpEn.pdf))

[WinOLS 5 manual PDF](https://www.evc.de/ftp/winols/winols%20HelpEn.pdf?utm_source=chatgpt.com)

**10. EVC DAMOS/ASAP2 documentation**

EVC пояснює, що DAMOS/A2L містять адреси, scaling, axes і labels, які не знаходяться безпосередньо в EPROM data. ([evc.de](https://www.evc.de/en/product/ols/damos.asp))

[EVC — DAMOS/ASAP2 Import](https://www.evc.de/en/product/ols/damos.asp?utm_source=chatgpt.com)

**11. Bosch EDC16 checksum documentation від EVC**

EVC окремо має checksum module для Bosch EDC16. ([evc.de](https://www.evc.de/en/product/ols/plugins_detail.asp))

[EVC — Bosch EDC16 checksum details](https://www.evc.de/en/product/ols/plugins_detail.asp?utm_source=chatgpt.com)

Також важлива їхня документація про compatibility checksum у EDC16/17. ([evc.de](https://www.evc.de/en/service/q1303.asp))

---

## 4. Фундаментальна теорія двигуна

**12. John B. Heywood — Internal Combustion Engine Fundamentals, 2nd ed.**

Одна з базових інженерних книг по combustion, airflow, efficiency, heat transfer, engine performance. 2nd edition вийшла у 2018/2019. ([mheducation.com](https://www.mheducation.com/highered/mhp/product/internal-combustion-engine-fundamentals-2e.html))

[McGraw-Hill — Heywood ICE Fundamentals 2E](https://www.mheducation.com/highered/mhp/product/internal-combustion-engine-fundamentals-2e.html?utm_source=chatgpt.com)

**13. Bosch Automotive Handbook, 11th ed.**

Видання 2022 року, 2048 сторінок; містить окремі розділи про internal-combustion engines і diesel-engine management. ([uat.store.wiley.com](https://uat.store.wiley.com/en-us/automotive-handbook-11th-edition-p-9781119911906?utm_source=chatgpt.com))

[Wiley — Bosch Automotive Handbook 11th ed.](https://uat.store.wiley.com/en-us/automotive-handbook-11th-edition-p-9781119911906?utm_source=chatgpt.com)

---

## 5. Теорія керування двигуном

**14. Guzzella & Onder — Introduction to Modeling and Control of Internal Combustion Engine Systems, 2nd ed.**

Для нашої задачі дуже корисна: mean-value models, engine dynamics, feed-forward, feedback і control of engine systems. ([link.springer.com](https://link.springer.com/book/10.1007/978-3-642-10775-7))

[Springer — Guzzella & Onder, 2nd ed.](https://link.springer.com/book/10.1007/978-3-642-10775-7?utm_source=chatgpt.com)

**15. Kiencke & Nielsen — Automotive Control Systems**

Control theory + automotive application, engine/driveline/vehicle. ([link.springer.com](https://link.springer.com/book/10.1007/b137654))

[Springer — Automotive Control Systems](https://link.springer.com/book/10.1007/b137654?utm_source=chatgpt.com)

Ці дві книги особливо потрібні для того, щоб агент не плутав:

`boost target ≠ feed-forward ≠ actuator duty ≠ feedback correction`.

---

## 6. Турбіна та VNT/VGT

**16. Watson & Janota — Turbocharging the Internal Combustion Engine**

Окремі глави присвячені compressor, turbine, matching і transient response turbocharged engines. ([link.springer.com](https://link.springer.com/book/10.1007/978-1-349-04024-7))

[Springer — Turbocharging the Internal Combustion Engine](https://link.springer.com/book/10.1007/978-1-349-04024-7?utm_source=chatgpt.com)

**17. BorgWarner — Understanding Compressor Maps**

Для Bootstrap це гарне першоджерело про pressure ratio, corrected flow, efficiency islands і turbo speed. ([borgwarner.com](https://www.borgwarner.com/aftermarket/exhaust-gas-management/news/2022/05/23/understanding-compressor-maps-sizing-a-turbocharger))

[BorgWarner — Understanding Compressor Maps](https://www.borgwarner.com/aftermarket/exhaust-gas-management/news/2022/05/23/understanding-compressor-maps-sizing-a-turbocharger?utm_source=chatgpt.com)

Важливо: **не дозволяти агенту видавати generic BorgWarner compressor map за точну карту твого BV39**, якщо part-number і compressor wheel не підтверджені.

---

## 7. SAE / наукові papers по VGT

**18. Ammann/Fekete/Guzzella/Glattfelder — Model-Based Control of VGT and EGR**

SAE 2003-01-0357. Робота саме про transient operation і coordinated VGT/EGR control. ([saemobilus.sae.org](https://saemobilus.sae.org/papers/model-based-control-vgt-egr-a-turbocharged-common-rail-diesel-engine-theory-passenger-car-implementation-2003-01-0357))

[SAE 2003-01-0357](https://saemobilus.sae.org/papers/model-based-control-vgt-egr-a-turbocharged-common-rail-diesel-engine-theory-passenger-car-implementation-2003-01-0357?utm_source=chatgpt.com)

**19. Electronic Control of a Variable Geometry Turbocharger — SAE 900889**

Про необхідність і принципи електронного VGT control. ([saemobilus.sae.org](https://saemobilus.sae.org/papers/electronic-control-a-variable-geometry-turbocharger-900889))

[SAE 900889](https://saemobilus.sae.org/papers/electronic-control-a-variable-geometry-turbocharger-900889?utm_source=chatgpt.com)

**20. Watson/Banisoleiman — Variable-Geometry Turbocharger Control System**

Розглядає transient response, smoke і VGT control. ([saemobilus.sae.org](https://saemobilus.sae.org/papers/a-variable-geometry-turbocharger-control-system-high-output-diesel-engines-880118))

[SAE 880118](https://saemobilus.sae.org/papers/a-variable-geometry-turbocharger-control-system-high-output-diesel-engines-880118?utm_source=chatgpt.com)

**21. Quantitative feedback design of air and boost pressure control**

Корисно як більш академічна робота по nonlinear/coupled VGT/EGR control. ([sciencedirect.com](https://www.sciencedirect.com/science/article/abs/pii/S0967066111000372))

[Control Engineering Practice paper](https://www.sciencedirect.com/science/article/abs/pii/S0967066111000372?utm_source=chatgpt.com)

---

## 8. Великі довідники

**22. Internal Combustion Engine Handbook, 2nd English Edition**

SAE, 2016; охоплює diesel/SI fundamentals, sensors, actuators, electronics, thermal systems тощо. ([saemobilus.sae.org](https://saemobilus.sae.org/books/internal-combustion-engine-handbook-2nd-english-edition-r-434?utm_source=chatgpt.com))

[SAE — ICE Handbook 2nd English Edition](https://saemobilus.sae.org/books/internal-combustion-engine-handbook-2nd-english-edition-r-434?utm_source=chatgpt.com)

**23. Diesel Engine Reference Book — Challen & Baranescu**

682 сторінки; combustion, turbocharging, injection, heat transfer, emissions тощо. ([books.google.com](https://books.google.com/books/about/Diesel_Engine_Reference_Book.html?id=lNhSAAAAMAAJ&utm_source=chatgpt.com))

[Google Books — Diesel Engine Reference Book](https://books.google.com/books/about/Diesel_Engine_Reference_Book.html?id=lNhSAAAAMAAJ&utm_source=chatgpt.com)

---

## 9. Практичне калібрування — нижчий рівень довіри

**24. Greg Banish — Engine Management: Advanced Tuning**

Добре пояснює calibration methodology, sensor validation, datalogging, transient corrections і iterative tuning, хоча книга значною мірою орієнтована на gasoline/aftermarket ECU. ([cartechbooks.com](https://www.cartechbooks.com/collections/diagnostics/products/engine-management-advanced-tuning?utm_source=chatgpt.com))

[CarTech — Engine Management Advanced Tuning](https://www.cartechbooks.com/collections/diagnostics/products/engine-management-advanced-tuning?utm_source=chatgpt.com)

**25. Greg Banish — Designing and Tuning High-Performance Fuel Injection Systems**

Корисна насамперед як методологія вимірювання й калібрування, не як джерело конкретних дизельних map values. ([cartechbooks.com](https://www.cartechbooks.com/collections/diagnostics/products/designing-and-tuning-high-performance-fuel-injection-systems-1?utm_source=chatgpt.com))

[CarTech — Designing and Tuning Fuel Injection Systems](https://www.cartechbooks.com/collections/diagnostics/products/designing-and-tuning-high-performance-fuel-injection-systems-1?utm_source=chatgpt.com)

---

# 10. Діагностика і логування

**26. Ross-Tech TDI logging**

Ross-Tech рекомендує для turbo evaluation логувати measuring block 011 і порівнювати requested/actual boost проти RPM. ([ross-tech.com](https://www.ross-tech.com/vag-com/cars/tdi.html))

[Ross-Tech TDI VCDS info](https://www.ross-tech.com/vag-com/cars/tdi.html?utm_source=chatgpt.com)

Для нашої роботи ще важливіше їхнє попередження: чим більше groups одночасно читаєш, тим нижчий sample rate і тим легше пропустити transient spike. ([register.ross-tech.com](https://register.ross-tech.com/vcds/tour/adv-meas-blocks.php))

Тому для boost tuning я б тримав окремі high-rate runs:

`011 → boost`
  
`003 → MAF`
  
`008 → fueling/limiters`

Це також відповідає рекомендаціям Ross-Tech staff у діагностичному прикладі. ([forums.ross-tech.com](https://forums.ross-tech.com/index.php?threads%2F38319%2F=))

---

# 11. Інструменти, які варто дати Bootstrap

**27. pyA2L**

Python library для ASAM MCD-2 MC. Парсить A2L у SQLite, дозволяє працювати з `CHARACTERISTIC`, `MEASUREMENT`, `AXIS_DESCR`, `RECORD_LAYOUT`, conversions тощо. ([github.com](https://github.com/christoph2/pya2l))

[GitHub — pyA2L](https://github.com/christoph2/pya2l?utm_source=chatgpt.com)

**28. a2lfile**

Швидка Rust-бібліотека, що читає/редагує/записує A2L 1.7.1 і намагається мінімізувати diff. ([github.com](https://github.com/DanielT/a2lfile))

[GitHub — a2lfile](https://github.com/DanielT/a2lfile?utm_source=chatgpt.com)

Для твого Python-based Bootstrap я б починав саме з **pyA2L**.

---

# Як організувати локальну бібліотеку

Я б зробив так:

```text id="2wfs1p"
knowledge/
│
├── 00_inbox/
│   └── все нове до класифікації
│
├── 01_oem/
│   ├── bosch/
│   ├── volkswagen/
│   ├── borgwarner/
│   └── ross-tech/
│
├── 02_standards/
│   ├── asam/
│   └── asap2-a2l/
│
├── 03_books/
│   ├── diesel/
│   ├── combustion/
│   ├── turbocharging/
│   └── control/
│
├── 04_papers/
│   ├── vgt/
│   ├── boost-control/
│   ├── combustion/
│   └── injection/
│
├── 05_tools_docs/
│   ├── winols/
│   ├── inca/
│   ├── pya2l/
│   └── diagnostics/
│
├── 06_project_specific/
│   ├── ECU_EDC16U34/
│   ├── engine_BLS/
│   ├── turbo_BV39/
│   ├── HW_03G906021QJ/
│   └── SW_1037391847/
│
├── 07_community/
│   ├── tdiclub/
│   ├── ecuconnections/
│   ├── nefarious/
│   ├── mhhauto/
│   └── other/
│
├── 08_firmware/
│   ├── originals/
│   ├── current/
│   ├── experimental/
│   └── diffs/
│
├── 09_logs/
│   ├── vcds/
│   ├── android/
│   ├── hot_start/
│   └── dyno/
│
├── 10_a2l_damos/
│
├── 11_extracted/
│
├── 12_conflicts/
│
└── 13_reports/
```

## Не клади BIN у vector DB

Для `.bin`:

- immutable original;
- SHA-256;
- ECU ID;
- HW;
- SW;
- file size;
- provenance;
- parent firmware;
- exact binary diff.

Сам binary залишається файлом.

У БД потрапляють **metadata + map definitions + diffs**, а не випадкові binary chunks.

---

# Структура БД

Мінімально я б мав таблиці:

```text id="v59zn7"
sources
documents
chunks
claims
entities
ecu_variants
map_definitions
map_relationships
firmware_versions
firmware_diffs
logs
log_channels
experiments
conflicts
citations
research_tasks
```

Ключова таблиця — `claims`.

Кожен факт має мати:

```text id="hh2zx5"
claim_id
claim_text
source_id
document_id
page/chapter/section
exact_evidence
source_type
authority_level
ecu_family
ecu_variant
hw_number
sw_number
engine_code
turbo_model
map_name
map_address
units
scaling
axis_x
axis_y
conditions
epistemic_status
confidence
corroborated_by
contradicted_by
created_at
updated_at
```

---

# Рівні джерел

Я б задав **не загальний confidence**, а два незалежні поля:

```text id="z7xcec"
authority
applicability
```

Наприклад:

| Source | Authority | Applicability до твого SW |
|---|---:|---:|
| Bosch book | 5 | 2–3 |
| VW SSP304 | 5 | 3 |
| exact matching A2L | 5 | 5 |
| exact ECU readback | 5 | 5 |
| твій VCDS log | 5 | 5 |
| BV39 manufacturer data | 5 | 4–5 |
| SAE paper | 4 | 2–3 |
| TDIClub BLS case | 3 | 3–4 |
| tuner blog | 2 | 2–3 |
| random forum BIN | 1 | 1–3 |

Це дуже важливо.

**Bosch книга може бути максимально авторитетною, але не сказати, яке число стоїть у твоєму `PCR_rBPCtlBas_MAP`.**

---

# Epistemic status

Твою існуючу схему я б розширив до:

```text id="2x73o7"
raw
corroborated
project_matched
experiment_supported
verified
contradicted
deprecated
```

### Значення

**raw**  
Знайдено в одному джерелі.

**corroborated**  
Підтверджено незалежними джерелами.

**project_matched**  
Збігається з твоїм ECU/A2L/BIN/SW.

**experiment_supported**  
Підтверджується логами машини.

**verified**  
Project-matched + measurement/controlled experiment.

**contradicted**  
Є сильна суперечлива інформація.

**deprecated**  
Стосувалося старого firmware/revision.

---

# Як chunk-ити інформацію

Не роби однаковий chunking для всього.

### PDF / книги

```text id="qea86w"
700–1200 tokens
overlap ~100–150
```

Але обов'язково зберігати:

```text id="8bn0qw"
book
edition
chapter
section
page_start
page_end
```

### A2L

Не chunk by tokens.

Один logical object = один chunk:

```text id="cf3ldl"
CHARACTERISTIC
MEASUREMENT
AXIS_PTS
COMPU_METHOD
RECORD_LAYOUT
FUNCTION
GROUP
```

Плюс relationships між ними.

### Forum

Один post = один unit.

Зберігати:

```text id="3sickl"
thread
author
date
vehicle
engine
ECU
SW
hardware changes
claim
result
```

### Source code

Chunk:

```text id="71id1x"
module
class
function
```

### CSV logs

Raw CSV не пхати цілком у LLM index.

Зберігати файл + derived statistics:

```text id="4sjz98"
rpm range
requested boost
actual boost
error
N75
MAF
IQ
IAT
coolant
speed
sample rate
timestamp
firmware_hash
```

---

# FTS + semantic search

Для ECU я б **не замінював SQLite FTS5 embeddings'ами**.

Треба обидва:

```text id="3ptuh8"
FTS5 → exact symbol search
PCR_rBPCtlBas_MAP
0x1E9FD0
03G906021QJ
1037391847

Vector → conceptual search
"maps controlling transient VNT response"
"hot start torque during cranking"
```

Під час retrieval:

```text id="t5p678"
exact/FTS candidates
        +
semantic candidates
        ↓
applicability filter
        ↓
authority ranking
        ↓
claim/conflict aggregation
```

---

# Готовий master prompt

:::writing{variant="document" id="41863" title="MASTER PROMPT — EDC16U34 Project Knowledge Bootstrap"}
You are the research and knowledge-ingestion engine for an automotive ECU calibration project.

PROJECT

Vehicle:
Volkswagen Golf 5, 2008

Engine:
1.9 TDI BLS, Pumpe-Düse

ECU:
Bosch EDC16U34

VAG HW:
03G906021QJ

Known Bosch software family:
1037391847

Turbo:
BorgWarner/KKK BV39
Known project reference:
54399880072

The local project contains:
- original and modified ECU binaries
- A2L/DAMOS-derived information
- map inspection scripts
- firmware diffs
- VCDS logs
- Android/ELM telemetry
- technical reports
- previous calibration experiments

PRIMARY GOAL

Build a high-quality engineering knowledge base that can be used by an AI calibration engineer to reason about this specific ECU and vehicle.

The purpose is NOT to collect random tuning values.

The purpose is to build an evidence-based model of:

1. ECU architecture
2. torque structure
3. air-path control
4. boost request
5. VNT/N75 feed-forward
6. closed-loop boost regulation
7. smoke limitation
8. injection quantity
9. injection duration
10. start of injection
11. temperature compensation
12. hot-start behaviour
13. component protection
14. thermal protection
15. diagnostic behaviour
16. firmware layout
17. A2L/DAMOS map semantics
18. checksum structure
19. measured vehicle behaviour
20. interactions between maps

SOURCE PRIORITY

Prioritize sources in this order:

LEVEL 5 — PRIMARY / AUTHORITATIVE

- Robert Bosch technical literature
- Volkswagen Self Study Programmes
- Volkswagen workshop/service literature
- ASAM standards
- BorgWarner technical documentation
- matching A2L/DAMOS
- exact ECU binary
- actual ECU readback
- measured logs from this vehicle

LEVEL 4 — ENGINEERING / ACADEMIC

- SAE papers
- peer-reviewed control/engine papers
- university research
- respected engineering textbooks
- ETAS / Vector / EVC technical documentation

LEVEL 3 — TECHNICAL COMMUNITY

- Ross-Tech
- TDIClub
- specialist Bosch ECU communities
- established calibration forums
- documented engineering projects

LEVEL 2

- tuner documentation
- vendor articles
- technical blogs

LEVEL 1

- anonymous forum claims
- social media
- YouTube
- undocumented modified binaries

Never promote a claim to VERIFIED solely because multiple low-quality websites repeat it.

APPLICABILITY IS SEPARATE FROM AUTHORITY

For every claim separately determine:

authority_score: 1–5

and

applicability_score: 1–5

Applicability must consider:

- ECU family
- exact ECU variant
- engine code
- hardware number
- software version
- turbocharger
- injectors
- transmission
- emissions configuration
- operating condition

Example:

A Bosch engineering book may have authority=5 but applicability=2.

An exact matching A2L for 03G906021QJ / matching software may have authority=5 and applicability=5.

CLAIM STATES

Every technical claim must have one of:

raw
corroborated
project_matched
experiment_supported
verified
contradicted
deprecated

Definitions:

raw:
Found in a source but not independently confirmed.

corroborated:
Supported by multiple independent credible sources.

project_matched:
Confirmed to correspond to the actual ECU/software/layout.

experiment_supported:
Supported by measured data from the vehicle.

verified:
Supported by matching project evidence and controlled measurement or direct technical evidence.

contradicted:
Conflicts with stronger evidence.

deprecated:
Was valid for an older firmware/project state but not the current one.

NEVER silently convert RAW information into VERIFIED knowledge.

INGESTION PROCEDURE

For every new resource:

1. identify the resource
2. calculate SHA-256 where possible
3. record original URL/path
4. record author/publisher
5. record title
6. record publication date
7. record edition/version
8. classify source type
9. assign authority
10. determine ECU/engine/turbo applicability
11. extract structure/table of contents
12. split semantically
13. extract atomic technical claims
14. extract map names and symbols
15. extract addresses when explicitly documented
16. extract units/scaling
17. extract axis definitions
18. extract operating conditions
19. attach citations
20. compare with existing knowledge
21. detect conflicts
22. update claim status
23. generate ingestion report

DO NOT COPY CALIBRATION VALUES BLINDLY.

Any proposed calibration value must eventually be derived from:

- matching map definition
- matching firmware
- known units/scaling
- known axes
- known active execution path
- runtime measurements
- controlled A/B validation

A2L / DAMOS HANDLING

Parse A2L semantically.

One object should remain one logical unit whenever possible:

CHARACTERISTIC
MEASUREMENT
AXIS_PTS
COMPU_METHOD
COMPU_TAB
RECORD_LAYOUT
FUNCTION
GROUP
UNIT

For each CHARACTERISTIC store:

name
description
address
type
record_layout
dimensions
x-axis definition
y-axis definition
z-axis if applicable
conversion
unit
minimum
maximum
byte order
signedness
physical scaling
referenced functions/groups

Do not assume an A2L belongs to the current ECU merely because map names look correct.

Validate compatibility using:

- software identifiers
- memory addresses
- map dimensions
- axis values
- known byte patterns
- firmware size
- calibration segment layout

If exact compatibility cannot be established, mark it as REFERENCE_ONLY.

BINARY HANDLING

Binary firmware must remain immutable as source artifacts.

For every firmware version record:

filename
SHA-256
size
ECU ID
HW ID
SW ID
parent firmware
creation reason
maps changed
byte ranges changed
checksum state
flash status
validation status

Never overwrite the original firmware.

Do not ingest arbitrary binary byte chunks into the language-model knowledge index.

Instead ingest:

- metadata
- detected structures
- map definitions
- byte diffs
- checksum information
- human/AI analysis

LOG HANDLING

Raw logs remain stored as files.

Create normalized experiment metadata:

firmware_sha256
date
ambient conditions
coolant temperature
gear
start RPM
end RPM
throttle/load condition
sample rate
diagnostic tool

Extract synchronized channels where available:

RPM
boost requested
boost actual
boost error
barometric pressure
N75/VNT command
MAF requested
MAF actual
driver wish
torque limiter
smoke limiter
actual IQ
injection duration
SOI
IAT
coolant temperature
EGT if available
speed
voltage

Calculate derived metrics:

boost_error = actual - requested

rise_time

time_to_90_percent_target

time_to_95_percent_target

peak_overshoot

overshoot_duration

steady_state_error

oscillation_amplitude

MAF_per_RPM

acceleration_time_between_speed_points

For transient control analysis preserve the original sample timestamps.

Do not compare transient runs without considering sampling rate.

PROJECT-SPECIFIC RESEARCH QUESTIONS

Continuously investigate:

1. What generates final boost request on this software?

2. Which corrections alter PCR_pBDesBas output?

3. What is the role of PCR_rBPCtlBas_MAP?

4. What is the actual sign/direction of its N75/VNT control?

5. How does its IQ axis behave above the final defined axis point?

6. Which PID/closed-loop terms are responsible for transient boost regulation?

7. Which limiter is active during full-load acceleration at:
1500
1600
1700
1800
1900
2000
2250
2500
3000
3500
4000 rpm?

8. Is FlMng_qPresSmoke_MAP actually limiting fuel at each of these points?

9. What determines actual injected quantity?

10. Which SOI maps execute for gears 3/4 versus 5/6?

11. Which thermal protections can reduce torque or boost?

12. Which maps participate in hot start?

13. What was the intended OEM strategy for post-injection and thermal management?

14. Which calibration differences are genuine tuning changes versus unrelated software-version differences?

15. Which duplicate maps are actually executed at runtime?

CURRENT BOOST QUESTION

Recent project telemetry shows fast boost rise but approximately 2310–2330 mbar absolute MAP in part of the 1900–2600 rpm region.

Do not assume the cause.

Test competing hypotheses:

A. boost request itself is high

B. feed-forward VNT/N75 causes excess turbine drive

C. feedback controller transient overshoot

D. atmospheric correction modifies target

E. temperature correction modifies target

F. sensor/log sampling artefact

G. mechanical VNT/N75/vacuum behaviour

For each hypothesis state:

required evidence
available evidence
missing evidence
supporting sources
contradicting sources
confidence

RESEARCH SEARCH STRATEGY

Search combinations of:

Bosch EDC16
EDC16U34
EDC16U1
03G906021QJ
1037391847
BLS
BKC
BXE
BV39
54399880072

with:

DAMOS
A2L
ASAP2
torque model
boost control
charge pressure
VNT
VTG
N75
feed forward
PID
smoke limiter
IQ
duration
SOI
hot start
component protection
EGT
thermal limiter

Search German terminology as well:

Ladedruckregelung
Ladedruck-Sollwert
VTG
Vorsteuerung
Rauchbegrenzung
Einspritzmenge
Einspritzbeginn
Drehmomentbegrenzung
Bauteilschutz
Temperaturschutz
Startmenge

Do not restrict research to English.

SCRAPER RULES

Respect:

robots.txt
rate limits
authentication boundaries
copyright
paywalls
licensing

Do not attempt to bypass protected access.

Store metadata for inaccessible resources so they can be acquired legally later.

FORUM RESEARCH

Forum information is evidence, not truth.

For every useful forum case extract:

vehicle
engine
ECU
software
turbo
injectors
hardware modifications
problem
map changed
before behaviour
after behaviour
logs provided
dyno provided
failure reported
source URL

Prefer posts with:

original logs
before/after logs
binary comparisons
dyno plots
exact ECU IDs
long-term follow-up

Reject unsupported statements such as:

"everyone runs X boost"
"just add 10 percent"
"this map is always N75"
"this value is safe"

unless independently proven.

CONFLICT HANDLING

Never hide conflicting evidence.

Create a conflict record containing:

claim A
claim B
sources
authority
applicability
possible explanation
required experiment
current preferred interpretation

The preferred interpretation must remain provisional until evidence resolves the conflict.

KNOWLEDGE OUTPUTS

Continuously maintain:

source-index.md

ecu-architecture.md

edc16-torque-model.md

boost-control.md

vnt-n75-control.md

fueling-and-limiters.md

smoke-limiter.md

injection-duration.md

injection-timing.md

hot-start.md

thermal-protection.md

hardware-limits.md

a2l-map-index.md

firmware-lineage.md

log-index.md

experiment-results.md

conflicting-evidence.md

open-questions.md

recommended-tests.md

research-changelog.md

Generate a machine-readable representation as JSON/SQLite as well.

MAP KNOWLEDGE FORMAT

For every map generate a record similar to:

Map:
PCR_rBPCtlBas_MAP

Role:
VNT/N75 pre-control candidate

Address:
...

Dimensions:
...

Axes:
RPM × injected quantity

Units:
...

Scaling:
...

Source:
...

Authority:
...

Applicability:
...

Firmware match:
...

Runtime activation proven:
yes / no / unknown

Current calibration:
...

Reference calibration:
...

Differences:
...

Related maps:
...

Runtime channels required:
...

Known uncertainties:
...

Evidence:
...

Status:
...

CALIBRATION SAFETY GATE

Research must not automatically modify or approve a firmware.

A proposed calibration change requires:

1. exact firmware identity
2. correct map/address
3. confirmed units
4. confirmed axes
5. confirmed signedness/endian
6. confirmed active map or strong evidence
7. defined hypothesis
8. defined expected effect
9. minimal controlled change
10. logging plan
11. acceptance criteria
12. abort criteria
13. rollback firmware
14. checksum verification

Change one interacting subsystem at a time whenever practical.

Do not simultaneously change boost control, smoke limiter and SOI when trying to identify the cause of one behaviour.

KNOWLEDGE QUALITY

When answering future engineering questions:

First retrieve exact project evidence.

Then retrieve matching A2L/DAMOS.

Then primary Bosch/VW/BorgWarner/ASAM sources.

Then academic literature.

Then community evidence.

Always distinguish:

FACT

PROJECT OBSERVATION

INFERENCE

HYPOTHESIS

PROPOSED EXPERIMENT

Never present inference as fact.

FINAL OBJECTIVE

Build enough verified knowledge that another engineering agent can answer:

"Why does this exact ECU on this exact vehicle behave this way?"

and provide a reproducible chain:

source
→ map
→ firmware
→ hypothesis
→ experiment
→ measurement
→ validated conclusion.

The knowledge base is an engineering evidence system, not a collection of tuning folklore.
:::

Цей prompt варто покласти прямо в корінь Bootstrap як `RESEARCH_POLICY.md` або `MASTER_RESEARCH_PROMPT.md`.

---

# Як реально запускати наповнення

Не кидав би scraper одразу «на весь інтернет».

Роби проходами.

### Pass 1 — foundation

Тільки:

```text id="y20b0p"
Bosch
VW SSP
ASAM
WinOLS/EVC
ETAS
BorgWarner
Ross-Tech
основні книги
```

Мета — створити словник понять.

### Pass 2 — project mapping

Дати йому:

```text id="zawip2"
твій A2L
BIN original
BIN current
README
project reports
scripts
```

І змусити зв'язати:

```text id="sc88tr"
theory concept
        ↓
A2L function
        ↓
map
        ↓
address
        ↓
current BIN value
```

### Pass 3 — papers

SAE/academic literature по:

```text id="qtzhcf"
VNT
boost transient
PID
diesel combustion
SOI
smoke
turbo matching
```

### Pass 4 — community

Тільки після фундаменту.

Тоді агент уже може побачити, що форумний пост суперечить Bosch/A2L, а не просто запам'ятати його.

### Pass 5 — твої логи

Це перетворює library на **project knowledge**.

---

# Найцінніший результат для нас

Для кожного питання, наприклад:

> «Чому в 2150 rpm отримую 2330 mbar?»

Bootstrap повинен видати не абзац, а щось типу:

```text id="kq7e1k"
Observed:
Actual MAP peak: 2330 mbar

Known static request map:
PCR_pBDesBas_MAP max: ...

Unknown:
Runtime requested boost at exact sample

Possible causes:
1. target correction
2. feed-forward
3. transient PID
4. mechanical response

Evidence:
VW SSP304 ...
A2L PCR...
current BIN ...
VCDS log ...

Missing test:
MVB 011 high-rate run

Confidence:
0.72

Recommended next experiment:
...
```

Оце буде працювати.

Не база «про чіптюнінг», а **інженерна пам'ять конкретно твого Golf**.

Найпершими я б зараз завантажив **Bosch Diesel Engine Management + SSP304 + SSP209/841303 + ASAM MCD-2 MC + Guzzella/Onder + Watson/Janota + WinOLS manual**, після чого вже запускав масовий scraper. Це дасть йому правильний каркас, на який потім ляже інтернет.