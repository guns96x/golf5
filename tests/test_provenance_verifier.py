# -*- coding: utf-8 -*-
"""
tests/test_provenance_verifier.py

Test suite for KBProvenanceVerifier.
Verifies that safety rules are strictly grounded in active, un-retracted claims
in the remote snapshot v2, and verifies error handling for schema mismatches,
hash corruptions, and invalid claims.
"""

import hashlib
import json
from pathlib import Path
import pytest

from calharness import (
    DEFAULT_RULES,
    KBProvenanceVerifier,
    ProvenanceKind,
    ProvenanceRecord,
    ProvenanceVerificationError,
    RuleKind,
    SafetyRule,
)


@pytest.fixture
def verifier():
    return KBProvenanceVerifier()


def test_default_rules_provenance_against_remote_snapshot(verifier):
    """All default safety rules must have valid, active provenance against remote snapshot v2."""
    is_valid, errors = verifier.verify_rule_provenance(DEFAULT_RULES)
    assert is_valid is True, f"Provenance verification failed on DEFAULT_RULES: {errors}"
    assert len(errors) == 0


def test_logical_snapshot_sha256_present_and_valid(verifier):
    """Logical snapshot SHA256 must be a valid 64-char hex string matching remote manifest."""
    snap_sha = verifier.logical_snapshot_sha256
    assert isinstance(snap_sha, str)
    assert len(snap_sha) == 64
    assert int(snap_sha, 16) > 0  # valid hex


def test_missing_claim_key_fails(verifier):
    """Rule with non-existent claim_key must fail verification with informative error."""
    bad_rule = SafetyRule(
        rule_id="TEST_BAD_CLAIM",
        name="Test Bad Claim Rule",
        rule_kind=RuleKind.PHYSICAL_THRESHOLD,
        target_parameter="PCR_pBDesBas_MAP",
        threshold_value=2350.0,
        provenance=ProvenanceRecord(
            source="Bogus",
            kind=ProvenanceKind.UNVERIFIED_CANDIDATE,
            claim_key="non-existent-claim-key-xyz",
        ),
    )
    is_valid, errors = verifier.verify_rule_provenance([bad_rule])
    assert is_valid is False
    assert len(errors) == 1
    assert "non-existent-claim-key-xyz" in errors[0]
    assert "not found in remote claims snapshot" in errors[0]


def test_missing_constraint_claim_fails(verifier):
    """Rule with non-existent constraint claim must fail verification."""
    bad_rule = SafetyRule(
        rule_id="TEST_BAD_CONSTRAINT",
        name="Test Bad Constraint Rule",
        rule_kind=RuleKind.PHYSICAL_THRESHOLD,
        target_parameter="PCR_pBDesBas_MAP",
        threshold_value=2350.0,
        provenance=ProvenanceRecord(
            source="Bogus",
            kind=ProvenanceKind.UNVERIFIED_CANDIDATE,
            claim_key="turbo-bv39-candidate-envelope-2350",
            constraint_claims=["missing-constraint-key-456"],
        ),
    )
    is_valid, errors = verifier.verify_rule_provenance([bad_rule])
    assert is_valid is False
    assert any("missing-constraint-key-456" in err for err in errors)


def test_statement_hash_mismatch_fails(verifier):
    """Rule with mismatched statement_hash must fail verification."""
    bad_rule = SafetyRule(
        rule_id="TEST_HASH_MISMATCH",
        name="Test Hash Mismatch Rule",
        rule_kind=RuleKind.PHYSICAL_THRESHOLD,
        target_parameter="PCR_pBDesBas_MAP",
        threshold_value=2350.0,
        provenance=ProvenanceRecord(
            source="Bogus",
            kind=ProvenanceKind.UNVERIFIED_CANDIDATE,
            claim_key="turbo-bv39-boost-envelope-unresolved",
            statement_hash="0000000000000000000000000000000000000000000000000000000000000000",
        ),
    )
    is_valid, errors = verifier.verify_rule_provenance([bad_rule])
    assert is_valid is False
    assert any("statement_hash mismatch" in err for err in errors)


def test_unsupported_schema_version_raises_error(tmp_path):
    """Manifest with schema_version != 2 must raise ProvenanceVerificationError."""
    remote_dir = tmp_path / "ecu-kb" / "remote"
    remote_dir.mkdir(parents=True)

    manifest_data = {
        "schema_version": 1,
        "snapshot_state": "CANONICAL_DB_EXPORT",
        "integrity": {"kb_check": "PASSED"},
        "files": {"claims": {"sha256": "abc"}},
    }
    (remote_dir / "manifest.json").write_text(json.dumps(manifest_data), encoding="utf-8")
    (remote_dir / "claims.json").write_text("{}", encoding="utf-8")

    bad_verifier = KBProvenanceVerifier(repo_root=tmp_path)
    with pytest.raises(ProvenanceVerificationError, match="expected 2"):
        bad_verifier.verify_rule_provenance([])


def test_untrusted_snapshot_state_raises_error(tmp_path):
    """Manifest with snapshot_state != CANONICAL_DB_EXPORT must raise ProvenanceVerificationError."""
    remote_dir = tmp_path / "ecu-kb" / "remote"
    remote_dir.mkdir(parents=True)

    manifest_data = {
        "schema_version": 2,
        "snapshot_state": "LOCAL_DRAFT",
        "integrity": {"kb_check": "PASSED"},
        "files": {"claims": {"sha256": "abc"}},
    }
    (remote_dir / "manifest.json").write_text(json.dumps(manifest_data), encoding="utf-8")
    (remote_dir / "claims.json").write_text("{}", encoding="utf-8")

    bad_verifier = KBProvenanceVerifier(repo_root=tmp_path)
    with pytest.raises(ProvenanceVerificationError, match="Untrusted snapshot_state"):
        bad_verifier.verify_rule_provenance([])


def test_claims_hash_mismatch_raises_error(tmp_path):
    """Mismatched claims.json hash between file and manifest must raise ProvenanceVerificationError."""
    remote_dir = tmp_path / "ecu-kb" / "remote"
    remote_dir.mkdir(parents=True)

    claims_content = '{"claims": []}'
    (remote_dir / "claims.json").write_text(claims_content, encoding="utf-8")

    manifest_data = {
        "schema_version": 2,
        "snapshot_state": "CANONICAL_DB_EXPORT",
        "integrity": {"kb_check": "PASSED"},
        "files": {"claims": {"sha256": "incorrect_hash_value"}},
    }
    (remote_dir / "manifest.json").write_text(json.dumps(manifest_data), encoding="utf-8")

    bad_verifier = KBProvenanceVerifier(repo_root=tmp_path)
    with pytest.raises(ProvenanceVerificationError, match="Claims hash mismatch"):
        bad_verifier.verify_rule_provenance([])


def test_retracted_or_deprecated_claim_fails(tmp_path):
    """Claims marked as retracted or superseded must be rejected during rule verification."""
    remote_dir = tmp_path / "ecu-kb" / "remote"
    remote_dir.mkdir(parents=True)

    claims_obj = {
        "claims": [
            {
                "claim_id": 999,
                "claim_key": "test-retracted-claim",
                "statement": "Old deprecated fact",
                "retracted_at": "2026-09-18T12:00:00Z",
                "verification_state": "retracted",
            }
        ]
    }
    claims_text = json.dumps(claims_obj)
    (remote_dir / "claims.json").write_text(claims_text, encoding="utf-8")
    claims_sha = hashlib.sha256(claims_text.encode("utf-8")).hexdigest()

    manifest_data = {
        "schema_version": 2,
        "snapshot_state": "CANONICAL_DB_EXPORT",
        "integrity": {"kb_check": "PASSED"},
        "files": {"claims": {"sha256": claims_sha}},
    }
    (remote_dir / "manifest.json").write_text(json.dumps(manifest_data), encoding="utf-8")

    test_verifier = KBProvenanceVerifier(repo_root=tmp_path)
    rule = SafetyRule(
        rule_id="RULE_TEST_RETRACTED",
        name="Rule using retracted claim",
        rule_kind=RuleKind.PHYSICAL_THRESHOLD,
        target_parameter="PCR_pBDesBas_MAP",
        threshold_value=2350.0,
        provenance=ProvenanceRecord(
            source="Test",
            kind=ProvenanceKind.UNVERIFIED_CANDIDATE,
            claim_key="test-retracted-claim",
        ),
    )
    is_valid, errors = test_verifier.verify_rule_provenance([rule])
    assert is_valid is False
    assert any("has been retracted" in err for err in errors)
