# -*- coding: utf-8 -*-
"""
calharness.checksum

Read-only Checksum Inspector for Bosch EDC16U34 (VW Golf 5 1.9 TDI BLS, SW 1037391847).

Contract:
  - Verify-only mode: inspects binary data without attempting automatic mutation.
  - Multi-binary corroborated candidate invariant: 0xD01FE500.
  - Covers dual calibration segments:
      * Segment 1 (Block 1): 0x180000..0x1C0000 (0x40000 bytes / 256 KB)
      * Segment 2 (Block 2): 0x1C0000..0x1FE000 (0x3E000 bytes / 248 KB)
      * Padding (0xFF):      0x1FE000..0x200000 (0x2000 bytes / 8 KB)
"""

from __future__ import annotations

import struct
from pathlib import Path
from typing import List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from calharness.address_space import AddressSpace


# Candidate invariant observed across verified local binaries (stock, stage1_CS_OK, etc.)
EDC16_CANDIDATE_INVARIANT = 0xD01FE500

# Segment sizes in EDC16U34 calibration area
BLOCK1_SIZE = 0x40000  # 256 KB
BLOCK2_SIZE = 0x3E000  # 248 KB
PADDING_SIZE = 0x02000 # 8 KB


def sum32_be(data: bytes | bytearray, start: int, length: int) -> int:
    """Calculate modulo-2^32 sum of 32-bit big-endian words."""
    if start < 0 or start % 4 != 0:
        raise ValueError(f"Start offset 0x{start:X} must be non-negative and 4-byte aligned")
    if length <= 0 or length % 4 != 0:
        raise ValueError(f"Length 0x{length:X} must be positive and 4-byte aligned")
    end = start + length
    if end > len(data):
        raise ValueError(f"Range [0x{start:X}, 0x{end:X}) exceeds data size 0x{len(data):X}")

    total = 0
    view = memoryview(data)
    for offset in range(start, end, 4):
        word = int.from_bytes(view[offset : offset + 4], "big")
        total = (total + word) & 0xFFFFFFFF
    return total


class ChecksumBlockResult(BaseModel):
    """Inspection result for an individual EDC16 calibration block."""
    model_config = ConfigDict(extra="forbid")

    block_id: int
    name: str
    start_offset: int
    end_offset: int
    hex_range: str
    observed_sum: int
    observed_hex: str
    expected_hex: str
    matches_candidate: bool
    correction_word_hex: str


class ChecksumInspectionReport(BaseModel):
    """Report detailing the read-only checksum verification of an ECU binary."""
    model_config = ConfigDict(extra="forbid")

    file_size: int
    base_offset: int
    is_512k_cal_read: bool
    is_2m_full_read: bool
    is_corroborated: bool
    blocks: List[ChecksumBlockResult] = Field(default_factory=list)
    evidence_notes: List[str] = Field(default_factory=list)

    def summary(self) -> str:
        """Human-readable overview of checksum verification."""
        status_str = "PASS (CORROBORATED)" if self.is_corroborated else "MISMATCH / UNVERIFIED"
        lines = [
            f"EDC16 Checksum Inspection: [{status_str}]",
            f"  Binary Size: 0x{self.file_size:X} ({'2MB Full' if self.is_2m_full_read else '512KB Cal' if self.is_512k_cal_read else 'Custom'})",
            f"  Candidate Invariant: 0x{EDC16_CANDIDATE_INVARIANT:08X}",
        ]
        for b in self.blocks:
            match_sym = "[OK]" if b.matches_candidate else "[FAIL]"
            lines.append(
                f"  {match_sym} Block {b.block_id} ({b.hex_range}): "
                f"Sum = {b.observed_hex} (Expected {b.expected_hex}) | Corr Word = {b.correction_word_hex}"
            )
        lines.append("\nEvidence & Provenance:")
        for note in self.evidence_notes:
            lines.append(f"  - {note}")
        return "\n".join(lines)


class ChecksumInspector:
    """
    Read-only inspector for EDC16 dual-block additive checksums.
    Strictly verify-only: does not modify binaries without proven algorithms.
    """

    def __init__(self, candidate_invariant: int = EDC16_CANDIDATE_INVARIANT):
        self.candidate_invariant = candidate_invariant

    def inspect(self, binary_data_or_path: Union[Path, str, bytes, bytearray]) -> ChecksumInspectionReport:
        """Inspect dual-block checksums of an EDC16 binary."""
        if isinstance(binary_data_or_path, (bytes, bytearray)):
            data = bytes(binary_data_or_path)
        else:
            p = Path(binary_data_or_path)
            data = p.read_bytes()

        size = len(data)
        addr_space = AddressSpace.from_binary(size)
        is_2m = addr_space.is_full_image
        is_512k = addr_space.is_calibration_slice
        base_offset = addr_space.to_offset(0x180000)

        # Block 1: 0x180000..0x1C0000 (size 0x40000)
        b1_start = addr_space.to_offset(0x180000)
        b1_len = BLOCK1_SIZE
        b1_end = b1_start + b1_len
        b1_sum = sum32_be(data, b1_start, b1_len)
        b1_corr = data[b1_end - 4 : b1_end].hex()
        b1_match = (b1_sum == self.candidate_invariant)

        b1_res = ChecksumBlockResult(
            block_id=1,
            name="EDC16 Calibration Block 1",
            start_offset=b1_start,
            end_offset=b1_end,
            hex_range=f"0x{addr_space.to_ecu_address(b1_start):06X}..0x{addr_space.to_ecu_address(b1_end):06X}",
            observed_sum=b1_sum,
            observed_hex=f"0x{b1_sum:08X}",
            expected_hex=f"0x{self.candidate_invariant:08X}",
            matches_candidate=b1_match,
            correction_word_hex=b1_corr,
        )

        # Block 2: 0x1C0000..0x1FE000 (size 0x3E000)
        b2_start = b1_end
        b2_len = BLOCK2_SIZE
        b2_end = b2_start + b2_len
        b2_sum = sum32_be(data, b2_start, b2_len)
        b2_corr = data[b2_end - 4 : b2_end].hex()
        b2_match = (b2_sum == self.candidate_invariant)

        b2_res = ChecksumBlockResult(
            block_id=2,
            name="EDC16 Calibration Block 2",
            start_offset=b2_start,
            end_offset=b2_end,
            hex_range=f"0x{addr_space.to_ecu_address(b2_start):06X}..0x{addr_space.to_ecu_address(b2_end):06X}",
            observed_sum=b2_sum,
            observed_hex=f"0x{b2_sum:08X}",
            expected_hex=f"0x{self.candidate_invariant:08X}",
            matches_candidate=b2_match,
            correction_word_hex=b2_corr,
        )

        is_corroborated = b1_match and b2_match
        notes = [
            f"Candidate invariant 0x{self.candidate_invariant:08X}: "
            + ("matches across verified local files." if is_corroborated else "does not match this binary."),
            "Verify-only inspection mode: auto-fixer is not enabled pending complete cross-hardware proof.",
            f"Trailing padding 0x{addr_space.to_ecu_address(b2_end):06X}..0x{addr_space.end_ecu_address:06X} (8 KB) is excluded from checksum calculations.",
        ]

        return ChecksumInspectionReport(
            file_size=size,
            base_offset=base_offset,
            is_512k_cal_read=is_512k,
            is_2m_full_read=is_2m,
            is_corroborated=(b1_match and b2_match),
            blocks=[b1_res, b2_res],
            evidence_notes=notes,
        )
