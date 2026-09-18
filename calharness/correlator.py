# -*- coding: utf-8 -*-
"""
calharness.correlator

Evidence-First Map Exposure Engine with Strict Semantic Provenance.
Maps telemetry samples (TelemetryPoint from VCDS or Android OBD logs) onto exact A2L
calibration map meshes (PCR_pBDesBas_MAP, PCR_rBPCtlBas_MAP, FlMng_qPresSmoke_MAP, etc.)
to establish spatial exposure and correlation without assuming causality or issuing
ungrounded tuning advice.

Core Invariants:
  1. Strict Epistemic Discipline: Reports where the engine operated during events
     (exposure), never stating a cell "caused" an overshoot or defect.
  2. Explicit AxisResolverRegistry: Replaces unit-based inferences with explicit
     A2L symbol registrations. Unregistered symbols (e.g. Amb_p_mp, Trq_limGear_mp,
     Inj_qPilot_mp) are strictly rejected as MISSING, regardless of matching units.
  3. Zero Evidence Clamping:
     - STRICT: Out-of-domain points on target maps are dropped.
     - EXPERIMENTAL: Out-of-domain points on target maps are dropped with clear OOD evidence.
     - VISUAL_ONLY: Coordinate clamping allowed for UI inspection, but clamped points
       never accumulate into the evidence cell_hit_matrix.
  4. FMTC_trq2qBas_MAP Domain Bounding: Torque axis ends at ~336 Nm. WOT torque
     requests (> 336 Nm) are marked DERIVED_OUT_OF_DOMAIN and dropped.
  5. Downstream Comparison Accounting: Distinguishes base calibration map outputs from
     downstream ECU control signals (e.g. PCR_pBDesBas_MAP base target vs final Boost
     Specified; PCR_rBPCtlBas_MAP feedforward vs closed-loop N75 duty).
  6. Unquantified Uncertainty: Removes arbitrary percentage guesses (5/8/10%).
     Unmeasured uncertainties are explicitly UNQUANTIFIED with qualitative caveats.
  7. Exact Project Provenance: Grounded in exact project A2L / PROJECT_VERIFIED metadata.
"""

from __future__ import annotations

import enum
import math
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple, Union

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from calharness.decoder import MapDecoder
from calharness.models import AxisData, DecodedMap
from calharness.log_analyzer import TelemetryPoint, WOTSegmentMetrics


class SignalProvenanceKind(str, enum.Enum):
    """Provenance hierarchy of an axis input signal."""
    MEASURED_INTERNAL = "MEASURED_INTERNAL"      # Direct internal ECU variable from RAM/XCP (e.g. PCR_qDes, PCR_qCtl)
    MEASURED_DIAGNOSTIC = "MEASURED_DIAGNOSTIC"  # Standard OBD/VCDS diagnostic channel (e.g. Eng_nAvrg RPM, pInM Boost)
    DERIVED_EXACT = "DERIVED_EXACT"              # Formally proven derivation without unmodeled compensations
    DERIVED_APPROXIMATE = "DERIVED_APPROXIMATE"  # Estimated via proxy calibration (e.g. FMTC within domain)
    DERIVED_OUT_OF_DOMAIN = "DERIVED_OUT_OF_DOMAIN" # Query point falls outside the calibration map's axis boundaries
    MISSING = "MISSING"                          # Signal unavailable or rejected due to semantic mismatch


# Backwards-compatible alias
SignalSourceKind = SignalProvenanceKind


class SemanticMatchLevel(str, enum.Enum):
    """Semantic alignment between target A2L axis definition and telemetry signal."""
    EXACT = "EXACT"                            # Exact 1:1 match of ECU variable and measurement
    PROXY_APPROXIMATE = "PROXY_APPROXIMATE"    # Approximate surrogate with documented lag/error
    MISMATCH = "MISMATCH"                      # Incompatible signal (e.g. raw MAP instead of corrected pressure)


class UncertaintyStatus(str, enum.Enum):
    """Classification of signal uncertainty estimation."""
    QUANTIFIED = "QUANTIFIED"                  # Statistically or empirically quantified
    UNQUANTIFIED = "UNQUANTIFIED"              # Qualitative proxy; numerical error bound is unquantified


class ComparisonKind(str, enum.Enum):
    """Relationship between calibration map output and observed telemetry channel."""
    SAME_SEMANTIC = "SAME_SEMANTIC"            # Direct observation of the same physical variable
    DOWNSTREAM_SIGNAL = "DOWNSTREAM_SIGNAL"    # Observation after downstream closed-loop/environmental compensations
    PROXY = "PROXY"                            # Indirect observation
    NONE = "NONE"                              # No corresponding observed channel


class CorrelatorMode(str, enum.Enum):
    """Operational mode of the Map Correlator."""
    STRICT = "STRICT"                          # Only exact/grounded signals; all out-of-domain/approximations dropped
    EXPERIMENTAL = "EXPERIMENTAL"              # Allows DERIVED_APPROXIMATE within domain; target map OOD dropped
    VISUAL_ONLY = "VISUAL_ONLY"                # Edge-clamping allowed for UI display; clamped points excluded from hit matrix
    COVERAGE_ONLY = "COVERAGE_ONLY"            # Audits which map axes can be grounded from telemetry


class AxisSignal(BaseModel):
    """Represents a validated input coordinate for an axis with full provenance chain."""
    model_config = ConfigDict(extra="forbid")

    parameter_name: str = Field(..., description="A2L symbol or parameter name (e.g. Eng_nAvrg, PCR_qDes)")
    value: Optional[float] = Field(None, description="Numerical value of the signal (None if missing/out-of-domain)")
    unit: str = Field("", description="Engineering unit (e.g. rpm, mg/hub, hPa)")
    provenance_kind: SignalProvenanceKind = Field(..., description="Provenance category")
    semantic_match: SemanticMatchLevel = Field(..., description="Semantic fidelity to A2L symbol")
    provenance_chain: List[str] = Field(default_factory=list, description="Audit chain of transformations/conversions")
    conversion_map: Optional[str] = Field(None, description="Calibration map used if DERIVED")
    uncertainty_pct: Optional[float] = Field(None, description="Quantified uncertainty percentage (None if unquantified)")
    uncertainty_status: UncertaintyStatus = Field(UncertaintyStatus.UNQUANTIFIED, description="Uncertainty quantification status")
    caveat: Optional[str] = Field(None, description="Explicit warning or technical limitation")

    @property
    def source_kind(self) -> SignalProvenanceKind:
        return self.provenance_kind


class CellExposure(BaseModel):
    """Exposure weight for an individual map grid node."""
    model_config = ConfigDict(extra="forbid")

    x_index: int = Field(..., description="X-axis node index in map grid")
    y_index: Optional[int] = Field(None, description="Y-axis node index in map grid (None for 1D)")
    x_breakpoint: float = Field(..., description="Physical breakpoint value of X node")
    y_breakpoint: Optional[float] = Field(None, description="Physical breakpoint value of Y node")
    weight: float = Field(..., ge=0.0, le=1.0, description="Interpolation weight (0.0 to 1.0)")


class ObservedComparison(BaseModel):
    """Detailed provenance-aware comparison between base calibration output and observed telemetry."""
    model_config = ConfigDict(extra="forbid")

    observed_value: Optional[float] = Field(None, description="Observed sensor reading or actuator command")
    channel_name: Optional[str] = Field(None, description="Telemetry channel or PID name")
    provenance: Optional[SignalProvenanceKind] = Field(None, description="Provenance of observed channel")
    comparison_kind: ComparisonKind = Field(ComparisonKind.NONE, description="Relationship to base map output")
    observed_minus_base_map: Optional[float] = Field(
        None, description="observed_value - interpolated_map_value (denoted as comparison delta, NOT base map error)"
    )
    caveat: Optional[str] = Field(None, description="Technical explanation of downstream effects or compensations")


class PointCorrelation(BaseModel):
    """Correlated telemetry point mapped onto a calibration mesh."""
    model_config = ConfigDict(extra="forbid")

    time_s: float
    map_name: str
    mode: CorrelatorMode
    x_signal: AxisSignal
    y_signal: Optional[AxisSignal] = None
    interpolated_map_value: float = Field(..., description="Bilinear interpolated value from calibration grid")
    comparison: ObservedComparison = Field(default_factory=ObservedComparison)
    active_cells: List[CellExposure] = Field(default_factory=list, description="Surrounding grid nodes with weight > 0")
    is_clamped: bool = Field(False, description="True if query coordinates were clamped to axis boundaries")
    clamp_axes: List[str] = Field(default_factory=list, description="List of axes that required clamping ('X', 'Y')")

    # Compatibility properties
    @property
    def actual_observed_value(self) -> Optional[float]:
        return self.comparison.observed_value

    @property
    def discrepancy(self) -> Optional[float]:
        return self.comparison.observed_minus_base_map


class MapExposureReport(BaseModel):
    """Aggregate exposure report across a sequence of telemetry points."""
    model_config = ConfigDict(extra="forbid")

    map_name: str
    mode: CorrelatorMode
    map_shape: Tuple[int, ...]
    x_axis_name: str
    y_axis_name: Optional[str] = None
    total_points_evaluated: int = 0
    mapped_points_count: int = 0
    dropped_points_count: int = 0
    drop_reasons: Dict[str, int] = Field(default_factory=dict)
    axis_coverage_summary: Dict[str, str] = Field(default_factory=dict)
    cell_hit_matrix: List[List[float]] = Field(
        default_factory=list,
        description="Continuous exposure matrix accumulating bilinear weights (sum_w) from in-domain evidence"
    )
    discrete_hit_counts: List[List[int]] = Field(
        default_factory=list,
        description="Discrete integer count of points activating each grid cell (weight > 0)"
    )
    correlations: List[PointCorrelation] = Field(default_factory=list)
    exposure_observations: List[str] = Field(
        default_factory=list,
        description="Neutral, evidence-first exposure observations during key telemetry events"
    )


def _validate_axis_monotonic(pts: np.ndarray, axis_label: str = "axis") -> None:
    """Validate that axis breakpoints are strictly monotonically increasing."""
    if len(pts) < 2:
        return
    diffs = np.diff(pts)
    if np.any(diffs <= 0):
        non_mono_indices = np.where(diffs <= 0)[0]
        details = ", ".join(
            f"[{i}]={pts[i]} >= [{i+1}]={pts[i+1]}" for i in non_mono_indices[:3]
        )
        raise ValueError(
            f"Non-monotonic axis detected in {axis_label}: {details}. "
            "ASAP2 calibration meshes must have strictly increasing breakpoints."
        )


class TorqueToFuelConverter:
    """
    Evaluates engine torque (Nm) to fuel quantity (mg/cycle or mg/stroke)
    using the exact project A2L / PROJECT_VERIFIED calibration map `FMTC_trq2qBas_MAP`.

    Enforces strict axis domain bounds:
    The torque axis ends at ~336 Nm. WOT torque requests (> 336 Nm) are strictly
    identified as DERIVED_OUT_OF_DOMAIN. Clamping or extrapolation is forbidden.
    """

    def __init__(self, map_or_decoder: Union[DecodedMap, MapDecoder]):
        if isinstance(map_or_decoder, MapDecoder):
            self.map_obj = map_or_decoder.decode("FMTC_trq2qBas_MAP")
        else:
            self.map_obj = map_or_decoder

        x_pts = np.array(self.map_obj.x_axis.physical_values, dtype=float)
        y_pts = np.array(self.map_obj.y_axis.physical_values, dtype=float) if self.map_obj.y_axis else None
        if y_pts is None:
            raise ValueError("FMTC_trq2qBas_MAP must be a 2D map with Y-axis")

        _validate_axis_monotonic(x_pts, "FMTC_trq2qBas_MAP X (RPM)")
        _validate_axis_monotonic(y_pts, "FMTC_trq2qBas_MAP Y (Torque Nm)")

        self.x_pts = x_pts
        self.y_pts = y_pts
        self.grid = self.map_obj.numpy_physical()

        self.x_min, self.x_max = float(x_pts[0]), float(x_pts[-1])
        self.y_min, self.y_max = float(y_pts[0]), float(y_pts[-1])

    def convert(self, rpm: float, torque_nm: float) -> Tuple[Optional[float], SignalProvenanceKind, Optional[str]]:
        """
        Convert (RPM, Torque Nm) to base fuel quantity in mg/cyc.
        Returns: (fuel_mg, provenance_kind, reason_or_caveat).
        If outside domain, returns (None, DERIVED_OUT_OF_DOMAIN, reason).
        """
        # Strict Domain Boundary Check
        if rpm < self.x_min or rpm > self.x_max or torque_nm < self.y_min or torque_nm > self.y_max:
            reasons = []
            if torque_nm > self.y_max:
                reasons.append(f"Torque {torque_nm:.1f} Nm > map limit {self.y_max:.1f} Nm")
            elif torque_nm < self.y_min:
                reasons.append(f"Torque {torque_nm:.1f} Nm < map limit {self.y_min:.1f} Nm")
            if rpm > self.x_max or rpm < self.x_min:
                reasons.append(f"RPM {rpm:.0f} outside map range [{self.x_min:.0f}..{self.x_max:.0f}]")
            
            return None, SignalProvenanceKind.DERIVED_OUT_OF_DOMAIN, "; ".join(reasons)

        # Within domain: perform standard bilinear interpolation
        interp_val, _, _, _ = _bilinear_interpolate(
            self.x_pts, self.y_pts, self.grid, rpm, torque_nm, allow_clamping=False
        )
        return float(interp_val), SignalProvenanceKind.DERIVED_APPROXIMATE, None


# ==============================================================================
# Explicit AxisResolverRegistry
# ==============================================================================

class AxisResolverRegistry:
    """
    Explicit registry of supported A2L axis symbols.
    Prevents generic inference based on physical units (e.g. hPa -> boost, Nm -> torque, mg -> fuel).
    Any symbol not explicitly registered is rejected with UNSUPPORTED_AXIS.
    """

    def __init__(self, torque_converter: Optional[TorqueToFuelConverter] = None):
        self.torque_converter = torque_converter

    def resolve(
        self,
        axis: AxisData,
        point: TelemetryPoint,
        map_name: str,
        axis_role: str,
        mode: CorrelatorMode,
    ) -> AxisSignal:
        """Dispatch resolution to explicit symbol resolver handler."""
        symbol = axis.name.strip()

        # 1. Engine Speed
        if symbol in ("Eng_nAvrg", "N_2Z_W"):
            return self._resolve_rpm(axis, point)

        # 2. Target Formation Injection Quantity
        if symbol == "PCR_qDes":
            return self._resolve_pcr_qdes(axis, point, mode)

        # 3. Control Injection Quantity
        if symbol == "PCR_qCtl":
            return self._resolve_pcr_qctl(axis, point, mode)

        # 4. Corrected Pressure for Smoke Limiting
        if symbol == "FlMng_pIATCorr_mp":
            return self._resolve_smoke_corr_press(axis, point, mode)

        # 5. Engine Internal Setpoint Torque
        if symbol == "CoEng_trqInrSet":
            return self._resolve_coeng_trq(axis, point)

        # 6. Physical Intake Manifold Pressure
        if symbol in ("Air_pInMPrec_mp", "Air_pInM_mp"):
            return self._resolve_intake_press(axis, point)

        # 7. Uncompressed Setpoint Injection Quantity (General Fueling Map)
        if symbol in ("InjCrv_qSetUncomp", "InjCrv_qSet_mp"):
            return self._resolve_inj_qset(axis, point, mode)

        # Explicit rejection for any unrecognized symbol
        return AxisSignal(
            parameter_name=axis.name,
            value=None,
            unit=axis.unit,
            provenance_kind=SignalProvenanceKind.MISSING,
            semantic_match=SemanticMatchLevel.MISMATCH,
            caveat=(
                f"Unsupported axis symbol '{axis.name}'. No explicit resolver registered "
                f"in AxisResolverRegistry. Generic unit-based matching is forbidden."
            ),
        )

    def _resolve_rpm(self, axis: AxisData, point: TelemetryPoint) -> AxisSignal:
        if point.rpm is not None and not math.isnan(point.rpm):
            return AxisSignal(
                parameter_name=axis.name,
                value=float(point.rpm),
                unit=axis.unit or "rpm",
                provenance_kind=SignalProvenanceKind.MEASURED_DIAGNOSTIC,
                semantic_match=SemanticMatchLevel.EXACT,
                provenance_chain=["VCDS_OBD_RPM", axis.name],
            )
        return AxisSignal(
            parameter_name=axis.name,
            value=None,
            unit=axis.unit or "rpm",
            provenance_kind=SignalProvenanceKind.MISSING,
            semantic_match=SemanticMatchLevel.EXACT,
            caveat="Engine speed (RPM) absent from telemetry sample",
        )

    def _resolve_pcr_qdes(self, axis: AxisData, point: TelemetryPoint, mode: CorrelatorMode) -> AxisSignal:
        if mode == CorrelatorMode.STRICT:
            return AxisSignal(
                parameter_name=axis.name,
                value=None,
                unit=axis.unit or "mg/hub",
                provenance_kind=SignalProvenanceKind.MISSING,
                semantic_match=SemanticMatchLevel.MISMATCH,
                caveat=(
                    "In STRICT mode, diagnostic telemetry cannot be substituted for internal "
                    "ECU variable PCR_qDes (Einspritzmenge für Sollwertbildung)."
                ),
            )

        # In EXPERIMENTAL / VISUAL_ONLY / COVERAGE_ONLY:
        trq = (
            point.trq_request_nm
            if point.trq_request_nm is not None
            else (point.trq_limit_nm if point.trq_limit_nm is not None else point.trq_smoke_nm)
        )
        if trq is not None and not math.isnan(trq) and point.rpm is not None and not math.isnan(point.rpm):
            if self.torque_converter is not None:
                fuel_mg, prov, reason = self.torque_converter.convert(point.rpm, trq)
                if prov == SignalProvenanceKind.DERIVED_OUT_OF_DOMAIN:
                    return AxisSignal(
                        parameter_name=axis.name,
                        value=None,
                        unit=axis.unit or "mg/hub",
                        provenance_kind=SignalProvenanceKind.DERIVED_OUT_OF_DOMAIN,
                        semantic_match=SemanticMatchLevel.PROXY_APPROXIMATE,
                        caveat=f"Torque conversion out of domain: {reason}",
                    )
                return AxisSignal(
                    parameter_name=axis.name,
                    value=round(fuel_mg, 3) if fuel_mg is not None else None,
                    unit=axis.unit or "mg/hub",
                    provenance_kind=SignalProvenanceKind.DERIVED_APPROXIMATE,
                    semantic_match=SemanticMatchLevel.PROXY_APPROXIMATE,
                    provenance_chain=["VCDS_008_trq_request_nm", "FMTC_trq2qBas_MAP", "PCR_qDes_PROXY"],
                    conversion_map="FMTC_trq2qBas_MAP",
                    uncertainty_pct=None,
                    uncertainty_status=UncertaintyStatus.UNQUANTIFIED,
                    caveat=(
                        "Experimental proxy: FMTC_trq2qBas_MAP in-domain conversion used as surrogate "
                        "for PCR_qDes. Actual target formation fueling may incorporate unmodeled compensations."
                    ),
                )

        # Fallback to direct fuel if present
        direct_q = (
            point.driver_wish_iq_mg
            if point.driver_wish_iq_mg is not None
            else (point.smoke_limit_iq_mg if point.smoke_limit_iq_mg is not None else point.torque_limit_iq_mg)
        )
        if direct_q is not None and not math.isnan(direct_q):
            return AxisSignal(
                parameter_name=axis.name,
                value=float(direct_q),
                unit=axis.unit or "mg/hub",
                provenance_kind=SignalProvenanceKind.DERIVED_APPROXIMATE,
                semantic_match=SemanticMatchLevel.PROXY_APPROXIMATE,
                provenance_chain=["VCDS_008_Diagnostic_IQ", "PCR_qDes_PROXY"],
                uncertainty_pct=None,
                uncertainty_status=UncertaintyStatus.UNQUANTIFIED,
                caveat="Diagnostic IQ used as surrogate for PCR_qDes.",
            )

        return AxisSignal(
            parameter_name=axis.name,
            value=None,
            unit=axis.unit or "mg/hub",
            provenance_kind=SignalProvenanceKind.MISSING,
            semantic_match=SemanticMatchLevel.EXACT,
            caveat="Fuel quantity / torque absent from telemetry",
        )

    def _resolve_pcr_qctl(self, axis: AxisData, point: TelemetryPoint, mode: CorrelatorMode) -> AxisSignal:
        if mode == CorrelatorMode.STRICT:
            return AxisSignal(
                parameter_name=axis.name,
                value=None,
                unit=axis.unit or "mg/hub",
                provenance_kind=SignalProvenanceKind.MISSING,
                semantic_match=SemanticMatchLevel.MISMATCH,
                caveat=(
                    "In STRICT mode, diagnostic telemetry cannot be substituted for internal "
                    "ECU variable PCR_qCtl (für die Steuerung benutztes Einspritzmengensignal)."
                ),
            )

        trq = (
            point.trq_request_nm
            if point.trq_request_nm is not None
            else (point.trq_limit_nm if point.trq_limit_nm is not None else point.trq_smoke_nm)
        )
        if trq is not None and self.torque_converter is not None and point.rpm is not None:
            fuel_mg, prov, reason = self.torque_converter.convert(point.rpm, trq)
            if prov == SignalProvenanceKind.DERIVED_OUT_OF_DOMAIN:
                return AxisSignal(
                    parameter_name=axis.name,
                    value=None,
                    unit=axis.unit or "mg/hub",
                    provenance_kind=SignalProvenanceKind.DERIVED_OUT_OF_DOMAIN,
                    semantic_match=SemanticMatchLevel.PROXY_APPROXIMATE,
                    caveat=f"Torque conversion out of domain: {reason}",
                )
            return AxisSignal(
                parameter_name=axis.name,
                value=round(fuel_mg, 3) if fuel_mg is not None else None,
                unit=axis.unit or "mg/hub",
                provenance_kind=SignalProvenanceKind.DERIVED_APPROXIMATE,
                semantic_match=SemanticMatchLevel.PROXY_APPROXIMATE,
                provenance_chain=["VCDS_008_trq_request_nm", "FMTC_trq2qBas_MAP", "PCR_qCtl_PROXY"],
                conversion_map="FMTC_trq2qBas_MAP",
                uncertainty_pct=None,
                uncertainty_status=UncertaintyStatus.UNQUANTIFIED,
                caveat=(
                    "Experimental proxy: FMTC_trq2qBas_MAP in-domain conversion used as surrogate for "
                    "PCR_qCtl. Note that governor control quantity differs from target formation quantity."
                ),
            )

        direct_q = (
            point.driver_wish_iq_mg
            if point.driver_wish_iq_mg is not None
            else (point.smoke_limit_iq_mg if point.smoke_limit_iq_mg is not None else point.torque_limit_iq_mg)
        )
        if direct_q is not None and not math.isnan(direct_q):
            return AxisSignal(
                parameter_name=axis.name,
                value=float(direct_q),
                unit=axis.unit or "mg/hub",
                provenance_kind=SignalProvenanceKind.DERIVED_APPROXIMATE,
                semantic_match=SemanticMatchLevel.PROXY_APPROXIMATE,
                provenance_chain=["VCDS_008_Diagnostic_IQ", "PCR_qCtl_PROXY"],
                uncertainty_pct=None,
                uncertainty_status=UncertaintyStatus.UNQUANTIFIED,
                caveat="Diagnostic IQ used as surrogate for PCR_qCtl.",
            )

        return AxisSignal(
            parameter_name=axis.name,
            value=None,
            unit=axis.unit or "mg/hub",
            provenance_kind=SignalProvenanceKind.MISSING,
            semantic_match=SemanticMatchLevel.EXACT,
            caveat="Control fuel quantity absent from telemetry",
        )


    def _resolve_smoke_corr_press(self, axis: AxisData, point: TelemetryPoint, mode: CorrelatorMode) -> AxisSignal:
        raw_boost = point.boost_act_mbar if point.boost_act_mbar is not None else point.boost_spec_mbar
        if raw_boost is None or math.isnan(raw_boost):
            return AxisSignal(
                parameter_name=axis.name,
                value=None,
                unit=axis.unit or "hPa",
                provenance_kind=SignalProvenanceKind.MISSING,
                semantic_match=SemanticMatchLevel.MISMATCH,
                caveat="Boost pressure reading absent from telemetry",
            )

        if mode == CorrelatorMode.STRICT:
            return AxisSignal(
                parameter_name=axis.name,
                value=None,
                unit=axis.unit or "hPa",
                provenance_kind=SignalProvenanceKind.MISSING,
                semantic_match=SemanticMatchLevel.MISMATCH,
                caveat=(
                    f"In STRICT mode, raw VCDS boost ({raw_boost:.1f} mbar) cannot be substituted "
                    f"for '{axis.name}' without modeling FlMng_pIATCorr_MAP temperature correction."
                ),
            )
        elif mode in (CorrelatorMode.EXPERIMENTAL, CorrelatorMode.VISUAL_ONLY):
            return AxisSignal(
                parameter_name=axis.name,
                value=float(raw_boost),
                unit=axis.unit or "hPa",
                provenance_kind=SignalProvenanceKind.DERIVED_APPROXIMATE,
                semantic_match=SemanticMatchLevel.PROXY_APPROXIMATE,
                provenance_chain=["VCDS_011_boost_act_mbar", "RAW_MAP_WITHOUT_TEMP_CORR"],
                uncertainty_pct=None,
                uncertainty_status=UncertaintyStatus.UNQUANTIFIED,
                caveat=(
                    "Experimental approximation: Raw manifold pressure used directly without "
                    "exact project A2L temperature correction map (FlMng_pIATCorr_MAP)."
                ),
            )
        else:  # COVERAGE_ONLY
            return AxisSignal(
                parameter_name=axis.name,
                value=float(raw_boost),
                unit=axis.unit or "hPa",
                provenance_kind=SignalProvenanceKind.DERIVED_APPROXIMATE,
                semantic_match=SemanticMatchLevel.PROXY_APPROXIMATE,
                caveat="Requires FlMng_pIATCorr_MAP temperature correction",
            )

    def _resolve_coeng_trq(self, axis: AxisData, point: TelemetryPoint) -> AxisSignal:
        trq_val = (
            point.trq_request_nm
            if point.trq_request_nm is not None
            else (point.trq_limit_nm if point.trq_limit_nm is not None else point.trq_smoke_nm)
        )
        if trq_val is not None and not math.isnan(trq_val):
            return AxisSignal(
                parameter_name=axis.name,
                value=float(trq_val),
                unit=axis.unit or "Nm",
                provenance_kind=SignalProvenanceKind.MEASURED_DIAGNOSTIC,
                semantic_match=SemanticMatchLevel.EXACT,
                provenance_chain=["VCDS_008_Torque_Nm", axis.name],
            )
        return AxisSignal(
            parameter_name=axis.name,
            value=None,
            unit=axis.unit or "Nm",
            provenance_kind=SignalProvenanceKind.MISSING,
            semantic_match=SemanticMatchLevel.EXACT,
            caveat="Engine torque absent from telemetry",
        )

    def _resolve_intake_press(self, axis: AxisData, point: TelemetryPoint) -> AxisSignal:
        val = point.boost_act_mbar if point.boost_act_mbar is not None else point.boost_spec_mbar
        if val is not None and not math.isnan(val):
            return AxisSignal(
                parameter_name=axis.name,
                value=float(val),
                unit=axis.unit or "hPa",
                provenance_kind=SignalProvenanceKind.MEASURED_DIAGNOSTIC,
                semantic_match=SemanticMatchLevel.EXACT,
                provenance_chain=["VCDS_011_Boost_Pressure", axis.name],
            )
        return AxisSignal(
            parameter_name=axis.name,
            value=None,
            unit=axis.unit or "hPa",
            provenance_kind=SignalProvenanceKind.MISSING,
            semantic_match=SemanticMatchLevel.EXACT,
            caveat="Manifold pressure absent from telemetry",
        )

    def _resolve_inj_qset(self, axis: AxisData, point: TelemetryPoint, mode: CorrelatorMode) -> AxisSignal:
        direct_q = (
            point.driver_wish_iq_mg
            if point.driver_wish_iq_mg is not None
            else (point.smoke_limit_iq_mg if point.smoke_limit_iq_mg is not None else point.torque_limit_iq_mg)
        )
        if direct_q is not None and not math.isnan(direct_q):
            return AxisSignal(
                parameter_name=axis.name,
                value=float(direct_q),
                unit=axis.unit or "mg/hub",
                provenance_kind=SignalProvenanceKind.MEASURED_DIAGNOSTIC,
                semantic_match=SemanticMatchLevel.EXACT,
                provenance_chain=["VCDS_008_Diagnostic_IQ", axis.name],
            )
        return AxisSignal(
            parameter_name=axis.name,
            value=None,
            unit=axis.unit or "mg/hub",
            provenance_kind=SignalProvenanceKind.MISSING,
            semantic_match=SemanticMatchLevel.EXACT,
            caveat="Fuel quantity absent from telemetry",
        )


# Backward-compatible alias for AxisSignalResolver
AxisSignalResolver = AxisResolverRegistry


def _find_bounding_interval(
    pts: np.ndarray, val: float, allow_clamping: bool = False
) -> Tuple[int, float, bool, bool]:
    """
    Find lower bracket index i and local normalized weight w in [0, 1].
    Returns: (index, weight, is_clamped, is_out_of_domain).
    """
    n = len(pts)
    if n < 2:
        return 0, 0.0, False, False

    if val < pts[0]:
        if not allow_clamping:
            return 0, 0.0, True, True
        return 0, 0.0, True, False
    if val > pts[-1]:
        if not allow_clamping:
            return n - 2, 1.0, True, True
        return n - 2, 1.0, True, False

    idx = int(np.searchsorted(pts, val) - 1)
    idx = max(0, min(idx, n - 2))

    denom = pts[idx + 1] - pts[idx]
    w = 0.0 if denom == 0 else (val - pts[idx]) / denom
    w = max(0.0, min(1.0, w))
    return idx, w, False, False


def _bilinear_interpolate(
    x_pts: np.ndarray,
    y_pts: np.ndarray,
    grid: np.ndarray,
    x: float,
    y: float,
    allow_clamping: bool = False,
) -> Tuple[float, List[CellExposure], bool, List[str]]:
    """
    Perform 2D bilinear interpolation on grid with shape (len(x_pts), len(y_pts)).
    """
    i, wx, clamp_x, ood_x = _find_bounding_interval(x_pts, x, allow_clamping)
    j, wy, clamp_y, ood_y = _find_bounding_interval(y_pts, y, allow_clamping)

    clamp_axes = []
    if clamp_x:
        clamp_axes.append("X")
    if clamp_y:
        clamp_axes.append("Y")
    is_clamped = bool(clamp_axes)

    w00 = (1.0 - wx) * (1.0 - wy)
    w10 = wx * (1.0 - wy)
    w01 = (1.0 - wx) * wy
    w11 = wx * wy

    interp_val = (
        w00 * grid[i, j]
        + w10 * grid[i + 1, j]
        + w01 * grid[i, j + 1]
        + w11 * grid[i + 1, j + 1]
    )

    active_cells: List[CellExposure] = []
    candidates = [
        (i, j, x_pts[i], y_pts[j], w00),
        (i + 1, j, x_pts[i + 1], y_pts[j], w10),
        (i, j + 1, x_pts[i], y_pts[j + 1], w01),
        (i + 1, j + 1, x_pts[i + 1], y_pts[j + 1], w11),
    ]
    for r, c, xp, yp, w in candidates:
        if w > 1e-6:
            active_cells.append(
                CellExposure(
                    x_index=r,
                    y_index=c,
                    x_breakpoint=round(float(xp), 4),
                    y_breakpoint=round(float(yp), 4),
                    weight=round(float(w), 6),
                )
            )

    return float(interp_val), active_cells, is_clamped, clamp_axes


def _linear_interpolate_1d(
    x_pts: np.ndarray,
    values: np.ndarray,
    x: float,
    allow_clamping: bool = False,
) -> Tuple[float, List[CellExposure], bool, List[str]]:
    """
    Perform 1D linear interpolation on a curve with shape (len(x_pts),).
    """
    i, wx, clamp_x, _ = _find_bounding_interval(x_pts, x, allow_clamping)
    clamp_axes = ["X"] if clamp_x else []
    is_clamped = clamp_x

    w0 = 1.0 - wx
    w1 = wx

    interp_val = w0 * values[i] + w1 * values[i + 1]

    active_cells: List[CellExposure] = []
    if w0 > 1e-6:
        active_cells.append(
            CellExposure(
                x_index=i,
                y_index=None,
                x_breakpoint=round(float(x_pts[i]), 4),
                y_breakpoint=None,
                weight=round(float(w0), 6),
            )
        )
    if w1 > 1e-6:
        active_cells.append(
            CellExposure(
                x_index=i + 1,
                y_index=None,
                x_breakpoint=round(float(x_pts[i + 1]), 4),
                y_breakpoint=None,
                weight=round(float(w1), 6),
            )
        )

    return float(interp_val), active_cells, is_clamped, clamp_axes


class MapCorrelator:
    """
    Evidence-First Map Correlator.
    Maps TelemetryPoint records onto exact project A2L calibration meshes under
    STRICT, EXPERIMENTAL, VISUAL_ONLY, or COVERAGE_ONLY modes.
    """

    def __init__(
        self,
        decoder: MapDecoder,
        torque_converter: Optional[TorqueToFuelConverter] = None,
        mode: CorrelatorMode = CorrelatorMode.STRICT,
    ):
        self.decoder = decoder
        self.torque_converter = torque_converter
        self.mode = mode
        self.registry = AxisResolverRegistry(torque_converter=torque_converter)
        # Compatibility attribute
        self.resolver = self.registry
        self._map_cache: Dict[str, DecodedMap] = {}

    def get_decoded_map(self, map_name: str) -> DecodedMap:
        """Fetch or decode map with memoization."""
        if map_name not in self._map_cache:
            self._map_cache[map_name] = self.decoder.decode(map_name)
        return self._map_cache[map_name]

    def _resolve_observed_comparison(
        self,
        map_name: str,
        point: TelemetryPoint,
        base_map_value: float,
    ) -> ObservedComparison:
        """
        Resolve structured provenance-aware comparison between base calibration output
        and observed telemetry channels. Explicitly classifies downstream signals.
        """
        name_upper = map_name.upper()

        # 1. Boost Target Map: PCR_pBDesBas_MAP (base target) vs VCDS Boost Specified (downstream)
        if "PBDES" in name_upper:
            if point.boost_spec_mbar is not None and not math.isnan(point.boost_spec_mbar):
                delta = point.boost_spec_mbar - base_map_value
                return ObservedComparison(
                    observed_value=float(point.boost_spec_mbar),
                    channel_name="boost_spec_mbar",
                    provenance=SignalProvenanceKind.MEASURED_DIAGNOSTIC,
                    comparison_kind=ComparisonKind.DOWNSTREAM_SIGNAL,
                    observed_minus_base_map=round(delta, 4),
                    caveat=(
                        "Comparison against downstream final boost request (boost_spec_mbar). "
                        "PCR_pBDesBas_MAP is a base calibration target; downstream compensations "
                        "(altitude, intake air temp) may alter final specified boost."
                    ),
                )
            elif point.boost_act_mbar is not None and not math.isnan(point.boost_act_mbar):
                delta = point.boost_act_mbar - base_map_value
                return ObservedComparison(
                    observed_value=float(point.boost_act_mbar),
                    channel_name="boost_act_mbar",
                    provenance=SignalProvenanceKind.MEASURED_DIAGNOSTIC,
                    comparison_kind=ComparisonKind.DOWNSTREAM_SIGNAL,
                    observed_minus_base_map=round(delta, 4),
                    caveat=(
                        "Comparison against downstream manifold sensor reading (boost_act_mbar). "
                        "Denotes physical tracking relative to base target, not governor closed-loop error."
                    ),
                )

        # 2. N75 Precontrol Map: PCR_rBPCtlBas_MAP (feedforward) vs VCDS N75 Duty (closed-loop)
        elif "RBPCTL" in name_upper or "N75" in name_upper:
            if point.n75_duty_pct is not None and not math.isnan(point.n75_duty_pct):
                delta = point.n75_duty_pct - base_map_value
                return ObservedComparison(
                    observed_value=float(point.n75_duty_pct),
                    channel_name="n75_duty_pct",
                    provenance=SignalProvenanceKind.MEASURED_DIAGNOSTIC,
                    comparison_kind=ComparisonKind.DOWNSTREAM_SIGNAL,
                    observed_minus_base_map=round(delta, 4),
                    caveat=(
                        "Comparison against downstream final actuator command (n75_duty_pct). "
                        "PCR_rBPCtlBas_MAP is a base feedforward duty cycle; closed-loop PID "
                        "and dynamic compensations alter the final governor command."
                    ),
                )

        # 3. Smoke Limiter Map: FlMng_qPresSmoke_MAP vs VCDS Smoke Limit IQ
        elif "SMOKE" in name_upper and "Q" in name_upper:
            if point.smoke_limit_iq_mg is not None and not math.isnan(point.smoke_limit_iq_mg):
                delta = point.smoke_limit_iq_mg - base_map_value
                return ObservedComparison(
                    observed_value=float(point.smoke_limit_iq_mg),
                    channel_name="smoke_limit_iq_mg",
                    provenance=SignalProvenanceKind.MEASURED_DIAGNOSTIC,
                    comparison_kind=ComparisonKind.DOWNSTREAM_SIGNAL,
                    observed_minus_base_map=round(delta, 4),
                    caveat="Comparison against downstream smoke limiter output. Dynamic smoke filters may apply.",
                )

        return ObservedComparison()

    def correlate_point(
        self,
        map_or_name: Union[str, DecodedMap],
        point: TelemetryPoint,
        mode: Optional[CorrelatorMode] = None,
    ) -> Tuple[Optional[PointCorrelation], Optional[str]]:
        """
        Correlate a single TelemetryPoint against a calibration map.
        Returns (correlation, drop_reason).
        """
        active_mode = mode or self.mode
        if isinstance(map_or_name, str):
            decoded = self.get_decoded_map(map_or_name)
        else:
            decoded = map_or_name

        x_pts = decoded.x_axis.to_numpy()
        _validate_axis_monotonic(x_pts, f"{decoded.name} X-axis")

        # 1. Resolve X-axis signal
        x_sig = self.registry.resolve(decoded.x_axis, point, decoded.name, "X", active_mode)
        if x_sig.value is None or x_sig.provenance_kind in (
            SignalProvenanceKind.MISSING,
            SignalProvenanceKind.DERIVED_OUT_OF_DOMAIN,
        ):
            reason = x_sig.caveat or f"MISSING_SIGNAL: X-axis '{decoded.x_axis.name}' unavailable"
            return None, reason

        # 2. Check 1D vs 2D
        if decoded.y_axis is None:
            # 1D Curve Domain check:
            is_ood_x = x_sig.value < x_pts[0] or x_sig.value > x_pts[-1]
            if is_ood_x and active_mode != CorrelatorMode.VISUAL_ONLY:
                return None, f"OUT_OF_DOMAIN: X ({x_sig.value:.1f}) outside curve range [{x_pts[0]}..{x_pts[-1]}]"

            allow_clamp = (active_mode == CorrelatorMode.VISUAL_ONLY)
            interp_val, active_cells, is_clamped, clamp_axes = _linear_interpolate_1d(
                x_pts, decoded.numpy_physical(), x_sig.value, allow_clamping=allow_clamp
            )
            comp = self._resolve_observed_comparison(decoded.name, point, interp_val)

            corr = PointCorrelation(
                time_s=point.time_s,
                map_name=decoded.name,
                mode=active_mode,
                x_signal=x_sig,
                y_signal=None,
                interpolated_map_value=round(float(interp_val), 4),
                comparison=comp,
                active_cells=active_cells,
                is_clamped=is_clamped,
                clamp_axes=clamp_axes,
            )
            return corr, None

        # 2D Map
        y_pts = decoded.y_axis.to_numpy()
        _validate_axis_monotonic(y_pts, f"{decoded.name} Y-axis")

        y_sig = self.registry.resolve(decoded.y_axis, point, decoded.name, "Y", active_mode)
        if y_sig.value is None or y_sig.provenance_kind in (
            SignalProvenanceKind.MISSING,
            SignalProvenanceKind.DERIVED_OUT_OF_DOMAIN,
        ):
            reason = y_sig.caveat or f"MISSING_SIGNAL: Y-axis '{decoded.y_axis.name}' unavailable"
            return None, reason

        # Check Target Map Domain in STRICT and EXPERIMENTAL modes (DROP if out-of-domain!)
        is_ood_x = x_sig.value < x_pts[0] or x_sig.value > x_pts[-1]
        is_ood_y = y_sig.value < y_pts[0] or y_sig.value > y_pts[-1]
        if (is_ood_x or is_ood_y) and active_mode != CorrelatorMode.VISUAL_ONLY:
            ood_details = []
            if is_ood_x:
                ood_details.append(f"X '{decoded.x_axis.name}' ({x_sig.value:.1f}) outside [{x_pts[0]}..{x_pts[-1]}]")
            if is_ood_y:
                ood_details.append(f"Y '{decoded.y_axis.name}' ({y_sig.value:.1f}) outside [{y_pts[0]}..{y_pts[-1]}]")
            return None, f"OUT_OF_DOMAIN: Target map coordinate out of domain: {'; '.join(ood_details)}"

        allow_clamp = (active_mode == CorrelatorMode.VISUAL_ONLY)
        grid = decoded.numpy_physical()
        interp_val, active_cells, is_clamped, clamp_axes = _bilinear_interpolate(
            x_pts, y_pts, grid, x_sig.value, y_sig.value, allow_clamping=allow_clamp
        )
        comp = self._resolve_observed_comparison(decoded.name, point, interp_val)

        corr = PointCorrelation(
            time_s=point.time_s,
            map_name=decoded.name,
            mode=active_mode,
            x_signal=x_sig,
            y_signal=y_sig,
            interpolated_map_value=round(float(interp_val), 4),
            comparison=comp,
            active_cells=active_cells,
            is_clamped=is_clamped,
            clamp_axes=clamp_axes,
        )
        return corr, None

    def correlate_points(
        self,
        map_or_name: Union[str, DecodedMap],
        points: Sequence[TelemetryPoint],
        mode: Optional[CorrelatorMode] = None,
    ) -> MapExposureReport:
        """
        Correlate an ordered sequence of TelemetryPoints onto a calibration map mesh.
        """
        active_mode = mode or self.mode
        if isinstance(map_or_name, str):
            decoded = self.get_decoded_map(map_or_name)
        else:
            decoded = map_or_name

        nx = decoded.x_axis.count
        ny = decoded.y_axis.count if decoded.y_axis else 1

        cell_hit_matrix = [[0.0 for _ in range(ny)] for _ in range(nx)]
        discrete_hit_counts = [[0 for _ in range(ny)] for _ in range(nx)]

        correlations: List[PointCorrelation] = []
        drop_reasons: Dict[str, int] = {}
        total_eval = len(points)
        mapped_count = 0
        dropped_count = 0

        # Coverage assessment
        x_sig_counts = {"GROUNDED": 0, "MISSING": 0, "OUT_OF_DOMAIN": 0}
        y_sig_counts = {"GROUNDED": 0, "MISSING": 0, "OUT_OF_DOMAIN": 0}

        for pt in points:
            # Audit axis coverage
            xs = self.registry.resolve(decoded.x_axis, pt, decoded.name, "X", active_mode)
            if xs.value is not None:
                x_sig_counts["GROUNDED"] += 1
            elif xs.provenance_kind == SignalProvenanceKind.DERIVED_OUT_OF_DOMAIN:
                x_sig_counts["OUT_OF_DOMAIN"] += 1
            else:
                x_sig_counts["MISSING"] += 1

            if decoded.y_axis:
                ys = self.registry.resolve(decoded.y_axis, pt, decoded.name, "Y", active_mode)
                if ys.value is not None:
                    y_sig_counts["GROUNDED"] += 1
                elif ys.provenance_kind == SignalProvenanceKind.DERIVED_OUT_OF_DOMAIN:
                    y_sig_counts["OUT_OF_DOMAIN"] += 1
                else:
                    y_sig_counts["MISSING"] += 1

            if active_mode == CorrelatorMode.COVERAGE_ONLY:
                continue

            corr, reason = self.correlate_point(decoded, pt, active_mode)
            if corr is not None:
                correlations.append(corr)
                mapped_count += 1

                # Accumulate hits into evidence heatmap:
                # In VISUAL_ONLY mode: clamped points MUST NOT accumulate hits!
                if not (active_mode == CorrelatorMode.VISUAL_ONLY and corr.is_clamped):
                    for cell in corr.active_cells:
                        r = cell.x_index
                        c = cell.y_index if cell.y_index is not None else 0
                        if 0 <= r < nx and 0 <= c < ny:
                            cell_hit_matrix[r][c] += cell.weight
                            discrete_hit_counts[r][c] += 1
            else:
                dropped_count += 1
                r_key = reason or "UNKNOWN_DROP"
                drop_reasons[r_key] = drop_reasons.get(r_key, 0) + 1

        for r in range(nx):
            for c in range(ny):
                cell_hit_matrix[r][c] = round(cell_hit_matrix[r][c], 4)

        coverage_summary = {
            f"X_{decoded.x_axis.name}": f"{x_sig_counts['GROUNDED']}/{total_eval} grounded ({x_sig_counts['OUT_OF_DOMAIN']} out-of-domain, {x_sig_counts['MISSING']} missing)",
        }
        if decoded.y_axis:
            coverage_summary[f"Y_{decoded.y_axis.name}"] = (
                f"{y_sig_counts['GROUNDED']}/{total_eval} grounded ({y_sig_counts['OUT_OF_DOMAIN']} out-of-domain, {y_sig_counts['MISSING']} missing)"
            )

        observations = self._generate_observations(decoded, correlations, points, active_mode, coverage_summary)

        return MapExposureReport(
            map_name=decoded.name,
            mode=active_mode,
            map_shape=decoded.shape,
            x_axis_name=decoded.x_axis.name,
            y_axis_name=decoded.y_axis.name if decoded.y_axis else None,
            total_points_evaluated=total_eval,
            mapped_points_count=mapped_count,
            dropped_points_count=dropped_count,
            drop_reasons=drop_reasons,
            axis_coverage_summary=coverage_summary,
            cell_hit_matrix=cell_hit_matrix,
            discrete_hit_counts=discrete_hit_counts,
            correlations=correlations,
            exposure_observations=observations,
        )

    def correlate_pull(
        self,
        map_or_name: Union[str, DecodedMap],
        segment_points: Sequence[TelemetryPoint],
        mode: Optional[CorrelatorMode] = None,
    ) -> MapExposureReport:
        """Correlate telemetry points belonging to an acceleration segment."""
        return self.correlate_points(map_or_name, segment_points, mode)

    def _generate_observations(
        self,
        decoded: DecodedMap,
        correlations: Sequence[PointCorrelation],
        all_points: Sequence[TelemetryPoint],
        mode: CorrelatorMode,
        coverage_summary: Dict[str, str],
    ) -> List[str]:
        """
        Generate neutral, evidence-first exposure observations.
        Denotes spatial exposure during telemetry phenomena without claiming causality.
        """
        obs: List[str] = []

        if mode == CorrelatorMode.COVERAGE_ONLY:
            obs.append(f"Coverage audit for '{decoded.name}': {'; '.join(f'{k}: {v}' for k, v in coverage_summary.items())}.")
            return obs

        if not correlations:
            if all_points:
                obs.append(
                    f"Zero telemetry points could be mapped to '{decoded.name}' in {mode.value} mode. "
                    f"Coverage: {'; '.join(f'{k}: {v}' for k, v in coverage_summary.items())}."
                )
            return obs

        # Summary of operating range
        x_vals = [c.x_signal.value for c in correlations if c.x_signal.value is not None]
        if x_vals:
            x_min, x_max = min(x_vals), max(x_vals)
            if decoded.y_axis:
                y_vals = [c.y_signal.value for c in correlations if c.y_signal and c.y_signal.value is not None]
                if y_vals:
                    y_min, y_max = min(y_vals), max(y_vals)
                    obs.append(
                        f"Engine operated across map region: {decoded.x_axis.name} "
                        f"[{x_min:.1f} .. {x_max:.1f} {decoded.x_axis.unit}], "
                        f"{decoded.y_axis.name} [{y_min:.1f} .. {y_max:.1f} {decoded.y_axis.unit}]."
                    )
            else:
                obs.append(
                    f"Engine operated across curve region: {decoded.x_axis.name} "
                    f"[{x_min:.1f} .. {x_max:.1f} {decoded.x_axis.unit}]."
                )

        # Overshoot correlation
        overshoot_points = []
        for c in correlations:
            for p in all_points:
                if math.isclose(p.time_s, c.time_s, abs_tol=1e-4):
                    if p.boost_act_mbar is not None and p.boost_spec_mbar is not None:
                        delta = p.boost_act_mbar - p.boost_spec_mbar
                        if delta >= 80.0:
                            overshoot_points.append((delta, c, p))
                    break

        if overshoot_points:
            overshoot_points.sort(key=lambda item: item[0], reverse=True)
            peak_delta, peak_c, peak_p = overshoot_points[0]
            top_cells = sorted(peak_c.active_cells, key=lambda cell: cell.weight, reverse=True)
            cell_desc = ", ".join(
                f"({cell.x_index}, {cell.y_index}) [weight {cell.weight:.2f}]"
                if cell.y_index is not None
                else f"({cell.x_index}) [weight {cell.weight:.2f}]"
                for cell in top_cells
            )
            y_info = (
                f", {peak_c.y_signal.parameter_name}={peak_c.y_signal.value:.1f} {peak_c.y_signal.unit}"
                if peak_c.y_signal and peak_c.y_signal.value is not None
                else ""
            )
            obs.append(
                f"Peak boost overshoot (+{peak_delta:.1f} hPa) observed at t={peak_c.time_s:.2f}s "
                f"while engine operated in region: {peak_c.x_signal.parameter_name}={peak_c.x_signal.value:.0f} "
                f"{peak_c.x_signal.unit}{y_info}. Active grid nodes: {cell_desc}. "
                "Spatial association denotes exposure during the event; causality is not established."
            )

        # Clamping reporting in VISUAL_ONLY
        if mode == CorrelatorMode.VISUAL_ONLY:
            clamped_points = [c for c in correlations if c.is_clamped]
            if clamped_points:
                clamped_pct = (len(clamped_points) / len(correlations)) * 100.0
                obs.append(
                    f"Visual edge-clamping applied to {len(clamped_points)}/{len(correlations)} points ({clamped_pct:.1f}%). "
                    "Notice: Clamped points are strictly excluded from the cumulative evidence heatmap."
                )

        return obs
