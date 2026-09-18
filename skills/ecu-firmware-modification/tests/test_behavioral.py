"""Behavioral fixtures and executable tests for the ECU firmware skill.

The scenario catalog is intended for agent-level forward testing.  The
executable unittest cases exercise the deterministic image-inspection and
integrity helpers without pretending that prose guidance itself is executable.
"""

from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import inspect_image  # noqa: E402
import verify_integrity  # noqa: E402


PASS = "PASS"
FAIL = "FAIL"
UNKNOWN = "UNKNOWN"
BLOCK = "BLOCK"


@dataclass(frozen=True)
class BehavioralScenario:
    name: str
    stimulus: str
    expected_disposition: str
    required_observations: tuple[str, ...]


BEHAVIORAL_SCENARIOS = (
    BehavioralScenario(
        "wrong_software_same_size",
        "A 512 KiB image has the expected length but mismatches the bound SW identity/hash.",
        BLOCK,
        ("size is not identity evidence", "report the identity mismatch"),
    ),
    BehavioralScenario(
        "wrong_byte_order_plausible",
        "Little-endian decoding produces plausible values for a big-endian object.",
        BLOCK,
        ("use the object/profile byte order", "reject plausibility as proof"),
    ),
    BehavioralScenario(
        "shared_axes_and_inactive_allocation",
        "Allocated dimensions exceed active dimensions and an axis is shared by other maps.",
        BLOCK,
        ("edit active cells only", "enumerate shared-axis consumers"),
    ),
    BehavioralScenario(
        "unsupported_conversion_and_oob_pointer",
        "The A2L conversion is unsupported and a resolved pointer leaves the image segment.",
        BLOCK,
        ("conversion status UNKNOWN", "out-of-bounds pointer is an error"),
    ),
    BehavioralScenario(
        "quantization_overflow_and_protected_change",
        "A physical request overflows storage and the diff touches a protected range.",
        BLOCK,
        ("do not clip silently", "report the protected-region change"),
    ),
    BehavioralScenario(
        "truncated_image_and_incomplete_backup",
        "The artifact is short and does not cover the required recovery ranges.",
        BLOCK,
        ("report truncation", "do not call a partial read a full backup"),
    ),
    BehavioralScenario(
        "original_byte_mismatch",
        "A patch's expected original bytes differ from the input artifact.",
        BLOCK,
        ("apply no bytes", "report the mismatching offset"),
    ),
    BehavioralScenario(
        "corruption_inside_and_outside_checksum_coverage",
        "One mutation is inside and another is outside a declared checksum range.",
        BLOCK,
        ("inside mutation fails that checksum", "outside mutation is not covered evidence"),
    ),
    BehavioralScenario(
        "valid_checksum_invalid_signature",
        "The additive checksum passes while a required signature fails.",
        BLOCK,
        ("overall integrity fails", "do not equate checksum with authenticity"),
    ),
    BehavioralScenario(
        "unsupported_checksum_algorithm",
        "The required integrity algorithm has no verified implementation.",
        UNKNOWN,
        ("return UNKNOWN", "block flash readiness"),
    ),
    BehavioralScenario(
        "missing_power_or_recovery_evidence",
        "Preflight lacks a target-specific power envelope or an available recovery route.",
        BLOCK,
        ("do not initiate programming", "name the missing evidence"),
    ),
    BehavioralScenario(
        "diagnostic_edit_unresolved_reaction",
        "A DTC reporting edit leaves substitute values or torque reaction unresolved.",
        BLOCK,
        ("reporting suppression is insufficient", "trace trigger through recovery"),
    ),
)


class BehavioralFixtureCatalogTests(unittest.TestCase):
    def test_all_requested_scenarios_have_blocking_or_unknown_outcomes(self) -> None:
        self.assertEqual(len(BEHAVIORAL_SCENARIOS), 12)
        self.assertEqual(len({case.name for case in BEHAVIORAL_SCENARIOS}), 12)
        self.assertTrue(
            all(case.expected_disposition in {BLOCK, UNKNOWN} for case in BEHAVIORAL_SCENARIOS)
        )
        self.assertTrue(all(case.required_observations for case in BEHAVIORAL_SCENARIOS))


class InspectImageBehaviorTests(unittest.TestCase):
    def _write(self, data: bytes) -> Path:
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=".bin")
        handle.write(data)
        handle.close()
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        return Path(handle.name)

    def test_wrong_software_version_is_rejected_even_when_size_matches(self) -> None:
        path = self._write(b"\xFF" * 0x80000)
        report = inspect_image.inspect_image(
            path,
            expected_size=0x80000,
            expected_identity={"hw": "03G906021QJ", "sw": "391847"},
            observed_identity={"hw": "03G906021QJ", "sw": "391848"},
        )
        self.assertEqual(report["size_check"]["status"], PASS)
        self.assertEqual(report["identity_check"]["status"], FAIL)

    def test_truncated_image_and_incomplete_declared_coverage_fail(self) -> None:
        path = self._write(b"\x00" * 0x7FFF0)
        report = inspect_image.inspect_image(
            path,
            expected_size=0x80000,
            declared_coverage=((0, 0x7FFF0),),
            required_coverage=((0, 0x80000),),
        )
        self.assertEqual(report["size_check"]["status"], FAIL)
        self.assertEqual(report["coverage_check"]["status"], FAIL)

    def test_raw_image_reports_hashes_without_inventing_ecu_identity(self) -> None:
        data = b"firmware" * 64
        path = self._write(data)
        report = inspect_image.inspect_image(path)
        self.assertEqual(report["format"], "raw-binary")
        self.assertEqual(report["hashes"]["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(report["hashes"]["sha512"], hashlib.sha512(data).hexdigest())
        self.assertEqual(report["identity_check"]["status"], UNKNOWN)
        self.assertEqual(report["coverage_check"]["status"], UNKNOWN)


class IntegrityBehaviorTests(unittest.TestCase):
    @staticmethod
    def _valid_block(size: int = 0x80000) -> bytes:
        # Hand-derived fixture: all zero words plus K stored as the final BE word.
        return bytes(size - 4) + verify_integrity.EDC16_INVARIANT.to_bytes(4, "big")

    def test_wrong_byte_order_does_not_pass_even_if_values_look_plausible(self) -> None:
        data = self._valid_block()
        self.assertEqual(
            verify_integrity.verify_integrity(data, algorithm="additive32-be")["status"],
            PASS,
        )
        self.assertNotEqual(
            verify_integrity.additive32_sum(data, byteorder="little"),
            verify_integrity.EDC16_INVARIANT,
        )

    def test_corruption_inside_fails_but_outside_is_not_covered(self) -> None:
        covered = bytearray(self._valid_block())
        container = covered + bytearray(b"outside")

        outside_changed = bytearray(container)
        outside_changed[-1] ^= 0x01
        outside_report = verify_integrity.verify_integrity(
            outside_changed,
            algorithm="additive32-be",
            start=0,
            size=0x80000,
        )
        self.assertEqual(outside_report["status"], PASS)
        self.assertEqual(outside_report["coverage"], [0, 0x80000])

        inside_changed = bytearray(container)
        inside_changed[0] ^= 0x01
        inside_report = verify_integrity.verify_integrity(
            inside_changed,
            algorithm="additive32-be",
            start=0,
            size=0x80000,
        )
        self.assertEqual(inside_report["status"], FAIL)

    def test_valid_checksum_with_invalid_required_signature_fails_overall(self) -> None:
        report = verify_integrity.verify_integrity(
            self._valid_block(),
            algorithm="additive32-be",
            signature_status=FAIL,
        )
        self.assertEqual(report["checksum"]["status"], PASS)
        self.assertEqual(report["signature"]["status"], FAIL)
        self.assertEqual(report["status"], FAIL)

    def test_unsupported_checksum_algorithm_returns_unknown(self) -> None:
        report = verify_integrity.verify_integrity(
            self._valid_block(), algorithm="mystery-crc"
        )
        self.assertEqual(report["status"], UNKNOWN)

    def test_truncated_additive_region_fails_closed(self) -> None:
        report = verify_integrity.verify_integrity(
            self._valid_block()[:-4],
            algorithm="additive32-be",
            start=0,
            size=0x80000,
        )
        self.assertEqual(report["status"], FAIL)


if __name__ == "__main__":
    unittest.main()
