#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
specialist.py — evidence-oriented specialist for this EDC16U34 / BLS project.

Important architecture rule:
- technical facts come from the knowledge base / exported snapshot;
- this Python file contains retrieval and presentation logic only;
- no component identity, safe boost limit or symptom diagnosis is hard-coded here.

The specialist prefers the local SQLite DB. If the DB is unavailable, it can
read the generated read-only snapshot from ecu-kb/remote/.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

from remote_bridge import (
    DEFAULT_OUT,
    DB_PATH,
    epistemic_role,
    safe_group_name,
    snapshot_integrity,
)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

KB_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = Path("C:/Users/pavlo/.gemini/config/scripts")


def _terms(text: str) -> list[str]:
    parts = [x.casefold() for x in re.findall(r"[\w.-]+", text, flags=re.UNICODE) if len(x) >= 2]
    return parts or [text.casefold()]


def _score(text: str, terms: list[str], exact: str) -> int:
    hay = (text or "").casefold()
    return sum(3 for t in terms if t in hay) + (8 if exact and exact in hay else 0)


class DieselSpecialist:
    def __init__(self, db_path: Path = DB_PATH, snapshot_dir: Path = DEFAULT_OUT):
        self.db_path = Path(db_path)
        self.snapshot_dir = Path(snapshot_dir)
        self.conn: sqlite3.Connection | None = None
        self.snapshot_manifest: dict = {}
        self.mode = "sqlite" if self.db_path.is_file() else "snapshot"

        if self.mode == "sqlite":
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA foreign_keys = ON")
        else:
            required = [
                self.snapshot_dir / "manifest.json",
                self.snapshot_dir / "claims.json",
                self.snapshot_dir / "gaps.json",
            ]
            missing = [str(p) for p in required if not p.is_file()]
            if missing:
                raise FileNotFoundError(
                    "Neither local SQLite DB nor a complete remote snapshot is available. "
                    f"Missing: {', '.join(missing)}"
                )
            ok, failures, manifest = snapshot_integrity(self.snapshot_dir)
            if not ok:
                raise RuntimeError(
                    "Remote snapshot is not a verified canonical export: "
                    + ", ".join(failures)
                )
            self.snapshot_manifest = manifest

    def _claim_citations_sqlite(self, claim_id: int) -> list[dict]:
        assert self.conn is not None
        rows = self.conn.execute(
            """
            SELECT ci.locator, ci.quote, ci.verified_at,
                   d.rel_path AS document, d.sha256 AS document_sha256,
                   s.title AS source_title, s.tier, s.authority,
                   s.applicability, s.obtainability
            FROM citations ci
            JOIN documents d ON d.sha256 = ci.doc_sha256
            JOIN sources s ON s.id = d.source_id
            WHERE ci.claim_id = ?
            ORDER BY ci.id
            """,
            (claim_id,),
        ).fetchall()
        return [dict(x) for x in rows]

    def get_claims(self, query: str | None = None, limit: int = 12) -> list[dict]:
        terms = _terms(query or "")
        exact = (query or "").casefold().strip()

        if self.mode == "snapshot":
            data = json.loads((self.snapshot_dir / "claims.json").read_text(encoding="utf-8"))
            rows = data.get("claims", [])
            if not query:
                return rows[:limit]
            scored = []
            for row in rows:
                text = " ".join(str(row.get(k) or "") for k in ("statement", "missing_evidence", "turbo_model"))
                s = _score(text, terms, exact)
                if s:
                    scored.append((s, row))
            scored.sort(key=lambda z: (-z[0], z[1].get("id", 0)))
            return [r for _, r in scored[:limit]]

        assert self.conn is not None
        rows = self.conn.execute(
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
            row = dict(rr)
            if query:
                text = " ".join(str(row.get(k) or "") for k in ("statement", "missing_evidence", "turbo_model"))
                s = _score(text, terms, exact)
                if not s:
                    continue
            else:
                s = 0
            row["epistemic_role"] = epistemic_role(row)
            row["citations"] = self._claim_citations_sqlite(row["id"])
            out.append((s, row))

        out.sort(key=lambda z: (-z[0], z[1]["id"]))
        return [r for _, r in out[:limit]]

    def search_a2l_symbols(self, query: str, limit: int = 12) -> list[dict]:
        tokens = re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}", query)
        exact = query.casefold().strip()
        terms = _terms(query)

        if self.mode == "snapshot":
            a2l_dir = self.snapshot_dir / "a2l"
            files = []
            if tokens and "_" in tokens[0]:
                group = tokens[0].split("_", 1)[0]
                p = a2l_dir / (safe_group_name(group) + ".json")
                if p.is_file():
                    files = [p]
            if not files:
                files = list(a2l_dir.glob("*.json"))

            hits = []
            for p in files:
                data = json.loads(p.read_text(encoding="utf-8"))
                for row in data.get("objects", []):
                    text = " ".join(str(row.get(k) or "") for k in ("name", "description", "address", "func_group"))
                    s = _score(text, terms, exact)
                    if s:
                        hits.append((s, row))
            hits.sort(key=lambda z: (-z[0], z[1].get("name", "")))
            return [r for _, r in hits[:limit]]

        assert self.conn is not None
        token = tokens[0] if tokens else query.strip()
        rows = self.conn.execute(
            """
            SELECT sw_number, name, description, obj_type, kind, address,
                   record_layout, func_group, a2l_sha256
            FROM a2l_objects
            WHERE name LIKE ? OR description LIKE ? OR address = ?
            ORDER BY CASE WHEN name = ? THEN 0 WHEN name LIKE ? THEN 1 ELSE 2 END, name
            LIMIT ?
            """,
            (f"%{token}%", f"%{token}%", token, token, f"{token}%", limit),
        ).fetchall()
        return [dict(x) for x in rows]

    def search_literature_chunks(self, query: str, limit: int = 5) -> list[dict]:
        # Raw literature chunks are deliberately not present in the GitHub snapshot.
        if self.mode != "sqlite":
            return []

        assert self.conn is not None
        try:
            rows = self.conn.execute(
                """
                SELECT ch.id, ch.page_from, ch.page_to, ch.content,
                       d.rel_path, s.obtainability, s.tier, s.applicability
                FROM chunks_fts f
                JOIN chunks ch ON ch.id = f.rowid
                JOIN documents d ON d.id = ch.document_id
                JOIN sources s ON s.id = d.source_id
                WHERE chunks_fts MATCH ?
                ORDER BY bm25(chunks_fts) +
                         CASE s.obtainability WHEN 'PROJECT_DRAFT' THEN 5.0 ELSE 0 END
                LIMIT ?
                """,
                (query, limit),
            ).fetchall()
            return [dict(x) for x in rows]
        except sqlite3.OperationalError:
            rows = self.conn.execute(
                """
                SELECT ch.id, ch.page_from, ch.page_to, ch.content,
                       d.rel_path, s.obtainability, s.tier, s.applicability
                FROM chunks ch
                JOIN documents d ON d.id = ch.document_id
                JOIN sources s ON s.id = d.source_id
                WHERE ch.content LIKE ?
                LIMIT ?
                """,
                (f"%{query}%", limit),
            ).fetchall()
            return [dict(x) for x in rows]

    def get_gaps(self, query: str | None = None, limit: int = 8) -> list[dict]:
        if self.mode == "snapshot":
            data = json.loads((self.snapshot_dir / "gaps.json").read_text(encoding="utf-8"))
            rows = data.get("gaps", [])
        else:
            assert self.conn is not None
            rows = [dict(x) for x in self.conn.execute(
                "SELECT * FROM gaps ORDER BY priority ASC, id ASC"
            ).fetchall()]

        if not query:
            return rows[:limit]

        terms = _terms(query)
        exact = query.casefold().strip()
        hits = []
        for row in rows:
            text = " ".join(str(row.get(k) or "") for k in ("question", "why_needed", "needed_source"))
            s = _score(text, terms, exact)
            if s:
                hits.append((s, row))
        hits.sort(key=lambda z: (-z[0], z[1].get("priority", 99), z[1].get("id", 0)))
        return [r for _, r in hits[:limit]]

    def evaluate_hypothesis(self, text: str) -> list[dict]:
        """Routing warnings only. This function intentionally contains no project facts."""
        lower = text.casefold()
        checks = []

        if any(x in lower for x in ("stage 1", "stage 2", "тюнінг", "прошити", "chip tuning")):
            checks.append({
                "verdict": "EVIDENCE_AND_PREFLIGHT_REQUIRED",
                "topic": "Firmware modification",
                "explanation": (
                    "Do not derive a calibration change from the question itself. "
                    "Check current claims/gaps, component evidence and flash-preflight state first."
                ),
            })

        if any(x in lower for x in ("2.4", "2.5", "2.6", "2400", "2500", "2600")) and any(
            x in lower for x in ("наддув", "тиск", "boost", "mbar", "бар")
        ):
            checks.append({
                "verdict": "COMPONENT_LIMIT_EVIDENCE_REQUIRED",
                "topic": "Turbocharger physical limit",
                "explanation": (
                    "A requested/calibrated pressure is not proof of a safe component limit. "
                    "Use a matching compressor/component source or an explicit verified claim."
                ),
            })

        if "garrett" in lower and any(x in lower for x in ("турб", "turbo", "bls", "bv39")):
            checks.append({
                "verdict": "IDENTITY_EVIDENCE_REQUIRED",
                "topic": "Turbocharger identity",
                "explanation": (
                    "Resolve component identity from current measured/corroborated claims; "
                    "do not use a hard-coded model assumption from this program."
                ),
            })

        return checks

    def consult(self, question: str, engine: str = "local") -> str:
        claims = self.get_claims(question, limit=8)
        a2l_hits = self.search_a2l_symbols(question, limit=8)
        gaps = self.get_gaps(question, limit=6)
        chunks = self.search_literature_chunks(question, limit=3)
        routing = self.evaluate_hypothesis(question)

        snapshot_age = ""
        if self.mode == "snapshot":
            snapshot_age = f" | snapshot={self.snapshot_manifest.get('generated_at_utc', 'unknown')}"
        report = [
            "═══════════════════════════════════════════════════════════════════",
            f" EDC16U34 / BLS SPECIALIST — evidence mode: {self.mode}{snapshot_age}",
            "═══════════════════════════════════════════════════════════════════",
            f"QUERY: {question}",
            "",
        ]

        if routing:
            report.append("── ROUTING / SAFETY OF INFERENCE ──")
            for item in routing:
                report.append(f"• [{item['verdict']}] {item['topic']}: {item['explanation']}")
            report.append("")

        report.append("── CURRENT CLAIMS ──")
        if claims:
            for c in claims:
                role = c.get("epistemic_role") or epistemic_role(c)
                report.append(
                    f"• #{c.get('id')} [{role}|{c.get('evidence_kind')}|{c.get('verification_state')}] "
                    f"{c.get('statement')}"
                )
                if c.get("missing_evidence"):
                    report.append(f"  missing evidence: {c['missing_evidence']}")
                for ci in (c.get("citations") or [])[:2]:
                    report.append(
                        f"  source: {ci.get('source_title') or ci.get('document')} "
                        f"({ci.get('locator')})"
                    )
        else:
            report.append("  No matching current claim.")
        report.append("")

        report.append("── A2L ──")
        if a2l_hits:
            for s in a2l_hits:
                report.append(
                    f"• {s.get('address') or '-'} [{s.get('kind')}/{s.get('obj_type')}] "
                    f"{s.get('name')}: {s.get('description') or ''}"
                )
        else:
            report.append("  No matching A2L object.")
        report.append("")

        report.append("── RELEVANT GAPS ──")
        if gaps:
            for g in gaps:
                report.append(
                    f"• #{g.get('id')} [{g.get('status')}|P{g.get('priority')}] {g.get('question')}"
                )
        else:
            report.append("  No matching gap.")
        report.append("")

        if chunks:
            report.append("── LOCAL LITERATURE CHUNKS ──")
            for ch in chunks:
                tag = " [PROJECT_DRAFT]" if ch.get("obtainability") == "PROJECT_DRAFT" else ""
                clean = " ".join((ch.get("content") or "")[:260].split())
                report.append(
                    f"• {ch.get('rel_path')} p.{ch.get('page_from')}{tag}: {clean}…"
                )
            report.append("")

        support_n = sum((c.get("epistemic_role") or epistemic_role(c)) == "support" for c in claims)
        negative_n = sum((c.get("epistemic_role") or epistemic_role(c)) == "negative" for c in claims)
        open_gap_n = sum(g.get("status") in {"OPEN", "RESEARCHING", "PARTIAL"} for g in gaps)

        report.append("── EVIDENCE SUMMARY ──")
        report.append(
            f"support claims={support_n}; negative claims={negative_n}; "
            f"relevant unresolved gaps={open_gap_n}; A2L hits={len(a2l_hits)}"
        )
        if not claims and not a2l_hits and not chunks:
            report.append("Evidence is insufficient. Create/research a GAP instead of guessing.")
        elif open_gap_n:
            report.append("Answer must preserve the unresolved limitations above.")
        else:
            report.append("Use only the evidence states shown above; do not upgrade confidence implicitly.")

        local_output = "\n".join(report)

        if engine == "local":
            return local_output
        if engine in ("codex", "claude"):
            return self._delegate_llm(question, local_output, engine)
        return local_output

    def _delegate_llm(self, question: str, evidence_report: str, engine: str) -> str:
        prompt = f"""
[EVIDENCE AUDIT — EDC16U34/BLS]
User question: {question}

CURRENT RETRIEVED EVIDENCE:
{evidence_report}

RULES:
1. Treat support/context/negative as distinct epistemic roles.
2. Do not invent component limits, A2L semantics or causal diagnoses.
3. If a relevant GAP is unresolved, preserve it in the conclusion.
4. Do not use this Python program as a factual source.
"""
        script = SCRIPTS_DIR / ("Invoke-Codex.ps1" if engine == "codex" else "Invoke-Claude.ps1")
        if not script.is_file():
            return f"{evidence_report}\n\n[Delegation unavailable: {script} not found]"

        mode = "audit" if engine == "codex" else "debug"
        cmd = [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(script), "-Mode", mode, "-Prompt", prompt,
        ]
        try:
            res = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120,
                encoding="utf-8", errors="replace"
            )
            body = res.stdout if res.returncode == 0 else (res.stdout + "\n" + res.stderr)
            return f"{evidence_report}\n\n── {engine.upper()} SYNTHESIS ──\n{body.strip()}"
        except Exception as exc:
            return f"{evidence_report}\n\n[Delegation error: {exc}]"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evidence-oriented specialist for VW Golf 5 BLS / EDC16U34"
    )
    parser.add_argument("query", help="question or hypothesis")
    parser.add_argument("--engine", choices=["local", "codex", "claude"], default="local")
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    spec = DieselSpecialist(snapshot_dir=args.snapshot)
    print(spec.consult(args.query, engine=args.engine))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
