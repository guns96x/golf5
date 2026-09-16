# Research ledger — plan: C:/Users/pavlo/golf5/START-HERE.md

Scope: authenticated forum research plus local regeneration evidence audit, following the next actions in START-HERE.md. The requested subagent-driven-development skill is applied as bounded analysis, report and separate review; this is not a Git checkout and no firmware/code implementation or branch integration is requested.

- Browser authentication: verified 2026-09-10; private technical sections and search available.
- Task 1: local regeneration evidence audit — `task-1-report.md`, DONE_WITH_CONCERNS; 12 A2L/runtime entries, extents and raw bytes checked. Concerns are expected missing ECU readback, Auto-Scan/logs, physical checks and Bosch checksum validation.
- Forum research: `forum-findings.md`; exact BLS/03G906021QJ topic, user's historical symptom topic, EGT/aftertreatment context, white-smoke comparison, MPPS/checksum cases, and 2 MiB versus partial-read context recorded with stable links.
- User clarification 2026-09-10: VCDS on the OFF firmware does not expose emissions-related parameters. Groups 070/075 are therefore not an available validation channel for this configuration; absence is not treated as proof of all-path disablement.
- Internet original supplied 2026-09-10: ZIP/BIN hashes and byte comparisons recorded in `internet-original-comparison.md`. Its `0x180000–0x1FFFFF` region is byte-identical to the HEX/S19-derived reference; the leading `0x180000` bytes are `FF`.
- Review: independent reviewer dispatch failed on account usage limit after the implementer completed; main agent performed focused source/hash self-review and recorded this limitation.
- Main agent added and independently verified a second review-only duration-isolation candidate; source hashes and exact 229-byte change set are recorded in `deep-audit/repair-manifests.review-only.json`. No ECU write was performed.
- Preserve original ECU files; no posting or uploads authorized.
