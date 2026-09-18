# VW Golf 5 1.9 TDI BLS — Bosch EDC16U34 Engineering Context

> **Для Claude Code:** Цей файл є точкою входу в проєкт. Не скануй репозиторій наосліп.  
> Усі ключові файли, дампи, A2L та посібники чітко розписані нижче.

---

## 1. Паспорт автомобіля та блоку (ВСТАНОВЛЕНО — НЕ перепитувати)
* **Авто:** Volkswagen Golf V (1K1), 2008 рік.
* **Двигун:** 1.9 TDI 8V Pumpe-Düse, код **BLS** (77 кВт / 105 к.с., 250 Нм).
* **ЕБУ (ECU):** Bosch **EDC16U34-3.42**, мікроконтролер Motorola/Freescale MPC562.
* **Апаратний номер (HW):** `03G 906 021 QJ`
* **Програмний номер (SW):** `1037391847`, оновлення (Upg) `1984`, проєкт Bosch `P447_HAXN`.
* **Турбокомпресор:** BorgWarner / KKK BV39A-0072 (`03G253014M` / `03G253019K`).
* **Насос-форсунки:** 038 130 073 BN (Bosch 0 414 720 229, тип PDE-P1.1).

---

## 2. Карта проєкту та ключові файли істини

### 2.1 Офіційний інженерний опис (A2L Damos)
* 📁 [`diagnostic-review/definitions/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42/`](file:///D:/golf5-ecu-system/diagnostic-review/definitions/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42)
  * `...3.42.a2l` — 16 772 параметри Bosch (назви карт, адреси, формули перерахунку).
  * `...3.42.HEX` — повний заводський Intel-HEX образ (кодова зона MPC562 + калібрування).
  * `...3.42.S19` — образ у форматі Motorola S-Record.
  * `...3.42.sgm` — метадані проекту Bosch.

### 2.2 База еталонних дампів (`firmware/reference_dumps/`)
* 📁 [`firmware/reference_dumps/VW_Jetta_1.9TDI_SW391847_HW03G906021QJ_Stock_and_EGRoff/`](file:///D:/golf5-ecu-system/firmware/reference_dumps/VW_Jetta_1.9TDI_SW391847_HW03G906021QJ_Stock_and_EGRoff)
  * `flashORGIG` — 100% точний збіг калібрувань стоку (`0x180000..0x1FDFFF`, 0 байт різниці).
  * `WinOLS (VW Jetta (egr off_dtc off ) - 391847)` — робоче вимкнення EGR/DTC.
* 📁 [`firmware/reference_dumps/VW_Golf5_1.9TDI_SW389289_HW03G906021QJ_Stage1_DPFoff_WinOLS_OLS_KP/`](file:///D:/golf5-ecu-system/firmware/reference_dumps/VW_Golf5_1.9TDI_SW389289_HW03G906021QJ_Stage1_DPFoff_WinOLS_OLS_KP)
  * Повний проєкт WinOLS **`.ols`** та Map Pack **`.kp`** під залізо `03G906021QJ`.
* 📁 [`firmware/reference_dumps/Seat_Leon_1.9TDI_SW382081_HW03G906021LK_EDC16U34_EGRoff/`](file:///D:/golf5-ecu-system/firmware/reference_dumps/Seat_Leon_1.9TDI_SW382081_HW03G906021LK_EDC16U34_EGRoff)
  * Повний **2MB BDM-дамп EDC16U34** (1 001 844 байти кодової зони MPC562, вирішення Gap #23/#2).
* Інші референси 1.9 TDI BLS: VW Caddy BLS Stage 1, VW Passat B6 EDC16U34.

### 2.3 Документація та посібники калібрування
* 📄 [`docs/tuning/stage1_bls_edc16u34_master_guide.md`](file:///D:/golf5-ecu-system/docs/tuning/stage1_bls_edc16u34_master_guide.md) — **Головний інженерний посібник Stage 1**:
  * Математичний розрахунок безпечного надуву BV39 ($P_{boost} \le 2350$ мбар, $AFR \approx 18.5:1$).
  * Захист безспуттерних вкладишів BLS (плавний вихід на момент 336 Нм після 2250 об/хв).
  * Розв'язання Gap #10 (канали лімітерів у VAG Group 008).
* 📄 [`docs/knowledge/4pda_firmware_damos_catalog.md`](file:///D:/golf5-ecu-system/docs/knowledge/4pda_firmware_damos_catalog.md) — каталог теми 4PDA, структура WinOLS Damos Sammlung (800 GB) та опис консольного клієнта торентів `aria2c`.
* 📄 [`docs/CONTROL-PATH-STOCK-boost.md`](file:///D:/golf5-ecu-system/docs/CONTROL-PATH-STOCK-boost.md) — детальний ланцюг керування наддувом стоку.
* 📄 [`docs/CONTROL-PATH-STOCK-fuel.md`](file:///D:/golf5-ecu-system/docs/CONTROL-PATH-STOCK-fuel.md) — детальний ланцюг керування паливом стоку.
* 📄 [`CURRENT_STATE.md`](file:///D:/golf5-ecu-system/CURRENT_STATE.md) — оперативний зріз поточного стану.

---

## 3. Робота з базою знань (`ecu-kb`)

```bat
cd ecu-kb
python kb.py status                 # статус бази (claims, gaps, sources)
python kb.py check                  # валідація цитувань (має бути 0 порушень)
python kb.py claims                 # затверджені інженерні твердження
python kb.py consult "<запит>"      # консультація вузькопрофільного спеціаліста
python kb.py search "<запит>"       # пошук у FTS5 індексі першоджерел
```

---

## 4. Фізичні та калібрувальні інваріанти
1. **Турбіна BV39:** Не перевищувати 2350 мбар абсолютного тиску (1.35 бар наддуву). При 2420+ мбар турбіна виходить у зону перекруту та протитиску $P_3 > 2.8$ бар.
2. **Вкладиші BLS:** Не давати більше 290 Нм до 2000 об/хв. Піковий момент 330–336 Нм подавати строго після 2250 об/хв.
3. **Карти тривалості (Duration):** Залишати заводськими! Не задирати Duration для збереження коректної моделі розрахунку моменту та $EGT$.
4. **Кінець впорскування (EOI):** Утримувати не пізніше $8–10^\circ$ після ВМТ (ATDC).

