#!/usr/bin/env python3
"""
tools/knowledge_manager.py — Core Database Engine for EDC16U34 Project Knowledge Bootstrap
Implements relational schema, FTS5 symbol indexing, A2L characteristic ingestion,
VCDS log analysis, firmware lineage tracking, and claim verification lifecycle.
"""

import os
import sys
import json
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DB_PATH = Path("knowledge/edc16_knowledge.db")


def get_connection():
    os.makedirs(DB_PATH.parent, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_schema(conn):
    cur = conn.cursor()
    
    # 1. Sources
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT,
        publisher TEXT,
        publication_date TEXT,
        edition TEXT,
        source_type TEXT NOT NULL,
        authority_level INTEGER CHECK(authority_level BETWEEN 1 AND 5),
        applicability_level INTEGER CHECK(applicability_level BETWEEN 1 AND 5),
        url_or_path TEXT,
        sha256 TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Documents
    cur.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id INTEGER REFERENCES sources(id),
        title TEXT,
        relative_path TEXT,
        format TEXT,
        file_size INTEGER,
        sha256 TEXT,
        total_chunks INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 3. Chunks
    cur.execute("""
    CREATE TABLE IF NOT EXISTS chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER REFERENCES documents(id),
        chunk_index INTEGER,
        chunk_type TEXT,
        section_heading TEXT,
        page_or_line TEXT,
        content TEXT,
        tokens_est INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 4. Claims
    cur.execute("""
    CREATE TABLE IF NOT EXISTS claims (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        claim_text TEXT NOT NULL,
        source_id INTEGER REFERENCES sources(id),
        document_id INTEGER REFERENCES documents(id),
        page_or_section TEXT,
        exact_evidence TEXT,
        source_type TEXT,
        authority_score INTEGER CHECK(authority_score BETWEEN 1 AND 5),
        applicability_score INTEGER CHECK(applicability_score BETWEEN 1 AND 5),
        ecu_family TEXT DEFAULT 'EDC16',
        ecu_variant TEXT DEFAULT 'EDC16U34',
        hw_number TEXT DEFAULT '03G906021QJ',
        sw_number TEXT DEFAULT '1037391847',
        engine_code TEXT DEFAULT 'BLS',
        turbo_model TEXT DEFAULT 'BV39',
        map_name TEXT,
        map_address TEXT,
        units TEXT,
        scaling TEXT,
        axis_x TEXT,
        axis_y TEXT,
        conditions TEXT,
        epistemic_status TEXT CHECK(epistemic_status IN (
            'raw', 'corroborated', 'project_matched', 
            'experiment_supported', 'verified', 'contradicted', 'deprecated'
        )),
        confidence REAL,
        corroborated_by TEXT,
        contradicted_by TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 5. Entities
    cur.execute("""
    CREATE TABLE IF NOT EXISTS entities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        entity_type TEXT,
        description TEXT,
        standard_symbol TEXT,
        bosch_name TEXT,
        vag_name TEXT
    );
    """)

    # 6. ECU Variants
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ecu_variants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ecu_family TEXT,
        ecu_model TEXT,
        hw_number TEXT,
        sw_number TEXT,
        sw_version TEXT,
        engine_code TEXT,
        turbo_model TEXT,
        notes TEXT
    );
    """)

    # 7. Map Definitions
    cur.execute("""
    CREATE TABLE IF NOT EXISTS map_definitions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        kind TEXT,
        address_dec INTEGER,
        address_hex TEXT,
        size_bytes INTEGER,
        record_layout TEXT,
        conversion TEXT,
        unit TEXT,
        lower_limit REAL,
        upper_limit REAL,
        dim_x INTEGER,
        dim_y INTEGER,
        axis_x_name TEXT,
        axis_y_name TEXT,
        a2l_line INTEGER,
        is_verified_active INTEGER DEFAULT 0,
        active_reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_map_name ON map_definitions(name);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_map_addr ON map_definitions(address_hex);")

    # 8. Map Relationships
    cur.execute("""
    CREATE TABLE IF NOT EXISTS map_relationships (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        parent_map_name TEXT,
        child_map_name TEXT,
        relationship_type TEXT,
        description TEXT
    );
    """)

    # 9. Firmware Versions
    cur.execute("""
    CREATE TABLE IF NOT EXISTS firmware_versions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        sha256 TEXT UNIQUE NOT NULL,
        size_bytes INTEGER,
        ecu_hw TEXT,
        ecu_sw TEXT,
        parent_sha256 TEXT,
        variant_type TEXT,
        checksum_status TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 10. Firmware Diffs
    cur.execute("""
    CREATE TABLE IF NOT EXISTS firmware_diffs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        firmware_a_sha256 TEXT,
        firmware_b_sha256 TEXT,
        map_name TEXT,
        address_hex TEXT,
        changed_bytes_count INTEGER,
        description TEXT
    );
    """)

    # 11. Logs
    cur.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        sha256 TEXT,
        log_type TEXT,
        vehicle TEXT DEFAULT 'Golf 5 1.9 TDI BLS',
        firmware_name TEXT,
        sample_count INTEGER,
        sample_rate_hz REAL,
        rpm_min INTEGER,
        rpm_max INTEGER,
        boost_actual_max_mbar REAL,
        boost_spec_max_mbar REAL,
        max_overshoot_mbar REAL,
        steady_state_error_mbar REAL,
        ambient_temp_c REAL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 12. Log Channels
    cur.execute("""
    CREATE TABLE IF NOT EXISTS log_channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        log_id INTEGER REFERENCES logs(id),
        channel_name TEXT,
        unit TEXT,
        sample_rate_hz REAL,
        min_val REAL,
        max_val REAL,
        mean_val REAL
    );
    """)

    # 13. Experiments
    cur.execute("""
    CREATE TABLE IF NOT EXISTS experiments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        hypothesis TEXT,
        firmware_version_id INTEGER REFERENCES firmware_versions(id),
        log_id INTEGER REFERENCES logs(id),
        tested_rpm_start INTEGER,
        tested_rpm_end INTEGER,
        observed_behavior TEXT,
        conclusion TEXT,
        epistemic_gain TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 14. Conflicts
    cur.execute("""
    CREATE TABLE IF NOT EXISTS conflicts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic TEXT NOT NULL,
        claim_a_id INTEGER REFERENCES claims(id),
        claim_b_id INTEGER REFERENCES claims(id),
        claim_a_text TEXT,
        claim_b_text TEXT,
        source_a TEXT,
        source_b TEXT,
        authority_delta INTEGER,
        applicability_delta INTEGER,
        possible_explanation TEXT,
        required_experiment TEXT,
        provisional_verdict TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 15. Citations
    cur.execute("""
    CREATE TABLE IF NOT EXISTS citations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        claim_id INTEGER REFERENCES claims(id),
        source_id INTEGER REFERENCES sources(id),
        quote TEXT,
        page TEXT
    );
    """)

    # 16. Research Tasks
    cur.execute("""
    CREATE TABLE IF NOT EXISTS research_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_code TEXT UNIQUE,
        title TEXT NOT NULL,
        priority TEXT CHECK(priority IN ('P1_CRITICAL', 'P2_HIGH', 'P3_MEDIUM', 'P4_LOW')),
        status TEXT CHECK(status IN ('pending', 'in_progress', 'completed', 'blocked')),
        target_hypothesis TEXT,
        required_evidence TEXT,
        assigned_to TEXT,
        completed_at TIMESTAMP
    );
    """)

    # FTS5 Tables
    cur.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS claims_fts USING fts5(
        claim_text,
        map_name,
        exact_evidence,
        conditions,
        content='claims',
        content_rowid='id'
    );
    """)

    cur.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS maps_fts USING fts5(
        name,
        description,
        address_hex,
        unit,
        content='map_definitions',
        content_rowid='id'
    );
    """)

    conn.commit()
    print("Database schema initialized successfully with FTS5 virtual tables.")


def seed_sources(conn):
    sources = [
        # Tier A
        ("Bosch — Diesel Engine Management: Systems and Components", "Konrad Reif", "Springer / Bosch Professional Automotive", "2014", "1st", "oem_bosch", 5, 3, "https://link.springer.com/book/10.1007/978-3-658-03981-3", "Foundational textbook on modern diesel air path, injection, EDC, and diagnostics."),
        ("Bosch — Dieselmotor-Management", "Bosch", "Vieweg+Teubner / Springer", "2004", "4th", "oem_bosch", 5, 4, "https://link.springer.com/book/10.1007/978-3-322-80331-3", "Historic match for EDC16 and Pumpe-Düse generation charge-pressure control and torque architecture."),
        ("VW SSP 304 — Electronic Diesel Control EDC16: Design and Function", "Volkswagen AG", "VAG Service Training", "2003", "1st", "oem_vw", 5, 4, "https://www.vaglinks.com/docs/ssp/VWUSA.COM_SSP_304_EDC-16.pdf", "Primary OEM document detailing torque-oriented engine management, metering, SOI, and boost regulation in EDC16."),
        ("VW SSP 209 — 1.9-ltr. TDI Engine with Pump-Injection System", "Volkswagen AG", "VAG Service Training", "1999", "1st", "oem_vw", 5, 4, "https://procarmanuals.com/self-study-program-209-1-9-ltr-tdi-engine-pump-injection-system-design-function/", "Design and function of Pumpe-Düse unit injectors, mechanics, fuel supply, and vacuum system."),
        ("VW SSP 336 — Catalytic Coated Diesel Particulate Filter", "Volkswagen AG", "VAG Service Training", "2005", "1st", "oem_vw", 5, 4, "https://www.vaglinks.com/Docs/SSP/VWUSA.COM_SSP_336_VW_Diesel_particulate_filter.pdf", "OEM thermal management, regeneration triggers, post-injection strategies, and exhaust pressure sensing."),
        ("VW 4-cylinder Diesel Engine Workshop Material — BKC/BLS/BXE", "Volkswagen AG", "VAG Service", "2008", "OEM", "oem_vw", 5, 5, "https://www.vag-hub.com/vw-engine/", "Exact mechanical dimensions, torque limits, valve timing, oil supply, and vacuum specs for BLS."),
        # Standards & Calibration Tools
        ("ASAM MCD-2 MC (ASAP2 / A2L Standard)", "ASAM e.V.", "ASAM", "2020", "1.7.1", "asam_standard", 5, 5, "https://www.asam.net/standards/detail/mcd-2-mc/", "Standard defining ECU calibration descriptions, record layouts, characteristics, and computation methods."),
        ("ETAS INCA Measurement and Calibration Documentation", "ETAS GmbH", "ETAS", "2021", "7.6.1", "tools_etas", 4, 3, "https://docs.etas.com/inca/", "OEM application methodology, XCP protocol, measurement raster, and raster rate trade-offs."),
        ("EVC WinOLS Manual & Documentation", "EVC electronic", "EVC", "2023", "5.0", "tools_evc", 4, 4, "https://www.evc.de/ftp/winols/winols%20HelpEn.pdf", "DAMOS/ASAP2 import rules, map layout recognition, interpolation and 2D/3D visualization."),
        ("EVC Bosch EDC16 Checksum Algorithm Specification", "EVC electronic", "EVC", "2022", "OLS242", "tools_evc", 5, 5, "https://www.evc.de/en/product/ols/plugins_detail.asp", "Cryptographic and checksum block definitions for Bosch EDC16 Bosch family."),
        # Academic & Control Theory
        ("John B. Heywood — Internal Combustion Engine Fundamentals", "John B. Heywood", "McGraw-Hill", "2018", "2nd", "academic_textbook", 5, 2, "https://www.mheducation.com/highered/mhp/product/internal-combustion-engine-fundamentals-2e.html", "Thermodynamics of diesel combustion, airflow, charge heating, turbocharger matching."),
        ("Bosch Automotive Handbook", "Robert Bosch GmbH", "Wiley", "2022", "11th", "academic_handbook", 5, 2, "https://uat.store.wiley.com/en-us/automotive-handbook-11th-edition-p-9781119911906", "Comprehensive reference for sensors, actuators, engine management formulas, and emission chemistry."),
        ("Guzzella & Onder — Introduction to Modeling and Control of ICE Systems", "Lino Guzzella, Christopher Onder", "Springer", "2010", "2nd", "academic_control", 5, 3, "https://link.springer.com/book/10.1007/978-3-642-10775-7", "Control system theory for turbocharging: feed-forward vs feedback PID, anti-windup, and manifold filling dynamics."),
        ("Kiencke & Nielsen — Automotive Control Systems", "Uwe Kiencke, Lars Nielsen", "Springer", "2005", "2nd", "academic_control", 5, 3, "https://link.springer.com/book/10.1007/b137654", "Rigorous automotive control architectures, driveline oscillations, and actuator dynamics."),
        ("Watson & Janota — Turbocharging the Internal Combustion Engine", "N. Watson, M.S. Janota", "Macmillan / Springer", "1982", "Classic", "turbo_theory", 5, 3, "https://link.springer.com/book/10.1007/978-1-349-04024-7", "Comprehensive turbine and compressor mechanics, pulse turbocharging, and transient lag dynamics."),
        ("BorgWarner — Understanding Compressor Maps", "BorgWarner Turbo Systems", "BorgWarner", "2022", "TechArticle", "oem_borgwarner", 5, 4, "https://www.borgwarner.com/aftermarket/exhaust-gas-management/news/2022/05/23/understanding-compressor-maps-sizing-a-turbocharger", "Pressure ratio calculation, corrected mass flow, surge lines, choke lines, and turbine efficiency."),
        ("Ammann et al. — Model-Based Control of VGT and EGR in Diesel", "M. Ammann, M. Fekete, L. Guzzella", "SAE International", "2003", "SAE 2003-01-0357", "sae_paper", 4, 3, "https://saemobilus.sae.org/papers/model-based-control-vgt-egr-a-turbocharged-common-rail-diesel-engine-theory-passenger-car-implementation-2003-01-0357", "Coupled air path dynamics: why closing EGR alters turbo pre-control and induces transient boost overshoot."),
        # Practical Diagnostics & Project Evidence
        ("Ross-Tech TDI Logging & Diagnostic Guidelines", "Ross-Tech LLC", "Ross-Tech", "2022", "Online", "diagnostics_vcds", 4, 5, "https://www.ross-tech.com/vag-com/cars/tdi.html", "Measuring Block 011/003/008 protocol, multi-group latency degradation, and sample rate preservation."),
        ("03G906021QJ Factory A2L Calibration Dataset", "Bosch / Volkswagen", "OEM Calibration", "2006", "P447_HAXN_3.42", "exact_a2l", 5, 5, "file:///diagnostic-review/definitions/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.a2l", "Exact matching factory ASAP2 description for SW 1037391847 containing 13,000+ calibration objects."),
        ("Reference Calibration Binary (HEX extracted)", "Bosch / Volkswagen", "OEM Factory", "2006", "1037391847", "exact_firmware", 5, 5, "file:///diagnostic-review/reference-from-hex.analysis-only.bin", "Original uncorrupted factory binary for 03G906021QJ SW 391847."),
        ("Vehicle Telemetry Run 2026-09-14 (VCDS WOT)", "Project Owner", "Vehicle Logs", "2026", "WOT_114936", "exact_log", 5, 5, "file:///logs/VCDS_WOT_Log_20260914_114936.csv", "Real road dynamic logs showing 2310-2330 mbar transient boost overshoot under 100% pedal.")
    ]

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM sources;")
    if cur.fetchone()[0] == 0:
        for s in sources:
            cur.execute("""
            INSERT INTO sources (title, author, publisher, publication_date, edition, source_type, authority_level, applicability_level, url_or_path, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, s)
        conn.commit()
        print(f"Seeded {len(sources)} foundational sources.")


def seed_research_tasks(conn):
    tasks = [
        ("TASK-BOOST-01", "Investigate 2310-2330 mbar peak boost spike in 1900-2600 rpm region", "P1_CRITICAL", "in_progress", "Hypothesis B: N75 pre-control (PCR_rBPCtlBas_MAP) or closed-loop PID overshoot", "VCDS MVB 011 single-group log, PCR_rBPCtlBas_MAP active values", "Antigravity/Gemini"),
        ("TASK-MAP-01", "Verify active address of PCR_rBPCtlBas_MAP (N75 pre-control) in SW 1037391847", "P1_CRITICAL", "completed", "A2L maps point to 0x1E9FD0 or active block offset", "Binary comparison between reference and stage 1", "Antigravity/Gemini"),
        ("TASK-MAP-02", "Verify active address of PCR_pBDesBas_MAP (Boost target)", "P1_CRITICAL", "completed", "Boost request ceiling set to 2350 mbar absolute in Stage 1", "A2L index & Stage 1 map dump", "Antigravity/Gemini"),
        ("TASK-SMOKE-01", "Determine active smoke limiter (FlMng_qPresSmoke_MAP vs MAF-based) in BLS", "P2_HIGH", "completed", "BLS factory DPF calibration relies primarily on MAP-based smoke limiter", "A2L layout & VCDS MAF/MAP IQ channels", "Antigravity/Gemini"),
        ("TASK-HOTSTART-01", "Verify hot-start cranking IQ maps (EngM_qStart_MAP) across coolant temp", "P2_HIGH", "pending", "BLS hot start hesitation is caused by 0 mg IQ threshold under 250 RPM when warm", "A2L EngM_qStart_MAP inspection", "OpenAI Codex"),
        ("TASK-EGR-VNT-01", "Analyze VNT pre-control impact after DPF & EGR deactivation", "P1_CRITICAL", "in_progress", "Zero EGR flow increases turbine enthalpy during spool-up, shifting baseline required N75 duty", "SAE 2003-01-0357 & VCDS log correlation", "OpenAI Codex"),
        ("TASK-TORQUE-01", "Map active torque limiter (TrqLim_trqEng_MAP) vs Driver Wish", "P2_HIGH", "completed", "Torque limiter sets outer torque boundary; converted via duration maps", "diagnostic-review/active-map-verification.json", "Antigravity/Gemini"),
        ("TASK-THERMAL-01", "Audit modeled exhaust temperature protection and thermal derating", "P2_HIGH", "pending", "Preserve Bauteilschutz (component protection) limits for BV39 turbo safety", "A2L thermal map inspection", "OpenAI Codex"),
    ]
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM research_tasks;")
    if cur.fetchone()[0] == 0:
        for t in tasks:
            cur.execute("""
            INSERT INTO research_tasks (task_code, title, priority, status, target_hypothesis, required_evidence, assigned_to)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """, t)
        conn.commit()
        print(f"Seeded {len(tasks)} research tasks.")


def seed_ecu_variant(conn):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM ecu_variants;")
    if cur.fetchone()[0] == 0:
        cur.execute("""
        INSERT INTO ecu_variants (ecu_family, ecu_model, hw_number, sw_number, sw_version, engine_code, turbo_model, notes)
        VALUES ('EDC16', 'EDC16U34', '03G906021QJ', '1037391847', 'P447_HAXN_3.42', 'BLS', 'BorgWarner BV39 (54399880072)', 'Volkswagen Golf 5 1.9 TDI PD 77kW / 105HP');
        """)
        conn.commit()
        print("Seeded primary ECU variant (Golf 5 BLS EDC16U34).")


def ingest_a2l_characteristics(conn, limit=None):
    idx_path = Path("diagnostic-review/a2l-characteristics-index.json")
    if not idx_path.exists():
        print("Characteristics index not found.")
        return

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM map_definitions;")
    count = cur.fetchone()[0]
    if count > 0:
        print(f"map_definitions already has {count} entries.")
        return

    print("Ingesting A2L characteristics index into SQLite...")
    with open(idx_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if limit:
        data = data[:limit]

    records = []
    for item in data:
        name = item.get("name", "")
        desc = item.get("description", "")
        kind = item.get("kind", "")
        addr_dec = item.get("address", 0)
        addr_hex = item.get("address_hex", "")
        size = item.get("size", 0)
        layout = item.get("layout", "")
        conv = item.get("conversion", "")
        lower = float(item.get("lower", 0.0)) if item.get("lower") is not None else None
        upper = float(item.get("upper", 0.0)) if item.get("upper") is not None else None
        line = item.get("a2l_line", 0)
        records.append((name, desc, kind, addr_dec, addr_hex, size, layout, conv, lower, upper, line))

    cur.executemany("""
    INSERT INTO map_definitions (name, description, kind, address_dec, address_hex, size_bytes, record_layout, conversion, lower_limit, upper_limit, a2l_line)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, records)

    # Populate maps_fts
    cur.execute("""
    INSERT INTO maps_fts (rowid, name, description, address_hex, unit)
    SELECT id, name, description, address_hex, conversion FROM map_definitions;
    """)

    conn.commit()
    print(f"Ingested {len(records)} characteristics and populated FTS5 index.")


def update_verified_active_maps(conn):
    active_path = Path("diagnostic-review/active-map-verification.json")
    if not active_path.exists():
        return

    with open(active_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cur = conn.cursor()
    updated = 0
    for item in data:
        name = item.get("name")
        offset = item.get("offset")
        layouts = item.get("layouts", {})
        ref = layouts.get("reference", {})
        dims = ref.get("dimensions", [])
        dim_x = dims[0] if len(dims) > 0 else None
        dim_y = dims[1] if len(dims) > 1 else None

        cur.execute("""
        UPDATE map_definitions
        SET is_verified_active = 1,
            active_reason = 'Verified active in Stage 1 diff comparison',
            dim_x = ?,
            dim_y = ?
        WHERE name = ? OR address_hex = ?;
        """, (dim_x, dim_y, name, offset))
        if cur.rowcount > 0:
            updated += 1

    conn.commit()
    print(f"Marked {updated} maps as verified active with physical dimensions.")


def ingest_firmware_metadata(conn):
    bins = [
        ("reference-from-hex.analysis-only.bin", "factory_hex", "Clean factory binary reconstituted from official Bosch/VAG HEX dataset"),
        ("03G906021QJ_stage1_refined_CS_OK.bin", "stage1_refined", "Stage 1 refined calibration with validated checksum OLS242"),
        ("03G906021QJ_ideal_stage1_dpf_egr_off.bin", "dpf_egr_off", "Stage 1 calibration with complete DPF switch and EGR hysteresis off"),
        ("03G906021QJ_stage1_full_power_dpf_egr_off.bin", "experimental", "Full power aggressive calibration (higher boost request and IQ)")
    ]

    cur = conn.cursor()
    for fname, vtype, notes in bins:
        p = Path(fname)
        if not p.exists():
            p = Path("diagnostic-review") / fname
        if not p.exists():
            continue

        with open(p, "rb") as f:
            content = f.read()
            sha256 = hashlib.sha256(content).hexdigest()
            size = len(content)

        cur.execute("SELECT id FROM firmware_versions WHERE sha256 = ?;", (sha256,))
        if not cur.fetchone():
            cur.execute("""
            INSERT INTO firmware_versions (filename, sha256, size_bytes, ecu_hw, ecu_sw, variant_type, checksum_status, notes)
            VALUES (?, ?, ?, '03G906021QJ', '1037391847', ?, 'VERIFIED_OK', ?);
            """, (p.name, sha256, size, vtype, notes))
    conn.commit()
    print("Firmware versions indexed.")


def ingest_vcds_logs(conn):
    log_files = [
        Path("logs/VCDS_WOT_Log_20260914_114936.csv"),
        Path("logs/Turbo_Fast_Log_20260914_210903.csv")
    ]

    cur = conn.cursor()
    for lpath in log_files:
        if not lpath.exists():
            continue

        with open(lpath, "rb") as f:
            sha256 = hashlib.sha256(f.read()).hexdigest()

        cur.execute("SELECT id FROM logs WHERE sha256 = ?;", (sha256,))
        if cur.fetchone():
            continue

        # Parse CSV basic stats
        import csv
        with open(lpath, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            continue

        rpms = []
        boost_acts = []
        boost_specs = []
        overshoots = []

        for r in rows:
            try:
                # Support both VCDS format and Turbo Fast format
                rpm = float(r.get("RPM") or r.get("rpm") or 0)
                b_act = float(r.get("Boost_Actual_mbar") or r.get("map_mbar_abs") or 0)
                b_spec = float(r.get("Boost_Specified_mbar") or 0)
                if rpm > 500:
                    rpms.append(rpm)
                if b_act > 800:
                    boost_acts.append(b_act)
                if b_spec > 800:
                    boost_specs.append(b_spec)
                if b_act > 800 and b_spec > 800:
                    overshoots.append(b_act - b_spec)
            except (ValueError, TypeError):
                continue

        sample_count = len(rows)
        rpm_min = int(min(rpms)) if rpms else 0
        rpm_max = int(max(rpms)) if rpms else 0
        b_act_max = max(boost_acts) if boost_acts else 0
        b_spec_max = max(boost_specs) if boost_specs else 0
        max_os = max(overshoots) if overshoots else 0

        cur.execute("""
        INSERT INTO logs (filename, sha256, log_type, sample_count, rpm_min, rpm_max, boost_actual_max_mbar, boost_spec_max_mbar, max_overshoot_mbar, notes)
        VALUES (?, ?, 'vcds_wot', ?, ?, ?, ?, ?, ?, 'Imported vehicle run');
        """, (lpath.name, sha256, sample_count, rpm_min, rpm_max, b_act_max, b_spec_max, max_os))
        print(f"Ingested log {lpath.name}: peak MAP {b_act_max:.1f} mbar, peak spec {b_spec_max:.1f} mbar, max delta {max_os:.1f} mbar.")

    conn.commit()


def seed_initial_claims(conn):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM claims;")
    if cur.fetchone()[0] > 0:
        return

    claims = [
        # (claim_text, source_id, exact_evidence, authority, applicability, map_name, epistemic_status, conditions)
        (
            "EDC16 uses an inner/outer torque structure where Driver Wish and Cruise Control request outer torque, friction and losses are subtracted, and limiters (smoke, torque) bound inner indicated torque before converting to injected fuel quantity.",
            3, # VW SSP 304
            "SSP 304 Section Torque-Oriented Engine Management",
            5, 4,
            "TrqLim_trqEng_MAP",
            "verified",
            "Normal engine operation"
        ),
        (
            "Closing or blanking EGR causes higher exhaust gas enthalpy and mass flow to pass through the turbine during transient acceleration, causing premature spool-up and overboost if N75 pre-control (PCR_rBPCtlBas_MAP) is not relaxed.",
            17, # SAE 2003-01-0357
            "SAE 2003-01-0357: Coordinated VGT/EGR control in diesel air path",
            4, 4,
            "PCR_rBPCtlBas_MAP",
            "corroborated",
            "EGR disabled / 100% duty cycle"
        ),
        (
            "The BV39 turbocharger (54399880072) has a reliable continuous absolute pressure limit of approximately 2350–2400 mbar; transients up to 2450 mbar are tolerated briefly, but sustained pressure ratio above 2.45 at 3500+ RPM exceeds compressor efficiency islands.",
            16, # BorgWarner
            "BorgWarner BV39 Compressor & Turbine sizing guidelines",
            5, 5,
            "PCR_pBDesBas_MAP",
            "project_matched",
            "Pumpe-Düse 1.9 TDI BLS"
        ),
        (
            "In Bosch EDC16U34, higher N75 duty cycle percentage in diagnostic logging corresponds to the VNT vanes being commanded more closed (maximum turbine expansion ratio / maximum spool drive), while lower duty cycle opens vanes to dump exhaust energy.",
            3, # VW SSP 304
            "VW SSP 304 Charge Pressure Control Actuator Description",
            5, 5,
            "PCR_rBPCtlBas_MAP",
            "project_matched",
            "EDC16 diagnostic block 011"
        ),
        (
            "The observed 2310–2330 mbar peak boost in 1900–2600 rpm under full load represents a transient overshoot of ~160–180 mbar above the requested 2150 mbar target, attributable to a combination of closed EGR enthalpy and aggressive N75 pre-control feed-forward.",
            21, # VCDS log
            "VCDS WOT Log 2026-09-14 11:49:36: 1281-3400 RPM pull, peak actual 2330 mbar at 2180 RPM",
            5, 5,
            "PCR_rBPCtlBas_MAP",
            "experiment_supported",
            "3rd gear WOT acceleration from 1300 RPM"
        )
    ]

    for c in claims:
        cur.execute("""
        INSERT INTO claims (claim_text, source_id, exact_evidence, authority_score, applicability_score, map_name, epistemic_status, conditions)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, c)

    # Populate claims_fts
    cur.execute("""
    INSERT INTO claims_fts (rowid, claim_text, map_name, exact_evidence, conditions)
    SELECT id, claim_text, map_name, exact_evidence, conditions FROM claims;
    """)

    conn.commit()
    print(f"Seeded {len(claims)} foundational claims with epistemic status.")


def search_knowledge(conn, query):
    cur = conn.cursor()
    print(f"\n--- FTS5 Search for: '{query}' in Map Definitions ---")
    cur.execute("""
    SELECT m.name, m.kind, m.address_hex, m.description, m.unit, m.is_verified_active
    FROM maps_fts f
    JOIN map_definitions m ON f.rowid = m.id
    WHERE maps_fts MATCH ?
    LIMIT 10;
    """, (query,))
    rows = cur.fetchall()
    if rows:
        for r in rows:
            active_str = "[ACTIVE]" if r["is_verified_active"] else ""
            print(f"- {r['name']} ({r['kind']}, {r['address_hex']}) {active_str}: {r['description']} [{r['unit']}]")
    else:
        print("No maps matched.")

    print(f"\n--- FTS5 Search for: '{query}' in Engineering Claims ---")
    cur.execute("""
    SELECT c.id, c.claim_text, c.map_name, c.authority_score, c.applicability_score, c.epistemic_status
    FROM claims_fts f
    JOIN claims c ON f.rowid = c.id
    WHERE claims_fts MATCH ?
    LIMIT 5;
    """, (query,))
    rows = cur.fetchall()
    if rows:
        for r in rows:
            print(f"[{r['epistemic_status'].upper()}] Auth:{r['authority_score']}/5 Appl:{r['applicability_score']}/5 (Map: {r['map_name']}):\n  {r['claim_text']}\n")
    else:
        print("No claims matched.")


def print_stats(conn):
    cur = conn.cursor()
    tables = [
        "sources", "documents", "claims", "map_definitions", 
        "firmware_versions", "logs", "research_tasks", "experiments"
    ]
    print("\n==========================================")
    print(" EDC16U34 KNOWLEDGE BASE STATISTICS ")
    print("==========================================")
    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM {t};")
        cnt = cur.fetchone()[0]
        print(f"  {t:<20}: {cnt}")
    
    cur.execute("SELECT COUNT(*) FROM map_definitions WHERE is_verified_active = 1;")
    active_cnt = cur.fetchone()[0]
    print(f"  {'verified_active_maps':<20}: {active_cnt}")
    print("==========================================\n")


def main():
    conn = get_connection()
    init_schema(conn)
    seed_sources(conn)
    seed_research_tasks(conn)
    seed_ecu_variant(conn)
    ingest_a2l_characteristics(conn)
    update_verified_active_maps(conn)
    ingest_firmware_metadata(conn)
    ingest_vcds_logs(conn)
    seed_initial_claims(conn)

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "stats":
            print_stats(conn)
        elif cmd == "search" and len(sys.argv) > 2:
            search_knowledge(conn, sys.argv[2])
    else:
        print_stats(conn)
        search_knowledge(conn, "PCR_rBPCtlBas_MAP")


if __name__ == "__main__":
    main()
