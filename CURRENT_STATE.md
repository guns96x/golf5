# CURRENT_STATE.md — ОПЕРАТИВНИЙ ЗРІЗ СТАНУ ПРОЄКТУ
> **ПРАВИЛО ПЕРШОЇ ДІЇ:** якщо існує `ecu-kb/remote/manifest.json`, зовнішня модель
> читає його ПЕРШИМ, а цей файл — другим. `CURRENT_STATE.md` є оперативним
> narrative/handoff і може відставати від canonical SQLite state. Локальні агенти
> перевіряють актуальний стан командами `kb.py claims`, `kb.py gaps`, `kb.py check`.
> **ЗАБОРОНЕНО** починати сесію зі сліпого сканування директорій
> (`find_by_name`, `list_dir`, `grep_search`).

---

## 1. Головна мета та епістемічний протокол

1. **Ціль:** Створення автономної, непохитної бази знань та вузькопрофільного спеціаліста з калібрування дизельних систем (Pumpe-Düse / EDC16U34) на базі першоджерел (OEM-мануали, SSP, патенти, стандарти, A2L).
2. **Черговість робіт:** **СПОЧАТКУ знання та повний аналіз стоку, тюнінг — ПОТІМ.** Питання модифікації прошивки (Stage 1 / DPF OFF) розглядаються лише після повної готовності доказової бази.
3. **Захист від галюцинацій та підлабузництва:**
   - Жодне твердження не приймається без дослівної цитати або A2L-змінної (`python kb.py check`).
   - «Ой, ви праві» без нового першоджерела заборонено. Зміна позиції — це запис у БД з `retraction_reason`, а не речення в чаті.
   - Власні чернетки (`base/knowledge/drafts/`) мають статус `PROJECT_DRAFT` і не є доказом.

---

## 2. Паспорт автомобіля (ВСТАНОВЛЕНО — НЕ шукати й НЕ перепитувати)

| Параметр | Значення | Статус доказу |
|---|---|---|
| Авто | VW Golf 5 (1K1), 2008 | `ASSUMED` |
| Двигун | 1.9 TDI 8V Pumpe-Düse, **BLS**, 77 kW / 105 к.с. | `OEM_DOCUMENTED` |
| ECU | Bosch **EDC16U34**-3.42, процесор Motorola/Freescale MPC562 | `OEM_DOCUMENTED` |
| HW | `03G 906 021 QJ` | `MEASURED` (наліпка блоку) |
| SW | `1037391847`, проєкт `P447_HAXN` | `MEASURED` |
| Турбіна | **BorgWarner BV39A-0072**; `03G253014M`; довга цифрова послідовність Lader-Nr ще має невизначеність розбивки | `MEASURED/corroborated` для позначення BV39A-0072; див. current claims |
| КПП | 02M (6-ступенева механіка) | `ASSUMED` |

---

## 3. Точні шляхи до первинної істини (НЕ сканувати диски)

- **Робочі директорії на ПК:**
  * Головний робочий репозиторій: `D:\golf5-ecu-system\` (GitHub: `guns96x/golf5-ecu-system`, гілка `main`).
  * Дзеркало робочого простору Claude: `D:\CLAUDE\golf5\` (гілка `claude/prompt-review-iuvqhg`).
- **A2L-специфікація (16 772 об'єкти):**
  `diagnostic-review/definitions/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.a2l`
- **Еталон прошивки для аналізу (HEX / BIN):**
  * `diagnostic-review/definitions/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.HEX`
  * `diagnostic-review/reference-from-hex.analysis-only.bin` (реконструйований з hex, sha256 `cf891152…`)
  * `firmware/reference_dumps/VW_Jetta_1.9TDI_SW391847_HW03G906021QJ_Stock_and_EGRoff/flashORGIG` (100% точний сток калібрувань)
- **База еталонних дампів та WinOLS проєктів (`firmware/reference_dumps/`):**
  * `VW_Golf5_1.9TDI_SW389289_HW03G906021QJ_Stage1_DPFoff_WinOLS_OLS_KP/` — повний проєкт WinOLS `.ols` та Map Pack `.kp` під залізо `03G906021QJ`.
  * `Seat_Leon_1.9TDI_SW382081_HW03G906021LK_EDC16U34_EGRoff/` — повний 2MB BDM-дамп EDC16U34 з 1 МБ кодової зони процесора MPC562 (вирішення Gap #23/#2).
  * `VW_Caddy_1.9TDI_BLS_SW377228_HW03G906021AR_Stage1/` — референс Stage 1 на моторі BLS.
  * `VW_PassatB6_1.9TDI_SW380420_HW03G906021LR_EDC16U34_Stage1/` — референс EDC16U34 Stage 1.
- **Інженерна документація калібрування:**
  * `docs/tuning/stage1_bls_edc16u34_master_guide.md` — інженерний посібник Stage 1: розрахунок наддуву BV39, захист вкладишів BLS, карти A2L, вирішення Gap #10.
  * `docs/knowledge/4pda_firmware_damos_catalog.md` — каталог посилань 4PDA, структура WinOLS Damos Sammlung (800 GB) та опис `aria2c`.
  * `docs/CONTROL-PATH-STOCK-boost.md` — ланцюг керування наддувом стоку.
  * `docs/CONTROL-PATH-STOCK-fuel.md` — ланцюг керування паливом стоку.
- **База знань (SQLite + FTS5):**
  `ecu-kb/knowledge/kb.sqlite3` (реєстр: `ecu-kb/remote/manifest.json`).

---

## 4. Стан бази знань (`ecu-kb`)

> Нижчі числові показники — історичний зріз на момент написання цього файла.
> Для поточного стану використовуй `kb.py status` або
> `ecu-kb/remote/manifest.json -> stats`.

- **Документів у базі:** 97 (76 `HAVE_LOCAL` + 21 `PROJECT_DRAFT`).
- **Текстових чанків:** 8 732 (усі прив'язані до точних номерів сторінок).
- **Ідентифікаторів:** 2 565 точних токенів (A2L, адреси `0x…`, парт-номери).
- **Тверджень (Claims):** 52 formal claims (наддув, паливо, момент, Pumpe-Düse, BV39).
- **Цитат у базі:** 20 verbatim citations з першоджерел.
- **Цілісність (`python kb.py check`):** **0 порушень.**

### Швидкі команди роботи з базою знань:
```bat
cd D:\golf5-ecu-system\ecu-kb
python kb.py status                 # загальний стан
python kb.py check                  # перевірка порушень цитувань (0 порушень)
python kb.py claims                 # перегляд усіх затверджених тверджень
python kb.py consult "<запит>"      # консультація вузькопрофільного спеціаліста (анти-сикофантія)
python kb.py search "<запит>"       # точний пошук за словом/номером
python kb.py a2l <префікс>          # перегляд карт A2L за групою (наприклад, PCR, FlMng, InjVlv)
python kb.py gaps                   # перелік відкритих прогалин
```

---

## 5. Поточний статус робіт і наступні кроки

1. **Завершено:**
   - Повний вертикальний зріз стоку наддуву (`docs/CONTROL-PATH-STOCK-boost.md`): педаль $\to$ внутрішній момент $\to$ лімітери $\to$ паливо $\to$ уставка наддуву $\to$ PID $\to$ N75.
   - Повний вертикальний зріз стоку палива та моменту (`docs/CONTROL-PATH-STOCK-fuel.md`): `AccPed` $\to$ `CoEng` $\to$ `FMTC` $\to$ `FlMng` $\to$ `InjCtl` $\to$ `InjVlv` / `InjCrv` / `BIP`.
   - Інгест фізичних claims системи Pumpe-Düse (SSP 209, SSP 315) та турбіни BV39 (BorgWarner).
   - Модуль автономного спеціаліста `specialist.py` / `kb.py consult` з жорсткими анти-сикофантичними запобіжниками.
   - Формалізоване відокремлення `PROJECT_DRAFT` від зовнішніх доказів у KB.
2. **В роботі ЗАРАЗ:**
   - Декодування числових значень решіток палива з заводського BIN (`FMTC_trq2qBas_MAP`, `FlMng_qAFSCDSmoke_MAP`, `InjVlv_phiInjMI1_MAP0`, `InjCrv_phiBas0_GMAP`).
   - Аналіз тригерів післявпорскування (Post-Injection `InjVlv_phiInjPoI2`) та регенерації в OFF-прошивці для виявлення причини білого диму.
3. **Прогалини:** не дублювати тут вручну як канонічний список.
   Поточний стан дивись через `python kb.py gaps` або
   `ecu-kb/remote/gaps.json`. Це усуває вже виявлений drift, коли #1 і #12
   лишались записані тут як відкриті після появи нових доказів/часткового закриття.
