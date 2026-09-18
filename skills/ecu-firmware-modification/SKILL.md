---
name: ecu-firmware-modification
description: Use when analyzing or changing automotive ECU firmware, calibrations, integrity checks, flash procedures, or recovery for an identified hardware and software version.
metadata:
  short-description: ECU firmware analysis and modification
---

# ECU Firmware Modification

Evidence-led workflow for ECU firmware inspection, bounded calibration work, integrity verification, and authorized programming or recovery. This skill does not make an unidentified image, an unverified integrity profile, or an unsupported tool safe to flash.

## Reference Routing

Read only the references needed for the operation:

| Operation | Required references |
|---|---|
| Identify an ECU or artifact | [ecu-profiles.md](references/ecu-profiles.md) and [memory-and-addressing.md](references/memory-and-addressing.md) |
| Resolve maps or A2L objects | Add [map-identification.md](references/map-identification.md) |
| Change tuning or emissions-related behavior | Add [tuning-and-emissions.md](references/tuning-and-emissions.md) |
| Verify a checksum, CRC, or signature | Add [integrity-algorithms.md](references/integrity-algorithms.md) |
| Program or recover an ECU | Add [flashing-and-recovery.md](references/flashing-and-recovery.md) |

## Execution Contract

For every firmware task, follow these steps in order:

1. **Establish operation**: inspection, calibration modification, executable-code modification, integrity verification, flashing, or recovery.
2. **Identify target**: ECU hardware number, software number, engine, fuel system, transmission, and acquisition method.
3. **Preserve original**: Record hash (SHA-256), provenance, coverage (physical read vs partial/virtual), and limitations.
4. **Select profile**: Match from [references/ecu-profiles.md](references/ecu-profiles.md); record each field as `OBSERVED`, `DATASHEET_SUPPORTED`, `TOOL_REPORTED`, `INFERRED`, or `FIXTURE_VERIFIED`, plus unresolved ambiguities.
5. **Identify calibration objects**: Use A2L/DAMOS or heuristic scanning per [references/map-identification.md](references/map-identification.md). Confirm consumers and active extents.
6. **Prepare changes**: Explicit before/after bytes, physical values, dependencies, and rationale. Every changed byte belongs to an authorized object.
7. **Validate image**: Protected regions, applicable integrity per [references/integrity-algorithms.md](references/integrity-algorithms.md).
8. **Plan flash & recovery**: Concrete plan bound to exact artifact and ECU per [references/flashing-and-recovery.md](references/flashing-and-recovery.md).
9. **Execute**: Only within established authorization and verified tool support.
10. **Report**: Static validation, programming, and vehicle acceptance as distinct results.

## Core Rules

| Rule | Required behavior |
|---|---|
| Exact identity | Match HW/SW identifiers and trusted artifact provenance; file size alone is not identity evidence |
| Immutable baseline | Preserve originals. Label tuned images accurately — "original" ≠ factory stock |
| Evidence separation | Distinguish observed bytes, decoded structure, inferred function, measured runtime |
| Explicit coverage | Distinguish physical reads, partial/calibration reads, virtual reads, full backups |
| Candidate isolation | Heuristic candidates remain read-only until structure and semantics established |
| Bounded edits | Every changed byte → authorized object, reviewed code patch, or documented integrity update |
| Protection preservation | Preserve thermal derating, knock control, overspeed, torque monitoring, unrelated diagnostics |
| Identity preservation | Exclude immobilizer, keys, coding, adaptations from ordinary calibration edits |
| Fail closed | Unknown checksum, required signature, addressing, write coverage, power envelope, or recovery route blocks flash readiness |
| Honest completion | Checksum pass ≠ successful write ≠ successful engine validation |
| Legal eligibility | Unknown jurisdictional eligibility blocks deployment of emissions-related changes |

## Evidence Ladder

```
CANDIDATE → STRUCTURE_VERIFIED → SEMANTICS_VERIFIED → RUNTIME_VALIDATED
```

Each level carries evidence references. Avoid numerical "confidence scores" that resemble measured probabilities.

## Artifact Schemas

| Artifact | Required content |
|---|---|
| ECU Profile | HW/SW identity, MCU, fuel system, segments, address translations, protected ranges, integrity rules, tool protocol, recovery requirements |
| Map Catalog | Address/offset, datatype, dimensions, axes, conversions, units, active selection, evidence, status |
| Change Manifest | Input/output hashes, profile version, expected original bytes, replacement bytes, physical values, rationale, authorized scope |

## Included Scripts

| Script | Contract |
|---|---|
| `inspect_image.py` | Identify format, calculate hashes, report coverage and structural anomalies |
| `verify_integrity.py` | Verify supported checks; correction requires explicit output and supported profile |

Run each command with `--help` for its interface. Both scripts are read-only, deterministic, preserve originals, and return structured findings. `verify_integrity.py` proves only the declared mathematical layer; it does not establish ECU identity, address mapping, signature validity, or flash readiness. An unknown required check returns `UNKNOWN`, never success.

The other workflow capabilities (A2L import, candidate scanning, map validation, bounded patch application, and preflight) are behavioral contracts, not bundled commands. If implementing them, use [tests/test_behavioral.py](tests/test_behavioral.py) as the minimum failure-scenario catalog.

## Pre-Flash Evidence Gates

| Gate | Required evidence |
|---|---|
| Identity | Physical target and diagnostic IDs match profile and artifact |
| Backup | Available memories preserved; missing coverage documented |
| Artifact | Final hash, reviewed byte diff, protected-region checks, integrity results |
| Tool | Exact hardware, software version, license/protocol, supported operation |
| Power | OEM/tool voltage range, current capacity, stable supply, monitored connection |
| Connection | Exact pinout, adapter, grounding |
| Recovery | Documented failure route, usable backup coverage, required access, equipment |
| Execution | Authorization covers this ECU, image, and operation |
| Legal | Jurisdiction and intended use permit the requested deployment |
| Acceptance | Post-write verification and engine-validation plan established |

## Final Report Structure

```
Target and requested operation:
Baseline provenance and coverage:
Profile and evidence:
Modified objects and byte ranges:
Preserved protected regions:
Static/map validation: PASS / FAIL / NOT RUN
Checksum verification: PASS / FAIL / UNKNOWN / NOT APPLICABLE
Signature verification: PASS / FAIL / UNKNOWN / NOT APPLICABLE
Programming: PASS / FAIL / NOT RUN
Readback/tool verification: PASS / FAIL / NOT RUN
Controlled engine validation: PASS / FAIL / NOT RUN
Unresolved limitations:
Recovery artifact and procedure:
```

## References

Read the relevant reference for detailed guidance:

- Memory architecture, addressing, byte order: [references/memory-and-addressing.md](references/memory-and-addressing.md)
- Map identification, A2L integration, formulas: [references/map-identification.md](references/map-identification.md)
- Tuning disciplines, emissions modifications: [references/tuning-and-emissions.md](references/tuning-and-emissions.md)
- Checksum, CRC, cryptographic integrity: [references/integrity-algorithms.md](references/integrity-algorithms.md)
- ECU family profiles and routing: [references/ecu-profiles.md](references/ecu-profiles.md)
- Flashing safety, recovery procedures: [references/flashing-and-recovery.md](references/flashing-and-recovery.md)

## Important Distinctions

- **"Create firmware"** needs explicit branching: calibration editing modifies data; executable patches require instruction-level analysis; building replacement firmware requires source/compiler/linker and separate validation.
- **OBD, bench, boot** describe different access arrangements — bench ≠ BDM/JTAG automatically; boot mode ≠ unrestricted memory access.
- A **patched verification routine** is a code/security change, never "signature repaired."
- **Recovery** is conditional and failure-dependent, not a universal safety net.
