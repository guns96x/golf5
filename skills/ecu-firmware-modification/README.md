# ECU Firmware Modification & Reverse Engineering Skill

Автомобільний інженерний скіл та набір інструментів для аналізу, модифікації, контролю цілісності та безпечного прошивання автомобільних блоків керування двигуном (ECU).

Проект розроблений у співпраці **GPT-6 Astra**, **GPT-5.6 Sol (High Effort)** та **Antigravity (Gemini)** під платформу VAG (первинний цільовий блок: **Bosch EDC16U34, VW Golf 5 1.9 TDI BLS, HW `03G906021QJ`, SW `391847`**).

---

## 📁 Структура репозиторію

```text
├── SKILL.md                          # Головна точка входу та маршрутизатор правил
├── references/                       # Спеціалізовані інженерні довідники
│   ├── ecu-profiles.md               # Профілі сімейств ECU та специфікація Golf 5 EDC16U34
│   ├── memory-and-addressing.md      # Архітектури пам'яті (C167 DPP, PowerPC MPC5xx, TriCore, SH)
│   ├── map-identification.md         # A2L/ASAM MCD-2 MC, формули афінних перетворень та інтерполяції
│   ├── integrity-algorithms.md       # Контрольні суми (EDC16 32-bit BE 0xD01FE500), CRC та RSA підписи
│   ├── tuning-and-emissions.md       # Межі калібрування, кути впорскування, деактивація DPF/EGR/AdBlue, DTC
│   └── flashing-and-recovery.md      # 10 передфлеш-шлюзів, живлення, відновлення BDM/Boot
├── scripts/                          # Автономні валідаційні Python-скрипти
│   ├── inspect_image.py              # Інспекція бінарників (хеші SHA-256/512, межі покриття пам'яті)
│   └── verify_integrity.py           # Перевірка адитивної контрольної суми блоку EDC16
└── tests/                            # Тестовий набір
    └── test_behavioral.py            # 12 поведінкових сценаріїв відмови та 9 automated unit-тестів
```

---

## 🤖 Для ChatGPT та зовнішніх ШІ-асистентів

Цей репозиторій є **джерелом істини** для роботи над прошивками. 

### Як залишати правки та інструкції:
1. **Аналіз карт та байтів**: використовуйте точні зміщення (offsets), шістнадцяткові значення та формули з `references/map-identification.md`.
2. **Формат правок для Antigravity**:
   - Вказуйте файл або дамп, точний діапазон байтів (`[Start:End]`), очікувані вихідні байти (original bytes) та цільові байти (replacement bytes).
   - Вказуйте фізичне значення до та після перетворення ($p = a \cdot r + b$).
   - Вказуйте обґрунтування (rationale) з посиланням на відповідні правила безпеки з `references/tuning-and-emissions.md`.
3. **Контроль цілісності**: після будь-яких правок калібровок обов'язково викликайте `scripts/verify_integrity.py` для перерахунку фінального інваріанту `0xD01FE500`.

---

## 🧪 Запуск тестів

```bash
python -m unittest discover -s tests
```
