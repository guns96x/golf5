#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools.kb_a2l_doc_linter

Engineering Documentation Linter:
Validates ECU documentation (Markdown files, tables, and Mermaid diagrams) against:
1. Exact A2L ASAP2 symbol naming in Bosch EDC16U34 P447_HAXN database.
2. Conceptual alias syntax for intentional generalizations:
   <!-- conceptual-alias: MoF_trqDes_MAP -> AccPed_trqEng*_MAP (Driver wish family) -->
3. Controlled Epistemic Tags Vocabulary:
   Every physical engineering assertion (boost, torque, power, airflow, cylinder pressure,
   duration, EGT, smoke limit) MUST include a controlled epistemic tag:
     [MODELLED]
     [UNVERIFIED_CANDIDATE]
     [HEURISTIC]
     [CONTEXT]
     [VERIFIED_PROJECT]
     [VERIFIED_OEM_SPEC]
"""

from __future__ import annotations

import argparse
import glob
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Candidate A2L identifier: starts with uppercase, has underscore, alphanumeric + underscore
RE_CANDIDATE_A2L = re.compile(r"^[A-Z][A-Za-z0-9]{2,}_[A-Za-z0-9_]{2,}$")

# Physical assertions with units requiring epistemic tagging
RE_PHYSICAL_CLAIM = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:mbar|hPa|bar|бар|Nm|Нм|hp|к\.с\.|kW|кВт|kg/s|кг/с|°C|ATDC|BTDC|mg/hub|мг/такт|mg/stroke|rpm|об/хв)\b",
    re.IGNORECASE,
)

# Conceptual alias comment pattern
RE_CONCEPTUAL_ALIAS = re.compile(
    r"<!--\s*conceptual-alias:\s*([A-Za-z0-9_]+)(?:\s*->\s*([^\s-]+))?(?:\s*\(([^)]+)\))?\s*-->"
)

# Controlled vocabulary of epistemic qualifiers
CONTROLLED_EPISTEMIC_TAGS = {
    "[MODELLED]",
    "[UNVERIFIED_CANDIDATE]",
    "[HEURISTIC]",
    "[CONTEXT]",
    "[VERIFIED_PROJECT]",
    "[VERIFIED_OEM_SPEC]",
}

KNOWN_NON_A2L_EXCLUSIONS = {
    "P447_HAXN",
    "VAG_EDC16",
    "EDC16_U34",
    "BOSCH_EDC16",
    "CAN_BUS",
    "KWP_2000",
    "ISO_14230",
    "SAE_J1979",
    "GIT_COMMIT",
    "WOT_PULL",
}


class LintFinding:
    def __init__(self, file_path: Path, line_no: int, kind: str, message: str):
        self.file_path = file_path
        self.line_no = line_no
        self.kind = kind
        self.message = message

    def __str__(self) -> str:
        return f"{self.file_path}:{self.line_no} [{self.kind}] {self.message}"


class A2LDocLinter:
    def __init__(self, a2l_symbols: Optional[Set[str]] = None):
        self.a2l_symbols = a2l_symbols if a2l_symbols is not None else self._load_a2l_symbols()

    @staticmethod
    def _load_a2l_symbols() -> Set[str]:
        """Load all valid symbol names from A2LCatalog."""
        try:
            from calharness.a2l_catalog import A2LCatalog
            from pya2l import model
            catalog = A2LCatalog()
            symbols = set()
            for r in catalog.session.query(model.Characteristic.name).all():
                symbols.add(r[0])
            for r in catalog.session.query(model.AxisPts.name).all():
                symbols.add(r[0])
            for r in catalog.session.query(model.Measurement.name).all():
                symbols.add(r[0])
            for r in catalog.session.query(model.CompuMethod.name).all():
                symbols.add(r[0])
            # FUNCTION names are first-class A2L symbols. This A2L defines 486 of
            # them and they carry the authoritative Bosch functional decomposition
            # (PCR_DesValCalc "Ladedruck Sollwertbildung", FlMng_InjMassLim, ...).
            # Omitting them made the linter reject correct references to functions.
            try:
                for r in catalog.session.query(model.Function.name).all():
                    symbols.add(r[0])
            except Exception:
                pass
            return symbols
        except Exception as e:
            # Fallback: scan raw A2L text directly if database unavailable
            a2l_path = Path("diagnostic-review/definitions/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.a2l")
            if a2l_path.exists():
                text = a2l_path.read_text(encoding="latin-1", errors="ignore")
                matches = set(re.findall(r"/begin\s+(?:CHARACTERISTIC|AXIS_PTS|MEASUREMENT|FUNCTION)\s+([A-Za-z0-9_]+)\b", text))
                return matches
            return set()

    def lint_file(self, path: Path) -> List[LintFinding]:
        findings: List[LintFinding] = []
        if not path.exists():
            return [LintFinding(path, 0, "FILE_NOT_FOUND", f"Target file not found: {path}")]

        content = path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()

        # Step 1: Parse conceptual aliases defined in the file
        aliases: Set[str] = set()
        for alias_match in RE_CONCEPTUAL_ALIAS.finditer(content):
            alias_name = alias_match.group(1)
            aliases.add(alias_name)

        in_code_block = False
        is_mermaid_block = False

        for i, line in enumerate(lines, start=1):
            stripped = line.strip()

            if stripped.startswith("```"):
                if in_code_block:
                    in_code_block = False
                    is_mermaid_block = False
                else:
                    in_code_block = True
                    is_mermaid_block = "mermaid" in stripped.lower()
                continue

            # Skip markdown table separator lines (e.g. | :--- | :---: |)
            if re.match(r"^\s*\|?\s*:?-+:?\s*\|", stripped):
                continue

            # Candidate tokens for A2L symbol check
            candidate_tokens: List[Tuple[str, str]] = []

            if in_code_block and is_mermaid_block:
                # Extract quoted labels in Mermaid nodes
                node_labels = re.findall(r'\["([^"]+)"\]|\("([^"]+)"\)|{"([^"]+)"}', line)
                for groups in node_labels:
                    label_text = next(g for g in groups if g)
                    # Split label text into words/tokens
                    for word in re.findall(r"[A-Za-z0-9_]+", label_text):
                        if RE_CANDIDATE_A2L.match(word):
                            candidate_tokens.append((word, "Mermaid diagram node"))
            elif not in_code_block:
                # Extract backticked words in regular markdown
                backticks = re.findall(r"`([^`]+)`", line)
                for b in backticks:
                    clean_b = b.strip()
                    if RE_CANDIDATE_A2L.match(clean_b):
                        candidate_tokens.append((clean_b, "inline backtick"))

            # Check candidate tokens against A2L catalog and conceptual aliases
            for token, source_ctx in candidate_tokens:
                if token in aliases or token in KNOWN_NON_A2L_EXCLUSIONS:
                    continue
                # Handle wildcard patterns like AccPed_trqEng*_MAP if alias
                if any(re.match(r"^" + a.replace("*", ".*") + r"$", token) for a in aliases):
                    continue

                if self.a2l_symbols and token not in self.a2l_symbols:
                    findings.append(
                        LintFinding(
                            path,
                            i,
                            "UNKNOWN_A2L_SYMBOL",
                            (
                                f"Symbol '{token}' ({source_ctx}) not found in A2L database P447_HAXN. "
                                "Use exact Bosch A2L name or declare conceptual alias via "
                                f"<!-- conceptual-alias: {token} -> TargetA2L (reason) -->."
                            ),
                        )
                    )

            # Check epistemic labeling for physical assertions
            # Only check non-code-block lines, non-headings, and table data rows
            if not in_code_block and not stripped.startswith("#"):
                # Ignore markdown image lines, links without claims, etc.
                if RE_PHYSICAL_CLAIM.search(line):
                    # Check if line contains one of the controlled epistemic tags
                    has_epistemic_tag = any(tag in line for tag in CONTROLLED_EPISTEMIC_TAGS)
                    # Also permit explicit references to formal Claims: e.g., Claim #83 or Claim #71
                    has_claim_ref = bool(re.search(r"\bClaim\s*#\d+\b", line, re.IGNORECASE))
                    # Also permit table headers or metadata lines
                    is_header_row = stripped.startswith("|") and ("Параметр" in line or "Parameter" in line)

                    if not (has_epistemic_tag or has_claim_ref or is_header_row):
                        findings.append(
                            LintFinding(
                                path,
                                i,
                                "UNQUALIFIED_PHYSICAL_CLAIM",
                                (
                                    "Physical engineering assertion on this line lacks a controlled epistemic qualifier. "
                                    f"Must include one of {sorted(CONTROLLED_EPISTEMIC_TAGS)} or cite a formal Claim #id."
                                ),
                            )
                        )

        return findings


def main():
    parser = argparse.ArgumentParser(description="A2L and Epistemic Documentation Linter")
    parser.add_argument("target", help="File path or glob pattern to lint")
    parser.add_argument("--strict", action="store_true", help="Exit with non-zero status on lint findings")
    args = parser.parse_args()

    target_pattern = args.target
    matched_paths = [Path(p) for p in glob.glob(target_pattern, recursive=True)]
    if not matched_paths and Path(target_pattern).exists():
        matched_paths = [Path(target_pattern)]

    if not matched_paths:
        print(f"No files matched target pattern: {target_pattern}")
        sys.exit(1 if args.strict else 0)

    linter = A2LDocLinter()
    print(f"Loaded {len(linter.a2l_symbols):,} A2L symbols for verification.")

    total_findings = 0
    for p in matched_paths:
        findings = linter.lint_file(p)
        if findings:
            total_findings += len(findings)
            print(f"\n[!] Findings in {p} ({len(findings)} issues):")
            for f in findings:
                print(f"  Line {f.line_no}: [{f.kind}] {f.message}")
        else:
            print(f"[OK] {p}: All symbols and epistemic qualifiers verified.")

    if total_findings > 0 and args.strict:
        print(f"\nStrict lint failed with {total_findings} total issue(s).")
        sys.exit(1)

    print(f"\nLint complete: {total_findings} finding(s) reported.")
    sys.exit(0)


if __name__ == "__main__":
    main()
