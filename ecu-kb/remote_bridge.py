#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
remote_bridge.py — read-only bridge from the private local SQLite knowledge base
to a GitHub-readable specialist snapshot.

Design goals:
- SQLite remains the canonical mutable store.
- Raw corpus, PDFs, firmware binaries and the SQLite file are NEVER exported.
- Only current claims, their attached citation snippets/provenance, gaps,
  conflicts and the A2L object catalogue are exported.
- `kb.py check` must pass before publishing unless --skip-check is explicit.
- Remote consumers can verify every generated file by SHA-256 from manifest.json.

This bridge exists for external AI clients (including ChatGPT via the GitHub
connector) that can read the repository but cannot access the user's local PC.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "knowledge" / "kb.sqlite3"
DEFAULT_OUT = ROOT / "remote"
SCHEMA_VERSION = 2

PROFILE = {
    "vehicle": "Volkswagen Golf 5 (1K1), 2008",
    "engine_code": "BLS",
    "engine": "1.9 TDI 8V Pumpe-Duese",
    "ecu_family": "EDC16",
    "ecu_variant": "EDC16U34-3.42",
    "sw_number": "1037391847",
    "hw_number": "03G906021QJ",
}

SUPPORT_STATES = {"corroborated", "project_matched", "experiment_supported", "verified"}
NEGATIVE_STATES = {"contradicted"}
NON_SUPPORT_KINDS = {"HYPOTHESIS", "COMMUNITY_CLAIM", "MODEL_RECALL", "UNKNOWN"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sha256_json(payload) -> str:
    raw = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def connect(db_path: Path) -> sqlite3.Connection:
    if not db_path.is_file():
        raise FileNotFoundError(f"Knowledge DB not found: {db_path}")
    c = sqlite3.connect(str(db_path))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


def table_exists(c: sqlite3.Connection, name: str) -> bool:
    return bool(c.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name=?", (name,)
    ).fetchone())


def run_kb_check() -> tuple[bool, str]:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "kb.py"), "check"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    summary = (proc.stdout + "\n" + proc.stderr).strip()
    return proc.returncode == 0, summary[-3000:]


def epistemic_role(row: dict) -> str:
    state = row.get("verification_state")
    kind = row.get("evidence_kind")
    if state in NEGATIVE_STATES:
        return "negative"
    if state in SUPPORT_STATES and kind not in NON_SUPPORT_KINDS:
        return "support"
    return "context"


def export_claims(c: sqlite3.Connection) -> list[dict]:
    rows = c.execute(
        """
        SELECT *
        FROM claims
        WHERE retracted_at IS NULL
          AND verification_state NOT IN ('deprecated','superseded')
        ORDER BY id
        """
    ).fetchall()

    out = []
    for rr in rows:
        claim = dict(rr)
        claim["epistemic_role"] = epistemic_role(claim)
        citations = c.execute(
            """
            SELECT ci.id, ci.locator, ci.quote, ci.verified_at,
                   d.rel_path AS document, d.sha256 AS document_sha256,
                   s.title AS source_title, s.publisher, s.year,
                   s.tier, s.authority, s.applicability, s.obtainability
            FROM citations ci
            JOIN documents d ON d.sha256 = ci.doc_sha256
            JOIN sources s ON s.id = d.source_id
            WHERE ci.claim_id = ?
            ORDER BY ci.id
            """,
            (claim["id"],),
        ).fetchall()
        claim["citations"] = [dict(x) for x in citations]
        out.append(claim)
    return out


def export_retractions(c: sqlite3.Connection) -> list[dict]:
    cols = [r[1] for r in c.execute("PRAGMA table_info(claims)").fetchall()]
    sc_select = "source_class," if "source_class" in cols else "NULL AS source_class,"
    rows = c.execute(
        f"""
        SELECT id, claim_key, statement, evidence_kind, verification_state, {sc_select}
               ecu_family, ecu_variant, sw_number, engine_code, turbo_model,
               supersedes_id, retracted_at, retraction_reason, updated_at
        FROM claims
        WHERE retracted_at IS NOT NULL
           OR verification_state IN ('deprecated','superseded')
        ORDER BY id
        """
    ).fetchall()
    return [dict(r) for r in rows]


def export_gaps(c: sqlite3.Connection) -> list[dict]:
    if not table_exists(c, "gaps"):
        return []
    return [dict(r) for r in c.execute(
        "SELECT * FROM gaps ORDER BY priority ASC, id ASC"
    ).fetchall()]


def export_corpus(c: sqlite3.Connection) -> list[dict]:
    if not table_exists(c, "corpus_artifacts") or not table_exists(c, "corpus_sources"):
        return []
    rows = c.execute(
        """
        SELECT a.id, a.artifact_type, a.name, a.source_url,
               a.ecu_family, a.ecu_variant, a.vag_part_number, a.vag_hw_number,
               a.vag_sw_version, a.bosch_sw_number, a.calibration_id,
               a.project_code, a.engine_code, a.vehicle, a.power_kw,
               a.file_size, a.sha256, a.access_state, a.identity_state,
               a.license_note, a.notes, a.verified_at,
               s.source_key, s.title AS source_title, s.source_type,
               s.url AS source_home, s.access_mode, s.trust_tier,
               s.license_note AS source_license_note,
               m.match_class, m.score, m.reasons_json, m.computed_at
        FROM corpus_artifacts a
        JOIN corpus_sources s ON s.id = a.source_id
        LEFT JOIN corpus_matches m ON m.artifact_id = a.id
        ORDER BY COALESCE(m.score,0) DESC, a.id
        """
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["match_reasons"] = json.loads(d.pop("reasons_json") or "[]")
        except Exception:
            d["match_reasons"] = []
            d.pop("reasons_json", None)

        if table_exists(c, "corpus_observations"):
            obs = c.execute(
                """
                SELECT observation_kind, value, observed_at
                FROM corpus_observations
                WHERE artifact_id=?
                ORDER BY id
                """,
                (d["id"],),
            ).fetchall()
            # Intentionally omit observation.source: it may contain a local path.
            d["observations"] = [dict(x) for x in obs]
        else:
            d["observations"] = []

        # local_rel_path is intentionally never selected/exported.
        out.append(d)
    return out


def export_conflicts(c: sqlite3.Connection) -> list[dict]:
    if not table_exists(c, "conflicts"):
        return []
    return [dict(r) for r in c.execute(
        """
        SELECT cf.*,
               a.statement AS claim_a_statement,
               b.statement AS claim_b_statement
        FROM conflicts cf
        LEFT JOIN claims a ON a.id = cf.claim_a_id
        LEFT JOIN claims b ON b.id = cf.claim_b_id
        ORDER BY cf.id
        """
    ).fetchall()]


def safe_group_name(group: str | None) -> str:
    value = (group or "_UNGROUPED").strip() or "_UNGROUPED"
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def export_a2l(c: sqlite3.Connection, out_dir: Path, generated_at: str) -> dict:
    a2l_dir = out_dir / "a2l"
    a2l_dir.mkdir(parents=True, exist_ok=True)

    # Remove stale generated JSON files from groups that disappeared.
    for old in a2l_dir.glob("*.json"):
        old.unlink()

    rows = c.execute(
        """
        SELECT sw_number, name, description, obj_type, kind, address,
               record_layout, func_group, a2l_sha256
        FROM a2l_objects
        ORDER BY name
        """
    ).fetchall()

    # Group case-insensitively to prevent file collision on Windows/cross-platform git
    grouped: dict[str, dict] = {}
    for r in rows:
        raw_group = (r["func_group"] or "").strip() or "_UNGROUPED"
        safe_name = safe_group_name(raw_group)
        key = safe_name.lower()
        if key not in grouped:
            grouped[key] = {
                "canonical_name": safe_name,
                "raw_groups": set(),
                "objects": [],
            }
        grouped[key]["raw_groups"].add(raw_group)
        grouped[key]["objects"].append(dict(r))

    result = {}
    for key, data in sorted(grouped.items(), key=lambda x: x[1]["canonical_name"]):
        canon = data["canonical_name"]
        filename = canon + ".json"
        path = a2l_dir / filename
        write_json(path, {
            "schema_version": SCHEMA_VERSION,
            "generated_at_utc": generated_at,
            "profile": PROFILE,
            "func_group": canon,
            "raw_groups": sorted(data["raw_groups"]),
            "objects": data["objects"],
        })
        sha = sha256_file(path)
        for raw in data["raw_groups"]:
            result[raw] = {
                "path": f"a2l/{filename}",
                "count": len(data["objects"]),
                "sha256": sha,
            }
    return result


def a2l_logical_sha256(c: sqlite3.Connection) -> str:
    rows = c.execute(
        """
        SELECT sw_number, name, description, obj_type, kind, address,
               record_layout, func_group, a2l_sha256
        FROM a2l_objects
        ORDER BY sw_number, name
        """
    ).fetchall()
    return sha256_json([dict(r) for r in rows])


def collect_stats(c: sqlite3.Connection, claims: list[dict], gaps: list[dict]) -> dict:
    def count(table: str) -> int:
        if not table_exists(c, table):
            return 0
        return int(c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])

    return {
        "sources": count("sources"),
        "documents": count("documents"),
        "chunks": count("chunks"),
        "identifiers": count("identifiers"),
        "a2l_objects": count("a2l_objects"),
        "corpus_sources": count("corpus_sources"),
        "corpus_artifacts": count("corpus_artifacts"),
        "corpus_exact": (
            int(c.execute("SELECT COUNT(*) FROM corpus_matches WHERE match_class='EXACT'").fetchone()[0])
            if table_exists(c, "corpus_matches") else 0
        ),
        "claims_current": len(claims),
        "claims_support": sum(x["epistemic_role"] == "support" for x in claims),
        "claims_context": sum(x["epistemic_role"] == "context" for x in claims),
        "claims_negative": sum(x["epistemic_role"] == "negative" for x in claims),
        "gaps_total": len(gaps),
        "gaps_open": sum(x.get("status") in {"OPEN", "RESEARCHING", "PARTIAL"} for x in gaps),
    }


def export_snapshot(db_path: Path, out_dir: Path, skip_check: bool = False) -> int:
    if not skip_check:
        ok, detail = run_kb_check()
        if not ok:
            print("REFUSED: kb.py check failed; snapshot was not published.", file=sys.stderr)
            if detail:
                print(detail, file=sys.stderr)
            return 2

    generated_at = utc_now()
    c = connect(db_path)
    try:
        claims = export_claims(c)
        retractions = export_retractions(c)
        gaps = export_gaps(c)
        conflicts = export_conflicts(c)
        corpus = export_corpus(c)

        out_dir.mkdir(parents=True, exist_ok=True)
        claims_path = out_dir / "claims.json"
        retractions_path = out_dir / "retractions.json"
        gaps_path = out_dir / "gaps.json"
        conflicts_path = out_dir / "conflicts.json"
        corpus_path = out_dir / "corpus.json"

        common = {
            "schema_version": SCHEMA_VERSION,
            "generated_at_utc": generated_at,
            "profile": PROFILE,
        }
        write_json(claims_path, {**common, "claims": claims})
        write_json(retractions_path, {**common, "retractions": retractions})
        write_json(gaps_path, {**common, "gaps": gaps})
        write_json(conflicts_path, {**common, "conflicts": conflicts})
        write_json(corpus_path, {**common, "corpus": corpus})

        a2l_groups = export_a2l(c, out_dir, generated_at)

        files = {
            "claims": {"path": "claims.json", "sha256": sha256_file(claims_path), "count": len(claims)},
            "retractions": {
                "path": "retractions.json",
                "sha256": sha256_file(retractions_path),
                "count": len(retractions),
            },
            "gaps": {"path": "gaps.json", "sha256": sha256_file(gaps_path), "count": len(gaps)},
            "conflicts": {
                "path": "conflicts.json",
                "sha256": sha256_file(conflicts_path),
                "count": len(conflicts),
            },
            "corpus": {
                "path": "corpus.json",
                "sha256": sha256_file(corpus_path),
                "count": len(corpus),
            },
        }

        warnings = []
        for claim in claims:
            if claim.get("source_class") == "document_citation" and not claim.get("citations"):
                warnings.append(f"claim #{claim['id']} document_citation has no exported citation")
            if claim.get("verification_state") == "contradicted":
                warnings.append(f"claim #{claim['id']} is contradicted; do not use as positive support")

        manifest = {
            "schema_version": SCHEMA_VERSION,
            "snapshot_state": "CANONICAL_DB_EXPORT",
            "generated_at_utc": generated_at,
            "profile": PROFILE,
            "canonical_source": "ecu-kb/knowledge/kb.sqlite3 (local, not committed)",
            "logical_snapshot_sha256": sha256_json({
                "claims": claims,
                "retractions": retractions,
                "gaps": gaps,
                "conflicts": conflicts,
                "corpus": corpus,
                "a2l_logical_sha256": a2l_logical_sha256(c),
            }),
            "integrity": {
                "kb_check": "SKIPPED_EXPLICITLY" if skip_check else "PASSED",
                "export_warnings": warnings,
            },
            "epistemic_policy": {
                "support_states": sorted(SUPPORT_STATES),
                "negative_states": sorted(NEGATIVE_STATES),
                "non_support_evidence_kinds": sorted(NON_SUPPORT_KINDS),
                "rule": (
                    "Use epistemic_role=support for positive factual support; context requires explicit "
                    "qualification; negative records contradict rather than support a proposition."
                ),
            },
            "privacy_boundary": {
                "raw_corpus_exported": False,
                "sqlite_exported": False,
                "firmware_binaries_exported": False,
                "local_corpus_paths_exported": False,
                "corpus_metadata_exported": True,
                "citation_snippets_attached_to_claims": True,
                "retraction_history_exported": True,
            },
            "stats": collect_stats(c, claims, gaps),
            "files": files,
            "a2l_groups": a2l_groups,
            "consumer_entrypoint": "docs/CHATGPT-KB-BRIDGE.md",
        }
        write_json(out_dir / "manifest.json", manifest)
    finally:
        c.close()

    print(f"Published specialist snapshot: {out_dir / 'manifest.json'}")
    return 0


def snapshot_integrity(out_dir: Path) -> tuple[bool, list[str], dict]:
    manifest_path = out_dir / "manifest.json"
    if not manifest_path.is_file():
        return False, ["manifest.json"], {}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return False, ["manifest.json:invalid_json"], {}

    failures = []
    if manifest.get("snapshot_state") != "CANONICAL_DB_EXPORT":
        failures.append("manifest.json:snapshot_state")
    if manifest.get("integrity", {}).get("kb_check") != "PASSED":
        failures.append("manifest.json:kb_check")

    for info in manifest.get("files", {}).values():
        p = out_dir / info["path"]
        if not p.is_file() or sha256_file(p) != info["sha256"]:
            failures.append(info["path"])
    for info in manifest.get("a2l_groups", {}).values():
        p = out_dir / info["path"]
        if not p.is_file() or sha256_file(p) != info["sha256"]:
            failures.append(info["path"])

    return not failures, failures, manifest


def verify_snapshot(out_dir: Path) -> int:
    ok, failures, manifest = snapshot_integrity(out_dir)
    if not ok:
        print(json.dumps({"ok": False, "failed": failures}, ensure_ascii=False))
        return 2
    print(json.dumps({
        "ok": True,
        "snapshot_state": manifest.get("snapshot_state"),
        "generated_at_utc": manifest.get("generated_at_utc"),
        "stats": manifest.get("stats", {}),
    }, ensure_ascii=False))
    return 0

def search_snapshot(out_dir: Path, query: str, limit: int = 12) -> int:
    q = query.casefold()
    terms = [x for x in re.findall(r"[\w.-]+", q, flags=re.UNICODE) if len(x) >= 2]
    if not terms:
        terms = [q]

    def score(text: str) -> int:
        hay = (text or "").casefold()
        return sum(3 if t in hay else 0 for t in terms) + (8 if q in hay else 0)

    claims_data = json.loads((out_dir / "claims.json").read_text(encoding="utf-8"))
    gaps_data = json.loads((out_dir / "gaps.json").read_text(encoding="utf-8"))
    claim_hits = []
    for x in claims_data.get("claims", []):
        s = score(x.get("statement", "")) + score(x.get("missing_evidence", ""))
        if s:
            claim_hits.append((s, x))
    claim_hits.sort(key=lambda z: (-z[0], z[1].get("id", 0)))

    gap_hits = []
    for x in gaps_data.get("gaps", []):
        s = score(x.get("question", "")) + score(x.get("why_needed", "")) + score(x.get("needed_source", ""))
        if s:
            gap_hits.append((s, x))
    gap_hits.sort(key=lambda z: (-z[0], z[1].get("priority", 99), z[1].get("id", 0)))

    a2l_hits = []
    a2l_dir = out_dir / "a2l"
    # If query starts with a Bosch function prefix, scan that group first.
    token = next(iter(re.findall(r"[A-Za-z][A-Za-z0-9]+_", query)), None)
    preferred = []
    if token:
        group = token[:-1]
        p = a2l_dir / (safe_group_name(group) + ".json")
        if p.is_file():
            preferred.append(p)
    files = preferred or list(a2l_dir.glob("*.json"))
    for p in files:
        data = json.loads(p.read_text(encoding="utf-8"))
        for x in data.get("objects", []):
            text = " ".join(str(x.get(k) or "") for k in ("name", "description", "address", "func_group"))
            s = score(text)
            if s:
                a2l_hits.append((s, x))
    a2l_hits.sort(key=lambda z: (-z[0], z[1].get("name", "")))

    print(json.dumps({
        "query": query,
        "claims": [x for _, x in claim_hits[:limit]],
        "gaps": [x for _, x in gap_hits[:limit]],
        "a2l": [x for _, x in a2l_hits[:limit]],
    }, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Publish/query a read-only ECU-KB snapshot for remote AI clients")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("export", help="export canonical local SQLite state into ecu-kb/remote")
    p.add_argument("--db", type=Path, default=DB_PATH)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--skip-check", action="store_true", help="publish even if kb.py check was not run; not recommended")

    p = sub.add_parser("check", help="verify snapshot file hashes")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)

    p = sub.add_parser("query", help="query exported snapshot without SQLite")
    p.add_argument("query")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--limit", type=int, default=12)

    a = ap.parse_args()
    if a.cmd == "export":
        return export_snapshot(a.db, a.out, a.skip_check)
    if a.cmd == "check":
        return verify_snapshot(a.out)
    if a.cmd == "query":
        return search_snapshot(a.out, a.query, a.limit)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
