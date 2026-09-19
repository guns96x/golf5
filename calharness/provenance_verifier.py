# -*- coding: utf-8 -*-
"""
calharness.provenance_verifier

Strict KB Provenance Verifier:
Validates safety rules against the git-tracked remote specialist snapshot (v2) in CI
and optionally against canonical local SQLite when available.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from calharness.rules import SafetyRule


class ProvenanceVerificationError(Exception):
    """Raised when provenance verification fails against the canonical KB or remote snapshot."""
    pass


class KBProvenanceVerifier:
    """
    Verifies that all safety rules and candidate thresholds with claim keys or constraint
    claims are strictly grounded in active, un-retracted claims in the knowledge base.
    """

    def __init__(self, repo_root: Optional[Path] = None):
        if repo_root is None:
            self.repo_root = Path(__file__).resolve().parent.parent
        else:
            self.repo_root = Path(repo_root)

        self.remote_dir = self.repo_root / "ecu-kb" / "remote"
        self.manifest_path = self.remote_dir / "manifest.json"
        self.claims_path = self.remote_dir / "claims.json"
        self.db_path = self.repo_root / "ecu-kb" / "knowledge" / "kb.sqlite3"

        self._manifest: Optional[Dict[str, Any]] = None
        self._claims_by_key: Optional[Dict[str, Dict[str, Any]]] = None

    def _load_and_verify_remote_snapshot(self) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
        if not self.manifest_path.exists():
            raise ProvenanceVerificationError(f"Remote snapshot manifest missing at {self.manifest_path}")
        if not self.claims_path.exists():
            raise ProvenanceVerificationError(f"Remote snapshot claims missing at {self.claims_path}")

        with open(self.manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        if manifest.get("schema_version") != 2:
            raise ProvenanceVerificationError(
                f"Unsupported remote snapshot schema_version {manifest.get('schema_version')}; expected 2"
            )
        if manifest.get("snapshot_state") != "CANONICAL_DB_EXPORT":
            raise ProvenanceVerificationError(
                f"Untrusted snapshot_state '{manifest.get('snapshot_state')}'; expected CANONICAL_DB_EXPORT"
            )
        integrity = manifest.get("integrity", {})
        if integrity.get("kb_check") != "PASSED":
            raise ProvenanceVerificationError(
                f"Remote snapshot integrity failed: kb_check is '{integrity.get('kb_check')}', expected PASSED"
            )

        files_entry = manifest.get("files", {})
        claims_meta = files_entry.get("claims")
        if not claims_meta or "sha256" not in claims_meta:
            raise ProvenanceVerificationError("Manifest missing files.claims.sha256 entry")

        expected_claims_sha = claims_meta["sha256"]
        actual_claims_sha = hashlib.sha256(self.claims_path.read_bytes()).hexdigest()
        if actual_claims_sha != expected_claims_sha:
            raise ProvenanceVerificationError(
                f"Claims hash mismatch! Manifest expected {expected_claims_sha}, computed {actual_claims_sha}"
            )

        with open(self.claims_path, "r", encoding="utf-8") as f:
            claims_data = json.load(f)

        raw_claims = claims_data.get("claims", [])
        claims_by_key = {}
        for c in raw_claims:
            key = c.get("claim_key")
            if key:
                claims_by_key[key] = c

        self._manifest = manifest
        self._claims_by_key = claims_by_key
        return manifest, claims_by_key

    @property
    def logical_snapshot_sha256(self) -> str:
        if self._manifest is None:
            self._load_and_verify_remote_snapshot()
        return self._manifest.get("logical_snapshot_sha256", "")

    def verify_rule_provenance(self, rules: List[SafetyRule]) -> Tuple[bool, List[str]]:
        """
        Verify every rule's claim_key and constraint_claims against the verified remote snapshot.
        Returns (is_valid, list_of_errors).
        """
        if self._claims_by_key is None:
            self._load_and_verify_remote_snapshot()

        errors = []
        for rule in rules:
            prov = rule.provenance

            if prov.claim_key:
                if prov.claim_key not in self._claims_by_key:
                    errors.append(
                        f"Rule '{rule.rule_id}': claim_key '{prov.claim_key}' not found in remote claims snapshot."
                    )
                else:
                    claim = self._claims_by_key[prov.claim_key]
                    if claim.get("retracted_at") is not None:
                        errors.append(
                            f"Rule '{rule.rule_id}': claim '{prov.claim_key}' has been retracted on {claim.get('retracted_at')}."
                        )
                    if claim.get("verification_state") in ("deprecated", "superseded"):
                        errors.append(
                            f"Rule '{rule.rule_id}': claim '{prov.claim_key}' is {claim.get('verification_state')}."
                        )
                    if prov.statement_hash:
                        statement = claim.get("statement", "")
                        stmt_hash = hashlib.sha256(statement.encode("utf-8")).hexdigest()
                        if stmt_hash != prov.statement_hash:
                            errors.append(
                                f"Rule '{rule.rule_id}': statement_hash mismatch for claim '{prov.claim_key}'."
                            )

            for constraint_key in prov.constraint_claims:
                if constraint_key not in self._claims_by_key:
                    errors.append(
                        f"Rule '{rule.rule_id}': constraint claim '{constraint_key}' not found in remote claims snapshot."
                    )
                else:
                    c_claim = self._claims_by_key[constraint_key]
                    if c_claim.get("retracted_at") is not None:
                        errors.append(
                            f"Rule '{rule.rule_id}': constraint claim '{constraint_key}' has been retracted."
                        )
                    if c_claim.get("verification_state") in ("deprecated", "superseded"):
                        errors.append(
                            f"Rule '{rule.rule_id}': constraint claim '{constraint_key}' is {c_claim.get('verification_state')}."
                        )

        return (len(errors) == 0, errors)
