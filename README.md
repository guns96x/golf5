# Golf 5 EDC16U34 — Autonomous ECU Calibration & Knowledge System

Інженерний комплекс дослідження, калібрування та верифікації системи керування
**VW Golf 5 1.9 TDI BLS / Bosch EDC16U34-3.42 / SW 1037391847**.

Головний принцип: технічна відповідь має походити з доказового шару
(A2L / claims / вимірювання / джерела), а не з пам'яті моделі або старого
чат-транскрипту.

## Швидкий старт для ChatGPT та зовнішніх LLM

1. Спочатку прочитати `ecu-kb/remote/manifest.json`, якщо він уже опублікований.
2. Потім прочитати `docs/CHATGPT-KB-BRIDGE.md`.
3. Для актуальних фактів використовувати:
   - `ecu-kb/remote/claims.json`
   - `ecu-kb/remote/gaps.json`
   - `ecu-kb/remote/conflicts.json`
   - `ecu-kb/remote/a2l/<FUNC_GROUP>.json`
4. `CURRENT_STATE.md` використовувати як оперативний narrative/handoff, а не як
   заміну поточного стану SQLite.
5. Правила агентів: `CLAUDE.md`, `AGENTS.md`, `PROMPT_FOR_CHATGPT.md`.

Якщо remote snapshot ще не опублікований, зовнішня модель може читати
`ecu-kb/claims/*.json` і профільні документи, але повинна явно зазначити, що
не бачить canonical DB state (ретракції, поточні gaps, review metadata).

## Джерела істини

Пріоритет для технічного висновку:

1. локальна `ecu-kb/knowledge/kb.sqlite3` — canonical mutable state;
2. її read-only GitHub snapshot у `ecu-kb/remote/`;
3. A2L конкретного SW та детерміновано декодовані BIN/log-derived артефакти;
4. перевірені першоджерела / claims;
5. похідні Markdown-звіти;
6. старі чати та чернетки — лише як гіпотези.

## Структура репозиторію

- `ecu-kb/` — доказова база знань:
  - `kb.py` — ingest, search, A2L, claims, integrity check, gaps, flash-preflight;
  - `specialist.py` — evidence-driven specialist; читає SQLite або remote snapshot;
  - `remote_bridge.py` — експорт canonical DB у read-only GitHub snapshot;
  - `claims/` — versioned claim inputs/history;
  - `knowledge/kb.sqlite3` — локальна canonical DB, у Git не комітиться.
- `ecu-kb/remote/` — згенерований зовнішній specialist view:
  `manifest.json`, current claims/gaps/conflicts, `corpus.json`, A2L по функціональних групах.
- `ecu-kb/corpus/seeds.json` + `tools/ecu_corpus_harvester.py` — metadata-first каталог DAMOS/A2L/OLS/XDF/ORI/SGO з EXACT/SIBLING/ANALOG класифікацією.
- `docs/` — інженерні зрізи та ревю:
  - `CONTROL-PATH-STOCK-boost.md`
  - `CONTROL-PATH-STOCK-fuel.md`
  - `FIRMWARE-REVIEW-current.md`
  - `FIRMWARE-MODIFICATION-RELIABILITY.md`
  - `CHATGPT-KB-BRIDGE.md`
- `diagnostic-review/` — A2L, BIN/HEX, декодовані карти, статичний аналіз.
- `base-knowledge/library/` — tracked source library та registry. Наявність файла
  в Git не робить його автоматично доказом: applicability/authority/ingest state
  визначає KB.
- `base-knowledge/drafts/` — проєктні чернетки; не зовнішні докази.
- `tools/`, `scripts/`, `skills/` — калькулятори, automation та project skills.

## Основні команди

```bat
cd ecu-kb

python kb.py status
python kb.py check
python kb.py claims
python kb.py gaps
python kb.py search "PCR_rBPCtlBas_MAP"
python kb.py a2l PCR
python kb.py consult "як працює feed-forward VNT?"
```

Публікація актуального specialist snapshot для ChatGPT:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Publish-KBRemoteSnapshot.ps1
```

Або вручну:

```bat
python ecu-kb\kb.py check
python ecu-kb\remote_bridge.py export
python ecu-kb\remote_bridge.py check
```

Remote snapshot — лише export. Нові факти, ретракції та зміни gaps спочатку
вносяться в локальний KB workflow, а вже потім публікуються.


## ECU corpus

```bat
python tools\ecu_corpus_harvester.py seed
python tools\ecu_corpus_harvester.py report
python tools\ecu_corpus_harvester.py scan D:\ECU-Corpus
```

Деталі: `docs/ECU-CORPUS-HARVESTER.md`.
