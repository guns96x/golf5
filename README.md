# 🚗 Volkswagen Golf 5 1.9 TDI BLS — ECU Bosch EDC16U34 Tuning & Research Master Repository

> **Цільовий автомобіль:** VW Golf 5 1.9 TDI (код двигуна BLS, 8 клапанів, Pumpe-Düse / PD, заводський DPF видалено, EGR заглушено).  
> **VIN:** `WVWZZZ1KZ8M338620`  
> **Блок керування (ECU):** Bosch EDC16U34 | VAG HW: `03G906021QJ` | SW: `1037387342` / `1037391847` | Версія: `P447HAXN`  
> **Турбіна:** 100% заводський оригінал **BorgWarner (KKK) BV39** (`03G253014M` / `54399880072`). Механічно перевірена, люфти в нормі, випускний тракт герметичний.

---

## 🟢 1. ПОТОЧНИЙ СТАН АВТОМОБІЛЯ ТА ЗАЛИТА ПРОШИВКА (FOR CHATGPT & TUNERS)

### 🔥 ПРОШИВКА, ЯКА ЗАРАЗ ЗАЛИТА В БЛОЦІ І НА ЯКІЙ ЇЗДИТЬ АВТО:
📁 **[`03G906021QJ_stage1_full_power_dpf_egr_off.bin`](./03G906021QJ_stage1_full_power_dpf_egr_off.bin)**
* **Розмір:** `2 097 152 байти` (рівно 2.0 МБ)
* **SHA-256:** `d8296554b0342a9a4eb1ca0af0a17ccbbecc066349907448213ea6179ad2bfe0`
* **Що налаштовано та працює в авто прямо зараз:**
  1. **Stage 1 Full Power:** розрахункова потужність **~140–145 к.с. та 325–330 Нм** (цільовий наддув `PCR_pBDesBas_MAP` піднято до 2214 мбар).
  2. **Повна ліквідація димності та смороду (PoI2 OFF):** 5 карт післявпорскування (`0x1E1616..0x1E654A`, 1534 байти) повністю обнулено (`0.0 мг`). Блок більше не ллє сиру солярку у випуск на фазі випуску, дим і сморід усунені.
  3. **Виправлено датчик температури ОР (CTSCD):** за адресою `0x1CF2F6` відновлено штатне значення `0x0B` замість затертого нулями `0x00`. ЕБУ не падає у прихований аварійний захист після нагрівання до 87°C.
  4. **Захист турбіни:** відновлено карту лімітера крутного моменту за температурою перед турбіною `EngPrt_facTempPreTrbn_MAP` (EGT > 805°C).
* **Чого в ній ЩЕ НЕМАЄ (порівняно з наступною версією):**
  * Фіксу гарячого запуску `HS-250` (на гарячу стартер крутить 2–3 секунди через заводські нулі на 250 об/хв).
  * Трасового еко-випередження кута впорскування на 5–6 передачах (+0.703° BTDC).

---

### 🚀 НАСТУПНА ГОТОВА ПРОШИВКА ДЛЯ ЗАЛИВКИ (REFINED + HOT START FIX):
📁 **[`03G906021QJ_stage1_refined_CS_OK.bin`](./03G906021QJ_stage1_refined_CS_OK.bin)**
* **Розмір:** `2 097 152 байти`
* **SHA-256:** `a517affa3f89bf2ba188a84c6b6810b20f61fa297de4917e99cba5f1f18e2b44`
* **Що додано понад поточну прошивку:**
  1. **Hot Start Fix (`HS-250`):** у карті `StSys_trqStrtBas_MAP` (`0x1F0762`) на 250 об/хв при 40–100°C додано **108–125 Нм** $\rightarrow$ **запуск на гарячу за 0.5 с з пів оберту**.
  2. **Eco Cruise Timing:** на 5–6 передачах на круїзі (`InjCrv_phiBasGear56_MAP` на `0x1DACF8`) кут піднято на **+0.703° BTDC** під заглушений EGR (краще згоряння, менша витрата палива на 90–120 км/год).
  3. **Контрольні суми (CS_OK):** перераховані 32-бітні суми Bosch у двох банках (`0x1BFFFC` та `0x1FDFFC`).

---

### 📦 Інші версії прошивок у репозиторії:
* **`03G906021QJ_stage1_refined_dpf_egr_off.bin`**: ідентична до `_CS_OK`, але без попередньо прописаних у файл байтів КС (MPPS перераховує їх сам при записі).
* **`03G906021QJ_ideal_stage1_dpf_egr_off.bin`**: тестова збірка із заводськими картами Duration (поїхала занадто мляво, відхилена).
* **`gdrive_downloads/`**: папка з початковими дампами з Google Drive (`VW_Golf___391847_DPF__EGR_chk_ok.bin` тощо).

---

## 📊 2. РЕАЛЬНІ ДАНІ ТЕЛЕМЕТРІЇ (WOT ЛОГИ ДО ТА ПІСЛЯ)

### Порівняння заїзду 14 вересня (стара прошивка) vs 16 вересня (поточна прошивка `stage1_full_power`):

| Оберти двигуна (RPM) | Стара гаражна прошивка (14.09.2026) | **Поточна прошивка в авто (16.09.2026 об 11:20)** | Фізичний ефект |
| :--- | :--- | :--- | :--- |
| **~1400–1450 об/хв** | 1418 мбар (яма недодуву -336 мбар) | **1890 мбар** | **+472 мбар!** Турбіна підриває миттєво |
| **~1570 об/хв** | 1612 мбар (глибокий лаг -306 мбар) | **2020 мбар (1.02 бар надлишкового)** | **+408 мбар!** Повний підрив на 1-й, 2-й, 3-й передачах |
| **~1740 об/хв** | 1775 мбар | **2230 мбар (1.23 бар)** | **+455 мбар!** Вихід на робочий буст на 400 об/хв раніше |
| **2100–2600 об/хв** | Викид / овершут до **2438 мбар**! | **2310–2320 мбар** (ідеальна полиця) | **Небезпечний передув зник**, крильчатка BV39 захищена |
| **3600–4000 об/хв** | Спад тяги | **2160–2170 мбар** | Точно відповідає цільовій карті наддуву 2214 мбар |
| **Витрата повітря (MAF)**| В'яла | **108.50 г/с** | Максимальне наповнення циліндрів |
| **Швидкість розгону** | Слабкий розгін до 80 км/год | **з 47 до 143 км/год** | Повний розгін у відсічку |

*Файли логів збережені в папці [`logs/`](./logs/) та [`logs/20260916/`](./logs/20260916/).*

---

## 🧠 3. ІНЖЕНЕРНА БАЗА ЗНАНЬ ТА ОФІЦІЙНИЙ A2L (EDC16U34 SW 391847)

Репозиторій розгорнуто як повноцінну інженерну базу знань відповідно до **[EDC16U34 Knowledge Bootstrap Pack](./docs/knowledge/EDC16U34_KNOWLEDGE_BOOTSTRAP_PACK.md)** та **[Master Research Policy](./docs/knowledge/RESEARCH_POLICY.md)**.

### 📚 Центр знань та технічні документи:
* **Головний портал знань:** [`docs/knowledge/README.md`](./docs/knowledge/README.md)
* **Політика та правила фактів (Епістемічний статус):** [`docs/knowledge/RESEARCH_POLICY.md`](./docs/knowledge/RESEARCH_POLICY.md)
* **Каталог 21+ першоджерел (Tier A/B/C з рейтингами):** [`docs/knowledge/source-index.md`](./docs/knowledge/source-index.md)
* **Архітектура ECU (MPC562, Flash 2MB, розбивка пам'яті):** [`docs/knowledge/ecu-architecture.md`](./docs/knowledge/ecu-architecture.md)
* **Модель крутного моменту EDC16 (Indicated/Outer torque, втрати):** [`docs/knowledge/edc16-torque-model.md`](./docs/knowledge/edc16-torque-model.md)
* **Керування наддувом (`PCR_pBDesBas_MAP`, PID, корекції):** [`docs/knowledge/boost-control.md`](./docs/knowledge/boost-control.md)
* **Геометрія VNT та клапан N75 (`PCR_rBPCtlBas_MAP`, вплив EGR):** [`docs/knowledge/vnt-n75-control.md`](./docs/knowledge/vnt-n75-control.md)
* **Ієрархія паливних лімітерів (Driver Wish, Torque, Smoke):** [`docs/knowledge/fueling-and-limiters.md`](./docs/knowledge/fueling-and-limiters.md)
* **Димовий лімітер за тиском MAP (`FlMng_qPresSmoke_MAP`):** [`docs/knowledge/smoke-limiter.md`](./docs/knowledge/smoke-limiter.md)
* **Тривалість впорскування насос-форсунок (`InjCrv_phiDur_MAP`):** [`docs/knowledge/injection-duration.md`](./docs/knowledge/injection-duration.md)
* **Кути випередження впорскування SOI (`InjCrv_phiMI1Des_MAP`):** [`docs/knowledge/injection-timing.md`](./docs/knowledge/injection-timing.md)
* **Фікс гарячого запуску (`EngM_qStart_MAP`, чому глухне на 250 RPM):** [`docs/knowledge/hot-start.md`](./docs/knowledge/hot-start.md)
* **Температурний захист та модель EGT (Bauteilschutz):** [`docs/knowledge/thermal-protection.md`](./docs/knowledge/thermal-protection.md)
* **Межі заліза (Турбіна BV39, шатуни BLS, маховик DMF):** [`docs/knowledge/hardware-limits.md`](./docs/knowledge/hardware-limits.md)
* **Індекс активних карт у SW 1037391847:** [`docs/knowledge/a2l-map-index.md`](./docs/knowledge/a2l-map-index.md)
* **Лінійка прошивок та контрольні суми:** [`docs/knowledge/firmware-lineage.md`](./docs/knowledge/firmware-lineage.md)
* **Індекс логів VCDS та телеметрії:** [`docs/knowledge/log-index.md`](./docs/knowledge/log-index.md)
* **Аналіз овербусту 2310–2330 мbar за логами:** [`docs/knowledge/experiment-results.md`](./docs/knowledge/experiment-results.md)
* **Вирішення суперечливих даних (полярність N75, димність):** [`docs/knowledge/conflicting-evidence.md`](./docs/knowledge/conflicting-evidence.md)
* **15 відкритих інженерних питань та гіпотези наддуву:** [`docs/knowledge/open-questions.md`](./docs/knowledge/open-questions.md)
* **Рекомендовані протоколи діагностики VCDS:** [`docs/knowledge/recommended-tests.md`](./docs/knowledge/recommended-tests.md)

### 🗄️ Реляційна база знань SQLite з FTS5:
* **Файл БД:** [`knowledge/edc16_knowledge.db`](./knowledge/edc16_knowledge.db) (11 537 індексованих карт та характеристик з офіційного A2L).
* **CLI інструмент пошуку:** `python tools/knowledge_manager.py search <термін_або_адреса>`
* **Офіційний A2L опис (12 МБ):** [`diagnostic-review/definitions/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42/`](./diagnostic-review/definitions/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42/)
* **Індекс характеристик A2L (JSON):** [`diagnostic-review/a2l-characteristics-index.json`](./diagnostic-review/a2l-characteristics-index.json)

---

## 💬 4. ПОВНА ХРОНОЛОГІЯ ТА ЛИСТУВАННЯ ПО ПРОЄКТУ (1:1 БЕЗ ПРИКРАС)

Усі 395 діалогових кроків між користувачем та штучним інтелектом (Gemini / Antigravity, OpenAI Codex Sol 5.6 High, Astra High) експортовані без скорочень:
* **Текстовий повний лог (Markdown):** [`conversation_history/FULL_CONVERSATION_HISTORY.md`](./conversation_history/FULL_CONVERSATION_HISTORY.md)
* **Адаптивний мобільний переглядач (HTML):** [`conversation_history/FULL_CONVERSATION_HISTORY.html`](./conversation_history/FULL_CONVERSATION_HISTORY.html)
* **Системні логи траєкторії:** [`conversation_history/transcript_full.jsonl`](./conversation_history/transcript_full.jsonl)

---

## 🤖 5. ІНСТРУКЦІЯ ДЛЯ CHATGPT ТА ЗОВНІШНІХ ШІ-МОДЕЛЕЙ

Якщо ви працюєте над цим проєктом як ChatGPT, Claude або інший LLM-асистент:
1. **Базовий файл для наступних модифікацій:** використовуйте [`03G906021QJ_stage1_refined_CS_OK.bin`](./03G906021QJ_stage1_refined_CS_OK.bin), оскільки він містить Hot Start Fix, виправлений CTSCD та правильні контрольні суми.
2. **Формат правок:** вказуйте точні шістнадцяткові адреси (`0x...`), розмір у байтах, старі та нові значення з урахуванням `COMPU_METHOD` з A2L.
3. **Критичні інваріанти заліза:**
   * Турбіна BorgWarner BV39: максимальний піковий тиск наддуву не повинен перевищувати **2250–2300 мбар абс.**
   * Двомасовий маховик (DMF): не задирати крутний момент на низах (< 1900 об/хв) вище 330 Нм, щоб уникнути резонансних вібрацій та руйнування пружин.
   * Контрольна сума: після редагування байтів у секторі калібрувань обов'язково перераховуйте 32-бітну суму Bosch для блоків `0x1BFFFC` та `0x1FDFFC`.
