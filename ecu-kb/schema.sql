-- ECU Knowledge Base — схема з епістемічною моделлю
-- Два ортогональні виміри: ЧИМ є доказ (evidence_kind) і НАСКІЛЬКИ він перевірений (verification_state)

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ── ДЖЕРЕЛА ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sources (
    id              INTEGER PRIMARY KEY,
    title           TEXT NOT NULL,
    authors         TEXT,
    publisher       TEXT,
    year            INTEGER,
    -- ЗВІДКИ воно в нас. Головне поле: не даємо змішувати бажане з наявним.
    obtainability   TEXT NOT NULL CHECK (obtainability IN (
                        'HAVE_LOCAL',       -- файл є, інгестовано → можна цитувати
                        'HAVE_PUBLIC_URL',  -- легально доступне, ще не завантажене
                        'WANT_USER_COPY',   -- лише бібліографічний запис, цитувати НЕ МОЖНА
                        'PROJECT_DRAFT')),  -- наші власні робочі нотатки
    tier            TEXT CHECK (tier IN ('A','B','C','D','DRAFT')),
    authority       INTEGER CHECK (authority   BETWEEN 1 AND 5),
    applicability   INTEGER CHECK (applicability BETWEEN 1 AND 5),
    url             TEXT,
    license_note    TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

-- ── ДОКУМЕНТИ ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS documents (
    id              INTEGER PRIMARY KEY,
    source_id       INTEGER NOT NULL REFERENCES sources(id),
    rel_path        TEXT NOT NULL UNIQUE,
    sha256          TEXT NOT NULL UNIQUE,
    bytes           INTEGER,
    pages           INTEGER,
    -- ВИМІРЯНО парсером, не взято зі звіту
    text_layer      TEXT CHECK (text_layer IN ('GOOD','THIN','NONE')),
    chars_per_page  INTEGER,
    ingested_at     TEXT DEFAULT (datetime('now'))
);

-- ── ЧАНКИ ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS chunks (
    id              INTEGER PRIMARY KEY,
    document_id     INTEGER NOT NULL REFERENCES documents(id),
    ordinal         INTEGER NOT NULL,
    page_from       INTEGER,
    page_to         INTEGER,
    section         TEXT,
    context_prefix  TEXT,          -- contextual retrieval: чим є цей уривок
    content         TEXT NOT NULL,
    n_chars         INTEGER,
    UNIQUE (document_id, ordinal)
);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    content, context_prefix, section,
    content='chunks', content_rowid='id', tokenize='unicode61'
);
CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, content, context_prefix, section)
    VALUES (new.id, new.content, new.context_prefix, new.section);
END;
CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, content, context_prefix, section)
    VALUES ('delete', old.id, old.content, old.context_prefix, old.section);
END;

-- ── ТОЧНІ ІДЕНТИФІКАТОРИ (A2L-символи, адреси, парт-номери) ────────────────
-- Окремо від FTS: тут потрібен рівно точний збіг, не ранжування.
CREATE TABLE IF NOT EXISTS identifiers (
    id          INTEGER PRIMARY KEY,
    token       TEXT NOT NULL,
    kind        TEXT,                    -- a2l_symbol | address | part_number | dtc
    chunk_id    INTEGER REFERENCES chunks(id),
    UNIQUE (token, chunk_id)
);
CREATE INDEX IF NOT EXISTS idx_ident_token ON identifiers(token);

-- ── ТВЕРДЖЕННЯ ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS claims (
    id                 INTEGER PRIMARY KEY,
    statement          TEXT NOT NULL,
    -- ЧИМ є доказ
    evidence_kind      TEXT NOT NULL CHECK (evidence_kind IN (
                          'OEM_DOCUMENTED','STANDARD','TEXTBOOK','MEASURED','MAP_FACT',
                          'CALCULATED','INFERRED','HYPOTHESIS','COMMUNITY_CLAIM',
                          'MODEL_RECALL','UNKNOWN')),
    -- НАСКІЛЬКИ перевірений (життєвий цикл, ортогонально до типу)
    verification_state TEXT NOT NULL DEFAULT 'raw' CHECK (verification_state IN (
                          'raw','corroborated','project_matched','experiment_supported',
                          'verified','contradicted','deprecated','superseded')),
    -- Що це за величина — §1 вимагає розрізняти, тож даємо поля
    quantity_kind      TEXT CHECK (quantity_kind IN (
                          'physical','ecu_internal','calibration','diagnostic','modeled_proxy')),
    unit               TEXT,
    frame              TEXT CHECK (frame IN ('raw','physical')),
    is_modeled         INTEGER DEFAULT 0,
    -- Область дії: не переносимо знання між ECU/SW автоматично
    ecu_family         TEXT,
    ecu_variant        TEXT,
    sw_number          TEXT,
    engine_code        TEXT,
    turbo_model        TEXT,
    confidence         REAL CHECK (confidence BETWEEN 0 AND 1),
    missing_evidence   TEXT,             -- що саме підняло б статус
    -- Ретракції — first-class, бо вони тут реальність
    supersedes_id      INTEGER REFERENCES claims(id),
    retracted_at       TEXT,
    retraction_reason  TEXT,
    created_at         TEXT DEFAULT (datetime('now')),
    updated_at         TEXT DEFAULT (datetime('now'))
);

CREATE VIRTUAL TABLE IF NOT EXISTS claims_fts USING fts5(
    statement, content='claims', content_rowid='id', tokenize='unicode61');
CREATE TRIGGER IF NOT EXISTS claims_ai AFTER INSERT ON claims BEGIN
    INSERT INTO claims_fts(rowid, statement) VALUES (new.id, new.statement);
END;

-- ── ЦИТАТИ: тут живе чесність ──────────────────────────────────────────────
-- Цитата мусить ДОСЛІВНО існувати в інгестованому чанку. Перевіряє `kb check`.
CREATE TABLE IF NOT EXISTS citations (
    id           INTEGER PRIMARY KEY,
    claim_id     INTEGER NOT NULL REFERENCES claims(id),
    chunk_id     INTEGER NOT NULL REFERENCES chunks(id),
    doc_sha256   TEXT NOT NULL,
    locator      TEXT NOT NULL,        -- стор. / розділ
    quote        TEXT NOT NULL,        -- дослівний текст із чанка
    verified_at  TEXT
);

-- ── КОНФЛІКТИ ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS conflicts (
    id            INTEGER PRIMARY KEY,
    topic         TEXT NOT NULL,
    claim_a_id    INTEGER REFERENCES claims(id),
    claim_b_id    INTEGER REFERENCES claims(id),
    explanation   TEXT,                -- різні ECU gen / SW / turbo PN / одиниці?
    resolved_by   TEXT,
    created_at    TEXT DEFAULT (datetime('now'))
);

-- ── ПРОГАЛИНИ ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS gaps (
    id            INTEGER PRIMARY KEY,
    question      TEXT NOT NULL,
    why_needed    TEXT,
    priority      INTEGER DEFAULT 3,
    status        TEXT DEFAULT 'OPEN' CHECK (status IN
                     ('OPEN','RESEARCHING','PARTIAL','RESOLVED','BLOCKED')),
    needed_source TEXT,
    created_at    TEXT DEFAULT (datetime('now'))
);

-- ── A2L: калібрувальні об'єкти самої прошивки ──────────────────────────────
-- Це НЕ література. Це первинна істина про конкретний SW: applicability 5.
CREATE TABLE IF NOT EXISTS a2l_objects (
    id            INTEGER PRIMARY KEY,
    sw_number     TEXT NOT NULL,
    name          TEXT NOT NULL,
    description   TEXT,
    obj_type      TEXT,              -- MAP | CURVE | VALUE | ASCII …
    address       TEXT,
    record_layout TEXT,
    func_group    TEXT,              -- префікс Bosch: PCR, InjCrv, AirCtl…
    UNIQUE (sw_number, name)
);
CREATE INDEX IF NOT EXISTS idx_a2l_name  ON a2l_objects(name);
CREATE INDEX IF NOT EXISTS idx_a2l_group ON a2l_objects(func_group);
CREATE INDEX IF NOT EXISTS idx_a2l_addr  ON a2l_objects(address);

CREATE VIRTUAL TABLE IF NOT EXISTS a2l_fts USING fts5(
    name, description, func_group,
    content='a2l_objects', content_rowid='id', tokenize='unicode61');
CREATE TRIGGER IF NOT EXISTS a2l_ai AFTER INSERT ON a2l_objects BEGIN
    INSERT INTO a2l_fts(rowid,name,description,func_group)
    VALUES (new.id,new.name,new.description,new.func_group);
END;
