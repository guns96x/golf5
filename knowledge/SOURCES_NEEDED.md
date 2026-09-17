# Що потрібно від тебе: джерела та дані для knowledge base

**Дата:** 2026-09-17
**Пов'язано з:** `docs/prompt-review-2026-09-17-kb-v2.md` (редлайн B1 — розділення реєстру джерел)

Кожне джерело нижче має статус:

| Статус | Значення |
|---|---|
| `WANT_USER_COPY` | **Я не можу отримати легально. Потрібен твій файл.** |
| `HAVE_PUBLIC_URL` | Публічно і легально доступне — **завантажу сам, тобі робити нічого не треба** |
| `NEEDS_DECISION` | Платний стандарт / стаття — потрібне твоє рішення про покупку |
| `USER_DATA_ONLY` | Не література. Дані, які може дати лише власник авто |

> **Не купуй нічого з розділу 2** — воно безкоштовне і легальне, я заберу сам.

---

## 1. `WANT_USER_COPY` — книги, які маєш надати

### Пріоритет P0 — без них база залишиться теоретично порожньою

| # | Джерело | Видання | Що саме розблоковує | Потрібні розділи |
|---|---|---|---|---|
| U-01 | **Bosch — Dieselmotor-Management** (нім.) або **Diesel-Engine Management** (англ. переклад) | **4-те вид., 2004/2005** — саме воно, не 5-те | Епоха EDC16. Опис торк-структури, charge-pressure control, PD/UIS. Найближче до твого ECU з усіх книг | Electronic Diesel Control; Charge-air/boost control; Unit Injector System; Torque-led structure; Sensors |
| U-02 | **Bosch — Diesel Engine Management: Systems and Components** (K. Reif) | 5-те вид., 2014, Springer Vieweg | Ширше і сучасніше покриття: датчики, актуатори, архітектура EDC, діагностика. Доповнює U-01, не замінює | Diesel fuel-injection; Electronic control; Sensors; Air management; OBD |
| U-03 | **Bosch Technical Instruction — Diesel Fuel-Injection Systems: Unit Injector System / Unit Pump System (UIS/UPS)** | «жовта серія», ~1999-2003 | **Найточніше джерело саме по Pumpe-Düse.** Гідравліка PD-форсунки, вплив cam ramp, pre-injection, обмеження тривалості | Повністю (брошура ~60 стор.) |
| U-04 | **Guzzella & Onder — Introduction to Modeling and Control of IC Engine Systems** | 2-ге вид., 2010, Springer | Теоретична основа для `VNT_CONTROL` і `BOOST_CONTROL`: mean-value models, feed-forward + feedback, anti-windup, turbo dynamics | Гл. 2 (mean-value models); гл. 3-4 (control); turbocharger sections |
| U-05 | **J.B. Heywood — Internal Combustion Engine Fundamentals** | 1-ше (1988) або 2-ге (2018) — підійде будь-яке | Основа для `SMOKE_LIMITER` і для hallucination-тесту «lambda в дизелі»: сажоутворення, локальна vs глобальна lambda, AFR | Гл. 10 (combustion in CI engines); гл. 11 (pollutant formation, soot); гл. 4 (thermochemistry) |

### Пріоритет P1 — сильно підвищують якість, але не блокують старт

| # | Джерело | Видання | Що розблоковує |
|---|---|---|---|
| U-06 | **Kiencke & Nielsen — Automotive Control Systems** | 2-ге вид., 2005, Springer | Торк-структура, driveline oscillation damping. **Прямо стосується ASDdc**, який ми вже досліджували (`transient-torque-asddc-dynamic-smoke-2026-09-16.md`) |
| U-07 | **Bosch Technical Instruction — Electronic Diesel Control (EDC)** | «жовта серія» | Стисле OEM-пояснення саме структури EDC — торк-координатор, лімітери, шляхи захисту |
| U-08 | **Bosch Automotive Handbook** | 8-ме…11-те — будь-яке | Довідкові дані: криві датчиків, динаміка актуаторів, теплофізика |
| U-09 | **Hiereth & Prenninger — Charging the Internal Combustion Engine** (Springer, 2007) *або* **Watson & Janota — Turbocharging the ICE** (1982) | будь-яке | Turbine matching, VNT nozzle mechanics, pulse energy, surge/choke. Hiereth дістати легше — Watson давно не друкується |

### Пріоритет P2 — за бажанням, низька applicability до твого авто

| # | Джерело | Чому низький пріоритет |
|---|---|---|
| U-10 | Richard Stone — Introduction to Internal Combustion Engines | ~80% перетину з Heywood |
| U-11 | Lakshminarayanan & Aghav — Modelling Diesel Combustion | Глибоке моделювання сажі; корисно, але для калібрування надлишково |
| U-12 | Greg Banish — Engine Management: Advanced Tuning | Переважно бензин + MAF/VE-методологія; до PD-дизеля застосовне частково |

### Окремо: **DAMOS** для `1037391847`
`USER_COPY` — A2L у нас уже є (11 537 характеристик), але DAMOS додав би групування функцій і коментарі. Якщо в тебе є — клади. Якщо ні — **не шукай, не критично**: A2L покриває майже все.

---

## 2. `HAVE_PUBLIC_URL` — **не купуй, заберу сам**

- VW SSP **209** — 1.9 TDI Pumpe-Düse
- VW SSP **304** — Electronic Diesel Control EDC16 ← найцінніший публічний документ для проєкту
- VW SSP **315** — European OBD for Diesel Engines
- VW SSP **336** — Catalytic Coated DPF
- BorgWarner — Understanding Compressor Maps + reman turbo catalog (де `03G253014M` ↔ BV39)
- EVC WinOLS 5 manual (`winols HelpEn.pdf`) + DAMOS/ASAP2 import + EDC16 checksum plugin docs
- Ross-Tech Wiki: VCDS measuring blocks для EDC16, label files, EDC16 адаптації
- Kvaser CAN technical training
- Garrett Turbo Tech (загальна теорія: PR, corrected flow, surge, choke) — **позначу `applicability: generic, NOT this turbo`**, бо в тебе BorgWarner
- Open-access дисертації по VGT/air-path control (їх достатньо, і вони безкоштовні)

---

## 3. `NEEDS_DECISION` — платне, потрібне твоє рішення

| Джерело | Ціна (орієнтовно) | Моя рекомендація |
|---|---|---|
| **ASAM MCD-2 MC (A2L) специфікація** | сотні € | **Не купувати.** Твій власний `.a2l` на 12.6 MB — кращий доказ структури, ніж специфікація. Граматику виведу з нього |
| **ISO 14230 (KWP2000), ISO 15765, ISO 14229 (UDS)** | ~150-200 CHF за частину | **Не купувати зараз.** Для EDC16 по K-line достатньо публічних описів + твоїх реальних логів обміну (`mpps_capture.pcap` уже є) |
| **SAE papers** | ~$33/шт | Відкладаю. На етапі discovery складу короткий список 3-5 конкретних статей із обґрунтуванням «що саме це закриє» — тоді вирішиш. Одна вже ідентифікована: `2003-01-0357` (Ammann, VGT+EGR) |
| **VW erWin / ELSA** (офіційна сервісна документація) | **~€7 за годину доступу** | ⭐ **Найкраще співвідношення ціна/користь із усього платного.** Дає заводські специфікації BLS, тести актуаторів N75, значення адаптацій, опис вимірювальних груп саме для твого двигуна. Це applicability 5, дешевше за будь-яку книгу |

---

## 4. `USER_DATA_ONLY` — дані, які **важливіші за половину книг**

Книги дають applicability 2-3. Це дає applicability **5** — тобто твердження саме про твоє авто.

### 4.1 Firmware
- [ ] **Незайманий заводський віднятий дамп** цього ECU (повний flash), знятий **до** будь-яких змін, із зазначенням чим і коли знято. У репо зараз є `reference-from-hex.analysis-only.bin`, **реконструйований з HEX**, а не оригінальний readback — це не те саме, і це вже створює епістемічну дірку
- [ ] Якщо є — дамп ECU в стані «до видалення DPF/EGR» (у git-логу є згадка про «ON (pre-delete)» firmware)

### 4.2 Фото / підтвердження заліза
- [ ] Табличка турбіни (part number крупним планом) — щоб `BorgWarner BV39 54399880072` став `MEASURED`, а не `INFERRED` з каталогу
- [ ] Номери форсунок PD (`038 130 073 xx`) — визначають гідравлічну продуктивність
- [ ] Наліпка ECU (HW/SW номери)
- [ ] Наліпка коробки (літерний код) + підтвердження кількості передач
- [ ] Наявність/відсутність DPF і EGR фізично

### 4.3 VCDS
- [ ] Повний **Auto-Scan** (усі блоки)
- [ ] Блок 01: кодування, версія, всі **адаптаційні канали**
- [ ] Дамп вимірювальних груп 001-125 на прогрітому холостому ходу — це основа `log_channels` словника, без якого логи не крос-запитуються

### 4.4 Логи (за протоколом одного експерименту)
- [ ] WOT 3-та передача, від ~1500 до відсічки, рівна дорога, прогрітий двигун
- [ ] Те саме 4-та передача (для відділення навантаження від обертів)
- [ ] Холодний старт (для перевірки HS-250 фіксу)
- Для кожного: температура повітря, паливо, ухил, напрямок, пробіг

### 4.5 Базові факти авто (зараз це **припущення**, не записи)
- [ ] Рік випуску (у промті стоїть 2008 — це підтверджено?)
- [ ] Пробіг
- [ ] Коробка: механіка/DSG
- [ ] Історія: що робилось з двигуном, турбіною, форсунками
- [ ] Паливо, яким їздиш (цетанове число впливає на SOI)

---

## 5. Вимоги до формату файлів

- **Тільки PDF із текстовим шаром.** Сканована книга без OCR = ~0 користі, і OCR по формулах і таблицях дає сміття
- Оригінальні видавничі PDF, не «роздруківка в PDF» і не фото сторінок
- Німецькою — нормально (U-01 навіть краще в оригіналі)
- Клади в `knowledge/raw/` — ця тека піде в `.gitignore`

### Що буде з файлами (юридично)
- Індексуються **локально**, у git **не потрапляють** — бо git push на GitHub це вже поширення, а не особиста копія
- У репозиторій ідуть лише: sha256, бібліографічні метадані, локатори (сторінка/секція) і **короткі дослівні цитати** в обсязі, потрібному для підтвердження конкретного твердження
- Тобто база буде відтворювана, але не буде копією книг

---

## 6. Якщо можеш дати лише три

У порядку віддачі на вкладений час:

1. **U-01** — Bosch Dieselmotor-Management 4-те вид. (епоха EDC16)
2. **U-03** — Bosch UIS/UPS брошура (єдине точне джерело по Pumpe-Düse)
3. **U-04** — Guzzella & Onder (уся теорія boost/VNT control)

Плюс безкоштовне: **розділ 4.1 + 4.3** (незайманий дамп і дамп вимірювальних груп) — це дешевше за все і дає найвищу applicability.

---

## 7. Що я можу робити вже зараз, без жодного файлу від тебе

- M1 повністю: міграція схеми, `MODEL_RECALL`, ретро-переоцінка наявних 6 claims і 21 джерела, citation-integrity перевірка, `CLAUDE.md`, hallucination + retrieval тести
- Інгест усього з розділу 2 (публічне)
- Інгест того, що вже лежить у репо: A2L (11 537 мап), 7 BIN-ів, логи, `mpps_capture.pcap`

Тобто **старт не заблокований**. Твої файли потрібні для того, щоб claims перестали бути `MODEL_RECALL` і стали `OEM_DOCUMENTED` із цитатою.
