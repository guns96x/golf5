# ECU Knowledge Base — локальна

База знань по ECU calibration для VW Golf 5 1.9 TDI BLS / Bosch EDC16U34.
Працює повністю офлайн. Жодних сервісів, ключів і оплат.

## Головний принцип

Система не «знає» відповідь. Вона знає, **де шукати, що вважати доказом і коли
доказів недостатньо**.

Тому тут є одна річ, якої немає у звичайному RAG: **`kb check`** — детермінована
перевірка, яку не можна вмовити. Цитата, якої дослівно немає в інгестованому
документі, не проходить. Це не інструкція моделі, це SQL.

## Встановлення (Windows)

```bat
cd /d D:\CLAUDE\golf5\ecu-kb
pip install -r requirements.txt
python kb.py init
python seed_gaps.py
```

Потрібен Python 3.10+. Усе інше — `pypdf`, 400 KB.

## Наповнення

Повний прохід із нуля (перебудовується будь-коли, база в git не лежить):

```bat
python kb.py ingest-a2l "..\diagnostic-review\definitions\*\*.a2l" --sw 1037391847
python kb.py ingest D:\CLAUDE\base\knowledge\library
python kb.py ingest D:\CLAUDE\base\knowledge\drafts

python kb.py load-claims claims\boost-path-stock.json
python kb.py load-claims claims\turbo-bv39-scope.json
python kb.py load-claims claims\boost-path-values.json

REM claims\boost-path-values.json на самоперевірці змішав значення мапи (MAP_FACT)
REM з читанням цього значення (INFERRED/CALCULATED) в одному твердженні, і частина
REM тексту втрачала референт поза контекстом сусіднього рядка. Замість тихого
REM редагування — явне відкликання й заміна (правило "зміна думки — поле в БД"):
python kb.py retract 22 "Реєстр library_registry.json насправді вже коректно приписує документ TDIClub Technical Archive (не Pierburg). Помилка була моя — не перевірив реєстр перед тим, як написати claim."
python kb.py retract 28 "Змішано MAP_FACT і INFERRED в одному твердженні." --state superseded
python kb.py retract 29 "Те саме змішування, плюс несамодостатній текст «у тому самому образі»." --state superseded
python kb.py retract 30 "Змішано MAP_FACT (сирі байти) з INFERRED (сентинел); неповний перелік читань." --state superseded
python kb.py retract 32 "Несамодостатній текст «у цьому образі»." --state superseded
python kb.py retract 33 "Змішано MAP_FACT з INFERRED; несамодостатній текст." --state superseded
python kb.py retract 34 "Несамодостатній текст «у цьому образі»." --state superseded
python kb.py resolve-gap 13 RESOLVED --note "Не було потрібно — реєстр уже коректний."

python kb.py load-claims claims\boost-path-values-corrections.json
python kb.py resolve-gap 9 PARTIAL --note "Структуру й значення декодовано з reconstructed BIN; живого readback немає."

python kb.py load-claims claims\n75-duty-direction.json
python kb.py resolve-gap 12 PARTIAL --note "Напрямок встановлено MEASURED з logs/VCDS_WOT_Log_20260914_153242.csv: більша шпаруватість -> менший наддув (замкнений контур)."

python kb.py load-claims claims\logs-inventory.json
python kb.py resolve-gap 16 RESOLVED --note "Проскановано (Gemini-інвентаризація 52 файлів + вибіркова ручна перевірка)."

python kb.py load-claims claims\firmware-modification-reliability.json

REM Фото заводської таблички турбіни (закриває блокуючу P1-прогалину #1).
REM Ця сесія самого фото не бачила — текст переказаний іншою сесією, тому
REM короткі відмінні мітки (бренд, родина) MEASURED з вищою впевністю, довгі
REM буквено-цифрові коди — з нижчою. Старий каталожний номер турбіни на
REM табличці АГРЕГАТА відсутній — відкликано, не переписано тихо:
python kb.py load-claims claims\turbo-nameplate-photo.json
python kb.py retract 24 "Головна теза (безпечна межа наддуву невідома) лишається правильною. Але посилання на конкретне виконання '54399880072' застаріло: фото заводської таблички показує іншу систему нумерації агрегата — BV39A-0012 / NE 1003/1756-00002. Каталожний номер на табличці відсутній." --state superseded
python kb.py resolve-gap 1 RESOLVED --note "Фото зроблено й проаналізовано (переказ). BorgWarner BV39 підтверджено фізично."
python kb.py resolve-gap 14 BLOCKED --note "Замінено прогалиною #21: номер 54399880072 на табличці агрегата відсутній, пошук за ним був приречений."

REM Ревю поточної прошивки (new-inputs/on проти стоку) на прохання власника.
python kb.py load-claims claims\current-firmware-review.json

REM Знахідка: третій, чистіший кандидат лежить у сусідньому проєкті
REM golf5-android-flasher, поза golf5. Ще не з'ясовано, чи він записаний.
python kb.py load-claims claims\refined-calibration-discovery.json

REM Власник підтвердив: НЕ записаний. У машині — прошивка до проєкту
REM флешера (new-inputs/on). Закриває gap про те, чи refined_CS_OK у блоці.
python kb.py resolve-gap 24 RESOLVED --note "Власник підтвердив прямо: refined_CS_OK НЕ записаний. У машині — прошивка з ДО проєкту флешера, тобто new-inputs/on."
python kb.py load-claims claims\current-state-confirmed.json

REM Пряме читання фото (не переказ) + власник продиктував наживо: позначення
REM турбіни насправді BV39A-0072, не BV39A-0012. Три claims, що посилались
REM на 0012, відкликані — не переписані тихо. Lader-Nr лишається непевним.
python kb.py resolve-gap 20 RESEARCHING --note "Gemini запущено на пошук за BV39A-0072 (виправлений номер)."
python kb.py load-claims claims\turbo-designation-corrected.json

REM Gemini повернув 5 "джерел" з конкретними цифрами (розміри коліс,
REM ElsaWin-діапазон, заводська уставка). Перевірено відвідуванням КОЖНОГО
REM URL напряму — ЖОДНЕ не підтвердилось: головні сторінки без вмісту або
REM сторінки за антибот-захистом. Одне з чисел (2050 мбар) збігалось із вже
REM відомим фактом — саме тому й підозріле, не тому що надійне. gap #20
REM повернуто в OPEN, не залишено RESOLVED на слово воркера:
python kb.py load-claims claims\gemini-search-verification-failed.json
python kb.py resolve-gap 20 OPEN --note "Gemini-пошук завершено, але всі 5 джерел перевірено відвідуванням і жодне не підтвердилось."

python kb.py check
python kb.py status
```

Порядок команд відтворює реальний хід роботи, включно з власною помилкою і
самовиправленням — саме тому ретракції тут явні кроки, а не переписаний файл.

Що виходить на поточному корпусі: **16 772 об'єкти A2L** (11 537 CHARACTERISTIC,
5 220 MEASUREMENT, 15 AXIS_PTS), **97 документів** = 76 `HAVE_LOCAL` +
21 `PROJECT_DRAFT`, **8732 чанки**, 2565 ідентифікаторів.

Інгест сам:
- рахує SHA-256 і не бере дублікати повторно;
- **вимірює** текстовий шар парсером, а не вірить чужому звіту. Два файли
  відхилені саме так: `Heywood_…_Complete.pdf` (481 сторінка, 0 символів) і
  `Bosch_Diesel_PreTech_…pdf`;
- **не пускає файл, якого немає в реєстрі.** Інакше в корпус тихо заходять наші
  ж `LIBRARY_INDEX.md` і `MULTILINGUAL_RESEARCH_POLICY.md` — тим самим
  механізмом, яким чернетки колись отримали Tier A;
- чанкує зі збереженням номерів сторінок — без локатора цитата непридатна;
- будує contextual prefix до кожного чанка;
- витягує точні ідентифікатори: A2L-символи, адреси `0x…`, парт-номери, номери SW;
- **позначає власні чернетки як `PROJECT_DRAFT`**, а не як джерела (див. нижче);
- застосовує правила застосовності за назвою документа, причому «чужа система»
  (VP37, Common Rail, PE/PF, EDC17) має пріоритет: інакше `Einspritzpumpen PE/PF`
  ловиться підрядком «pumpe» і отримує ap4 замість ap1.

A2L читається як **latin-1** і далі не перекодовується — інакше німецькі описи
(`Ladedruckverhältnis`, `Verzögerungszeitkonstante`) стають сміттям.

## Пошук

```bat
python kb.py search "PCR_rBPCtlBas_MAP"
python kb.py search "charge pressure control solenoid valve"
```

Пошук гібридний: спершу **точний** збіг ідентифікаторів (для `FlMng_qPresSmoke_MAP`,
`0x1D6632`, `03G906021QJ` — тут ембединги не потрібні й тільки заважають),
потім **FTS5/BM25** для змістових запитів. Чернетки в ранжуванні штрафуються.

Якщо нічого не знайдено — це не привід здогадуватись, а привід завести `gap`.

## Чому чернетки відокремлені

У бібліотеці 21 Markdown-файл, який колись потрапив туди з міткою Tier A.
Це **наші власні робочі нотатки** з репозиторію golf5. Один із них перевірено —
байт-у-байт збігається з `docs/knowledge/boost-control.md`, який сам себе
називає «Draft Knowledge Layer».

Визначаються вони за полем реєстру `obtainability == "PROJECT_DRAFT"`, **не за
назвою видавця**: коли захист стояв на видавцеві, достатньо було стерти поле
`publisher` — і 21 чернетка мовчки поїхала в корпус як джерело.

Якби вони лишились джерелами, будь-яке твердження могло б «процитувати Tier A»,
а насправді послатися на нашу ж неперевірену чернетку. База підтверджувала б
сама себе. Тому вони інгестяться зі статусом `PROJECT_DRAFT`, у видачі
підписані `[ЧЕРНЕТКА]`, а `kb check` ловить спроби цитувати їх як OEM.

Вони не викинуті — це корисні гіпотези. Вони просто не докази.

## Перевірка цілісності

```bat
python kb.py check
```

Чотири правила, усі детерміновані:

1. твердження `OEM_DOCUMENTED`/`STANDARD`/`TEXTBOOK` **без цитати** — порушення;
2. цитата, якої **дослівно немає** в тексті чанка — порушення;
3. твердження, що цитує **власну чернетку** як зовнішнє джерело — порушення;
4. твердження про конкретний ECU **без номера SW** — порушення.

Правило 2 — те, заради чого все будувалось. Перевірено негативним тестом із
чотирьох порушень одразу: вигадана цитата «The maximum permissible boost
pressure for the BV39 turbocharger is 2450 mbar absolute», приписана SSP 304,
не потрапляє в базу взагалі — `load-claims` не знаходить її дослівно в жодному
чанку. Твердження при цьому лишається без цитати й падає на правилі 1.
Разом із ним тест ловить OEM-твердження без цитати, OEM-твердження, підперте
власною чернеткою, і твердження про EDC16U34 без номера SW.

Два рубежі різні: `load-claims` не дає вигаданій цитаті зайти, а `check` ловить
цитати, які «поїхали» після переінгесту корпусу.

## Епістемічна модель

Два **ортогональні** виміри, не один:

| `evidence_kind` — чим є доказ | `verification_state` — наскільки перевірений |
|---|---|
| `OEM_DOCUMENTED`, `STANDARD`, `TEXTBOOK` | `raw`, `corroborated` |
| `MEASURED`, `MAP_FACT`, `CALCULATED` | `project_matched`, `experiment_supported` |
| `INFERRED`, `HYPOTHESIS` | `verified` |
| `COMMUNITY_CLAIM`, **`MODEL_RECALL`**, `UNKNOWN` | `contradicted`, `deprecated`, `superseded` |

`MODEL_RECALL` — знання з навчання моделі, джерело локально не перевірене.
Без цього статусу модель змушена або мовчати, або підписати своє знання чужим
авторитетом. Саме так у базі й з'явився claim, підписаний VW SSP 304, якого
ніхто не читав.

Ретракції — повноцінні поля (`supersedes_id`, `retracted_at`,
`retraction_reason`), бо в цьому проєкті відкликання висновків реальність,
а не теорія.

**Третій, окремий вимір — `source_class`: ЯК саме підтверджено.**
`document_citation` (перевіряється `kb check` дослівним збігом) відрізняється
від `bin_derived`/`log_derived`/`computed` (провенанс — шлях і sha256 у
самому тексті твердження, як у `claims/boost-path-values.json`,
`claims/n75-duty-direction.json`) і від `human_attested` (`confirm-check`).
Раніше цього поля не було, і BIN/log-похідні claims просто не мали
структурованого способу сказати, чим саме вони підтверджені — тепер є.

**Межа, яку `kb check` НЕ закриває.** Перевірка ловить, що цитата
дослівно існує в чанку (`citation_verified`). Вона НЕ перевіряє, що ця
цитата логічно ПІДТВЕРДЖУЄ саме те твердження, до якого прикріплена
(`support_verified`) — цю різницю автоматизувати означало б знову довірити
моделі семантичне судження, тобто повернути саме той ризик, проти якого
все будувалось. Це залишається людською роботою при читанні claims.
З тієї самої причини `claims.created_by` і `claims.reviewed_by` — окремі
поля: `load-claims` завжди заповнює перше, друге лишається `NULL`, доки
хтось (за змогою — інша сесія чи людина) не підтвердить окремо. Self-review
(`created_by = reviewed_by`) схема не забороняє, але робить видимим.

## Прогалини

```bat
python kb.py gaps
python kb.py resolve-gap 9 PARTIAL --note "чому саме"
```

`resolve-gap` приймає `OPEN | RESEARCHING | PARTIAL | RESOLVED | BLOCKED`.
`--note` тільки друкується — сам текст пояснення варто лишити в claims-файлі
чи в документі, що на нього посилається; у БД зберігається лише статус.

Найважливіші відкриті: немає точного джерела по Pumpe-Düse (у секції injection
лежать VP37 і Common Rail — обидві системи не ті), немає незайманого дампа ECU
і фото таблички турбіни, немає компресорної карти саме на виконання BV39
`54399880072`.

## Відкликання тверджень

```bat
python kb.py retract 22 "чому саме — причина обов'язкова"
```

Ставить `verification_state='deprecated'`, `retracted_at`, `retraction_reason`.
Причина — поле в БД, а не речення в чаті: «ой, помилився, ви праві» без нового
доказу нічого не змінює (`CLAUDE.md`, правило 7). Використано на живому
прикладі: claim про те, що реєстр бібліотеки нібито приписує документ
Pierburg — реєстр насправді вже коректний, помилка була моя.

## Ворота перед прошивкою

`docs/FIRMWARE-MODIFICATION-RELIABILITY.md` — умови, за яких запис у ECU
перестає бути азартною грою. Розділ 9 того документа реалізований командами:

```bat
python kb.py record-readback dump1.bin dump2.bin --source own_readback --by "<ім'я>" --label "..."
python kb.py confirm-check recovery_tested --by "<ім'я>" --scope standing
python kb.py confirm-check power_confirmed --by "<ім'я>" --scope per_event
python kb.py confirm-check rollback_documented --by "<ім'я>" --scope per_event --note "який файл, чим, скільки часу"
python kb.py log-check logs\....csv --required Driver_Wish_IQ_mg,Torque_Limit_IQ_mg,Smoke_Limit_IQ_mg
python kb.py flash-preflight --target <образ> --log <лог>
```

`flash-preflight` повертає `exit 0` і `{"blocked": []}`, тільки якщо всі
шість умов виконані. Те, що софт може перевірити сам — перевіряється
автоматично й першим, ще до питань про процес:

- сам файл: існує, точно очікуваного розміру (2 097 152 байт), містить
  ASCII SW/HW-ідентифікатори цієї машини, контрольна сума EDC16 (дві
  32-бітні суми блоків, межі й ціль — з `tools/calmath_engine.py`,
  верифіковано раніше на цьому ж корпусі) збігається;
- живі канали в логах (той самий детектор, що ловив замерзлу телеметрію
  в `logs/`).

Те, чого софт знати не може (чи підключений зарядний, чи пройдено
відновлення на живому блоці, чи задокументований шлях відкату) — вимагає
`confirm-check` як людського засвідчення, і команда лише вимагає його
наявності. `record-readback` не приймає той самий файл як обидва
зчитування (`os.path.samefile`) — інакше ворота 2.1 тривіально обходились
копією одного дампа. Кожен виклик `flash-preflight` пишеться в
`flash_events` незалежно від результату; сам журнал незмінний —
`UPDATE`/`DELETE` на ньому забороняє тригер схеми.

## Що далі

Спочатку FTS5 на реальному корпусі — він уже покриває точні запити повністю.
Вектори мають сенс, коли точний пошук почне не справлятись: тоді BGE-M3
у fp16 (~1.2 GB) стане на RTX 3050 і дасть dense + sparse з однієї моделі.
Qdrant при 5 тисячах чанків не потрібен — це десятки мегабайт у RAM.

**Корпус у git не кладемо.** `.gitignore` вже це блокує: `git push` — це
поширення, а не особиста копія.
