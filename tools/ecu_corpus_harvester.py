#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ecu_corpus_harvester.py

Metadata-first corpus manager for ECU calibration artefacts.

It deliberately separates:
- discovery metadata (may describe a paid/private/unavailable file),
- local possession,
- identity verification,
- applicability to the target ECU.

It does NOT automatically download paid/proprietary DAMOS/BIN files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KB_DIR = ROOT / "ecu-kb"
DB = KB_DIR / "knowledge" / "kb.sqlite3"
SCHEMA = KB_DIR / "schema.sql"
DEFAULT_SEEDS = KB_DIR / "corpus" / "seeds.json"

TARGET = {
    "ecu_family": "EDC16U34",
    "ecu_variant": "EDC16U34-3.42",
    "vag_part_number": "03G906021QJ",
    "vag_sw_version": "1984",
    "bosch_sw_number": "1037391847",
    "calibration_id": "391847",
    "project_code": "P447 HAXN",
    "engine_code": "BLS",
}

EXT_TYPES = {
    ".a2l": "A2L",
    ".ols": "OLS",
    ".xdf": "XDF",
    ".bin": "BIN_ORI",
    ".ori": "BIN_ORI",
    ".sgo": "SGO",
    ".frf": "FRF",
    ".eep": "EEPROM",
    ".eeprom": "EEPROM",
    ".dam": "DAMOS",
    ".kp": "MAPPACK",
    ".kp2": "MAPPACK",
    ".hex": "OTHER",
    ".mot": "OTHER",
}

ASCII_PATTERNS = {
    "vag_part_number": re.compile(rb"\b0[0-9A-Z]{2}9060[0-9A-Z]{4,6}\b"),
    "bosch_sw_number": re.compile(rb"\b10[0-9]{8}\b"),
    "calibration_id": re.compile(rb"\b[235][0-9]{5}\b"),
    "project_code": re.compile(rb"\bP[0-9]{3}[\x20_-]?[A-Z0-9]{3,5}\b"),
}


def norm(value: str | None) -> str:
    return re.sub(r"[^A-Z0-9]", "", (value or "").upper())


def same(a: str | None, b: str | None) -> bool:
    return bool(a and b and norm(a) == norm(b))


def project_family(value: str | None) -> str:
    n = norm(value)
    return n[:4] if len(n) >= 4 else n


def extract_filename_metadata(path: Path) -> dict:
    """Parse high-signal identity tokens from structured ECU filenames.

    Filenames are discovery metadata, not proof by themselves, but they are much
    safer than treating an arbitrary six-digit number inside a 12 MiB A2L as a
    calibration ID.
    """
    name = path.name.upper()
    out: dict[str, str] = {}

    part = re.search(r"(?<![A-Z0-9])(0[0-9A-Z]{2}906[0-9A-Z]{5})(?![A-Z0-9])", name)
    if part:
        out["vag_part_number"] = part.group(1)

    tuple_match = re.search(
        r"(0[0-9A-Z]{2}906[0-9A-Z]{5})[_\- ]+(\d{4})[_\- ]+(\d{6})",
        name,
    )
    if tuple_match:
        out["vag_part_number"] = tuple_match.group(1)
        out["vag_sw_version"] = tuple_match.group(2)
        out["calibration_id"] = tuple_match.group(3)

    bosch_sw = re.search(r"(?<!\d)(10\d{8})(?!\d)", name)
    if bosch_sw:
        out["bosch_sw_number"] = bosch_sw.group(1)

    project = re.search(r"(?<![A-Z0-9])(P\d{3})[_\- ]+([A-Z0-9]{4})(?![A-Z0-9])", name)
    if project:
        out["project_code"] = f"{project.group(1)} {project.group(2)}"

    ecu = re.search(r"EDC16U34(?:[_\- ]+(\d+(?:\.\d+)?))?", name)
    if ecu:
        out["ecu_family"] = "EDC16U34"
        if ecu.group(1):
            out["ecu_variant"] = f"EDC16U34-{ecu.group(1)}"

    if re.search(r"(?<![A-Z0-9])BLS(?![A-Z0-9])", name):
        out["engine_code"] = "BLS"

    return out


def classify(meta: dict, target: dict = TARGET) -> tuple[str, int, list[str]]:
    reasons: list[str] = []
    family = norm(meta.get("ecu_family"))
    target_family = norm(target["ecu_family"])

    if family and family != target_family:
        if family.startswith("EDC16"):
            return "STRUCTURAL_ANALOG", 20, [f"same EDC16 generation, different family: {meta.get('ecu_family')}"]
        return "REJECT", 0, [f"ECU family mismatch: {meta.get('ecu_family')}"]

    score = 20 if family == target_family else 0
    if family == target_family:
        reasons.append("ECU family exact")

    part_exact = same(meta.get("vag_part_number"), target["vag_part_number"])
    if part_exact:
        score += 25
        reasons.append("VAG part number exact")

    hw_exact = same(meta.get("vag_hw_number"), target["vag_part_number"])
    if hw_exact:
        score += 5
        reasons.append("VAG hardware identity exact")

    full_sw_exact = same(meta.get("bosch_sw_number"), target["bosch_sw_number"])
    if full_sw_exact:
        score += 25
        reasons.append("Bosch full SW exact")

    cal_exact = same(meta.get("calibration_id"), target["calibration_id"])
    if cal_exact:
        score += 20
        reasons.append("calibration/software ID exact")

    version_exact = same(meta.get("vag_sw_version"), target["vag_sw_version"])
    if version_exact:
        score += 10
        reasons.append("VAG SW version exact")

    project_exact = norm(meta.get("project_code")) == norm(target["project_code"]) and bool(meta.get("project_code"))
    project_same_family = (
        project_family(meta.get("project_code"))
        and project_family(meta.get("project_code")) == project_family(target["project_code"])
    )
    if project_exact:
        score += 10
        reasons.append("Bosch/VAG project code exact")
    elif project_same_family:
        score += 6
        reasons.append("same P447 project family")

    engine = meta.get("engine_code")
    if engine:
        if same(engine, target["engine_code"]):
            score += 10
            reasons.append("engine code exact")
        else:
            score -= 5
            reasons.append(f"engine code differs: {engine} vs {target['engine_code']}")

    score = max(0, min(100, score))

    # Exact ECU identity can be established without an engine code if the
    # part + software tuple is exact. Engine metadata is kept as a separate
    # applicability dimension, never silently rewritten.
    exact_sw_tuple = part_exact and (
        full_sw_exact or (cal_exact and version_exact)
    )
    if exact_sw_tuple:
        return "EXACT", score, reasons

    if part_exact or hw_exact:
        return "SAME_HW_SIBLING", score, reasons

    if family == target_family and (
        project_same_family or norm(meta.get("vag_part_number")).startswith("03G906021")
    ):
        return "SAME_PROJECT_FAMILY", max(score, 45), reasons or ["same EDC16U34/P447 project family"]

    if family == target_family:
        return "STRUCTURAL_ANALOG", max(score, 30), reasons or ["same EDC16U34 family"]

    return "UNKNOWN", score, reasons or ["insufficient identity metadata"]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def connect(db_path: Path = DB) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(db_path))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


def ensure_schema(c: sqlite3.Connection) -> None:
    c.executescript(SCHEMA.read_text(encoding="utf-8"))
    c.commit()


def upsert_source(c: sqlite3.Connection, src: dict) -> int:
    c.execute(
        """
        INSERT INTO corpus_sources(
            source_key,title,source_type,url,access_mode,trust_tier,
            license_note,notes,last_checked_at
        ) VALUES(?,?,?,?,?,?,?,?,datetime('now'))
        ON CONFLICT(source_key) DO UPDATE SET
            title=excluded.title,
            source_type=excluded.source_type,
            url=excluded.url,
            access_mode=excluded.access_mode,
            trust_tier=excluded.trust_tier,
            license_note=excluded.license_note,
            notes=excluded.notes,
            last_checked_at=datetime('now')
        """,
        (
            src["source_key"], src["title"], src["source_type"], src.get("url"),
            src["access_mode"], src["trust_tier"], src.get("license_note"),
            src.get("notes"),
        ),
    )
    return int(c.execute(
        "SELECT id FROM corpus_sources WHERE source_key=?", (src["source_key"],)
    ).fetchone()[0])


def upsert_artifact(c: sqlite3.Connection, source_id: int, art: dict) -> int:
    cols = [
        "artifact_type","name","source_url","ecu_family","ecu_variant",
        "vag_part_number","vag_hw_number","vag_sw_version","bosch_sw_number",
        "calibration_id","project_code","engine_code","vehicle","power_kw",
        "file_size","sha256","local_rel_path","access_state","identity_state",
        "license_note","notes",
    ]
    vals = [art.get(k) for k in cols]
    vals[0] = vals[0] or "OTHER"
    vals[17] = vals[17] or "METADATA_ONLY"
    vals[18] = vals[18] or "UNVERIFIED"

    existing = c.execute(
        """
        SELECT * FROM corpus_artifacts
        WHERE source_id=? AND name=? AND COALESCE(source_url,'')=COALESCE(?, '')
        """,
        (source_id, art["name"], art.get("source_url")),
    ).fetchone()

    effective = dict(art)
    if existing:
        aid = int(existing["id"])
        current = dict(existing)

        # Start from the persisted row so optional seed fields cannot turn
        # NOT NULL/defaulted fields back into NULL on refresh.
        effective = dict(current)
        for key, value in art.items():
            if value is not None:
                effective[key] = value

        # Seed refreshes may update descriptive metadata, but MUST NOT erase
        # evidence acquired locally after the seed was first imported.
        protected = {
            "file_size", "sha256", "local_rel_path",
            "access_state", "identity_state", "verified_at",
        }
        for key in protected:
            if current.get(key) not in (None, "", "METADATA_ONLY", "UNVERIFIED"):
                effective[key] = current.get(key)

        # Preserve stronger identity fields learned from a local parser/review
        # when the incoming seed does not provide them.
        for key in (
            "ecu_family","ecu_variant","vag_part_number","vag_hw_number",
            "vag_sw_version","bosch_sw_number","calibration_id",
            "project_code","engine_code",
        ):
            if not effective.get(key) and current.get(key):
                effective[key] = current.get(key)

        update_cols = [k for k in cols if k != "verified_at"]
        update_vals = [effective.get(k) for k in update_cols]
        assignments = ", ".join(f"{k}=?" for k in update_cols)
        c.execute(f"UPDATE corpus_artifacts SET {assignments} WHERE id=?", (*update_vals, aid))
    else:
        effective.setdefault("artifact_type", "OTHER")
        effective.setdefault("access_state", "METADATA_ONLY")
        effective.setdefault("identity_state", "UNVERIFIED")
        vals = [effective.get(k) for k in cols]
        placeholders = ",".join("?" for _ in cols)
        c.execute(
            f"INSERT INTO corpus_artifacts(source_id,{','.join(cols)}) VALUES(?,{placeholders})",
            (source_id, *vals),
        )
        aid = int(c.execute("SELECT last_insert_rowid()").fetchone()[0])

    match_class, score, reasons = classify(effective)
    c.execute(
        """
        INSERT INTO corpus_matches(artifact_id,target_profile,match_class,score,reasons_json,computed_at)
        VALUES(?,?,?,?,?,datetime('now'))
        ON CONFLICT(artifact_id) DO UPDATE SET
            target_profile=excluded.target_profile,
            match_class=excluded.match_class,
            score=excluded.score,
            reasons_json=excluded.reasons_json,
            computed_at=datetime('now')
        """,
        (
            aid, "Golf5-BLS-EDC16U34-1037391847",
            match_class, score, json.dumps(reasons, ensure_ascii=False),
        ),
    )
    return aid


def load_seeds(c: sqlite3.Connection, seed_path: Path) -> tuple[int, int]:
    data = json.loads(seed_path.read_text(encoding="utf-8"))
    source_ids = {}
    for src in data.get("sources", []):
        source_ids[src["source_key"]] = upsert_source(c, src)

    count = 0
    for art in data.get("artifacts", []):
        sid = source_ids.get(art["source_key"])
        if sid is None:
            row = c.execute(
                "SELECT id FROM corpus_sources WHERE source_key=?", (art["source_key"],)
            ).fetchone()
            if not row:
                raise ValueError(f"Unknown source_key: {art['source_key']}")
            sid = int(row[0])
        upsert_artifact(c, sid, art)
        count += 1
    c.commit()
    return len(source_ids), count


def extract_ascii_metadata(path: Path) -> dict:
    # 2 MiB ECU images and ordinary definition files are small enough for one
    # bounded read. For larger archives only inspect first/last 4 MiB.
    size = path.stat().st_size
    with path.open("rb") as f:
        if size <= 8 * 1024 * 1024:
            data = f.read()
        else:
            head = f.read(4 * 1024 * 1024)
            f.seek(max(0, size - 4 * 1024 * 1024))
            data = head + f.read(4 * 1024 * 1024)

    out = {}
    for key, pat in ASCII_PATTERNS.items():
        matches = []
        for m in pat.finditer(data):
            try:
                val = m.group(0).decode("ascii", errors="strict")
            except Exception:
                continue
            if val not in matches:
                matches.append(val)
        if matches:
            out[key] = matches

    upper = data.upper()
    if b"EDC16U34" in upper:
        out["ecu_family"] = ["EDC16U34"]
    if b"HAXN" in upper and b"P447" in upper:
        out["project_code"] = ["P447 HAXN"]
    if b"BLS" in upper:
        out["engine_code"] = ["BLS"]
    return out


def choose_identity(meta: dict, observations: dict) -> dict:
    result = dict(meta)
    for key, vals in observations.items():
        if result.get(key) or not vals:
            continue

        target_val = TARGET.get(key)
        target_hit = next((v for v in vals if same(v, target_val)), None)
        if target_hit:
            result[key] = target_hit
            continue

        # Generic regexes in a large A2L can find many unrelated six-digit
        # constants. Never promote an arbitrary first match into identity.
        if len(vals) == 1:
            result[key] = vals[0]
    return result



def add_observation(
    c: sqlite3.Connection,
    artifact_id: int,
    kind: str,
    value: str,
    source: str | None,
) -> None:
    exists = c.execute(
        """
        SELECT 1 FROM corpus_observations
        WHERE artifact_id=? AND observation_kind=? AND value=?
          AND COALESCE(source,'')=COALESCE(?, '')
        LIMIT 1
        """,
        (artifact_id, kind, value, source),
    ).fetchone()
    if not exists:
        c.execute(
            "INSERT INTO corpus_observations(artifact_id,observation_kind,value,source) VALUES(?,?,?,?)",
            (artifact_id, kind, value, source),
        )


def local_source(c: sqlite3.Connection) -> int:
    return upsert_source(c, {
        "source_key":"user_local_corpus",
        "title":"User local ECU corpus",
        "source_type":"manual_entry",
        "url":None,
        "access_mode":"user_supplied",
        "trust_tier":"B",
        "license_note":"Local user-controlled files; not published by the harvester.",
        "notes":"Identity must be established from file observations and cross-reference metadata.",
    })


def scan_local(c: sqlite3.Connection, directory: Path) -> int:
    sid = local_source(c)
    n = 0
    for path in sorted(p for p in directory.rglob("*") if p.is_file()):
        kind = EXT_TYPES.get(path.suffix.lower())
        if not kind:
            continue
        digest = sha256_file(path)
        filename_meta = extract_filename_metadata(path)
        obs = extract_ascii_metadata(path)
        base = {
            "artifact_type": kind,
            "name": path.name,
            "source_url": None,
            "file_size": path.stat().st_size,
            "sha256": digest,
            "local_rel_path": str(path.resolve()),
            "access_state": "AVAILABLE_LOCAL",
            "identity_state": "HEADER_MATCHED" if (filename_meta or obs) else "UNVERIFIED",
            "notes": "Discovered by local corpus scan; no publication implied.",
            **filename_meta,
        }
        art = choose_identity(base, obs)
        aid = upsert_artifact(c, sid, art)
        for key, val in filename_meta.items():
            add_observation(c, aid, "filename", f"{key}={val}", str(path))
        add_observation(c, aid, "sha256", digest, str(path))
        add_observation(c, aid, "file_size", str(path.stat().st_size), str(path))
        for key, vals in obs.items():
            for val in vals:
                add_observation(c, aid, "ascii_id", f"{key}={val}", str(path))
        n += 1
    c.commit()
    return n


def rows_as_dicts(rows) -> list[dict]:
    return [dict(r) for r in rows]


def report(c: sqlite3.Connection, limit: int = 100) -> dict:
    summary = rows_as_dicts(c.execute(
        """
        SELECT m.match_class, COUNT(*) AS n, MAX(m.score) AS best_score
        FROM corpus_matches m
        GROUP BY m.match_class
        ORDER BY best_score DESC, n DESC
        """
    ).fetchall())
    top = rows_as_dicts(c.execute(
        """
        SELECT a.id,a.artifact_type,a.name,a.ecu_family,a.vag_part_number,
               a.vag_sw_version,a.bosch_sw_number,a.calibration_id,a.project_code,
               a.engine_code,a.file_size,a.sha256,a.access_state,a.identity_state,
               s.source_key,s.title AS source_title,s.access_mode,s.trust_tier,
               m.match_class,m.score,m.reasons_json
        FROM corpus_artifacts a
        JOIN corpus_sources s ON s.id=a.source_id
        JOIN corpus_matches m ON m.artifact_id=a.id
        ORDER BY m.score DESC,
                 CASE m.match_class
                   WHEN 'EXACT' THEN 0
                   WHEN 'SAME_HW_SIBLING' THEN 1
                   WHEN 'SAME_PROJECT_FAMILY' THEN 2
                   WHEN 'STRUCTURAL_ANALOG' THEN 3
                   ELSE 4
                 END,
                 a.id
        LIMIT ?
        """,
        (limit,),
    ).fetchall())
    return {"target": TARGET, "summary": summary, "artifacts": top}


def table_exists_local(c: sqlite3.Connection, name: str) -> bool:
    return bool(c.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name=?",
        (name,),
    ).fetchone())


def cmd_verify_local(c: sqlite3.Connection, artifact_id: int, path: Path) -> int:
    row = c.execute("SELECT * FROM corpus_artifacts WHERE id=?", (artifact_id,)).fetchone()
    if not row:
        print(f"Unknown artifact id {artifact_id}", file=sys.stderr)
        return 2

    digest = sha256_file(path)
    filename_meta = extract_filename_metadata(path)
    obs = extract_ascii_metadata(path)

    identity = dict(row)
    # Structured target tuple in the filename is stronger than a generic
    # six-digit regex hit from inside an A2L.
    identity.update({k: v for k, v in filename_meta.items() if v})
    identity = choose_identity(identity, obs)

    project_hash_evidence = []
    if table_exists_local(c, "a2l_objects"):
        sw_rows = c.execute(
            "SELECT DISTINCT sw_number FROM a2l_objects WHERE lower(a2l_sha256)=lower(?)",
            (digest,),
        ).fetchall()
        for sw_row in sw_rows:
            if sw_row[0]:
                project_hash_evidence.append(f"A2L DB hash maps to SW {sw_row[0]}")
                if same(sw_row[0], TARGET["bosch_sw_number"]):
                    identity["bosch_sw_number"] = sw_row[0]

    firmware_match = None
    if table_exists_local(c, "firmware_versions"):
        firmware_match = c.execute(
            "SELECT label,source,path FROM firmware_versions WHERE lower(sha256)=lower(?) LIMIT 1",
            (digest,),
        ).fetchone()
        if firmware_match:
            project_hash_evidence.append(
                f"known firmware hash: source={firmware_match['source']} label={firmware_match['label']}"
            )

    match_class, score, reasons = classify(identity)
    reasons.extend(project_hash_evidence)

    expected_sha = (row["sha256"] or "").lower()
    source_key = c.execute(
        "SELECT source_key FROM corpus_sources WHERE id=?", (row["source_id"],)
    ).fetchone()[0]

    if project_hash_evidence:
        identity_state = "PROJECT_VERIFIED"
    elif expected_sha and source_key != "user_local_corpus":
        identity_state = "HASH_MATCHED" if expected_sha == digest.lower() else "REJECTED"
        if identity_state == "REJECTED":
            reasons.append("local SHA-256 differs from previously recorded reference hash")
    elif filename_meta or obs:
        identity_state = "HEADER_MATCHED"
    else:
        identity_state = "UNVERIFIED"

    c.execute(
        """
        UPDATE corpus_artifacts
        SET sha256=?, file_size=?, local_rel_path=?, access_state='VERIFIED_LOCAL',
            identity_state=?, verified_at=datetime('now'),
            ecu_family=?,
            vag_part_number=?,
            bosch_sw_number=?,
            calibration_id=?,
            project_code=?,
            engine_code=?,
            vag_sw_version=?,
            ecu_variant=COALESCE(?, ecu_variant)
        WHERE id=?
        """,
        (
            digest, path.stat().st_size, str(path.resolve()),
            identity_state,
            identity.get("ecu_family"), identity.get("vag_part_number"),
            identity.get("bosch_sw_number"), identity.get("calibration_id"),
            identity.get("project_code"), identity.get("engine_code"),
            identity.get("vag_sw_version"), identity.get("ecu_variant"),
            artifact_id,
        ),
    )
    c.execute(
        """
        UPDATE corpus_matches
        SET match_class=?,score=?,reasons_json=?,computed_at=datetime('now')
        WHERE artifact_id=?
        """,
        (match_class, score, json.dumps(reasons, ensure_ascii=False), artifact_id),
    )
    for key, val in filename_meta.items():
        add_observation(c, artifact_id, "filename", f"{key}={val}", str(path))
    for item in project_hash_evidence:
        add_observation(c, artifact_id, "parser_result", item, str(path))
    add_observation(
        c, artifact_id, "manual_review",
        f"local verify sha256={digest}", str(path)
    )
    c.commit()
    print(json.dumps({
        "artifact_id": artifact_id,
        "sha256": digest,
        "match_class": match_class,
        "score": score,
        "observed": obs,
    }, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Metadata-first ECU corpus harvester")
    p.add_argument("--db", type=Path, default=DB)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init")

    ps = sub.add_parser("seed")
    ps.add_argument("--file", type=Path, default=DEFAULT_SEEDS)

    ps = sub.add_parser("scan")
    ps.add_argument("directory", type=Path)

    ps = sub.add_parser("report")
    ps.add_argument("--limit", type=int, default=100)
    ps.add_argument("--json", action="store_true")

    ps = sub.add_parser("verify-local")
    ps.add_argument("artifact_id", type=int)
    ps.add_argument("path", type=Path)

    args = p.parse_args()
    c = connect(args.db)
    try:
        ensure_schema(c)
        if args.cmd == "init":
            print(f"Corpus schema ready: {args.db}")
            return 0
        if args.cmd == "seed":
            ns, na = load_seeds(c, args.file)
            print(f"Seeded sources={ns}, artifacts={na}")
            return 0
        if args.cmd == "scan":
            n = scan_local(c, args.directory)
            print(f"Scanned artifacts={n}")
            return 0
        if args.cmd == "report":
            data = report(c, args.limit)
            if args.json:
                print(json.dumps(data, ensure_ascii=False, indent=2))
            else:
                print("ECU CORPUS REPORT")
                print(json.dumps(data["target"], ensure_ascii=False))
                for row in data["summary"]:
                    print(f"{row['match_class']:20} {row['n']:4}  best={row['best_score']}")
                print("")
                for a in data["artifacts"]:
                    print(
                        f"#{a['id']:4} {a['score']:3} {a['match_class']:20} "
                        f"{a['artifact_type']:18} {a['name']}"
                    )
            return 0
        if args.cmd == "verify-local":
            return cmd_verify_local(c, args.artifact_id, args.path)
    finally:
        c.close()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
