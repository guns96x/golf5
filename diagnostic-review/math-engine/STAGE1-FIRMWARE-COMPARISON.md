# Порівняння прошивок Stage 1 — 2026-09-16

## Огляд файлів

| Файл | SHA-256 | Розмір |
|---|---|---|
| `03G906021QJ_ideal_stage1_dpf_egr_off.bin` | `55c80596de4d8b622d0c1227e03e30e4b99ef22d3b9a3e0078ce6b5f0d84e3b7` | 2 097 152 байти |
| `03G906021QJ_stage1_full_power_dpf_egr_off.bin` | `d8296554b0342a9a4eb1ca0af0a17ccbbecc066349907448213ea6179ad2bfe0` | 2 097 152 байти |
| `03G906021QJ_stage1_refined_CS_OK.bin` | `a517affa3f89bf2ba188a84c6b6810b20f61fa297de4917e99cba5f1f18e2b44` | 2 097 152 байти |
| `03G906021QJ_stage1_refined_dpf_egr_off.bin` | `48c8f368b5ce26cd920e3e2dcc7be20762d0ab69684504843f2e23ebb0c56fe8` | 2 097 152 байти |

**Поточна прошивка в автомобілі:** `03G906021QJ_stage1_full_power_dpf_egr_off.bin` (d8296554...)

## Матриця відмінностей

| Порівняння | Різних байтів | Примітки |
|---|---|---|
| ideal ↔ full_power | 209 | Найбільша відмінність |
| ideal ↔ refined_CS_OK | 235 | |
| ideal ↔ refined | 227 | |
| **full_power ↔ refined_CS_OK** | **26** | Поточна → refined_CS_OK |
| **full_power ↔ refined** | **18** | Поточна → refined |
| refined_CS_OK ↔ refined | 8 | Мінімальна відмінність |

## Детальний аналіз: full_power → refined_CS_OK (+26 байтів)

### 1. Контрольні суми (8 байтів)
- **0x1BFFFC–0x1BFFFF** (4 байти): `446e54d3` → `de55fa0c`
- **0x1FDFFC–0x1FDFFF** (4 байти): `63396f40` → `e73ffa72`

### 2. FlMng_qPresSmoke_MAP — smoke limiter (1 байт)
- **0x1D6603**: `0x12` → `0xDA` (18 → 218 у raw hex)
- **Карта:** `FlMng_qPresSmoke_MAP` (адреса 0x1D65F8–0x1D6663)
- **Значення:** одна клітинка smoke limiter змінена
- **З candidate-vnext.json:** refined_CS_OK піднімає 2500 rpm/2000 hPa з 56.5 → 58.5 мг
- **Статус у DECISION:** поточне значення 56.5 мг cross-validated (ECU/road/air), refined значення не перевірено незалежно цією сесією

### 3. InjCrv_phiBasGear56_MAP — eco-cruise SOI (9 байтів)
- **0x1DACF8–0x1DAEF7** (регіон), змінено 9 байтів у різних місцях:
  - 0x1DACF: `0e` → `2c`
  - 0x1DADD1: `80` → `9e`
  - 0x1DADD3: `ab` → `c9`
  - 0x1DADEB: `38` → `56`
  - 0x1DADED: `80` → `9e`
  - 0x1DADEF: `ab` → `c9`
  - 0x1DAE07: `64` → `82`
  - 0x1DAE09: `80` → `9e`
  - 0x1DAE0B: `b1` → `cf`
- **Карта:** `InjCrv_phiBasGear56_MAP` (SOI для 5-ї/6-ї передач)
- **З candidate-vnext.json:** 1750–2250 rpm при 15/20/25 мг (легке круїз-навантаження) просунуто +0.703° BTDC
- **Ризик:** нульовий на WOT (колонки 55–60 мг не чіпаються)

### 4. StSys_trqStrtBas_MAP — hot-start fix (8 байтів)
- **0x1F0762–0x1F0769**: `0000000000000000` → `04e2046004380438`
- **Карта:** `StSys_trqStrtBas_MAP` (момент під час запуску)
- **З candidate-vnext.json:** 250 rpm / 40–100°C cranking cells 0 → 108–125 Нм
- **Ризик:** нульовий на WOT (тільки idle-speed cranking)

## Детальний аналіз: full_power → refined (-2 байти контрольних сум)

Refined містить **тільки eco-cruise SOI fix (9 байтів) + hot-start fix (8 байтів)**, але **БЕЗ** smoke limiter change.

### Зміни (10 байтів карт):
1. **InjCrv_phiBasGear56_MAP** (9 байтів) — ті самі зміни, що й у refined_CS_OK
2. **StSys_trqStrtBas_MAP** (8 байтів) — ті самі зміни, що й у refined_CS_OK
3. **Контрольні суми оновлені** (але без зміни smoke limiter)

## Детальний аналіз: refined_CS_OK ↔ refined (8 байтів)

Єдина відмінність — **smoke limiter cell**:
- refined_CS_OK має зміну на 0x1D6603
- refined **не має** цієї зміни

## Порівняння з ideal

`ideal` відрізняється від усіх інших на 200+ байтів, що вказує на суттєво іншу базу калібрування. Детальний аналіз ideal потребує окремого дослідження.

## Висновки

### Ієрархія прошивок:
```
full_power (поточна в авто)
    │
    ├─→ refined (full_power + hot-start + eco-cruise)
    │
    └─→ refined_CS_OK (full_power + hot-start + eco-cruise + 1 smoke cell @2500rpm)
```

### Рекомендації з STAGE1-ENGINEERING-PLAN.md:

**Етап 0 (готовий зараз):**
- Hot-start fix (HS-250) — ✅ є в refined і refined_CS_OK
- Eco-cruise SOI advance — ✅ є в refined і refined_CS_OK
- Статус: нульовий ризик на WOT, перевірено раніше

**Smoke limiter change (refined_CS_OK):**
- ❌ **Виключено з vNext** — поточне значення 56.5 мг cross-validated цією сесією
- refined_CS_OK підняв до 58.5 мг без незалежної перевірки
- Згідно з DECISION §3: "не можна знизити без ризику втрати на 3-й передачі"

### Вибір для Етапу 0:

**Рекомендація:** використати `refined` як базу для vNext, а не refined_CS_OK:
- Містить hot-start + eco-cruise (перевірені правки)
- НЕ містить непідтверджену зміну smoke limiter
- Узгоджується з candidate-vnext.json (excluded_from_refined_CS_OK)

**Або:** створити vNext з `full_power` + вибіркове копіювання перевірених карт (як у candidate-vnext.json).
