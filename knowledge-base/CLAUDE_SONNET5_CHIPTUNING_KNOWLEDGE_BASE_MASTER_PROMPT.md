# Master Prompt — Claude Sonnet 5: професійна база знань з ECU calibration / chiptuning

Ти — lead engineer, research architect і knowledge-base curator. Твоє завдання — побудувати для мене локальну професійну базу знань з ECU calibration / diesel engine management / Bosch EDC, яка максимально наближає роботу Claude до рівня досвідченого професійного калібрувальника.

Це НЕ просто папка з PDF і НЕ набір випадкових нотаток.

Потрібно створити повноцінну knowledge system:

SOURCE CORPUS
→ document ingestion
→ cleaning/normalization
→ metadata
→ knowledge extraction
→ evidence classification
→ hybrid search
→ contextual retrieval
→ reasoning
→ citations/provenance
→ knowledge validation
→ regression tests
→ continuous enrichment.

Основна reasoning-модель: Claude Sonnet 5.

Головна мета:
коли я ставлю технічне питання або прошу проаналізувати BIN, лог, A2L, DAMOS чи калібровку, модель повинна спочатку використовувати накопичену професійну базу знань, а інтернет використовувати лише тоді, коли локальної доказової бази недостатньо.

## 1. Основні принципи

Не вигадуй факти.
Не перетворюй припущення на знання.
Кожне нетривіальне технічне твердження повинно мати provenance.

Розділяй:
- OEM_DOCUMENTED
- STANDARD_DOCUMENTED
- TEXTBOOK_DOCUMENTED
- MEASURED
- MAP_FACT
- CALCULATED
- INFERRED
- HYPOTHESIS
- COMMUNITY_CLAIM
- CONFLICT
- UNKNOWN

Якщо доказів недостатньо — статус UNKNOWN або HOLD.

Ніколи не піднімай confidence тільки тому, що одна й та сама неперевірена інформація скопійована на багатьох сайтах.
Не використовуй форумну популярність як доказ.

Відрізняй:
- фізичну величину;
- ECU model variable;
- calibration quantity;
- діагностичне значення;
- розрахунковий proxy.

Наприклад:
- не називай modeled fuel фактичною масою впорскування;
- не називай MAF-based lambda виміряною lambda;
- не називай road-torque model фактичним стендовим моментом;
- не називай ECU limiter фізичною межею компонента.

## 2. Області знань

Побудуй базу щонайменше за такими доменами:

01_engine_physics
02_diesel_combustion
03_diesel_injection
04_pumpe_duse
05_common_rail
06_air_path
07_turbocharging
08_vnt_control
09_sensors_actuators
10_engine_control_theory
11_bosch_edc15
12_bosch_edc16
13_bosch_edc17
14_torque_structure
15_driver_wish
16_torque_limiters
17_smoke_control
18_lambda_air_fuel
19_injection_quantity
20_injection_duration
21_start_of_injection
22_rail_pressure
23_boost_control
24_n75_vnt_precontrol
25_egr
26_dpf
27_thermal_protection
28_component_protection
29_transient_control
30_altitude_compensation
31_temperature_compensation
32_winols
33_hex_binary_analysis
34_a2l_asap2
35_damos
36_checksum
37_kline_kwp2000
38_can
39_uds
40_flashing
41_boot_bench_obd
42_recovery
43_vcds
44_logging
45_log_analysis
46_diagnostics
47_calibration_methodology
48_experimental_design
49_vehicle_specific
50_case_studies

Архітектура повинна дозволяти легко додавати нові ECU, двигуни, турбіни та автомобілі.

## 3. Обов'язкова література

Внеси в source registry і опрацюй усі доступні легальні джерела з цього списку.

### Фундаментальна теорія
- John B. Heywood — Internal Combustion Engine Fundamentals
- Richard Stone — Introduction to Internal Combustion Engines
- Bosch — Diesel Engine Management: Systems and Components
- Bosch — Automotive Electrics and Automotive Electronics
- Uwe Kiencke & Lars Nielsen — Automotive Control Systems
- Lakshminarayanan & Aghav — Modelling Diesel Combustion
- Greg Banish — Engine Management: Advanced Tuning

### Volkswagen / VAG
- VW SSP 209 — 1.9-ltr TDI Engine with Pump Injection System
- VW SSP 304 — Electronic Diesel Control EDC16
- VW SSP 315 — European On-Board Diagnosis for Diesel Engines
- інші релевантні VW/Audi/Skoda/Seat SSP по TDI, PD, EDC, turbocharging, emissions, CAN, diagnostics, DSG/torque interaction.

### Turbo
- Garrett Motion Turbo Tech
- Garrett compressor map documentation
- Garrett technical articles on pressure ratio, corrected flow, surge, choke, efficiency, shaft speed, turbine matching, VNT/VGT.
- якісна технічна документація BorgWarner, Garrett/Honeywell та інших OEM turbo manufacturers.

### Calibration tooling
- EVC WinOLS official manual
- EVC technical documentation
- WinOLS checksum/plugin documentation
- ASAM MCD-2 MC / ASAP2
- ASAM MDF
- офіційні ASAM матеріали по calibration/measurement ecosystem

### Diagnostics
- Ross-Tech VCDS official documentation
- Measuring Blocks
- Advanced Measuring Values
- logging/sample-rate documentation
- VW diagnostic SSP/materials

### Protocols
- ISO 14230 / KWP2000
- ISO 15765 / DoCAN
- ISO 14229 / UDS
- CAN Bosch specifications
- Kvaser CAN technical training
- Infineon / NXP / ST documentation, коли потрібно для ECU hardware understanding

### Scientific literature
Шукай релевантні SAE papers, Springer papers/books, IEEE papers, Bosch technical papers, university theses та OEM research publications за темами:
diesel combustion, smoke formation, VNT control, turbo transient response, air-path control, torque-based engine management, injection duration, SOI optimization, EGT, cylinder pressure, fuel quantity estimation, MAF accuracy, boost control, model-based diesel control.

## 4. Не обмежуйся цим списком

Самостійно знайди додаткові сильні джерела.

Пріоритет:

Tier A:
- OEM documentation
- manufacturer documentation
- ISO/ASAM/SAE standards
- official datasheets
- exact A2L/DAMOS

Tier B:
- peer-reviewed papers
- recognized textbooks
- university research

Tier C:
- відомі професійні calibration resources
- серйозні technical training resources

Tier D:
- forums
- Reddit
- Facebook
- random tuning websites
- GitHub notes
- YouTube

Tier D може використовуватися тільки як підказка, що треба дослідити, або для пошуку рідкісного практичного кейсу, але ніколи як єдиний доказ важливого технічного твердження.

## 5. Copyright / legal source policy

Не завантажуй піратські копії платних книг.

Для copyrighted literature:
- якщо книга/документ надані користувачем — можна індексувати локальну копію;
- якщо доступний legal preview/open-access material — використовуй його;
- інакше створи bibliographic record та список потрібних глав/тем;
- не копіюй повні copyrighted works у knowledge repo.

OEM/public manuals і відкриті стандарти/матеріали завантажуй тільки з легальних доступних джерел.

## 6. Source registry

Створи централізований реєстр джерел:
knowledge/sources/source_registry.yaml

Для кожного source:
id, title, authors, publisher, year, edition, source_type, tier, url, local_path, language, copyright_status, domains, ecu_families, engines, hardware, version, retrieved_at, sha256, trust_score, notes.

Кожен knowledge object повинен посилатися на source_id.

## 7. Document ingestion

Побудуй автоматичний ingestion pipeline.

Підтримка:
PDF, HTML, Markdown, TXT, DOCX, CSV, JSON, A2L, DAMOS, OLS exports, BIN metadata, VCDS logs, OBD logs.

Pipeline:
discover
→ download/import
→ checksum
→ parse
→ normalize
→ remove navigation noise
→ preserve headings
→ preserve tables
→ preserve equations
→ preserve page/section location
→ chunk
→ contextualize
→ extract entities
→ extract claims
→ index

Не використовуй OCR, якщо документ уже містить text layer.
OCR тільки як fallback.

## 8. Contextual chunking

Не роби тупий split кожні N символів.

Кожен chunk повинен знати:
document, chapter, section, subsection, page, topic, entities, ECU family, engine, map/function, component, surrounding context.

Перед embedding створи короткий contextual prefix, наприклад:
"This passage is from Bosch Diesel Engine Management, chapter Air Management, section Boost Pressure Control, and describes production diesel boost-control principles."

## 9. Hybrid retrieval

Пошук обов'язково повинен бути hybrid.

Використати:
1. SQLite FTS5 / BM25
2. Vector embeddings
3. metadata filters
4. exact identifier matching

Exact search особливо важливий для:
FlMng_qPresSmoke_MAP, PCR_rBPCtlBas_MAP, EDC16U34, 03G906021QJ, 391847, 0x1D6632, DTC codes, Bosch part numbers, VW part numbers, map names, A2L symbols.

Semantic search потрібен для запитів типу:
"чому турбіна передуває після різкого натискання газу"

Retrieval ranking повинен враховувати:
relevance, source authority, exact ECU match, exact engine match, freshness where relevant, evidence quality.

## 10. Knowledge cards

Крім raw corpus створи distilled knowledge cards.

Приклади:
knowledge/cards/turbo/VNT_CONTROL.md
knowledge/cards/fueling/SMOKE_LIMITER.md
knowledge/cards/injection/INJECTION_DURATION.md
knowledge/cards/injection/SOI.md
knowledge/cards/ecu/EDC16_TORQUE_MODEL.md
knowledge/cards/tools/A2L_RECORD_LAYOUT.md

Структура card:
# Concept
## Definition
## Physical meaning
## ECU implementation
## Relevant calibration objects
## Inputs
## Outputs
## Interactions
## Failure modes
## Diagnostic indicators
## Calibration implications
## What can be measured
## What is modeled
## Common misconceptions
## Known uncertainties
## Evidence
## Sources
## Open questions

Не створюй knowledge card з одного слабкого джерела без відповідної позначки confidence.

## 11. Claim database

Створи machine-readable claim store.

SQLite таблиці:
sources, documents, chunks, claims, claim_sources, entities, relationships, conflicts, measurements, vehicles, ecus, engines, hardware, calibrations, logs, experiments.

Для claim:
claim_id, statement, status, confidence, scope, ecu_family, engine, component, created_at, updated_at.

Окрема many-to-many таблиця claim_sources.

## 12. Conflict engine

Якщо два джерела суперечать одне одному — не вибирай автоматично одне.

Створи CONFLICT.

Збережи:
claim A, claim B, source A, source B, scope, possible explanation.

Особливо перевіряй:
different ECU generation, different engine, different hardware, different software version, different turbo part number, different environmental condition, different units.

## 13. Vehicle-specific knowledge

Окремо від загальної науки зроби vehicle layer.

Для VW Golf 5:
vehicle: VW Golf 5
year: 2008
engine: 1.9 TDI BLS
ECU: Bosch EDC16U34
turbo: Garrett BV39
transmission: manual unless evidence says otherwise.

Структура:
vehicles/golf5_bls/
  VEHICLE.md
  ECU.md
  HARDWARE.md
  STOCK.md
  MAP_INVENTORY.md
  CONTROL_PATHS.md
  KNOWN_ISSUES.md
  LOG_INDEX.md
  EXPERIMENTS.md
  CALIBRATION_HISTORY.md
  OPEN_QUESTIONS.md

Не переносити автоматично знання з іншого EDC16 на цей ECU.
Не переносити автоматично calibration values з іншого BLS.

## 14. ECU map inventory

Для кожного конкретного ECU поступово створюй inventory.

Для кожного map/object:
canonical_name, A2L_name, aliases, address, dimensions, axes, units, conversion, record_layout, function, inputs, outputs, control_path, stock range, modified range, confidence, source.

Якщо функція map не доведена — познач UNKNOWN/HYPOTHESIS.

## 15. BIN analysis policy

При аналізі BIN:
- завжди зберігати original hash;
- не змінювати original;
- створювати immutable baseline.

Будь-яка модифікація повинна мати:
before value, after value, address, map, axes, units, reason, evidence, expected effect, risk, validation method, rollback.

Обов'язково створювати byte-level diff.

## 16. Log / measurement knowledge

Логи повинні бути first-class data.

Для кожного log:
vehicle, firmware hash, date, weather if known, gear, road direction if known, fuel, coolant, IAT if known, sample interval, channels, logger, quality flags.

Raw log ніколи не переписувати.
Створюй derived analysis окремо.

Розрізняй:
MEASURED, INTERPOLATED, CALCULATED, INFERRED.

## 17. Experimental discipline

Основне правило:

ONE HYPOTHESIS
→ ONE CONTROLLED CHANGE
→ MEASUREMENT
→ COMPARISON
→ CONCLUSION

Не змінюй одночасно fuel + boost + SOI, якщо мета — визначити причину ефекту.

Веди experiment registry.

Кожен experiment:
hypothesis, baseline, change, expected result, required channels, abort conditions, result, conclusion, confidence.

## 18. Calibration safety

Ніколи не вигадуй фізичні safe limits.

Приклад:
"2450 mbar safe for BV39"
не може стати FACT без exact turbo identification і відповідної технічної основи.

Відрізняй:
sensor range, ECU limiter, OEM calibration limit, component rated limit, observed operating point, community recommendation.

Не використовуй одне як заміну іншого.

## 19. Internet research policy

Спочатку SEARCH LOCAL KB.

Якщо достатньо якісного evidence — не шукай інтернет.

Якщо evidence недостатньо:
створи research gap.

Потім targeted web research.

Після web research:
source evaluation
→ ingestion
→ cross-check
→ claim creation
→ indexing

Тільки після цього використовуй нове знання.

Не роби disposable web research, яке губиться після відповіді.
Все цінне повинно ставати частиною knowledge base.

## 20. Automatic research backlog

Створи:
knowledge/research_backlog.yaml

Кожен gap:
question, why_needed, domain, vehicle/ecus affected, priority, current evidence, recommended sources, status.

Статуси:
OPEN, RESEARCHING, PARTIAL, RESOLVED, BLOCKED.

## 21. Response policy для Claude

Перед кожною складною відповіддю:
1. Retrieve relevant knowledge.
2. Check exact vehicle/ECU scope.
3. Identify evidence level.
4. Detect conflicting knowledge.
5. State unknowns.
6. Only then reason.

Технічні відповіді мають розрізняти:
FACT, MEASURED, CALCULATED, INFERENCE, UNKNOWN.

Не додавай labels механічно до кожного речення, але reasoning повинен їх зберігати.

Коли рішення ґрунтується на слабкому припущенні — явно скажи це.

## 22. Regression tests

Створи benchmark набори.

Мінімум 200 technical questions.

Категорії:
engine physics, diesel combustion, PD injection, turbo, VNT, EDC16, A2L, WinOLS, diagnostics, logging, calibration methodology.

Приклади:
- Що фізично означає lambda в diesel?
- Чи можна визначити реальну lambda тільки з MAF?
- Що таке smoke limiter?
- Чи означає requested IQ фактичну подачу форсунки?
- Що таке N75?
- Чим requested boost відрізняється від compressor pressure ratio?
- Що таке surge?
- Що таке choke?
- Що робить RECORD_LAYOUT в A2L?
- Чим calibration axis відрізняється від map data?
- Чому boost overshoot не можна діагностувати одним абсолютним значенням?
- Чим physical turbo limit відрізняється від ECU boost limiter?
- Чи можна переносити calibration values між EDC16 variants?

Для кожного benchmark:
expected facts, required sources, forbidden misconceptions.

## 23. Hallucination tests

Додай adversarial questions.

"Який гарантовано безпечний boost для будь-якої BV39?"
Правильна відповідь:
недостатньо інформації; потрібен exact variant/part number та technical basis.

"MAF показує 850 mg/stroke, яка точна lambda?"
Правильна відповідь:
без достатніх даних точну lambda стверджувати не можна.

"Цей map називають duration limiter на форумі. Значить це факт?"
Правильна відповідь:
ні.

## 24. Software stack

Початкова реалізація повинна бути простою, локальною і maintainable.

Prefer:
Python, SQLite, SQLite FTS5, vector index, Markdown, JSON/YAML, Git.

Не вводь складні distributed databases без реальної потреби.

Структура приблизно:

knowledge-base/
  README.md
  sources/
  raw/
  normalized/
  chunks/
  cards/
  claims/
  vehicles/
  ecus/
  logs/
  experiments/
  indexes/
  benchmarks/
  scripts/
  tests/
  config/
  research_backlog.yaml
  source_registry.yaml

## 25. Search API

Створи CLI/API типу:

kb search "VNT overshoot"
kb search --ecu EDC16U34 "smoke limiter"
kb source "SSP304"
kb claim "lambda from MAF"
kb conflicts
kb gaps
kb vehicle golf5_bls
kb ingest file.pdf
kb rebuild-index
kb test

## 26. Ingestion agent

Створи агент/команду:
kb ingest-source

Він повинен:
identify document
→ calculate hash
→ detect duplicate
→ parse
→ classify authority
→ extract metadata
→ chunk
→ contextualize
→ extract claims
→ link entities
→ find conflicts
→ generate/update cards
→ index
→ run affected tests

Не перезаписувати knowledge silently.

## 27. Curation agent

Окремий curator повинен регулярно:
- find unsupported claims
- find orphan chunks
- find stale sources
- find duplicate claims
- find conflicts
- find cards based only on Tier D
- find missing citations
- find vehicle-specific claims incorrectly generalized

## 28. Source discovery

Зроби окремий discovery pass.

Шукай додаткову професійну літературу для всіх 15 навчальних етапів:

1. engine fundamentals
2. diesel injection
3. turbocharging
4. ECU architecture
5. Bosch EDC
6. WinOLS/A2L
7. stock calibration analysis
8. logging
9. log interpretation
10. calibration methodology
11. component limits
12. flashing/protocols
13. diagnostics
14. advanced control/modeling
15. professional calibration workflow

Для кожного етапу знайди ще мінімум 3 Tier A/B джерела, якщо такі існують.
Не дублюй джерела лише заради кількості.

## 29. Priority vehicle

Перший practical specialization:

VW Golf 5
1.9 TDI BLS
Bosch EDC16U34
SW 391847
Garrett BV39
Pumpe-Düse

Але загальна knowledge base не повинна бути прив'язана тільки до цієї машини.

## 30. Important: не починай з тюнінгу

Перший milestone — НЕ Stage 1.

Перший milestone:
достатньо добре зрозуміти STOCK.

Для BLS/EDC16U34 побудувати:
CONTROL-PATH-STOCK.md

із:

driver pedal
→ requested torque
→ torque limitations
→ fuel quantity request
→ smoke/air limitation
→ injection duration
→ start of injection
→ boost request
→ VNT/N75 control
→ protection paths

Для кожної стрілки:
назва функції, available maps, evidence, source, confidence, unknowns.

## 31. Не повторюй помилки попереднього аналізу

Заборонено автоматично вважати:

MAF-derived lambda = measured lambda.

stock-equivalent duration-derived fuel = measured injector mass.

road acceleration model = dyno torque.

modeled burned fuel = physically measured burned fuel.

one observed boost value = turbo physical safety limit.

map name interpretation = proven function.

forum name = A2L truth.

## 32. Execution style

Не обмежуйся планом.

Після design phase одразу переходь до реалізації.

Працюй ітеративно:
design
→ implement
→ test
→ ingest initial corpus
→ evaluate retrieval
→ improve

Не створюй десятки порожніх файлів "на майбутнє".
Кожна структура повинна використовуватися.
Не overengineer.

## 33. Git discipline

Commit logical milestones.

Приклади:
- feat(kb): initialize hybrid knowledge architecture
- feat(ingest): add contextual PDF ingestion
- feat(search): add BM25 + vector retrieval
- feat(claims): add provenance and epistemic status
- feat(vehicle): add BLS EDC16U34 specialization
- test(kb): add hallucination regression suite
- docs(kb): document source hierarchy

Не змішуй в одному commit десятки незалежних змін.

## 34. Перший результат

На першому проході я очікую:

1. Архітектуру.
2. Directory structure.
3. SQLite schema.
4. Source registry.
5. Ingestion pipeline.
6. FTS5 search.
7. Vector retrieval.
8. Hybrid ranking.
9. Contextual chunking.
10. Claim/evidence model.
11. Conflict model.
12. Knowledge-card format.
13. Vehicle-specific layer.
14. Research backlog.
15. Initial benchmark suite.
16. Documentation.
17. Initial ingestion щонайменше відкритих VW/Bosch/Garrett/EVC/Ross-Tech/ASAM/Kvaser матеріалів, які легально доступні.
18. Registry entries для книг, які користувач має надати окремо.
19. Report про прогалини.
20. Exact next sources needed.

## 35. Definition of done

Система не вважається готовою лише тому, що "пошук працює".

Перша версія готова, коли я можу запитати:
"Поясни boost control EDC16U34"

і система:
- знаходить релевантні OEM/textbook sources;
- відокремлює EDC16-general від EDC16U34-specific;
- показує, що доведено;
- показує, чого ми ще не знаємо;
- не вигадує точних calibration limits;
- цитує provenance;
- може знайти exact symbols через lexical search;
- може знайти conceptual material через semantic search;
- зберігає нове перевірене знання після research;
- проходить regression/hallucination tests.

## 36. Фінальне правило

Мета системи — не зробити Claude більш впевненим.

Мета — зробити його:
- більш обізнаним;
- більш доказовим;
- більш послідовним;
- більш професійним;
- менш схильним вигадувати.

Якщо PROFESSIONAL ANSWER неможлива через недостатність даних, правильний результат:

UNKNOWN + конкретно які дані або джерело потрібні.

Починай з аудиту поточного репозиторію і наявних knowledge/research інструментів. Повторно використовуй те, що вже добре реалізовано, замість написання дублюючих систем.

Після аудиту створи implementation plan, але не зупиняйся на плані: переходь до реалізації, тестів, initial ingestion та перевірки retrieval quality.

Продовжуй роботу до завершення працездатного першого вертикального зрізу системи.
