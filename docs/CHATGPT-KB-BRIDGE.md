# ChatGPT ↔ ECU Knowledge Base bridge

## Purpose

This repository contains a local evidence-oriented knowledge base for the specific
VW Golf 5 BLS / Bosch EDC16U34 project. The mutable canonical database is
`ecu-kb/knowledge/kb.sqlite3` and intentionally never leaves the local PC.

External AI clients cannot read that SQLite file directly. The bridge publishes a
**read-only derived snapshot** into `ecu-kb/remote/`, which is safe to inspect
through the GitHub connector.

## Authoritative order

For project questions use this order:

1. `ecu-kb/remote/manifest.json` — first read on every session.
2. `ecu-kb/remote/claims.json` — current non-retracted claims from SQLite.
3. `ecu-kb/remote/retractions.json` — claims that were deprecated/superseded and why.
4. `ecu-kb/remote/gaps.json` — unknowns and unresolved evidence requirements.
5. `ecu-kb/remote/conflicts.json` — explicit conflicts.
6. `ecu-kb/remote/corpus.json` — DAMOS/A2L/OLS/XDF/ORI/SGO discovery registry with applicability class.
7. `ecu-kb/remote/a2l/<FUNC_GROUP>.json` — A2L catalogue split by Bosch function
   group, for example `PCR.json`, `FlMng.json`, `InjVlv.json`.
8. Project documents such as `docs/CONTROL-PATH-STOCK-boost.md` only for larger
   contiguous context after the snapshot has identified the relevant topic.

Do **not** treat `PROMPT_FOR_CHATGPT.md`, `specialist.py`, old chat transcripts,
or Markdown summaries as a factual source when they disagree with the current
snapshot. They are instructions or derived prose, not the mutable truth store.

## Epistemic handling

Every exported claim carries:
- `evidence_kind`
- `verification_state`
- `source_class`
- `confidence`
- `missing_evidence`
- `epistemic_role` = `support | context | negative`
- citation/provenance records where available.

Rules for an external specialist:

- Use `epistemic_role=support` for positive factual support.
- `context` may be discussed only with its uncertainty stated.
- `negative` means the record contradicts a proposition; never use it as
  positive evidence.
- If a relevant gap is OPEN / RESEARCHING / PARTIAL, expose that limitation.
- Never infer a component limit from an ECU calibration ceiling.
- Check `retractions.json` when an older Markdown/report contradicts current claims.
- Never silently revive a retracted/superseded claim.
- A citation proving that text exists is not automatically proof that the quote
  semantically establishes the whole claim; preserve the project's distinction
  between citation verification and support verification.

## Local publish workflow

From the repository root on the local PC:

```bat
python ecu-kb\kb.py check
python ecu-kb\remote_bridge.py export
python ecu-kb\remote_bridge.py check
```

Then commit the generated `ecu-kb/remote/` files. The repository agent policy
requires this after any meaningful KB mutation.

The exporter refuses to publish when `kb.py check` fails unless
`--skip-check` is explicitly supplied. Skipping is only for debugging and must
not be used for a normal published snapshot.

## What is exported

- current non-retracted claims;
- retracted/superseded claim history with reasons;
- claim citation snippets and provenance metadata;
- gaps;
- conflicts;
- full A2L object catalogue, split by function group;
- snapshot statistics and SHA-256 checksums.

## What is never exported

- raw PDF/library corpus;
- SQLite database;
- firmware binaries;
- full literature chunks unrelated to a claim.

This boundary preserves the local/offline design while giving remote AI clients
enough evidence to act as a narrow project specialist.

## Query without SQLite

A cloned repository can query the exported snapshot:

```bat
python ecu-kb\remote_bridge.py query "PCR_rBPCtlBas_MAP"
python ecu-kb\remote_bridge.py query "BV39 safe boost"
```

The command returns matching claims, gaps and A2L objects in JSON.

## ChatGPT session procedure

When the user asks about this ECU project, ChatGPT should:

1. Fetch `ecu-kb/remote/manifest.json`.
2. Check `snapshot_state`, generation time, profile and `integrity.kb_check`.
   A usable specialist snapshot requires `snapshot_state=CANONICAL_DB_EXPORT` and
   `integrity.kb_check=PASSED`; unchecked exports are diagnostics only.
3. Fetch only the smallest relevant generated file(s).
4. Answer from claims/A2L/provenance; use project docs for additional context.
5. If the snapshot is missing or stale, say that the canonical local DB state is
   not currently published and fall back to versioned claim files only with an
   explicit limitation.
6. When a new verified fact is discovered, it should be written back through the
   local claims workflow first; the remote snapshot is an export, never the place
   to edit truth directly.


## Corpus lookup rule

When a question depends on an external DAMOS/A2L/ORI/SGO candidate, inspect
`ecu-kb/remote/corpus.json` before using it.

- `EXACT` may be used as an identity candidate, but its contents still require
  local/hash verification before becoming project evidence.
- `SAME_HW_SIBLING` can support structural comparison, not fixed target addresses.
- `SAME_PROJECT_FAMILY` and `STRUCTURAL_ANALOG` are discovery/shape references only.
- Vendor/community metadata is never upgraded to OEM truth merely because the
  part number looks plausible.
