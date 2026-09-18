# -*- coding: utf-8 -*-
"""
calharness.safety_validator

Production Safety Validator:
Performs strict, provenance-backed validation of semantic diffs against:
  1. Structural Invariants (MPC562 executable code integrity, identity blocks, map headers, unmapped bytes) -> HARD_FAIL
  2. Physical Engineering Limits with Provenance Linkage:
       - VERIFIED_OEM_SPEC: within limit -> PASS; exceeded -> HARD_FAIL
       - UNVERIFIED_CANDIDATE: within limit -> UNVERIFIED; exceeded -> NEEDS_EVIDENCE
  3. Calibration Policies (Axis node rescaling, etc.) -> WARNING
"""

from __future__ import annotations

import enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from calharness.diff_engine import ByteCategory, SemanticDiffReport
from calharness.rules import (
    DEFAULT_RULES,
    ProvenanceKind,
    ProvenanceRecord,
    RuleKind,
    SafetyRule,
)


class SafetyLevel(str, enum.Enum):
    """Severity and epistemic level of a safety check result."""
    PASS = "PASS"                      # Formally verified requirement met
    UNVERIFIED = "UNVERIFIED"          # Within candidate threshold, but threshold itself lacks evidence
    WARNING = "WARNING"                # Advisory tuning policy deviation
    NEEDS_EVIDENCE = "NEEDS_EVIDENCE"  # Exceeds candidate threshold; evidence required
    HARD_FAIL = "HARD_FAIL"            # Non-negotiable structural invariant violation or OEM limit breach
    NOT_EVALUATED = "NOT_EVALUATED"    # Rule target map was not modified in diff


class SafetyRuleResult(BaseModel):
    """Result of an individual safety rule evaluation with full provenance."""
    model_config = ConfigDict(extra="forbid")

    rule_id: str
    name: str
    level: SafetyLevel
    message: str
    rule_kind: RuleKind
    provenance: ProvenanceRecord
    details: Optional[Dict[str, Any]] = None


class SafetyAuditReport(BaseModel):
    """Comprehensive safety audit report with distinct structural and epistemic verdicts."""
    model_config = ConfigDict(extra="forbid")

    overall_verdict: SafetyLevel
    total_rules_evaluated: int
    hard_fails_count: int
    needs_evidence_count: int
    unverified_count: int
    warnings_count: int
    not_evaluated_count: int = 0
    rule_results: List[SafetyRuleResult] = Field(default_factory=list)
    a2l_sha256: Optional[str] = None
    bin_sha256: Optional[str] = None

    @property
    def is_structurally_sound(self) -> bool:
        """True if all non-negotiable binary structural invariants passed (zero HARD_FAIL)."""
        return self.hard_fails_count == 0

    @property
    def is_safe(self) -> bool:
        """True only if structurally sound AND all evaluated rules have verified provenance without pending evidence."""
        return (
            self.hard_fails_count == 0
            and self.needs_evidence_count == 0
            and self.unverified_count == 0
        )

    def summary(self) -> str:
        """Human-readable summary of safety audit."""
        verdict_str = f"[{self.overall_verdict.value}]"
        lines = [
            f"Safety Audit: {verdict_str} (Overall Verdict: {self.overall_verdict.value})",
            f"  - Structural Soundness: {'PASS' if self.is_structurally_sound else 'HARD FAIL'}",
            f"  - Hard Fails:     {self.hard_fails_count}",
            f"  - Needs Evidence: {self.needs_evidence_count}",
            f"  - Unverified:     {self.unverified_count}",
            f"  - Warnings:       {self.warnings_count}",
            f"  - Total Rules:    {self.total_rules_evaluated}",
        ]
        if self.hard_fails_count > 0:
            lines.append("\n[!] Structural Invariant Violations (HARD FAIL):")
            for r in self.rule_results:
                if r.level == SafetyLevel.HARD_FAIL:
                    lines.append(f"  [X] {r.rule_id} ({r.name}): {r.message}")
        if self.needs_evidence_count > 0:
            lines.append("\n[?] Unproven Limits Exceeded (NEEDS_EVIDENCE):")
            for r in self.rule_results:
                if r.level == SafetyLevel.NEEDS_EVIDENCE:
                    claim_info = f" [Claim #{r.provenance.claim_id}]" if r.provenance.claim_id else ""
                    lines.append(f"  [?] {r.rule_id}: {r.message}{claim_info}")
        if self.unverified_count > 0:
            lines.append("\n[~] Unverified Thresholds (UNVERIFIED / INFO):")
            for r in self.rule_results:
                if r.level == SafetyLevel.UNVERIFIED:
                    lines.append(f"  [~] {r.rule_id}: {r.message}")
        if self.warnings_count > 0:
            lines.append("\n[*] Advisory Warnings (WARNING):")
            for r in self.rule_results:
                if r.level == SafetyLevel.WARNING:
                    lines.append(f"  [*] {r.rule_id}: {r.message}")
        return "\n".join(lines)


class SafetyValidator:
    """
    Evaluates provenance-backed safety rules over a SemanticDiffReport.
    
    Epistemic Principles:
      1. Structural Invariants (code, identity, map headers, unmapped bytes) trigger HARD_FAIL.
      2. VERIFIED_OEM_SPEC: within limit -> PASS; exceeded -> HARD_FAIL.
      3. UNVERIFIED_CANDIDATE: within limit -> UNVERIFIED; exceeded -> NEEDS_EVIDENCE.
         (An unproven threshold cannot prove safety either above or below).
      4. Tuning policy guidelines trigger WARNING.
    """

    def __init__(self, rules: Optional[List[SafetyRule]] = None):
        self.rules = rules if rules is not None else list(DEFAULT_RULES)
        self._rules_by_id = {r.rule_id: r for r in self.rules}

    def validate(self, diff_report: SemanticDiffReport) -> SafetyAuditReport:
        """Run all provenance-backed safety rules against the semantic diff report."""
        results: List[SafetyRuleResult] = []
        maps_by_name = {m.name: m for m in diff_report.maps_changed}

        for rule in self.rules:
            # 1. Structural Invariants
            if rule.rule_kind == RuleKind.STRUCTURAL_INVARIANT:
                if rule.rule_id == "RULE_CODE_AREA_INTACT":
                    if diff_report.code_area_bytes > 0:
                        results.append(
                            SafetyRuleResult(
                                rule_id=rule.rule_id,
                                name=rule.name,
                                level=SafetyLevel.HARD_FAIL,
                                message=f"Code area modified: {diff_report.code_area_bytes:,} bytes changed in executable firmware space (< 0x180000).",
                                rule_kind=rule.rule_kind,
                                provenance=rule.provenance,
                                details={"code_area_bytes": diff_report.code_area_bytes},
                            )
                        )
                    else:
                        results.append(
                            SafetyRuleResult(
                                rule_id=rule.rule_id,
                                name=rule.name,
                                level=SafetyLevel.PASS,
                                message="Code area intact: 0 bytes modified.",
                                rule_kind=rule.rule_kind,
                                provenance=rule.provenance,
                            )
                        )

                elif rule.rule_id == "RULE_IDENTITY_AREA_INTACT":
                    if diff_report.identity_area_bytes > 0:
                        results.append(
                            SafetyRuleResult(
                                rule_id=rule.rule_id,
                                name=rule.name,
                                level=SafetyLevel.HARD_FAIL,
                                message=f"Identity area modified: {diff_report.identity_area_bytes:,} bytes changed in VAG/Bosch software ID block.",
                                rule_kind=rule.rule_kind,
                                provenance=rule.provenance,
                                details={"identity_area_bytes": diff_report.identity_area_bytes},
                            )
                        )
                    else:
                        results.append(
                            SafetyRuleResult(
                                rule_id=rule.rule_id,
                                name=rule.name,
                                level=SafetyLevel.PASS,
                                message="Identity blocks intact: 0 bytes modified.",
                                rule_kind=rule.rule_kind,
                                provenance=rule.provenance,
                            )
                        )

                elif rule.rule_id == "RULE_MAP_HEADERS_INTACT":
                    hdr_bytes = (
                        diff_report.bytes_by_category.get(ByteCategory.MAP_HEADER.value, 0)
                        + diff_report.bytes_by_category.get(ByteCategory.CURVE_HEADER.value, 0)
                    )
                    header_corrupted = (
                        hdr_bytes > 0
                        or any(m.header_changed for m in diff_report.maps_changed)
                    )
                    if header_corrupted:
                        results.append(
                            SafetyRuleResult(
                                rule_id=rule.rule_id,
                                name=rule.name,
                                level=SafetyLevel.HARD_FAIL,
                                message=(
                                    f"Map dimension headers (nx, ny) were modified ({hdr_bytes} header bytes changed). "
                                    "Fixed table indexing bounds corrupted."
                                ),
                                rule_kind=rule.rule_kind,
                                provenance=rule.provenance,
                                details={"header_bytes": hdr_bytes},
                            )
                        )
                    else:
                        results.append(
                            SafetyRuleResult(
                                rule_id=rule.rule_id,
                                name=rule.name,
                                level=SafetyLevel.PASS,
                                message="All map dimension headers are intact.",
                                rule_kind=rule.rule_kind,
                                provenance=rule.provenance,
                            )
                        )

                elif rule.rule_id in ("RULE_NO_UNMAPPED_CALIBRATION", "RULE_NO_UNEXPLAINED_CALIBRATION"):
                    if diff_report.unmapped_bytes > 0:
                        results.append(
                            SafetyRuleResult(
                                rule_id=rule.rule_id,
                                name=rule.name,
                                level=SafetyLevel.HARD_FAIL,
                                message=f"Unmapped bytes detected: {diff_report.unmapped_bytes:,} diff bytes lack A2L symbol ownership or system block mapping.",
                                rule_kind=rule.rule_kind,
                                provenance=rule.provenance,
                                details={"unmapped_bytes": diff_report.unmapped_bytes},
                            )
                        )
                    else:
                        results.append(
                            SafetyRuleResult(
                                rule_id=rule.rule_id,
                                name=rule.name,
                                level=SafetyLevel.PASS,
                                message="All modified calibration bytes are accounted for by A2L characteristics or checksum blocks.",
                                rule_kind=rule.rule_kind,
                                provenance=rule.provenance,
                            )
                        )

            # 2. Physical / Engineering Thresholds
            elif rule.rule_kind == RuleKind.PHYSICAL_THRESHOLD:
                param = rule.target_parameter
                if param and param in maps_by_name:
                    map_diff = maps_by_name[param]
                    observed_val = map_diff.max_new
                    limit = rule.threshold_value

                    is_breached = False
                    if limit is not None:
                        if rule.operator in ("<=", "<", None):
                            is_breached = observed_val > limit
                        elif rule.operator in (">=", ">"):
                            is_breached = observed_val < limit

                    if is_breached:
                        # Breached threshold evaluation
                        if rule.provenance.kind == ProvenanceKind.VERIFIED_OEM_SPEC:
                            level = SafetyLevel.HARD_FAIL
                            msg = (
                                f"{param} max value {observed_val:.1f} {rule.unit or ''} exceeds "
                                f"verified OEM limit ({limit:.1f} {rule.unit or ''})."
                            )
                        else:
                            level = SafetyLevel.NEEDS_EVIDENCE
                            msg = (
                                f"{param} max value {observed_val:.1f} {rule.unit or ''} exceeds "
                                f"unverified candidate threshold ({limit:.1f} {rule.unit or ''}). "
                                f"Requires verified engineering evidence [Claim #{rule.provenance.claim_id or 'N/A'}]."
                            )

                        results.append(
                            SafetyRuleResult(
                                rule_id=rule.rule_id,
                                name=rule.name,
                                level=level,
                                message=msg,
                                rule_kind=rule.rule_kind,
                                provenance=rule.provenance,
                                details={
                                    "target_parameter": param,
                                    "observed_value": observed_val,
                                    "threshold_value": limit,
                                    "claim_id": rule.provenance.claim_id,
                                },
                            )
                        )
                    else:
                        # Within limit threshold evaluation
                        if rule.provenance.kind == ProvenanceKind.VERIFIED_OEM_SPEC:
                            level = SafetyLevel.PASS
                            msg = f"{param} max value {observed_val:.1f} {rule.unit or ''} is within verified OEM limit ({limit:.1f} {rule.unit or ''})."
                        else:
                            level = SafetyLevel.UNVERIFIED
                            msg = (
                                f"{param} max value {observed_val:.1f} {rule.unit or ''} is within "
                                f"candidate threshold ({limit:.1f} {rule.unit or ''}), but threshold is UNVERIFIED. "
                                f"Candidate limit cannot prove safety without evidence."
                            )

                        results.append(
                            SafetyRuleResult(
                                rule_id=rule.rule_id,
                                name=rule.name,
                                level=level,
                                message=msg,
                                rule_kind=rule.rule_kind,
                                provenance=rule.provenance,
                                details={
                                    "target_parameter": param,
                                    "observed_value": observed_val,
                                    "threshold_value": limit,
                                },
                            )
                        )
                else:
                    # M5: Physical rule target map was not modified in diff -> NOT_EVALUATED
                    results.append(
                        SafetyRuleResult(
                            rule_id=rule.rule_id,
                            name=rule.name,
                            level=SafetyLevel.NOT_EVALUATED,
                            message=f"Target parameter '{param}' was not modified in calibration diff.",
                            rule_kind=rule.rule_kind,
                            provenance=rule.provenance,
                            details={"target_parameter": param},
                        )
                    )

            # 3. Calibration Policy
            elif rule.rule_kind == RuleKind.CALIBRATION_POLICY:
                if rule.rule_id == "RULE_AXIS_NODE_INTEGRITY":
                    axis_modified_maps = [m.name for m in diff_report.maps_changed if m.axis_changed]
                    if axis_modified_maps:
                        results.append(
                            SafetyRuleResult(
                                rule_id=rule.rule_id,
                                name=rule.name,
                                level=SafetyLevel.WARNING,
                                message=f"Axis breakpoint nodes modified in {len(axis_modified_maps)} maps: {', '.join(axis_modified_maps[:5])}.",
                                rule_kind=rule.rule_kind,
                                provenance=rule.provenance,
                                details={"maps": axis_modified_maps},
                            )
                        )
                    else:
                        results.append(
                            SafetyRuleResult(
                                rule_id=rule.rule_id,
                                name=rule.name,
                                level=SafetyLevel.PASS,
                                message="All axis breakpoint nodes are intact.",
                                rule_kind=rule.rule_kind,
                                provenance=rule.provenance,
                            )
                        )

        # Calculate counts and overall verdict
        hard_fails = sum(1 for r in results if r.level == SafetyLevel.HARD_FAIL)
        needs_evidence = sum(1 for r in results if r.level == SafetyLevel.NEEDS_EVIDENCE)
        unverified = sum(1 for r in results if r.level == SafetyLevel.UNVERIFIED)
        warnings = sum(1 for r in results if r.level == SafetyLevel.WARNING)
        not_evaluated = sum(1 for r in results if r.level == SafetyLevel.NOT_EVALUATED)

        if hard_fails > 0:
            overall = SafetyLevel.HARD_FAIL
        elif needs_evidence > 0:
            overall = SafetyLevel.NEEDS_EVIDENCE
        elif unverified > 0:
            overall = SafetyLevel.UNVERIFIED
        elif warnings > 0:
            overall = SafetyLevel.WARNING
        else:
            overall = SafetyLevel.PASS

        return SafetyAuditReport(
            overall_verdict=overall,
            total_rules_evaluated=len(results),
            hard_fails_count=hard_fails,
            needs_evidence_count=needs_evidence,
            unverified_count=unverified,
            warnings_count=warnings,
            not_evaluated_count=not_evaluated,
            rule_results=results,
            a2l_sha256=diff_report.a2l_sha256,
            bin_sha256=diff_report.mod_bin_sha256,
        )
