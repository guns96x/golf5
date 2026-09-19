# -*- coding: utf-8 -*-
"""
Unit tests for calharness.checksum (read-only EDC16 checksum inspection).
"""

from pathlib import Path
import pytest

from calharness.checksum import (
    BLOCK1_SIZE,
    BLOCK2_SIZE,
    EDC16_CANDIDATE_INVARIANT,
    ChecksumInspector,
    sum32_be,
)


@pytest.fixture
def stock_bin_path():
    p = Path("knowledge/08_firmware/originals/03G906021QJ_1984_391847_full_stock.bin")
    if not p.exists():
        pytest.skip(f"Stock binary not found at {p}")
    return p


def test_sum32_be_calculation():
    # 4 bytes: 0x01, 0x02, 0x03, 0x04 -> 0x01020304
    data = bytes([0x01, 0x02, 0x03, 0x04, 0x10, 0x20, 0x30, 0x40])
    s = sum32_be(data, 0, 8)
    expected = (0x01020304 + 0x10203040) & 0xFFFFFFFF
    assert s == expected


def test_stock_binary_checksum_corroboration(stock_bin_path):
    inspector = ChecksumInspector()
    report = inspector.inspect(stock_bin_path)

    assert report.is_2m_full_read is True
    assert report.is_512k_cal_read is False
    assert report.is_corroborated is True
    assert len(report.blocks) == 2

    # Block 1
    b1 = report.blocks[0]
    assert b1.block_id == 1
    assert b1.start_offset == 0x180000
    assert b1.end_offset == 0x1C0000
    assert b1.observed_sum == EDC16_CANDIDATE_INVARIANT
    assert b1.matches_candidate is True
    assert b1.correction_word_hex == "4c1a06d2"

    # Block 2
    b2 = report.blocks[1]
    assert b2.block_id == 2
    assert b2.start_offset == 0x1C0000
    assert b2.end_offset == 0x1FE000
    assert b2.observed_sum == EDC16_CANDIDATE_INVARIANT
    assert b2.matches_candidate is True
    assert b2.correction_word_hex == "fe53a1be"


def test_512k_slice_checksum_corroboration(stock_bin_path):
    full_data = stock_bin_path.read_bytes()
    # 512KB slice is 0x180000..0x200000
    cal_slice = full_data[0x180000:0x200000]
    assert len(cal_slice) == 0x80000

    inspector = ChecksumInspector()
    report = inspector.inspect(cal_slice)

    assert report.is_2m_full_read is False
    assert report.is_512k_cal_read is True
    assert report.is_corroborated is True

    assert report.blocks[0].start_offset == 0x000000
    assert report.blocks[0].end_offset == 0x040000
    assert report.blocks[0].observed_sum == EDC16_CANDIDATE_INVARIANT

    assert report.blocks[1].start_offset == 0x040000
    assert report.blocks[1].end_offset == 0x07E000
    assert report.blocks[1].observed_sum == EDC16_CANDIDATE_INVARIANT


def test_tampered_binary_fails_corroboration(stock_bin_path):
    tampered = bytearray(stock_bin_path.read_bytes())
    # Modify a byte inside Block 1 (0x190000)
    tampered[0x190000] = (tampered[0x190000] + 1) % 256

    inspector = ChecksumInspector()
    report = inspector.inspect(bytes(tampered))

    assert report.is_corroborated is False
    assert report.blocks[0].matches_candidate is False
    assert report.blocks[1].matches_candidate is True


def test_multi_binary_cross_validation():
    binaries = [
        ("knowledge/08_firmware/originals/03G906021QJ_1984_391847_full_stock.bin", True),
        ("firmware/03G906021QJ_stage1_refined_CS_OK.bin", True),
        ("diagnostic-review/new-inputs/on/03G906021QJ.Bin", True),
        ("diagnostic-review/new-inputs/off/03G906021QJ (DPF EGR OFF) NoCS.Bin", False),
    ]

    inspector = ChecksumInspector()
    for rel_path, expected_corroboration in binaries:
        p = Path(rel_path)
        if not p.exists():
            continue
        report = inspector.inspect(p)
        assert report.is_corroborated is expected_corroboration, f"File {rel_path} expected {expected_corroboration}"
