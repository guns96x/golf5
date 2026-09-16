# Deep audit — user requests firmware repair, 2026-09-10

- User confirms symptoms persist: thermostat resolution claim withdrawn.
- User reports similar behavior during regeneration with emissions ON, without visible smoke with DPF fitted. Do not equate this with proof of active regeneration in OFF.
- Main: physical Stage 1 decoding with actual record sizes and conversions; baseline identity, correction strategy and validation.
- Luna off_semantics: exact 311 OFF changes, diagnostics, unresolved regions and AirCtl.
- Luna code_gate_audit: reference program/SGM gate evidence and integrity metadata.
- Working directory is not a Git repository; dedicated deep-audit output directory used. Original binaries remain read-only.
- Stage 1: 4851 changed bytes. 1949 directly named bytes; 395 additional exact reference+Stage1 table-copy bytes; 2231 bytes in structurally consistent alternate maps with runtime symbol attribution NOT proven; 276 bytes remain in two opaque trailers.
- New concrete concern: duration maps changed at same quantity-axis labels, plus torque-to-fuel changes, expanded torque limit without axis extension, and weakened temperature protection. These are calibration concerns; no measured causal diagnosis yet.
- Added a second review-only isolation candidate: `03G906021QJ_stage1-preserving-restore-duration.review.bin` restores 209 duration-map bytes plus 19 thermal-factor bytes and 1 CTSCD diagnostic byte (229 total), while retaining all other Stage 1 and OFF bytes. SHA-256 `c41a1b3eb0b50d8944a0932f2cf0bb904548e0b416559c0232d5f9c17c086b81`. It is not selected, flash-ready or a safety certification.
- User states that vehicle diagnostics/logs will not be available; remaining firmware conclusions are therefore static and cannot prove symptom causality or physical safety.
- No physical acceptance, ECU readback or trusted Bosch checksum verification yet. Do not call a candidate ideal, tested, or flash-ready.
