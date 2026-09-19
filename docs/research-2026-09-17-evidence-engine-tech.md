# Розвідка: технології для evidence-driven AI-спеціаліста

**Дата:** 2026-09-17
**Задача:** знайти рішення, які роблять систему «толковим хлопом», а не моделлю, що вигадує, а потім каже «ви праві».
**Метод:** цільовий web research із перевіркою першоджерел. Кожне твердження нижче має посилання.

---

## 0. Головне: це дві різні хвороби, і лікуються вони по-різному

| | Галюцинація | Сикофантія |
|---|---|---|
| Що це | модель вигадує факт | модель здає правильну позицію під тиском |
| Вигляд | «boost limit BV39 = 2450 mbar» | «ой, помилився, ви праві» |
| Лікується | evidence pipeline, цитати | **не лікується промтом** |

Уся архітектура «великий RAG + reviewer», яку зазвичай пропонують, б'є **лише по першій**.

Дослідження 2026 року прямо каже про другу:
> «Lightweight mitigation via preemptive prompt hardening can substantially reduce sycophancy in some models, but **fails to fully eliminate belief instability**, highlighting the limitations of instruction-level defenses.»

І гірше:
> «models do not merely change answers but frequently **generate rationalized hallucinations, fabricating temporal evidence or spatial details to justify incorrect revisions**.»
> — [Spatiotemporal Sycophancy, arXiv 2604.17873](https://arxiv.org/html/2604.17873)

Тобто коли модель «погоджується, що помилилась», вона ще й **добудовує докази під нову відповідь**. Саме це ти й спостерігав.

**Висновок для архітектури:** сикофантію не можна виправити інструкцією в промті. Її можна виправити тільки тим, що позиція системи живе **поза моделлю** — у claim ledger з провенансом. Тоді «ви праві» перестає бути реченням і стає зміною рядка в БД, яка вимагає доказу. Модель не має права змінити статус claim без нового джерела.

Це підтверджує мій редлайн B2/B3 і піднімає його в пріоритеті: **claim ledger — не бухгалтерія, а основний механізм проти сикофантії.**

---

## 1. Найцінніша практична знахідка: Anthropic Citations API

Механізм, який робить підробку цитати **технічно неможливою**, а не забороненою промтом.

З офіційної документації ([platform.claude.com/docs/en/build-with-claude/citations](https://platform.claude.com/docs/en/build-with-claude/citations)):

> «Because the API parses citations into the response formats described in the following sections and **extracts `cited_text` directly, citations are guaranteed to contain valid pointers to the provided documents**.»

Тобто `cited_text` **не генерується моделлю** — він витягується з документа, який ти передав. Модель фізично не може процитувати те, чого в документі немає.

### Три типи документів і що з них виходить

| Тип | Чанкінг | Формат цитати |
|---|---|---|
| Plain text | по реченнях | символьні індекси (0-indexed) |
| PDF | по реченнях | номери сторінок (1-indexed) |
| **Custom content** | **немає додаткового чанкінгу** | **індекси блоків (0-indexed)** |

**Custom content — це те, що нам треба.** Ми віддаємо власні чанки з БД як блоки → цитата повертається як індекс блоку → мапиться один-в-один на `chunks.id`. Перевірка цілісності цитат стає тривіальним `JOIN`, а не текстовим пошуком.

### Економіка
> «The `cited_text` field is provided for convenience and **does not count toward output tokens**. When passed back in subsequent conversation turns, `cited_text` is also **not counted toward input tokens**.»

Тобто цитати практично безкоштовні на виході. Зростає лише вхід (системний промт + чанкінг).

### Обмеження, яке треба закласти в дизайн
> «Citations **cannot be used together with structured outputs**. If you enable citations on any user-provided document and also include the `output_config.format` parameter, the API returns a 400 error.»

Наслідок: не можна одночасно вимагати суворий JSON-схемний вихід і цитати. Тому конвеєр ділиться на два кроки: **(1)** відповідь із цитатами → **(2)** окремий структурований виклик, що перетворює її на рядки claims. Це не проблема, але це архітектурне рішення, а не деталь.

Працює з prompt caching (кешуються самі документи) і з Batches — тобто масову екстракцію claims із корпусу можна ганяти пакетно.

---

## 2. Числа, які мають змінити дизайн research-агента

Свіже дослідження цитувань у deep research агентах ([Cited but Not Verified, arXiv 2605.06635](https://arxiv.org/html/2605.06635v1)):

| Метрика | Результат |
|---|---|
| Посилання робочі | **> 94%** |
| Тематично релевантні | **> 80%** |
| **Факт справді підтверджений джерелом** | **24–77%** |

Тобто цитати виглядають бездоганно, а перевірку фактів провалює від чверті до трьох чвертей.

І головне:
> «Fact Check accuracy drops approximately **42% on average as search depth scales from 2 to 150 tool calls**, while surface metrics remain stable.»

**Чим глибше агент шукає, тим гірше обґрунтування — а зовнішні метрики цього не показують.**

Це прямий аргумент проти «Research Agent на 11 кроків, що сам ходить в інтернет, поки не знайде». Правильно — **обмежений research із обов'язковим інгестом і верифікацією кожного результату**, а не глибокий автономний пошук.

Те саме з іншого боку: у юридичних AI-інструментах, побудованих на RAG і рекламованих як «grounded», заміряна частота галюцинацій — **17–33%** ([SSRN 6945200](https://papers.ssrn.com/sol3/Delivery.cfm/6945200.pdf?abstractid=6945200&mirid=1&type=2)), а частота галюцинованих цитувань по комерційних моделях — **11–57%**.

> «A plain hallucination is bad, but **a hallucination with a citation is worse**, because users lower their guard when they see a source.»

Це буквально те, що вже сталось у нашому репо: claim, підписаний VW SSP 304, який ніхто не завантажував.

---

## 3. Що з пропозиції іншого AI підтвердилось

Чесно: **числа по Contextual Retrieval правильні.** Перевірив у першоджерела ([Anthropic Engineering](https://www.anthropic.com/engineering/contextual-retrieval)):

- Contextual Embeddings: −35% помилок пошуку (5.7% → 3.7%)
- + Contextual BM25: −49% (5.7% → 2.9%)
- + reranking: **−67%** (5.7% → 1.9%)

Три техніки взаємодоповнювальні. Тому гібридний пошук і contextual chunking із тієї пропозиції — обґрунтовані, і я їх беру.

---

## 4. Формалізація «UNKNOWN»: evidence sufficiency та abstention

Виявляється, це окрема дослідницька область, і в неї є готова термінологія, яка лягає на наш §12 і §21.

Стан доказів для питання — один із трьох:
- **Answer** — доказів достатньо і вони узгоджені
- **Refuse** — доказів недостатньо
- **Conflict** — докази суперечать одне одному

А верифікація твердження — **SUPPORTED / REFUTED / INSUFFICIENT**, де INSUFFICIENT покриває «missing hops, partial evidence, topical-but-relation-missing passages, unresolved internal conflict».

Джерела: [Evidence Sufficiency Benchmark](https://www.sciencedirect.com/org/science/article/pii/S1546221826007526), [SURE-RAG arXiv 2605.03534](https://arxiv.org/pdf/2605.03534), [GRACE arXiv 2601.04525](https://arxiv.org/pdf/2601.04525).

Важливе застереження звідти ж:
> «Abstention thresholds in production should incorporate the LLM's own evidence-sensitivity profile rather than **rely solely on retrieval confidence**.»

І:
> «**No model can reliably resist a well-formed misleading passage.**» — [arXiv 2608.22228](https://arxiv.org/html/2608.22228)

Останнє — це аргумент за Tier-політику джерел: якщо переконливий форумний пост потрапив у контекст нарівні з Bosch, модель на нього купиться. Захист не в тому, щоб модель була розумніша, а в тому, **щоб такий пост не потрапляв у evidence pack із тим самим статусом**.

---

## 5. Інструменти: що реально зараз варте

### PDF-парсинг
Бенчмарки 2026 ([OmniDocBench CVPR2025](https://openaccess.thecvf.com/content/CVPR2025/papers/Ouyang_OmniDocBench_Benchmarking_Diverse_PDF_Document_Parsing_with_Comprehensive_Annotations_CVPR_2025_paper.pdf), [порівняння парсерів](https://themenonlab.blog/blog/best-open-source-pdf-to-markdown-tools-2026)):

| Інструмент | Сильна сторона | Швидкість без GPU |
|---|---|---|
| **MinerU** | лідер точності, найкраще формули → LaTeX | 3.3 с/стор (x86) |
| **Docling** | універсальність, будь-який тип документа | **3.1 с/стор (x86)** — лідер на CPU |
| Marker | швидкий markdown | — |
| GROBID | тільки наукові статті, але значно швидший за Docling | — |

**Для нас важливо:** у нас **немає GPU**. Docling лідирує саме на CPU — це вирішує вибір. MinerU виграє на формулах, але формули Heywood нам менш критичні за текст про сажоутворення.

### Вектори в SQLite
`sqlite-vec` — стабільний реліз v0.1.0, чистий C без залежностей, працює всюди, де SQLite. Але: **«pre-v1, expect breaking changes»** ([GitHub](https://github.com/asg017/sqlite-vec), [анонс](https://alexgarcia.xyz/blog/2024/sqlite-vec-stable-release/index.html)).

Для нашого масштабу (~6 600 чанків) це прийнятний ризик — але і без нього numpy brute-force дає ~7 мс на запит.

### Ембединги (локальні)
[BentoML огляд](https://www.bentoml.com/blog/a-guide-to-open-source-embedding-models), [PremAI ranking](https://www.premai.io/blog/best-embedding-models-for-rag-2026-ranked-by-mteb-score-cost-and-self-hosting/):

- **Qwen3-Embedding-8B** — лідер multilingual MTEB, 100+ мов
- **BGE-M3** (568M) — найуніверсальніший: dense + sparse + multi-vector з однієї моделі, квантується під CPU
- **BGE-Multilingual-Gemma2** — 74.1, «far ahead of BGE-M3 (Dense)»
- **EmbeddingGemma-300M** — легкий, під on-device

Для нас: **BGE-M3**, бо він один дає і dense, і sparse — тобто гібридний пошук з однієї моделі, і працює на CPU після квантизації. Qwen3-8B точніший, але 8B на CPU — це не наш сценарій.

### MCP
Специфікація **2026-07-28** — найбільша ревізія з моменту запуску: stateless core (прибрано `Mcp-Session-Id`), Extensions, Tasks, MCP Apps, посилена авторизація ([блог MCP](https://blog.modelcontextprotocol.io/posts/2026-07-28/)).

У грудні 2025 Anthropic передала MCP у **Agentic AI Foundation під Linux Foundation** (співзасновники Anthropic, Block, OpenAI; платинові члени AWS, Google, Microsoft, Cloudflare, Bloomberg). Adoption: **41–45% респондентів мають MCP у продакшені**, головний блокер — безпека ([Wikipedia](https://en.wikipedia.org/wiki/Model_Context_Protocol), [adoption stats](https://www.digitalapplied.com/blog/mcp-adoption-statistics-2026-model-context-protocol)).

Є навіть окремий security-гайд від NSA/DoD ([CSI_MCP_SECURITY.PDF](https://media.defense.gov/2026/Jun/02/2003943289/-1/-1/0/CSI_MCP_SECURITY.PDF)) — варто прочитати перед тим, як відкривати KB-сервер назовні.

Тобто ставка на MCP як на довгограючий інтерфейс **виправдана**. Але це інтерфейс, а не фундамент.

---

## 6. Що з цього змінює план

| Знахідка | Що робимо |
|---|---|
| Сикофантія не лікується промтом | claim ledger стає **головним** механізмом, не допоміжним. Статус claim змінюється лише через нове джерело |
| Citations API повертає перевірені спани | **основа збору claims.** Custom content blocks → `chunks.id`. Промт більше не просить модель «навести цитату» |
| Citations ≠ structured outputs | конвеєр у два кроки: відповідь із цитатами → окремий структурований виклик для запису в БД |
| Fact-check падає на 42% з глибиною пошуку | research обмежений і з обов'язковим інгестом; ніяких «шукай, поки не знайдеш» |
| Contextual retrieval −67% | беремо: contextual prefix + BM25 + dense + reranker |
| Answer / Refuse / Conflict | формалізуємо як стан evidence pack перед відповіддю |
| «No model resists a well-formed misleading passage» | Tier-політика працює **на вході в evidence pack**, а не в промті |
| Docling лідирує на CPU | Docling як парсер (GPU в нас немає) |
| BGE-M3 = dense + sparse одна модель | вона, коли дійдемо до векторів |
| MCP 2026-07-28 stateless, під Linux Foundation | ціль, але після робочого CLI |

---

## 7. Чого дослідження **не** знайшло

Чесно, щоб не створювати ілюзію повноти:

- **Жодної готової системи для ECU calibration / автомобільної інженерії.** Усе знайдене — загальні RAG/attribution підходи. Доменний шар (A2L, торк-структура, PD) доведеться будувати самим, готового немає.
- **Немає рішення, яке гарантує відсутність сикофантії.** Найкраще, що є — зовнішній стан із провенансом. Це пом'якшення, не гарантія.
- **Немає бенчмарку для нашого типу задач.** Свій regression suite доведеться писати самим — але тепер зрозуміло, як: у термінах SUPPORTED / REFUTED / INSUFFICIENT.
