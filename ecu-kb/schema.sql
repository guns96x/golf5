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
    -- ЯК саме підтверджено — ортогонально і до evidence_kind, і до
    -- verification_state. citations (документна цитата) — єдиний тип, який
    -- перевіряє kb check дослівним збігом. bin_derived/log_derived/computed
    -- підтверджуються провенансом у самому statement (шлях, sha256) — це
    -- працювало ad hoc для claims/boost-path-values.json і claims/
    -- n75-duty-direction.json ще до того, як для цього з'явилось поле.
    source_class       TEXT CHECK (source_class IN (
                          'document_citation','bin_derived','log_derived',
                          'computed','human_attested')),
    -- Хто написав і хто перевірив — навмисно РІЗНІ люди/сесії, якщо можливо.
    -- Поки не має власного workflow: kb load-claims завжди ставить created_by,
    -- reviewed_by лишається NULL, доки хтось не підтвердить окремо. Самоперевірка
    -- (створив і перевірив — та сама сесія) не забороняється схемою, але видна:
    -- WHERE created_by = reviewed_by.
    created_by         TEXT,
    reviewed_by         TEXT,
    reviewed_at         TEXT,
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
    obj_type      TEXT,              -- MAP | CURVE | VALUE | ASCII | SWORD …
    kind          TEXT,              -- CHARACTERISTIC | MEASUREMENT | AXIS_PTS
    address       TEXT,
    record_layout TEXT,
    func_group    TEXT,              -- префікс Bosch: PCR, InjCrv, AirCtl…
    a2l_sha256    TEXT,              -- з якого саме файла взято
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

-- ── FLASH-PREFLIGHT: docs/FIRMWARE-MODIFICATION-RELIABILITY.md § 9 ──────────
-- Умови з розділу 2 того документа, зроблені машинно-перевірюваними: правило
-- не залежить від того, чи його хтось прочитав, так само як kb check не
-- залежить від сумління моделі. Те, що софт справді може перевірити сам
-- (хеші файлів, варіативність каналів у логах) — перевіряється автоматично.
-- Те, чого софт знати не може (чи підключений зарядний, чи справді пройдено
-- відновлення на живому блоці) — фіксується як людське засвідчення
-- (preflight_checks), і `flash-preflight` лише вимагає його НАЯВНОСТІ.

CREATE TABLE IF NOT EXISTS firmware_versions (
    id                  INTEGER PRIMARY KEY,
    label               TEXT,
    path                TEXT,
    sha256              TEXT NOT NULL,
    -- own_readback   знято з ЦІЄЇ машини;
    -- reconstructed  зібрано з hex/аналізу, не знято з ECU (як reference-from-hex);
    -- vendor_release заводський реліз без прив'язки до конкретного блоку;
    -- modified       наша власна змінена версія
    source              TEXT NOT NULL CHECK (source IN
                          ('own_readback','reconstructed','vendor_release','modified')),
    read_count          INTEGER NOT NULL DEFAULT 1,
    verified_twin_sha256 TEXT,     -- sha256 другого незалежного зчитування, якщо було
    notes               TEXT,
    created_at          TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS flash_events (
    id                   INTEGER PRIMARY KEY,
    target_path          TEXT,
    target_sha256        TEXT,
    baseline_firmware_id INTEGER REFERENCES firmware_versions(id),
    preflight_result      TEXT CHECK (preflight_result IN ('passed','blocked')),
    blocked_reasons       TEXT,        -- JSON-масив кодів
    written_at            TEXT,
    readback_after_sha256 TEXT,
    verified_byte_match   INTEGER CHECK (verified_byte_match IN (0,1)),
    notes                 TEXT,
    created_at             TEXT DEFAULT (datetime('now'))
);

-- Append-only: журнал спроб прошивки не можна ані виправити заднім числом,
-- ані видалити. written_at/readback_after_sha256/verified_byte_match у поточній
-- версії заповнюються при INSERT (або лишаються NULL) — команди дописати їх
-- ПІСЛЯ фізичного запису ще немає (окрема прогалина), але сам журнал уже
-- захищений від тихого редагування.
CREATE TRIGGER IF NOT EXISTS flash_events_no_update
BEFORE UPDATE ON flash_events BEGIN
    SELECT RAISE(ABORT, 'flash_events immutable: append a new row, do not edit');
END;
CREATE TRIGGER IF NOT EXISTS flash_events_no_delete
BEFORE DELETE ON flash_events BEGIN
    SELECT RAISE(ABORT, 'flash_events immutable: append a new row, do not delete');
END;

CREATE TABLE IF NOT EXISTS preflight_checks (
    id            INTEGER PRIMARY KEY,
    condition     TEXT NOT NULL,      -- recovery_tested | power_confirmed | log_baseline_captured …
    -- standing   одноразовий факт, лишається істинним (напр. "відновлення перевірене хоч раз");
    -- per_event  дійсний лише коротко навколо моменту засвідчення (напр. живлення ПЕРЕД записом)
    scope         TEXT NOT NULL DEFAULT 'standing' CHECK (scope IN ('standing','per_event')),
    confirmed     INTEGER NOT NULL DEFAULT 1 CHECK (confirmed IN (0,1)),
    confirmed_by  TEXT NOT NULL,      -- хто засвідчує — людина, не модель
    note          TEXT,
    flash_event_id INTEGER REFERENCES flash_events(id),
    created_at    TEXT DEFAULT (datetime('now'))
);


-- ── ECU CORPUS HARVESTER ───────────────────────────────────────────────────
-- Registry of external ECU artefacts. Metadata may be public while the actual
-- file remains unavailable/paid/user-supplied. Registry presence is NOT evidence
-- that a binary/DAMOS is correct; it only makes provenance and applicability
-- machine-readable.

CREATE TABLE IF NOT EXISTS corpus_sources (
    id              INTEGER PRIMARY KEY,
    source_key      TEXT NOT NULL UNIQUE,
    title           TEXT NOT NULL,
    source_type     TEXT NOT NULL CHECK (source_type IN (
                        'oem_catalog','public_repo','vendor_catalog','forum',
                        'community_archive','manual_entry')),
    url             TEXT,
    access_mode     TEXT NOT NULL CHECK (access_mode IN (
                        'metadata_only','public_download','authenticated',
                        'paid','user_supplied')),
    trust_tier      TEXT NOT NULL CHECK (trust_tier IN ('A','B','C','D')),
    license_note    TEXT,
    notes           TEXT,
    discovered_at   TEXT DEFAULT (datetime('now')),
    last_checked_at TEXT
);

CREATE TABLE IF NOT EXISTS corpus_artifacts (
    id                  INTEGER PRIMARY KEY,
    source_id           INTEGER NOT NULL REFERENCES corpus_sources(id),
    artifact_type       TEXT NOT NULL CHECK (artifact_type IN (
                            'A2L','DAMOS','OLS','XDF','MAPPACK','MAPPACK_SIGNATURES',
                            'BIN_ORI','BIN_MODIFIED','FULL_DUMP','EEPROM',
                            'SGO','FRF','OTHER')),
    name                TEXT NOT NULL,
    source_url          TEXT,
    ecu_family          TEXT,
    ecu_variant         TEXT,
    vag_part_number     TEXT,
    vag_hw_number       TEXT,
    vag_sw_version      TEXT,
    bosch_sw_number     TEXT,
    calibration_id      TEXT,
    project_code        TEXT,
    engine_code         TEXT,
    vehicle             TEXT,
    power_kw            REAL,
    file_size           INTEGER,
    sha256              TEXT,
    local_rel_path      TEXT,
    access_state        TEXT NOT NULL DEFAULT 'METADATA_ONLY' CHECK (access_state IN (
                            'METADATA_ONLY','AVAILABLE_LOCAL','VERIFIED_LOCAL',
                            'REJECTED','UNAVAILABLE')),
    identity_state      TEXT NOT NULL DEFAULT 'UNVERIFIED' CHECK (identity_state IN (
                            'UNVERIFIED','HEADER_MATCHED','HASH_MATCHED','PROJECT_VERIFIED',
                            'REJECTED')),
    license_note        TEXT,
    notes               TEXT,
    first_seen_at       TEXT DEFAULT (datetime('now')),
    verified_at         TEXT,
    UNIQUE (source_id, name, source_url)
);
CREATE INDEX IF NOT EXISTS idx_corpus_artifact_family ON corpus_artifacts(ecu_family);
CREATE INDEX IF NOT EXISTS idx_corpus_artifact_part ON corpus_artifacts(vag_part_number);
CREATE INDEX IF NOT EXISTS idx_corpus_artifact_bosch_sw ON corpus_artifacts(bosch_sw_number);
CREATE INDEX IF NOT EXISTS idx_corpus_artifact_cal ON corpus_artifacts(calibration_id);
CREATE INDEX IF NOT EXISTS idx_corpus_artifact_hash ON corpus_artifacts(sha256);

CREATE TABLE IF NOT EXISTS corpus_matches (
    artifact_id      INTEGER PRIMARY KEY REFERENCES corpus_artifacts(id) ON DELETE CASCADE,
    target_profile   TEXT NOT NULL,
    match_class      TEXT NOT NULL CHECK (match_class IN (
                        'EXACT','SAME_HW_SIBLING','SAME_PROJECT_FAMILY',
                        'STRUCTURAL_ANALOG','UNKNOWN','REJECT')),
    score            INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
    reasons_json     TEXT NOT NULL,
    computed_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS corpus_observations (
    id               INTEGER PRIMARY KEY,
    artifact_id      INTEGER NOT NULL REFERENCES corpus_artifacts(id) ON DELETE CASCADE,
    observation_kind TEXT NOT NULL CHECK (observation_kind IN (
                        'filename','ascii_id','file_size','sha256','manual_review',
                        'source_metadata','parser_result')),
    value            TEXT NOT NULL,
    source           TEXT,
    observed_at      TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_corpus_obs_artifact ON corpus_observations(artifact_id);
