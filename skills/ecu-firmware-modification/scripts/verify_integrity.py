#!/usr/bin/env python3
"""Read-only verification for explicitly selected firmware integrity profiles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence


PASS = "PASS"
FAIL = "FAIL"
UNKNOWN = "UNKNOWN"
NOT_APPLICABLE = "NOT_APPLICABLE"

EDC16_INVARIANT = 0xD01FE500
EDC16_BLOCK_SIZE = 0x80000


def additive32_sum(
    data: bytes | bytearray,
    *,
    start: int = 0,
    size: int | None = None,
    byteorder: str = "big",
) -> int:
    """Return the modulo-2**32 sum of aligned 32-bit words."""

    if byteorder not in {"big", "little"}:
        raise ValueError("byteorder must be 'big' or 'little'")
    if start < 0 or start % 4:
        raise ValueError("start must be non-negative and 4-byte aligned")
    if size is None:
        size = len(data) - start
    if size <= 0 or size % 4:
        raise ValueError("size must be positive and a multiple of 4")
    end = start + size
    if end > len(data):
        raise ValueError(
            f"covered range [0x{start:X}, 0x{end:X}) exceeds artifact length 0x{len(data):X}"
        )

    total = 0
    view = memoryview(data)
    for offset in range(start, end, 4):
        total = (total + int.from_bytes(view[offset : offset + 4], byteorder)) & 0xFFFFFFFF
    return total


def _combine(checksum_status: str, signature_status: str) -> str:
    statuses = {checksum_status, signature_status}
    if FAIL in statuses:
        return FAIL
    if UNKNOWN in statuses:
        return UNKNOWN
    return PASS


def verify_integrity(
    data: bytes | bytearray,
    *,
    algorithm: str,
    start: int = 0,
    size: int | None = None,
    invariant: int = EDC16_INVARIANT,
    signature_status: str | None = None,
) -> dict[str, object]:
    """Verify supported integrity without changing *data*.

    ``additive32-be`` proves only the declared additive layer.  ECU identity,
    address mapping, protected ranges, and flash readiness are separate gates.
    """

    signature = signature_status or NOT_APPLICABLE
    if signature not in {PASS, FAIL, UNKNOWN, NOT_APPLICABLE}:
        raise ValueError("invalid signature status")

    if algorithm != "additive32-be":
        return {
            "status": UNKNOWN,
            "algorithm": algorithm,
            "checksum": {
                "status": UNKNOWN,
                "reason": "unsupported or unverified integrity algorithm",
            },
            "signature": {"status": signature},
        }

    effective_size = len(data) - start if size is None else size
    try:
        observed = additive32_sum(data, start=start, size=effective_size, byteorder="big")
    except ValueError as exc:
        checksum: dict[str, object] = {"status": FAIL, "reason": str(exc)}
    else:
        checksum = {
            "status": PASS if observed == invariant else FAIL,
            "observed_residue": f"0x{observed:08X}",
            "expected_residue": f"0x{invariant & 0xFFFFFFFF:08X}",
        }

    checksum_status = str(checksum["status"])
    return {
        "status": _combine(checksum_status, signature),
        "algorithm": algorithm,
        "coverage": [start, start + effective_size],
        "word_size_bytes": 4,
        "byte_order": "big",
        "checksum": checksum,
        "signature": {"status": signature},
        "limitations": [
            "checksum result does not establish ECU identity or address mapping",
            "checksum result does not establish signature validity or flash readiness",
        ],
    }


def _integer(value: str) -> int:
    return int(value, 0)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("--algorithm", default="additive32-be")
    parser.add_argument("--start", type=_integer, default=0)
    parser.add_argument("--size", type=_integer)
    parser.add_argument("--invariant", type=_integer, default=EDC16_INVARIANT)
    parser.add_argument("--require-edc16-512k-shape", action="store_true")
    parser.add_argument(
        "--signature-status", choices=(PASS, FAIL, UNKNOWN, NOT_APPLICABLE)
    )
    args = parser.parse_args(argv)

    try:
        data = args.image.read_bytes()
    except OSError as exc:
        print(json.dumps({"status": FAIL, "error": str(exc)}, indent=2))
        return 1

    if args.require_edc16_512k_shape and (args.start != 0 or len(data) != EDC16_BLOCK_SIZE):
        report: dict[str, object] = {
            "status": FAIL,
            "reason": "EDC16 candidate profile requires one raw 524288-byte artifact and start 0",
            "actual_size": len(data),
        }
    else:
        try:
            report = verify_integrity(
                data,
                algorithm=args.algorithm,
                start=args.start,
                size=args.size,
                invariant=args.invariant,
                signature_status=args.signature_status,
            )
        except ValueError as exc:
            report = {"status": FAIL, "error": str(exc)}

    print(json.dumps(report, indent=2, sort_keys=True))
    return {PASS: 0, FAIL: 1, UNKNOWN: 2}.get(str(report["status"]), 2)


if __name__ == "__main__":
    raise SystemExit(main())
