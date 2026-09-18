# -*- coding: utf-8 -*-
"""
calharness - Open-source based calibration harness for Bosch EDC16 ECU systems.
"""

from calharness.a2l_catalog import A2LCatalog, A2LConverter, UnsupportedConversionError
from calharness.decoder import MapDecoder
from calharness.address_space import AddressSpace
from calharness.record_layout import RecordLayoutResolver, ResolvedLayout
from calharness.diff_engine import (
    CHECKSUM_RANGES,
    ByteCategory,
    ByteDiffClassification,
    CellDiff,
    MapDiffSummary,
    SemanticDiffEngine,
    SemanticDiffReport,
)
from calharness.models import AxisData, DecodedMap, FirmwareIdentity
from calharness.checksum import ChecksumInspectionReport, ChecksumInspector
from calharness.rules import (
    DEFAULT_RULES,
    N75_MAX_CONTROL_BOUND_PCT,
    N75_MIN_CONTROL_BOUND_PCT,
    ProvenanceKind,
    ProvenanceRecord,
    RuleKind,
    SafetyRule,
    SafetyWaiver,
)
from calharness.provenance_verifier import KBProvenanceVerifier, ProvenanceVerificationError
from calharness.log_analyzer import (
    LimiterBottleneck,
    LimiterMetrics,
    LogAnalysisReport,
    LogAnalyzer,
    LogFormat,
    PullKind,
    TelemetryPoint,
    WOTSegmentMetrics,
)
from calharness.correlator import (
    AxisResolverRegistry,
    AxisSignal,
    AxisSignalResolver,
    CellExposure,
    ComparisonKind,
    CorrelatorMode,
    MapCorrelator,
    MapExposureReport,
    ObservedComparison,
    PointCorrelation,
    SemanticMatchLevel,
    SignalProvenanceKind,
    SignalSourceKind,
    TorqueToFuelConverter,
    UncertaintyStatus,
)
from calharness.safety_validator import (
    SafetyAuditReport,
    SafetyLevel,
    SafetyRuleResult,
    SafetyValidator,
)

__all__ = [
    "A2LCatalog",
    "A2LConverter",
    "UnsupportedConversionError",
    "AddressSpace",
    "CHECKSUM_RANGES",
    "MapDecoder",
    "RecordLayoutResolver",
    "ResolvedLayout",
    "AxisData",
    "DecodedMap",
    "FirmwareIdentity",
    "ByteCategory",
    "ByteDiffClassification",
    "CellDiff",
    "MapDiffSummary",
    "SemanticDiffEngine",
    "SemanticDiffReport",
    "SafetyLevel",
    "SafetyRuleResult",
    "SafetyAuditReport",
    "SafetyValidator",
    "ChecksumInspector",
    "ChecksumInspectionReport",
    "SafetyRule",
    "SafetyWaiver",
    "KBProvenanceVerifier",
    "ProvenanceVerificationError",
    "ProvenanceRecord",
    "ProvenanceKind",
    "RuleKind",
    "DEFAULT_RULES",
    "N75_MIN_CONTROL_BOUND_PCT",
    "N75_MAX_CONTROL_BOUND_PCT",
    "LogAnalyzer",
    "LogAnalysisReport",
    "WOTSegmentMetrics",
    "LimiterBottleneck",
    "LimiterMetrics",
    "PullKind",
    "LogFormat",
    "TelemetryPoint",
    "MapCorrelator",
    "TorqueToFuelConverter",
    "AxisResolverRegistry",
    "AxisSignalResolver",
    "SignalProvenanceKind",
    "SignalSourceKind",
    "SemanticMatchLevel",
    "UncertaintyStatus",
    "ComparisonKind",
    "CorrelatorMode",
    "AxisSignal",
    "CellExposure",
    "ObservedComparison",
    "PointCorrelation",
    "MapExposureReport",
]



