# Architecture review — ECU knowledge system and remote specialist access

Date: 2026-09-18

## Scope

Reviewed:
- `ecu-kb/schema.sql`
- `ecu-kb/kb.py`
- `ecu-kb/specialist.py`
- versioned claim files
- `CURRENT_STATE.md`
- boost/fuel control-path documents
- `PROMPT_FOR_CHATGPT.md`
- repository agent policy

Goal: make the evidence system usable by an external AI client through GitHub
without exposing the canonical SQLite database or duplicating full corpus contents
into the generated remote snapshot.

## What is already strong

### 1. Evidence model is materially better than ordinary RAG

The project separates:
- evidence kind;
- verification state;
- source class;
- confidence;
- missing evidence;
- citations;
- retractions/supersession;
- explicit gaps;
- applicability to ECU/SW.

The deterministic citation check and the explicit distinction between project
drafts and external evidence are particularly important.

### 2. The canonical DB is correctly kept out of Git

`ecu-kb/knowledge/kb.sqlite3*` remains local and rebuildable. During this review,
the repository policy changed in parallel: the current `main` now tracks a
substantial source library under `base-knowledge/library/`, including OEM PDFs.
Therefore the old blanket statement “the corpus is never in Git” is no longer
true. The important invariant for this bridge is narrower: `ecu-kb/remote/`
must not duplicate the SQLite DB, firmware binaries, or arbitrary full literature
chunks. A file being tracked in the repository does not automatically make it
verified/applicable evidence in the KB.

### 3. A2L is treated as a distinct source class

The schema does not mix A2L objects with literature chunks. That is correct:
A2L is direct project/SW evidence about symbols and metadata, not general
technical literature.

### 4. Retractions are first-class

The system can preserve why an earlier belief was superseded instead of silently
rewriting history. This is essential for a long-running calibration project.

## Critical issues found

### P0 — external AI had no access to canonical current DB state

Before this change, ChatGPT could read GitHub documents and claim source files,
but not:
- current retraction state;
- current gap status;
- DB-only review metadata;
- current conflict table;
- the full A2L catalogue in a compact remote form.

Therefore GitHub review was not equivalent to consulting the knowledge base.

**Fix:** `ecu-kb/remote_bridge.py` exports a read-only canonical snapshot from
SQLite into `ecu-kb/remote/`.

### P0 — `specialist.py` contained its own technical “truth”

The previous specialist hard-coded:
- turbo identity details;
- a physical-risk conclusion around 2.4–2.6 bar;
- a project-stage restriction.

That creates a second truth store outside claims. It had already drifted from
newer turbo designation claims.

**Fix:** specialist logic now contains retrieval/inference-routing rules only.
Technical facts must come from SQLite or the generated snapshot.

### P0 — `PROMPT_FOR_CHATGPT.md` contained stale factual conclusions

The prompt included mutable technical conclusions, including a PoI2 causal
statement that is weaker than the current claim state.

A system prompt cannot safely be a knowledge database.

**Fix:** the prompt is now protocol-driven. It tells ChatGPT how to retrieve and
interpret the current snapshot rather than embedding mutable project facts.

## Important issues / limitations that remain

### P1 — semantic support is still human-reviewed

`kb check` proves that a cited quote exists in an ingested chunk. It does not
prove that the quote semantically establishes the whole claim.

This is an intentional and defensible boundary. Do not “solve” it by silently
letting an LLM mark its own semantic support as verified.

Recommended future addition:
- explicit reviewer workflow for `reviewed_by/reviewed_at`;
- optional second-session review queue;
- report of support claims with `reviewed_by IS NULL`.

### P1 — remote snapshot freshness is operational, not automatic infrastructure

The snapshot can only reflect the local DB after export.

Mitigations added:
- mandatory publish rule in `AGENTS.md`;
- `scripts/Publish-KBRemoteSnapshot.ps1`;
- generation timestamp;
- snapshot state;
- SHA-256 for generated files;
- logical snapshot fingerprint;
- explicit retraction export;
- consumer-side rejection of unchecked/non-canonical snapshots;
- exporter refuses normal publish when `kb.py check` fails.

Still, a machine that never runs/pushes the exporter will leave remote AI with
an old snapshot. ChatGPT must always inspect `generated_at_utc` first.

### P1 — remote snapshot intentionally does not mirror arbitrary literature

The generated specialist snapshot carries citation snippets attached to claims,
not full literature chunks. The repository itself currently tracks part of the
source library, so a GitHub-capable client may inspect a particular tracked
source when necessary; that source still must pass the KB applicability/evidence
rules before it supports a project claim.

For material not tracked or not ingested, the local agent must run `kb search`,
create/review a claim or document the gap, then republish.

### P1 — claim source JSON and SQLite are different layers

Versioned `claims/*.json` files are inputs/history. SQLite contains current
runtime state, including retractions and status changes.

External clients must not reconstruct current truth by naively concatenating all
claim JSON files. The remote snapshot exists specifically to solve this.

## New remote specialist architecture

```
local raw corpus / A2L / logs / BIN
            |
            v
      ecu-kb SQLite
   (canonical mutable state)
            |
      kb.py check  ----X----> block publish on integrity failure
            |
            v
   remote_bridge.py
            |
            v
      ecu-kb/remote/
        manifest.json
        claims.json
        retractions.json
        gaps.json
        conflicts.json
        a2l/<group>.json
            |
            v
  GitHub connector / ChatGPT
            |
            v
 evidence-aware specialist answer
```

The remote layer is strictly read-only. New truth must always flow back through
the local claims/retraction workflow first.

## Files added/changed

- Added `ecu-kb/remote_bridge.py`
- Added `docs/CHATGPT-KB-BRIDGE.md`
- Added `ecu-kb/remote/README.md`
- Added `scripts/Publish-KBRemoteSnapshot.ps1`
- Added `ecu-kb/tests/test_remote_bridge.py`
- Added `.github/workflows/kb-bridge-tests.yml`
- Refactored `ecu-kb/specialist.py`
- Reworked `PROMPT_FOR_CHATGPT.md`
- Extended `AGENTS.md` with mandatory remote snapshot refresh policy

## Required local validation before considering the bridge live

Run on the project PC:

```bat
python -m unittest discover ecu-kb\tests
python ecu-kb\kb.py check
python ecu-kb\remote_bridge.py export
python ecu-kb\remote_bridge.py check
```

Then commit/push the generated `ecu-kb/remote/` files.

Once `ecu-kb/remote/manifest.json` is present on GitHub with
`snapshot_state=CANONICAL_DB_EXPORT` and `integrity.kb_check=PASSED`,
ChatGPT can use the repository as a
narrow specialist view of the current canonical KB rather than merely reviewing
static project documents.
