#!/usr/bin/env python3
"""Read-only firmware artifact inspection.

This utility reports container hints, hashes, exact file length, and only the
coverage/identity evidence supplied by the caller.  It deliberately does not
infer ECU identity or physical-memory coverage from file size alone.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable, Mapping, Sequence


PASS = "PASS"
FAIL = "FAIL"
UNKNOWN = "UNKNOWN"
NOT_CHECKED = "NOT_CHECKED"


def _detect_format(data: bytes) -> str:
    stripped = data.lstrip()
    if stripped.startswith(b":"):
        return "intel-hex"
    if len(stripped) >= 2 and stripped[:1] == b"S" and stripped[1:2] in b"0123456789":
        return "motorola-srec"
    return "raw-binary"


def _normalize_ranges(ranges: Iterable[Sequence[int]]) -> list[list[int]]:
    normalized: list[list[int]] = []
    for item in ranges:
        if len(item) != 2:
            raise ValueError("ranges must contain exactly [start, end]")
        start, end = int(item[0]), int(item[1])
        if start < 0 or end <= start:
            raise ValueError(f"invalid half-open range [{start}, {end})")
        normalized.append([start, end])
    normalized.sort()
    merged: list[list[int]] = []
    for start, end in normalized:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged


def _range_is_covered(required: Sequence[int], available: list[list[int]]) -> bool:
    start, end = required
    return any(have_start <= start and have_end >= end for have_start, have_end in available)


def inspect_image(
    path: str | Path,
    *,
    expected_size: int | None = None,
    expected_identity: Mapping[str, str] | None = None,
    observed_identity: Mapping[str, str] | None = None,
    declared_coverage: Iterable[Sequence[int]] | None = None,
    required_coverage: Iterable[Sequence[int]] | None = None,
) -> dict[str, object]:
    """Inspect an artifact without modifying it.

    Coverage ranges are half-open ECU or logical address ranges supplied by
    external evidence.  The function reports, but never invents, their mapping.
    """

    artifact = Path(path)
    data = artifact.read_bytes()
    actual_size = len(data)
    anomalies: list[str] = []

    if expected_size is None:
        size_check = {"status": NOT_CHECKED, "expected": None, "actual": actual_size}
    else:
        size_status = PASS if actual_size == expected_size else FAIL
        size_check = {"status": size_status, "expected": expected_size, "actual": actual_size}
        if size_status == FAIL:
            anomalies.append("exact_size_mismatch")

    expected = dict(expected_identity or {})
    observed = dict(observed_identity or {})
    if not expected or not observed:
        identity_check: dict[str, object] = {
            "status": UNKNOWN,
            "expected": expected or None,
            "observed": observed or None,
            "reason": "identity requires independent diagnostic, metadata, or trusted hash evidence",
        }
    else:
        mismatches = {
            key: {"expected": value, "observed": observed.get(key)}
            for key, value in expected.items()
            if observed.get(key) != value
        }
        identity_check = {
            "status": FAIL if mismatches else PASS,
            "expected": expected,
            "observed": observed,
            "mismatches": mismatches,
        }
        if mismatches:
            anomalies.append("identity_mismatch")

    declared = _normalize_ranges(declared_coverage or ())
    required = _normalize_ranges(required_coverage or ())
    if not required:
        coverage_check: dict[str, object] = {
            "status": UNKNOWN,
            "declared": declared,
            "required": required,
            "reason": "physical/logical ECU coverage was not established",
        }
    elif not declared:
        coverage_check = {
            "status": FAIL,
            "declared": declared,
            "required": required,
            "missing": required,
        }
        anomalies.append("required_coverage_not_declared")
    else:
        missing = [item for item in required if not _range_is_covered(item, declared)]
        coverage_check = {
            "status": FAIL if missing else PASS,
            "declared": declared,
            "required": required,
            "missing": missing,
        }
        if missing:
            anomalies.append("incomplete_declared_coverage")

    return {
        "path": str(artifact.resolve()),
        "format": _detect_format(data),
        "size_bytes": actual_size,
        "artifact_file_range": [0, actual_size],
        "hashes": {
            "sha256": hashlib.sha256(data).hexdigest(),
            "sha512": hashlib.sha512(data).hexdigest(),
        },
        "size_check": size_check,
        "identity_check": identity_check,
        "coverage_check": coverage_check,
        "anomalies": anomalies,
    }


def _integer(value: str) -> int:
    return int(value, 0)


def _range(value: str) -> tuple[int, int]:
    try:
        start, end = value.split(":", 1)
        return _integer(start), _integer(end)
    except (ValueError, TypeError) as exc:
        raise argparse.ArgumentTypeError("range must be START:END (half-open)") from exc


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("--expected-size", type=_integer)
    parser.add_argument("--expected-hw")
    parser.add_argument("--expected-sw")
    parser.add_argument("--observed-hw")
    parser.add_argument("--observed-sw")
    parser.add_argument("--declared-range", action="append", type=_range, default=[])
    parser.add_argument("--required-range", action="append", type=_range, default=[])
    args = parser.parse_args(argv)

    expected = {k: v for k, v in {"hw": args.expected_hw, "sw": args.expected_sw}.items() if v}
    observed = {k: v for k, v in {"hw": args.observed_hw, "sw": args.observed_sw}.items() if v}
    try:
        report = inspect_image(
            args.image,
            expected_size=args.expected_size,
            expected_identity=expected,
            observed_identity=observed,
            declared_coverage=args.declared_range,
            required_coverage=args.required_range,
        )
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": FAIL, "error": str(exc)}, indent=2))
        return 1

    print(json.dumps(report, indent=2, sort_keys=True))
    checks = (report["size_check"], report["identity_check"], report["coverage_check"])
    return 1 if any(check["status"] == FAIL for check in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
