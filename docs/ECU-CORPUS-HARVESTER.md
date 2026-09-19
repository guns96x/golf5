# ECU Corpus Harvester

## Purpose

The harvester builds a broad **metadata-first** corpus around the target ECU
without allowing a random DAMOS/BIN from another software version to become
project truth.

Target profile:

- Bosch EDC16U34-3.42
- VAG part number: `03G906021QJ`
- project SW: `1037391847`
- calibration/software ID: `391847`
- VAG SW version: `1984`
- Bosch/VAG project family: `P447 HAXN`
- engine: `BLS`

## Evidence boundary

A row in `corpus_artifacts` means only:

> “this artefact is known to exist or has been observed.”

It does **not** mean its contents are correct or applicable.

There are separate states for:
- discovery metadata;
- local availability;
- identity/header matching;
- hash/provenance verification;
- applicability to the target ECU.

Paid/private files are never downloaded automatically.

## Match classes

| Class | Meaning |
|---|---|
| `EXACT` | target part number and target software identity match |
| `SAME_HW_SIBLING` | same VAG hardware/part family, different software |
| `SAME_PROJECT_FAMILY` | same EDC16U34 / P447 project family |
| `STRUCTURAL_ANALOG` | useful only for structural comparison |
| `UNKNOWN` | insufficient metadata |
| `REJECT` | incompatible ECU family |

A lower class must never supply fixed addresses to a higher-class target.

## Seed registry

`ecu-kb/corpus/seeds.json` contains discovery metadata only.

Initial registry includes:
- exact `03G906021QJ / 391847 / 1984` original-file candidates;
- exact `03G906021QJ_1984.sgo` candidates;
- exact DAMOS-index candidate
  `03G906021QJ 1984 391847 P447 HAXN EDC16U34 3.42`;
- QJ software siblings `0668 / 0779 / 1189 / 1340`;
- RN, JH, PB, PC, NK, MN, PN, PP, QB, QC and 03G906056AC P447
  siblings/analogues;
- open-source EDC16U34 structural detector references.

The source tier is intentionally conservative. A vendor catalog or community
index is discovery evidence, not OEM evidence.

## Commands

Initialize/upgrade corpus tables:

```bat
python tools\ecu_corpus_harvester.py init
```

Import/update seed metadata:

```bat
python tools\ecu_corpus_harvester.py seed
```

Show ranked candidates:

```bat
python tools\ecu_corpus_harvester.py report
python tools\ecu_corpus_harvester.py report --json
```

Scan a local folder containing legally obtained files:

```bat
python tools\ecu_corpus_harvester.py scan D:\ECU-Corpus
```

Supported discovery extensions include:
`.a2l`, `.dam`, `.ols`, `.xdf`, `.kp`, `.kp2`, `.bin`, `.ori`,
`.sgo`, `.frf`, `.eep`, `.eeprom`, `.hex`, `.mot`.

The scan:
- computes SHA-256;
- records file size;
- extracts obvious ASCII ECU identifiers;
- compares them with the target profile;
- does not upload or publish the source file.

Verify an obtained candidate against a registry row:

```bat
python tools\ecu_corpus_harvester.py verify-local 12 D:\ECU-Corpus\candidate.a2l
```

## Remote specialist export

`Publish-KBRemoteSnapshot.ps1` automatically initializes and seeds the registry
before running `kb.py check`.

The generated `ecu-kb/remote/corpus.json` exposes:
- source metadata;
- identity/applicability class;
- score and match reasons;
- SHA-256 when a local file has been observed;
- verification state.

It intentionally omits local filesystem paths and does not export binary/DAMOS
contents.

This lets ChatGPT answer questions such as:

- “Do we have an exact DAMOS candidate for 391847?”
- “Which QJ sibling is closest to the target?”
- “Is this map address from an exact file or only a structural analogue?”
- “Which candidate still needs an actual local file/hash?”

without direct access to the local machine.


## Critical provenance rule: reconstructed image != ECU readback

A 2 MiB image reconstructed from an Intel HEX can be byte-complete and still
remain a **derived/reconstructed reference**. Matching the known
`reference-from-hex.analysis-only.bin` SHA-256 proves identity with that
reconstructed reference; it does **not** prove that the image was independently
read from the physical ECU before tuning.

Therefore:
- a reconstructed HEX/BIN may be `PROJECT_VERIFIED` as a project artefact;
- it must not close a gap asking for an untouched `own_readback`;
- only an independently captured ECU readback with documented acquisition
  provenance can satisfy that requirement.

Likewise, re-running `seed` must never erase local verification state. Seed
metadata is weaker than locally observed hash/header/project evidence.
