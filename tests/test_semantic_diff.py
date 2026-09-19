# -*- coding: utf-8 -*-
"""
tests/test_semantic_diff.py

Comprehensive test suite for SemanticDiffEngine and SafetyValidator.
Verifies byte classification, A2L ownership, and safety invariant enforcement.
"""

from pathlib import Path
import numpy as np
import pytest

from calharness import (
    ByteCategory,
    MapDecoder,
    SafetyLevel,
    SafetyValidator,
    SemanticDiffEngine,
)

STOCK_BIN_PATH = Path("knowledge/08_firmware/originals/03G906021QJ_1984_391847_full_stock.bin")


@pytest.fixture(scope="module")
def stock_bytes():
    if not STOCK_BIN_PATH.exists():
        pytest.skip(f"Stock binary not found at {STOCK_BIN_PATH} (proprietary dump not in git)")
    with open(STOCK_BIN_PATH, "rb") as f:
        return f.read()


@pytest.fixture(scope="module")
def engine():
    return SemanticDiffEngine()


@pytest.fixture(scope="module")
def validator():
    return SafetyValidator()


def test_diff_identical_bins_produces_zero_changes(engine, validator, stock_bytes):
    report = engine.compare(stock_bytes, stock_bytes)
    assert report.total_bytes_changed == 0
    assert report.is_clean_calibration is True
    assert len(report.maps_changed) == 0

    audit = validator.validate(report)
    assert audit.is_safe is True
    assert audit.overall_verdict == SafetyLevel.PASS
    assert audit.hard_fails_count == 0


def test_diff_known_map_modification_classification(engine, validator, stock_bytes):
    # Modify 1 cell in PCR_pBDesBas_MAP (0x1EB0B2)
    # Header: 4 bytes, X-axis: 32 bytes, Y-axis: 20 bytes -> Values start @ 0x1EB0F2
    mod_bytes = bytearray(stock_bytes)
    cell_offset = 0x1EB0F2 + 20  # row 1, col 0
    mod_bytes[cell_offset : cell_offset + 2] = (2150).to_bytes(2, "big", signed=True)

    report = engine.compare(stock_bytes, bytes(mod_bytes))
    assert report.total_bytes_changed == 2
    assert report.code_area_bytes == 0
    assert report.identity_area_bytes == 0
    assert report.unmapped_bytes == 0
    assert report.is_clean_calibration is True

    # Verify classification
    assert len(report.classified_diffs) == 2
    for d in report.classified_diffs:
        assert d.category == ByteCategory.MAP_VALUE
        assert d.owner_symbol == "PCR_pBDesBas_MAP"

    # Verify map summary
    assert len(report.maps_changed) == 1
    m = report.maps_changed[0]
    assert m.name == "PCR_pBDesBas_MAP"
    assert m.changed_cells_count == 1
    assert m.changed_cells[0].new_phys == 2150.0

    # Safety validation: structurally sound, but epistemic verdict is UNVERIFIED because boost ceiling is unproven
    audit = validator.validate(report)
    assert audit.is_structurally_sound is True
    assert audit.is_safe is False
    assert audit.overall_verdict == SafetyLevel.UNVERIFIED


def test_diff_map_axis_modification_classification(engine, stock_bytes):
    # Modify X-axis node in PCR_pBDesBas_MAP (0x1EB0B2)
    # X-axis spans [0x1EB0B6 .. 0x1EB0D6)
    mod_bytes = bytearray(stock_bytes)
    axis_offset = 0x1EB0B6 + 4  # node 2
    mod_bytes[axis_offset : axis_offset + 2] = (1050).to_bytes(2, "big", signed=True)

    report = engine.compare(stock_bytes, bytes(mod_bytes))
    assert report.total_bytes_changed == 2
    for d in report.classified_diffs:
        assert d.category == ByteCategory.MAP_AXIS
        assert d.owner_symbol == "PCR_pBDesBas_MAP"

    m = report.maps_changed[0]
    assert m.axis_changed is True


def test_diff_map_header_modification_classification(engine, validator, stock_bytes):
    # Modify nx header of PCR_pBDesBas_MAP (0x1EB0B2)
    mod_bytes = bytearray(stock_bytes)
    mod_bytes[0x1EB0B2] = 0x00
    mod_bytes[0x1EB0B3] = 0x12  # change nx from 16 to 18

    report = engine.compare(stock_bytes, bytes(mod_bytes))
    for d in report.classified_diffs:
        assert d.category == ByteCategory.MAP_HEADER
        assert d.owner_symbol == "PCR_pBDesBas_MAP"

    audit = validator.validate(report)
    assert audit.is_safe is False
    assert audit.overall_verdict == SafetyLevel.HARD_FAIL
    fail_rules = [r.rule_id for r in audit.rule_results if r.level == SafetyLevel.HARD_FAIL]
    assert "RULE_MAP_HEADERS_INTACT" in fail_rules


def test_safety_hard_fail_on_code_area_modification(engine, validator, stock_bytes):
    mod_bytes = bytearray(stock_bytes)
    mod_bytes[0x002000] = (mod_bytes[0x002000] + 1) % 256

    report = engine.compare(stock_bytes, bytes(mod_bytes))
    assert report.code_area_bytes == 1

    audit = validator.validate(report)
    assert audit.is_safe is False
    assert audit.overall_verdict == SafetyLevel.HARD_FAIL
    fail_rules = [r.rule_id for r in audit.rule_results if r.level == SafetyLevel.HARD_FAIL]
    assert "RULE_CODE_AREA_INTACT" in fail_rules


def test_safety_hard_fail_on_identity_modification(engine, validator, stock_bytes):
    mod_bytes = bytearray(stock_bytes)
    # VAG Part Number string at 0x1C0CBE
    mod_bytes[0x1C0CBE] = 0x58

    report = engine.compare(stock_bytes, bytes(mod_bytes))
    assert report.identity_area_bytes == 1

    audit = validator.validate(report)
    assert audit.is_safe is False
    assert audit.overall_verdict == SafetyLevel.HARD_FAIL
    fail_rules = [r.rule_id for r in audit.rule_results if r.level == SafetyLevel.HARD_FAIL]
    assert "RULE_IDENTITY_AREA_INTACT" in fail_rules


def test_safety_hard_fail_on_unmapped_bytes(engine, validator, stock_bytes):
    # Use the known garage off binary which has 181 unmapped bytes
    off_path = Path("diagnostic-review/new-inputs/off/03G906021QJ (DPF EGR OFF) NoCS.Bin")
    on_path = Path("diagnostic-review/new-inputs/on/03G906021QJ.Bin")
    if not off_path.exists() or not on_path.exists():
        pytest.skip("new-inputs on/off binaries not found")

    report = engine.compare(on_path, off_path)
    assert report.unmapped_bytes > 0

    audit = validator.validate(report)
    assert audit.is_safe is False
    assert audit.overall_verdict == SafetyLevel.HARD_FAIL
    fail_rules = [r.rule_id for r in audit.rule_results if r.level == SafetyLevel.HARD_FAIL]
    assert "RULE_NO_UNMAPPED_CALIBRATION" in fail_rules


def test_safety_needs_evidence_on_overboost(engine, validator, stock_bytes):
    mod_bytes = bytearray(stock_bytes)
    cell_offset = 0x1EB0F2 + 20
    # 2500 hPa exceeds candidate threshold (2350 hPa)
    mod_bytes[cell_offset : cell_offset + 2] = (2500).to_bytes(2, "big", signed=True)

    report = engine.compare(stock_bytes, bytes(mod_bytes))
    audit = validator.validate(report)
    
    # Binary is structurally sound (0 code/id/unmapped fails), but requires evidence for unverified boost
    assert audit.is_structurally_sound is True
    assert audit.is_safe is False
    assert audit.overall_verdict == SafetyLevel.NEEDS_EVIDENCE
    assert audit.needs_evidence_count == 1
    needs_evidence_rules = [r.rule_id for r in audit.rule_results if r.level == SafetyLevel.NEEDS_EVIDENCE]
    assert "RULE_BOOST_LIMIT" in needs_evidence_rules


def test_safety_needs_evidence_on_high_smoke(engine, validator, stock_bytes):
    mod_bytes = bytearray(stock_bytes)
    # FlMng_qPresSmoke_MAP is @ 0x1D6490 (16x12)
    # values start @ 0x1D6490 + 4 + 2*16 + 2*12 = 0x1D64E8
    val_offset = 0x1D64E8 + 40
    # 70.0 mg (raw 7000) exceeds 65.0 mg
    mod_bytes[val_offset : val_offset + 2] = (7000).to_bytes(2, "big", signed=True)

    report = engine.compare(stock_bytes, bytes(mod_bytes))
    audit = validator.validate(report)
    assert audit.is_structurally_sound is True
    assert audit.is_safe is False
    assert audit.overall_verdict == SafetyLevel.NEEDS_EVIDENCE
    needs_evidence_rules = [r.rule_id for r in audit.rule_results if r.level == SafetyLevel.NEEDS_EVIDENCE]
    assert "RULE_SMOKE_LIMIT" in needs_evidence_rules


def test_safety_unverified_status_when_within_candidate_limit(engine, validator, stock_bytes):
    mod_bytes = bytearray(stock_bytes)
    cell_offset = 0x1EB0F2 + 20
    # 2200 hPa is within candidate threshold (2350 hPa), but threshold is unverified
    mod_bytes[cell_offset : cell_offset + 2] = (2200).to_bytes(2, "big", signed=True)

    report = engine.compare(stock_bytes, bytes(mod_bytes))
    audit = validator.validate(report)

    assert audit.is_structurally_sound is True
    # Crucial epistemic check: an unverified threshold cannot prove safety, so is_safe is False
    assert audit.is_safe is False
    assert audit.overall_verdict == SafetyLevel.UNVERIFIED
    assert audit.unverified_count >= 1
    unverified_rules = [r.rule_id for r in audit.rule_results if r.level == SafetyLevel.UNVERIFIED]
    assert "RULE_BOOST_LIMIT" in unverified_rules


