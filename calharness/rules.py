# -*- coding: utf-8 -*-
"""
calharness.rules

Provenance-backed calibration safety rules and constraints.
Every numerical threshold and structural invariant links to an explicit source,
KB claim ID, or project policy definition.
"""

from __future__ import annotations

import enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class RuleKind(str, enum.Enum):
    """Categorization of safety rules."""
    STRUCTURAL_INVARIANT = "STRUCTURAL_INVARIANT"  # Non-negotiable binary/firmware architecture rules
    PHYSICAL_THRESHOLD = "PHYSICAL_THRESHOLD"      # Physical engineering limits (boost, torque, temperature)
    CALIBRATION_POLICY = "CALIBRATION_POLICY"      # Project-specific tuning policy guidelines


class ProvenanceKind(str, enum.Enum):
    """Source authority level for a given rule or threshold."""
    VERIFIED_OEM_SPEC = "VERIFIED_OEM_SPEC"        # Verified against official OEM technical documentation / datasheet
    PROJECT_VERIFIED = "PROJECT_VERIFIED"          # Verified empirically against exact project SW/A2L/BIN layout
    PROJECT_POLICY = "PROJECT_POLICY"              # Explicit project architectural policy decision
    UNVERIFIED_CANDIDATE = "UNVERIFIED_CANDIDATE"  # Community heuristic / unproven threshold needing evidence


class SafetyWaiver(BaseModel):
    """Machine-verifiable calibration modification waiver."""
    model_config = ConfigDict(extra="forbid")

    waiver_id: str
    map_name: str
    reason: str
    approved_by: str
    scope: str
    evidence_ref: Optional[str] = None
    expiration_date: Optional[str] = None
    authorization_ref: Optional[str] = None


class ProvenanceRecord(BaseModel):
    """Provenance tracking metadata for a safety rule or threshold."""
    model_config = ConfigDict(extra="forbid")

    source: str
    kind: ProvenanceKind
    claim_id: Optional[int] = None
    claim_key: Optional[str] = None
    constraint_claims: List[str] = Field(default_factory=list)
    statement_hash: Optional[str] = None
    citation: Optional[str] = None
    notes: Optional[str] = None


class SafetyRule(BaseModel):
    """
    Definition of a calibration safety rule.
    
    Evaluation semantics:
      - VERIFIED_OEM_SPEC:
          within limit -> PASS
          exceeded     -> HARD_FAIL
      - PROJECT_VERIFIED / PROJECT_POLICY structural invariants:
          intact       -> PASS
          violated     -> HARD_FAIL
      - UNVERIFIED_CANDIDATE:
          within limit -> UNVERIFIED (cannot prove safety without evidence)
          exceeded     -> NEEDS_EVIDENCE
    """
    model_config = ConfigDict(extra="forbid")

    rule_id: str
    name: str
    rule_kind: RuleKind
    provenance: ProvenanceRecord
    target_parameter: Optional[str] = None
    threshold_value: Optional[float] = None
    unit: Optional[str] = None
    operator: Optional[str] = None  # e.g., "<=", ">="
    description: Optional[str] = None


# Default rules catalog with explicit provenance linkage
DEFAULT_RULES: List[SafetyRule] = [
    # --- 1. Structural Invariants (HARD_FAIL on breach) ---
    SafetyRule(
        rule_id="RULE_CODE_AREA_INTACT",
        name="MPC562 Program Code Area Integrity",
        rule_kind=RuleKind.STRUCTURAL_INVARIANT,
        provenance=ProvenanceRecord(
            source="EDC16U34 SW 1037391847 Binary Layout",
            kind=ProvenanceKind.PROJECT_VERIFIED,
            citation="External Flash 0x000000..0x17FFFF verified as MPC562 PowerPC executable microcode space.",
            notes="Modifying program code via calibration harness is forbidden.",
        ),
        description="Ensures executable firmware space (< 0x180000) is untouched.",
    ),
    SafetyRule(
        rule_id="RULE_IDENTITY_AREA_INTACT",
        name="Firmware Identity Block Integrity",
        rule_kind=RuleKind.STRUCTURAL_INVARIANT,
        provenance=ProvenanceRecord(
            source="EDC16U34 SW 1037391847 Identity Strings",
            kind=ProvenanceKind.PROJECT_VERIFIED,
            citation="Offsets 0x010150, 0x040010, 0x180010, 0x1C0010, 0x1C0CBE verified to hold part number and SW ID strings.",
            notes="Identity modifications cause diagnostic mismatches and immobilizer rejections.",
        ),
        description="Protects VAG part numbers and Bosch SW identification strings.",
    ),
    SafetyRule(
        rule_id="RULE_MAP_HEADERS_INTACT",
        name="Map Dimension Header Integrity",
        rule_kind=RuleKind.STRUCTURAL_INVARIANT,
        provenance=ProvenanceRecord(
            source="A2L ASAP2 Deposit Specifications (Kf_Xs16_Ys16_Ws16 / Kl_Xs16_Ws16)",
            kind=ProvenanceKind.PROJECT_VERIFIED,
            citation="Dimension words (nx, ny) establish compiled table indexing offsets in calibration memory.",
            notes="Modifying nx/ny desynchronizes data indexing relative to compiled table lookup routines.",
        ),
        description="Verifies map dimension headers (nx, ny) are not altered.",
    ),
    SafetyRule(
        rule_id="RULE_NO_UNMAPPED_CALIBRATION",
        name="Zero Unmapped Calibration Modifications",
        rule_kind=RuleKind.STRUCTURAL_INVARIANT,
        provenance=ProvenanceRecord(
            source="Project 100% Byte Accounting Policy",
            kind=ProvenanceKind.PROJECT_POLICY,
            citation="Every modified byte in calibration space (0x180000..0x1FDFFF) must map to an authorized A2L characteristic or project checksum block.",
            notes="Prevents silent or unmapped byte corruption.",
        ),
        description="Guarantees every diff byte belongs to a known A2L symbol or checksum block.",
    ),

    # --- 2. Physical / Engineering Thresholds (UNVERIFIED / NEEDS_EVIDENCE) ---
    SafetyRule(
        rule_id="RULE_BOOST_LIMIT",
        name="BorgWarner BV39 Turbo Boost Safety Limit",
        rule_kind=RuleKind.PHYSICAL_THRESHOLD,
        target_parameter="PCR_pBDesBas_MAP",
        threshold_value=2350.0,
        unit="hPa",
        operator="<=",
        provenance=ProvenanceRecord(
            source="Project candidate calibration threshold",
            kind=ProvenanceKind.UNVERIFIED_CANDIDATE,
            constraint_claims=["turbo-bv39-boost-envelope-unresolved"],
            citation="Continuous safe operating envelope for BV39A-0072 / 03G253014M is not documented in OEM datasheets.",
            notes=(
                "Canonical KB constraint claim turbo-bv39-boost-envelope-unresolved states that the currently ingested "
                "evidence contains no OEM compressor map or continuous allowable boost rating specific to BV39A-0072 / "
                "NE 1003/1756-00002. Therefore 2350 mbar remains a project UNVERIFIED_CANDIDATE threshold."
            ),
        ),
        description="Target boost pressure ceiling for BorgWarner BV39 turbocharger (Bank 1).",
    ),
    SafetyRule(
        rule_id="RULE_BOOST_LIMIT_2",
        name="BorgWarner BV39 Turbo Boost Safety Limit (Bank 2 / Variant)",
        rule_kind=RuleKind.PHYSICAL_THRESHOLD,
        target_parameter="PCR_pBDesBas2_MAP",
        threshold_value=2350.0,
        unit="hPa",
        operator="<=",
        provenance=ProvenanceRecord(
            source="Project candidate calibration threshold",
            kind=ProvenanceKind.UNVERIFIED_CANDIDATE,
            constraint_claims=["turbo-bv39-boost-envelope-unresolved"],
            citation="Continuous safe operating envelope for BV39A-0072 / 03G253014M is not documented in OEM datasheets.",
            notes="Evaluates candidate boost boundary for secondary/variant boost baseline map.",
        ),
        description="Target boost pressure ceiling for variant boost baseline map.",
    ),
    SafetyRule(
        rule_id="RULE_TORQUE_LIMIT",
        name="Engine Connecting Rod Mechanical Torque Limit (Gear 0)",
        rule_kind=RuleKind.PHYSICAL_THRESHOLD,
        target_parameter="AccPed_trqEng0_MAP",
        threshold_value=380.0,
        unit="Nm",
        operator="<=",
        provenance=ProvenanceRecord(
            source="Project candidate calibration threshold",
            kind=ProvenanceKind.UNVERIFIED_CANDIDATE,
            citation="Maximum engine torque request ceiling candidate. Mechanical connecting rod fatigue limits for BLS are unverified in OEM documentation.",
            notes=(
                "Unverified candidate: within limit -> UNVERIFIED; exceeded -> NEEDS_EVIDENCE. "
                "Note: Tuned BIN observation in Claim #71 records 380.7 Nm in EngPrt_trqLimP_MAP as calibration context, not physical proof."
            ),
        ),
        description="Maximum engine torque request ceiling to protect BLS rods and DMF (Gear 0).",
    ),
    SafetyRule(
        rule_id="RULE_TORQUE_LIMIT_DW1",
        name="Driver Wish Torque Limit (Gear 1)",
        rule_kind=RuleKind.PHYSICAL_THRESHOLD,
        target_parameter="AccPed_trqEng1_MAP",
        threshold_value=380.0,
        unit="Nm",
        operator="<=",
        provenance=ProvenanceRecord(
            source="Project candidate calibration threshold",
            kind=ProvenanceKind.UNVERIFIED_CANDIDATE,
            citation="Driver wish torque map for Gear 1 candidate ceiling.",
            notes="Unverified candidate ceiling.",
        ),
        description="Maximum driver wish torque request ceiling (Gear 1).",
    ),
    SafetyRule(
        rule_id="RULE_TORQUE_LIMIT_DW2",
        name="Driver Wish Torque Limit (Gear 2)",
        rule_kind=RuleKind.PHYSICAL_THRESHOLD,
        target_parameter="AccPed_trqEng2_MAP",
        threshold_value=380.0,
        unit="Nm",
        operator="<=",
        provenance=ProvenanceRecord(
            source="Project candidate calibration threshold",
            kind=ProvenanceKind.UNVERIFIED_CANDIDATE,
            citation="Driver wish torque map for Gear 2 candidate ceiling.",
            notes="Unverified candidate ceiling.",
        ),
        description="Maximum driver wish torque request ceiling (Gear 2).",
    ),
    SafetyRule(
        rule_id="RULE_TORQUE_LIMIT_DW3",
        name="Driver Wish Torque Limit (Gear 3)",
        rule_kind=RuleKind.PHYSICAL_THRESHOLD,
        target_parameter="AccPed_trqEng3_MAP",
        threshold_value=380.0,
        unit="Nm",
        operator="<=",
        provenance=ProvenanceRecord(
            source="Project candidate calibration threshold",
            kind=ProvenanceKind.UNVERIFIED_CANDIDATE,
            citation="Driver wish torque map for Gear 3 candidate ceiling.",
            notes="Unverified candidate ceiling.",
        ),
        description="Maximum driver wish torque request ceiling (Gear 3).",
    ),
    SafetyRule(
        rule_id="RULE_TORQUE_LIMIT_DW4",
        name="Driver Wish Torque Limit (Gear 4)",
        rule_kind=RuleKind.PHYSICAL_THRESHOLD,
        target_parameter="AccPed_trqEng4_MAP",
        threshold_value=380.0,
        unit="Nm",
        operator="<=",
        provenance=ProvenanceRecord(
            source="Project candidate calibration threshold",
            kind=ProvenanceKind.UNVERIFIED_CANDIDATE,
            citation="Driver wish torque map for Gear 4 candidate ceiling.",
            notes="Unverified candidate ceiling.",
        ),
        description="Maximum driver wish torque request ceiling (Gear 4).",
    ),
    SafetyRule(
        rule_id="RULE_TORQUE_LIMIT_DW5",
        name="Driver Wish Torque Limit (Gear 5)",
        rule_kind=RuleKind.PHYSICAL_THRESHOLD,
        target_parameter="AccPed_trqEng5_MAP",
        threshold_value=380.0,
        unit="Nm",
        operator="<=",
        provenance=ProvenanceRecord(
            source="Project candidate calibration threshold",
            kind=ProvenanceKind.UNVERIFIED_CANDIDATE,
            citation="Driver wish torque map for Gear 5 candidate ceiling.",
            notes="Unverified candidate ceiling.",
        ),
        description="Maximum driver wish torque request ceiling (Gear 5).",
    ),
    SafetyRule(
        rule_id="RULE_TORQUE_LIMIT_DW6",
        name="Driver Wish Torque Limit (Gear 6)",
        rule_kind=RuleKind.PHYSICAL_THRESHOLD,
        target_parameter="AccPed_trqEng6_MAP",
        threshold_value=380.0,
        unit="Nm",
        operator="<=",
        provenance=ProvenanceRecord(
            source="Project candidate calibration threshold",
            kind=ProvenanceKind.UNVERIFIED_CANDIDATE,
            citation="Driver wish torque map for Gear 6 candidate ceiling.",
            notes="Unverified candidate ceiling.",
        ),
        description="Maximum driver wish torque request ceiling (Gear 6).",
    ),
    SafetyRule(
        rule_id="RULE_TORQUE_LIMIT_ENGPRT",
        name="Engine Protection Main Torque Limiter",
        rule_kind=RuleKind.PHYSICAL_THRESHOLD,
        target_parameter="EngPrt_trqLimP_MAP",
        threshold_value=380.0,
        unit="Nm",
        operator="<=",
        provenance=ProvenanceRecord(
            source="Project candidate calibration threshold",
            kind=ProvenanceKind.UNVERIFIED_CANDIDATE,
            citation="Main torque limiter vs ambient pressure candidate ceiling.",
            notes="Unverified candidate ceiling.",
        ),
        description="Main torque limiter vs atmospheric pressure candidate ceiling.",
    ),
    SafetyRule(
        rule_id="RULE_SMOKE_LIMIT",
        name="Pumpe-Düse Injector Delivery Ceiling (Boost Pressure Based)",
        rule_kind=RuleKind.PHYSICAL_THRESHOLD,
        target_parameter="FlMng_qPresSmoke_MAP",
        threshold_value=65.0,
        unit="mg/hub",
        operator="<=",
        provenance=ProvenanceRecord(
            source="Project candidate calibration threshold",
            kind=ProvenanceKind.UNVERIFIED_CANDIDATE,
            citation="Stock PDE-P2 038130073BN nozzle maximum delivery estimate without factory test bench calibration sheet.",
            notes="Unverified candidate: within limit -> UNVERIFIED; exceeded -> NEEDS_EVIDENCE.",
        ),
        description="Fuel delivery ceiling per stroke on stock PDE-P2 nozzles (Boost MAP based).",
    ),
    SafetyRule(
        rule_id="RULE_SMOKE_LIMIT_MAF",
        name="Pumpe-Düse Injector Delivery Ceiling (Air Mass Based)",
        rule_kind=RuleKind.PHYSICAL_THRESHOLD,
        target_parameter="FlMng_qAFSCDSmoke_MAP",
        threshold_value=65.0,
        unit="mg/hub",
        operator="<=",
        provenance=ProvenanceRecord(
            source="Project candidate calibration threshold",
            kind=ProvenanceKind.UNVERIFIED_CANDIDATE,
            citation="Stock PDE-P2 038130073BN nozzle maximum delivery estimate without factory test bench calibration sheet.",
            notes="Unverified candidate: within limit -> UNVERIFIED; exceeded -> NEEDS_EVIDENCE.",
        ),
        description="Fuel delivery ceiling per stroke on stock PDE-P2 nozzles (Air mass MAF based).",
    ),
    SafetyRule(
        rule_id="RULE_SOI_LIMIT",
        name="Start of Injection Cylinder Overpressure Limit",
        rule_kind=RuleKind.PHYSICAL_THRESHOLD,
        target_parameter="InjCrv_phiBasGear34_MAP",
        threshold_value=30.0,
        unit="deg BTDC",
        operator="<=",
        provenance=ProvenanceRecord(
            source="Direct-Injection Diesel Thermodynamic Heuristics",
            kind=ProvenanceKind.UNVERIFIED_CANDIDATE,
            citation="30° BTDC empirical threshold to limit peak cylinder firing pressure (Pmax). Exact in-cylinder pressure transducer data missing.",
            notes="Unverified candidate: within limit -> UNVERIFIED; exceeded -> NEEDS_EVIDENCE.",
        ),
        description="Maximum injection advance angle before top dead center.",
    ),

    # --- 3. Calibration Policy Guidelines (WARNING on breach) ---
    SafetyRule(
        rule_id="RULE_AXIS_NODE_INTEGRITY",
        name="Axis Breakpoint Rescale Inspection",
        rule_kind=RuleKind.CALIBRATION_POLICY,
        provenance=ProvenanceRecord(
            source="Project Calibration Policy",
            kind=ProvenanceKind.PROJECT_POLICY,
            citation="Rescaling axis breakpoint nodes alters interpolation grid across operating ranges.",
            notes="Tuning best practice flags axis modifications for manual verification.",
        ),
        description="Flags modified axis breakpoint nodes for verification.",
    ),
    SafetyRule(
        rule_id="RULE_N75_CONTROL_BOUNDS",
        name="N75 Solenoid Linear Control Margin",
        rule_kind=RuleKind.CALIBRATION_POLICY,
        provenance=ProvenanceRecord(
            source="VNT Actuator Control Policy",
            kind=ProvenanceKind.PROJECT_POLICY,
            citation="Duty cycle outside 10%..85% indicates governor operating near vacuum actuator saturation margins.",
            notes="Observational metric for control headroom, not proof of mechanical failure.",
        ),
        description="Tracks governor duty cycle saturation boundaries (<= 10% or >= 85%).",
    ),
]

# Provenance-backed control policy thresholds
N75_MIN_CONTROL_BOUND_PCT = 10.0  # Duty cycle lower control margin (dumping boost)
N75_MAX_CONTROL_BOUND_PCT = 85.0  # Duty cycle upper control margin (building boost)
