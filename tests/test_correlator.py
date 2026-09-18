# -*- coding: utf-8 -*-
"""
tests.test_correlator

Comprehensive unit, synthetic regression, and integration tests for MapCorrelator,
AxisResolverRegistry, and the Map Exposure Engine under strict semantic provenance.
"""

import math
from pathlib import Path
import numpy as np
import pytest

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
    TorqueToFuelConverter,
    UncertaintyStatus,
    _bilinear_interpolate,
    _find_bounding_interval,
    _linear_interpolate_1d,
    _validate_axis_monotonic,
)
from calharness.decoder import MapDecoder
from calharness.log_analyzer import LogAnalyzer, TelemetryPoint
from calharness.models import AxisData, DecodedMap


def make_synthetic_map_2d(
    name: str = "Test_2D_MAP",
    x_name: str = "Eng_nAvrg",
    x_unit: str = "rpm",
    x_vals: list[float] = None,
    y_name: str = "PCR_qDes",
    y_unit: str = "mg/hub",
    y_vals: list[float] = None,
    grid: list[list[float]] = None,
) -> DecodedMap:
    """Construct a synthetic 2D DecodedMap for testing."""
    if x_vals is None:
        x_vals = [1000.0, 2000.0, 3000.0, 4000.0]
    if y_vals is None:
        y_vals = [10.0, 20.0, 30.0]
    nx = len(x_vals)
    ny = len(y_vals)

    if grid is None:
        grid = [
            [round(x * 0.1 + y * 10.0, 2) for y in y_vals]
            for x in x_vals
        ]

    x_axis = AxisData(
        name=x_name,
        unit=x_unit,
        count=nx,
        raw_values=[int(v) for v in x_vals],
        physical_values=x_vals,
    )
    y_axis = AxisData(
        name=y_name,
        unit=y_unit,
        count=ny,
        raw_values=[int(v) for v in y_vals],
        physical_values=y_vals,
    )
    return DecodedMap(
        name=name,
        description="Synthetic Test Map",
        obj_type="MAP",
        address=0x1E0000,
        record_layout="Kf_Xs16_Ys16_Ws16",
        unit="hPa",
        shape=(nx, ny),
        x_axis=x_axis,
        y_axis=y_axis,
        raw_grid=[[int(v) for v in row] for row in grid],
        physical_grid=grid,
    )


def make_synthetic_curve_1d(
    name: str = "Test_1D_CURVE",
    x_name: str = "Eng_nAvrg",
    x_unit: str = "rpm",
    x_vals: list[float] = None,
    values: list[float] = None,
) -> DecodedMap:
    """Construct a synthetic 1D DecodedMap (curve) for testing."""
    if x_vals is None:
        x_vals = [1000.0, 2000.0, 3000.0, 4000.0]
    if values is None:
        values = [100.0, 200.0, 300.0, 400.0]
    nx = len(x_vals)

    x_axis = AxisData(
        name=x_name,
        unit=x_unit,
        count=nx,
        raw_values=[int(v) for v in x_vals],
        physical_values=x_vals,
    )
    return DecodedMap(
        name=name,
        description="Synthetic Test Curve",
        obj_type="CURVE",
        address=0x1E1000,
        record_layout="Kl_Xs16_Ws16",
        unit="Nm",
        shape=(nx,),
        x_axis=x_axis,
        y_axis=None,
        raw_grid=[int(v) for v in values],
        physical_grid=values,
    )


class DummyDecoder:
    """Mock decoder for synthetic unit testing."""
    def __init__(self, maps: dict[str, DecodedMap]):
        self.maps = maps

    def decode(self, name: str) -> DecodedMap:
        if name in self.maps:
            return self.maps[name]
        raise KeyError(f"Map '{name}' not found in dummy decoder")


# ==============================================================================
# 1. Bilinear & Mathematical Invariant Tests
# ==============================================================================

def test_exact_grid_node():
    """A point matching an exact grid node must have weight 1.0 on that node and 0.0 elsewhere."""
    synth_map = make_synthetic_map_2d()
    x_pts = synth_map.x_axis.to_numpy()
    y_pts = synth_map.y_axis.to_numpy()
    grid = synth_map.numpy_physical()

    val, active_cells, is_clamped, clamp_axes = _bilinear_interpolate(
        x_pts, y_pts, grid, x=2000.0, y=20.0, allow_clamping=False
    )
    assert not is_clamped
    assert len(clamp_axes) == 0
    assert math.isclose(val, 400.0, abs_tol=1e-4)

    assert len(active_cells) == 1
    assert active_cells[0].x_index == 1
    assert active_cells[0].y_index == 1
    assert math.isclose(active_cells[0].weight, 1.0, abs_tol=1e-4)


def test_bilinear_interpolation_center():
    """A point between 4 cells must produce 4 non-zero weights summing to 1.0."""
    synth_map = make_synthetic_map_2d()
    x_pts = synth_map.x_axis.to_numpy()
    y_pts = synth_map.y_axis.to_numpy()
    grid = synth_map.numpy_physical()

    val, active_cells, is_clamped, clamp_axes = _bilinear_interpolate(
        x_pts, y_pts, grid, x=1500.0, y=15.0, allow_clamping=False
    )
    assert not is_clamped
    assert len(active_cells) == 4

    total_weight = sum(c.weight for c in active_cells)
    assert math.isclose(total_weight, 1.0, abs_tol=1e-4)

    for c in active_cells:
        assert math.isclose(c.weight, 0.25, abs_tol=1e-4)

    assert math.isclose(val, 300.0, abs_tol=1e-4)


def test_axis_clamping_boundary_in_visual_mode():
    """Coordinates outside axis range must be clamped only when allow_clamping is True."""
    synth_map = make_synthetic_map_2d()
    x_pts = synth_map.x_axis.to_numpy()
    y_pts = synth_map.y_axis.to_numpy()
    grid = synth_map.numpy_physical()

    val, active_cells, is_clamped, clamp_axes = _bilinear_interpolate(
        x_pts, y_pts, grid, x=500.0, y=50.0, allow_clamping=True
    )
    assert is_clamped is True
    assert "X" in clamp_axes
    assert "Y" in clamp_axes

    # Clamped to (1000, 30): index (0, 2)
    assert len(active_cells) == 1
    assert active_cells[0].x_index == 0
    assert active_cells[0].y_index == 2
    assert math.isclose(active_cells[0].weight, 1.0, abs_tol=1e-4)
    assert math.isclose(val, 400.0, abs_tol=1e-4)


def test_non_monotonic_axis_rejected():
    """Non-monotonic axis breakpoints must be strictly rejected with ValueError."""
    bad_x = np.array([1000.0, 2000.0, 1900.0, 3000.0])
    with pytest.raises(ValueError, match="Non-monotonic axis detected"):
        _validate_axis_monotonic(bad_x, "TestBadAxis")


# ==============================================================================
# 2. Explicit AxisResolverRegistry Tests (Zero Generic Unit Inferences)
# ==============================================================================

def test_unrelated_hpa_axis_rejected_not_resolved_to_map():
    """An unrelated A2L axis with unit hPa must NOT be resolved to manifold pressure."""
    registry = AxisResolverRegistry()
    pt = TelemetryPoint(time_s=1.0, rpm=2000.0, boost_act_mbar=1800.0)

    # Ambient pressure axis or Rail pressure axis
    unrelated_axis = AxisData(
        name="Amb_p_mp",
        unit="hPa",
        count=3,
        raw_values=[900, 1000, 1100],
        physical_values=[900.0, 1000.0, 1100.0],
    )
    sig = registry.resolve(unrelated_axis, pt, "SomeMap", "Y", CorrelatorMode.EXPERIMENTAL)

    assert sig.provenance_kind == SignalProvenanceKind.MISSING
    assert sig.value is None
    assert "Unsupported axis symbol 'Amb_p_mp'" in sig.caveat
    assert "Generic unit-based matching is forbidden" in sig.caveat


def test_unrelated_nm_axis_rejected_not_resolved_to_driver_request():
    """An unrelated A2L axis with unit Nm must NOT be resolved to driver request torque."""
    registry = AxisResolverRegistry()
    pt = TelemetryPoint(time_s=1.0, rpm=2000.0, trq_request_nm=300.0)

    unrelated_axis = AxisData(
        name="Trq_limGear_mp",
        unit="Nm",
        count=3,
        raw_values=[100, 200, 300],
        physical_values=[100.0, 200.0, 300.0],
    )
    sig = registry.resolve(unrelated_axis, pt, "SomeMap", "Y", CorrelatorMode.EXPERIMENTAL)

    assert sig.provenance_kind == SignalProvenanceKind.MISSING
    assert sig.value is None
    assert "Unsupported axis symbol 'Trq_limGear_mp'" in sig.caveat


def test_unrelated_mg_axis_rejected_not_resolved_to_driver_wish():
    """An unrelated A2L axis with unit mg/hub must NOT be resolved to driver wish or limiter IQ."""
    registry = AxisResolverRegistry()
    pt = TelemetryPoint(time_s=1.0, rpm=2000.0, driver_wish_iq_mg=45.0)

    unrelated_axis = AxisData(
        name="Inj_qPilot_mp",
        unit="mg/hub",
        count=3,
        raw_values=[1, 2, 3],
        physical_values=[1.0, 2.0, 3.0],
    )
    sig = registry.resolve(unrelated_axis, pt, "SomeMap", "Y", CorrelatorMode.EXPERIMENTAL)

    assert sig.provenance_kind == SignalProvenanceKind.MISSING
    assert sig.value is None
    assert "Unsupported axis symbol 'Inj_qPilot_mp'" in sig.caveat


# ==============================================================================
# 3. Domain Enforcement & Zero Evidence Clamping Tests
# ==============================================================================

def test_experimental_target_map_ood_is_dropped_not_clamped_into_heatmap():
    """In EXPERIMENTAL mode, target map OOD points are dropped and do NOT accumulate in heatmap."""
    synth_map = make_synthetic_map_2d(
        name="PCR_pBDesBas_MAP",
        x_vals=[1000.0, 2000.0, 3000.0, 4000.0],
        y_vals=[10.0, 20.0, 30.0],
    )
    correlator = MapCorrelator(
        decoder=DummyDecoder({"PCR_pBDesBas_MAP": synth_map}),
        mode=CorrelatorMode.EXPERIMENTAL,
    )

    # Point with RPM=4800 (exceeds map max 4000 RPM)
    pt_ood = TelemetryPoint(time_s=1.0, rpm=4800.0, driver_wish_iq_mg=20.0)
    corr, drop_reason = correlator.correlate_point(synth_map, pt_ood)

    assert corr is None
    assert drop_reason is not None
    assert "OUT_OF_DOMAIN" in drop_reason
    assert "Eng_nAvrg" in drop_reason

    # Verify that evaluating points drops OOD and leaves heatmap at zero
    report = correlator.correlate_points(synth_map, [pt_ood])
    assert report.mapped_points_count == 0
    assert report.dropped_points_count == 1
    assert any("OUT_OF_DOMAIN" in k for k in report.drop_reasons.keys())

    # Heatmap MUST NOT have any edge-clamped hits
    total_heatmap = sum(sum(row) for row in report.cell_hit_matrix)
    assert math.isclose(total_heatmap, 0.0, abs_tol=1e-6)


def test_visual_only_mode_clamped_points_exclude_from_heatmap():
    """In VISUAL_ONLY mode, clamped points are mapped for GUI but excluded from evidence heatmap."""
    synth_map = make_synthetic_map_2d(
        name="PCR_pBDesBas_MAP",
        x_vals=[1000.0, 2000.0, 3000.0, 4000.0],
        y_vals=[10.0, 20.0, 30.0],
    )
    correlator = MapCorrelator(
        decoder=DummyDecoder({"PCR_pBDesBas_MAP": synth_map}),
        mode=CorrelatorMode.VISUAL_ONLY,
    )

    # Point with RPM=4800 (exceeds map max 4000 RPM)
    pt_ood = TelemetryPoint(time_s=1.0, rpm=4800.0, driver_wish_iq_mg=20.0)
    corr, reason = correlator.correlate_point(synth_map, pt_ood)

    assert reason is None
    assert corr is not None
    assert corr.is_clamped is True

    # But when generating report, clamped point is excluded from accumulating into cell_hit_matrix
    report = correlator.correlate_points(synth_map, [pt_ood])
    assert report.mapped_points_count == 1
    total_heatmap = sum(sum(row) for row in report.cell_hit_matrix)
    assert math.isclose(total_heatmap, 0.0, abs_tol=1e-6)
    assert any("excluded from the cumulative evidence heatmap" in obs for obs in report.exposure_observations)


def test_fmtc_out_of_domain_rejection():
    """FMTC_trq2qBas_MAP caps at 336 Nm: requests > 336 Nm must be DERIVED_OUT_OF_DOMAIN."""
    fmtc_map = make_synthetic_map_2d(
        name="FMTC_trq2qBas_MAP",
        x_name="Eng_nAvrg",
        x_unit="rpm",
        x_vals=[1000.0, 2000.0, 3000.0],
        y_name="CoEng_trqInrSet",
        y_unit="Nm",
        y_vals=[100.0, 200.0, 336.0],
        grid=[[20.0, 40.0, 70.0], [20.0, 40.0, 70.0], [20.0, 40.0, 70.0]],
    )
    converter = TorqueToFuelConverter(fmtc_map)

    # 360 Nm request -> DERIVED_OUT_OF_DOMAIN
    fuel_ood, prov_ood, reason_ood = converter.convert(rpm=2000.0, torque_nm=360.0)
    assert fuel_ood is None
    assert prov_ood == SignalProvenanceKind.DERIVED_OUT_OF_DOMAIN
    assert "360.0 Nm > map limit 336.0 Nm" in reason_ood


# ==============================================================================
# 4. Downstream Comparison & Provenance Accounting Tests
# ==============================================================================

def test_base_boost_map_vs_final_boost_is_downstream_signal():
    """Comparison of PCR_pBDesBas_MAP against VCDS boost_spec_mbar must be DOWNSTREAM_SIGNAL."""
    synth_map = make_synthetic_map_2d(
        name="PCR_pBDesBas_MAP",
        x_vals=[1000.0, 2000.0, 3000.0],
        y_vals=[10.0, 20.0, 30.0],
    )
    correlator = MapCorrelator(
        decoder=DummyDecoder({"PCR_pBDesBas_MAP": synth_map}),
        mode=CorrelatorMode.EXPERIMENTAL,
    )

    pt = TelemetryPoint(
        time_s=2.0,
        rpm=2000.0,
        driver_wish_iq_mg=20.0,
        boost_spec_mbar=2150.0,
    )
    corr, reason = correlator.correlate_point(synth_map, pt)

    assert reason is None
    assert corr is not None
    assert corr.comparison.comparison_kind == ComparisonKind.DOWNSTREAM_SIGNAL
    assert corr.comparison.channel_name == "boost_spec_mbar"
    assert corr.comparison.observed_value == 2150.0
    # Difference is denoted as observed_minus_base_map, NOT control_error
    assert corr.comparison.observed_minus_base_map is not None
    assert "PCR_pBDesBas_MAP is a base calibration target" in corr.comparison.caveat


def test_base_n75_map_vs_final_n75_is_downstream_signal():
    """Comparison of PCR_rBPCtlBas_MAP against VCDS n75_duty_pct must be DOWNSTREAM_SIGNAL."""
    synth_map = make_synthetic_map_2d(
        name="PCR_rBPCtlBas_MAP",
        y_name="PCR_qCtl",
        x_vals=[1000.0, 2000.0, 3000.0],
        y_vals=[10.0, 20.0, 30.0],
    )
    correlator = MapCorrelator(
        decoder=DummyDecoder({"PCR_rBPCtlBas_MAP": synth_map}),
        mode=CorrelatorMode.EXPERIMENTAL,
    )

    pt = TelemetryPoint(
        time_s=3.0,
        rpm=2000.0,
        driver_wish_iq_mg=20.0,
        n75_duty_pct=72.5,
    )
    corr, reason = correlator.correlate_point(synth_map, pt)

    assert reason is None
    assert corr is not None
    assert corr.comparison.comparison_kind == ComparisonKind.DOWNSTREAM_SIGNAL
    assert corr.comparison.channel_name == "n75_duty_pct"
    assert corr.comparison.observed_value == 72.5
    assert "PCR_rBPCtlBas_MAP is a base feedforward duty cycle" in corr.comparison.caveat


def test_unquantified_proxy_uncertainty_has_no_arbitrary_percentage():
    """Proxy derivations must set uncertainty_pct=None and uncertainty_status=UNQUANTIFIED."""
    fmtc_map = make_synthetic_map_2d(
        name="FMTC_trq2qBas_MAP",
        x_vals=[1000.0, 2000.0, 3000.0],
        y_name="CoEng_trqInrSet",
        y_vals=[100.0, 200.0, 336.0],
        grid=[[20.0, 40.0, 70.0], [20.0, 40.0, 70.0], [20.0, 40.0, 70.0]],
    )
    converter = TorqueToFuelConverter(fmtc_map)
    registry = AxisResolverRegistry(torque_converter=converter)

    axis_qdes = AxisData(
        name="PCR_qDes",
        unit="mg/hub",
        count=3,
        raw_values=[1, 2, 3],
        physical_values=[10.0, 20.0, 30.0],
    )
    pt = TelemetryPoint(time_s=1.0, rpm=2000.0, trq_request_nm=250.0)
    sig = registry.resolve(axis_qdes, pt, "PCR_pBDesBas_MAP", "Y", CorrelatorMode.EXPERIMENTAL)

    assert sig.provenance_kind == SignalProvenanceKind.DERIVED_APPROXIMATE
    # Zero arbitrary percentages!
    assert sig.uncertainty_pct is None
    assert sig.uncertainty_status == UncertaintyStatus.UNQUANTIFIED
    assert sig.caveat is not None


# ==============================================================================
# 5. Integration Tests with Stock Firmware and VCDS Log
# ==============================================================================

STOCK_BIN = Path("knowledge/08_firmware/originals/03G906021QJ_1984_391847_full_stock.bin")
VCDS_LOG = Path("logs/VCDS_Logs/VCDS_WOT_Log_20260914_153242.csv")


@pytest.mark.skipif(not STOCK_BIN.exists(), reason="Stock firmware binary not found")
def test_real_firmware_strict_vs_experimental_modes():
    """Verify MapCorrelator against real stock binary under STRICT and EXPERIMENTAL modes."""
    decoder = MapDecoder(STOCK_BIN)
    torque_conv = TorqueToFuelConverter(decoder)

    # 1. STRICT Mode: Rejects torque conversion for PCR_pBDesBas_MAP
    strict_corr = MapCorrelator(decoder=decoder, torque_converter=torque_conv, mode=CorrelatorMode.STRICT)
    pt = TelemetryPoint(time_s=1.0, rpm=2250.0, trq_request_nm=240.0)
    corr, reason = strict_corr.correlate_point("PCR_pBDesBas_MAP", pt)
    assert corr is None
    assert "STRICT mode" in reason

    # 2. EXPERIMENTAL Mode: Maps in-domain torque request as DERIVED_APPROXIMATE
    exp_corr = MapCorrelator(decoder=decoder, torque_converter=torque_conv, mode=CorrelatorMode.EXPERIMENTAL)
    corr_exp, reason_exp = exp_corr.correlate_point("PCR_pBDesBas_MAP", pt)
    assert reason_exp is None
    assert corr_exp is not None
    assert corr_exp.y_signal.provenance_kind == SignalProvenanceKind.DERIVED_APPROXIMATE
    assert corr_exp.y_signal.semantic_match == SemanticMatchLevel.PROXY_APPROXIMATE
    assert corr_exp.y_signal.uncertainty_pct is None
    assert corr_exp.y_signal.uncertainty_status == UncertaintyStatus.UNQUANTIFIED


@pytest.mark.skipif(not (STOCK_BIN.exists() and VCDS_LOG.exists()), reason="Stock binary or VCDS log missing")
def test_real_vcds_pull_coverage_and_experimental_correlation():
    """Correlate real VCDS acceleration pull onto FlMng_qPresSmoke_MAP and PCR_pBDesBas_MAP."""
    decoder = MapDecoder(STOCK_BIN)
    torque_conv = TorqueToFuelConverter(decoder)
    analyzer = LogAnalyzer()
    points, fmt, meta = analyzer.parse_log(VCDS_LOG)
    pulls = analyzer.segment_wot_pulls(points)
    assert len(pulls) > 0

    pull_points = pulls[0]

    # 1. Test COVERAGE_ONLY mode on smoke map
    cov_correlator = MapCorrelator(decoder=decoder, mode=CorrelatorMode.COVERAGE_ONLY)
    cov_report = cov_correlator.correlate_points("FlMng_qPresSmoke_MAP", pull_points)
    assert cov_report.total_points_evaluated == len(pull_points)
    assert cov_report.mapped_points_count == 0
    assert "X_Eng_nAvrg" in cov_report.axis_coverage_summary

    # 2. Test STRICT mode on smoke map: all points dropped due to missing temperature correction
    strict_correlator = MapCorrelator(decoder=decoder, mode=CorrelatorMode.STRICT)
    strict_report = strict_correlator.correlate_points("FlMng_qPresSmoke_MAP", pull_points)
    assert strict_report.total_points_evaluated == len(pull_points)
    assert strict_report.mapped_points_count == 0
    assert strict_report.dropped_points_count == len(pull_points)
    assert any("STRICT mode" in r for r in strict_report.drop_reasons.keys())

    # 3. Test EXPERIMENTAL mode on smoke map: all points mapped with proxy caveat
    exp_correlator = MapCorrelator(decoder=decoder, mode=CorrelatorMode.EXPERIMENTAL)
    exp_report = exp_correlator.correlate_points("FlMng_qPresSmoke_MAP", pull_points)
    assert exp_report.total_points_evaluated == len(pull_points)
    # Notice: In EXPERIMENTAL mode, points outside target map domain are dropped!
    # For FlMng_qPresSmoke_MAP, Y axis ends at 2000 hPa in stock.
    # WOT pull reaches 2438 hPa, so points > 2000 hPa are dropped as OUT_OF_DOMAIN!
    assert exp_report.dropped_points_count > 0
    assert any("OUT_OF_DOMAIN" in k for k in exp_report.drop_reasons.keys())
    assert len(exp_report.exposure_observations) > 0
