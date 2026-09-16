# Task 1: Local regeneration evidence audit

Objective: support the ongoing Golf 5 BLS / Bosch EDC16U34 diagnosis by identifying exactly what the existing local files prove about regeneration, post-injection, EGT/LSU changes, and what they cannot prove.

Read START-HERE.md in C:/Users/pavlo/golf5 for the confirmed context and corrected table-size interpretation. Use existing diagnostic-review JSON reports, Python analysis sources and the supplied A2L/BIN as evidence. This is a bounded diagnostic task, not firmware implementation.

Required output:
1. Verify the important OFF changes against existing evidence (actual table extents, byte order, not reserved A2L ranges).
2. Identify up to 12 concrete A2L characteristics or measurements relevant to regeneration state, post-injection and temperature/air control; include descriptions, addresses where applicable, source file and line pointers, and whether ON/OFF differ if reliably determinable.
3. Assess whether supplied A2L/data can establish runtime dependencies or all-path disablement. State missing evidence explicitly, avoid inventing call graphs.
4. Provide a short evidence matrix: observed fact, supported conclusion, remaining uncertainty, practical measurement that would resolve it.

Constraints: preserve all existing files and ECU images. No firmware changes, flashing, checksum correction, web/browser actions, account access or external uploads. Only create task-1-report.md in this directory using apply_patch. Read-only focused shell/Python computations are allowed. Do not run scripts that overwrite existing reports. No Git repo is present; no commits, worktrees or code implementation are requested. Do not treat reference-from-hex.analysis-only.bin as verified factory or flashable image. Do not repeat the retracted working rev-limiter claim. No forced regeneration with removed DPF.

Use only local evidence for this task, not general automotive assertions from memory. Cite exact local line pointers and commands/results. Full report in task-1-report.md; return status DONE / DONE_WITH_CONCERNS / BLOCKED / NEEDS_CONTEXT, validation summary and concerns in at most 15 lines. Self-review before reporting.

Subagent policy: exactly gpt-5.6-luna, explicit high effort for this bounded audit, no nested delegation. At most one clarified retry if needed; main agent owns integration and verification.
