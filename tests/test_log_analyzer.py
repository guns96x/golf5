# -*- coding: utf-8 -*-
"""
Unit tests for calharness.log_analyzer v2 (Hardened).
Verifies:
  1. Multi-format detection (VCDS WOT, VCDS Multi-Group, Android Turbo_Pair, Android Event_RAW).
  2. Independent group timestamps & interpolation on canonical timeline without extrapolation.
  3. Freshness gap masking (stale PIDs masked to None after dropout).
  4. Pointwise overshoot calculation (verifying resilience against asynchronous peaks).
  5. Pointwise limiter bottleneck timeline and percentage accounting directly over TelemetryPoints.
  6. Persistent pull kind classification (rejects single-sample spikes, tests WOT_CONFIRMED, WOT_LIKELY, HIGH_LOAD_PULL).
  7. Android Event_RAW synchronization.
  8. Multi-session metadata parsing across all sessions.
"""

from pathlib import Path
import pytest
import numpy as np

from calharness.log_analyzer import (
    LimiterBottleneck,
    LogAnalyzer,
    LogFormat,
    PullKind,
    TelemetryPoint,
    estimate_gear,
    interpolate_channel,
)


@pytest.fixture
def analyzer():
    return LogAnalyzer(max_interpolation_gap_s=2.5)


@pytest.fixture
def vcds_wot_path():
    p = Path("logs/VCDS_Logs/VCDS_WOT_Log_20260914_153242.csv")
    if not p.exists():
        pytest.skip(f"Log file not found: {p}")
    return p


@pytest.fixture
def vcds_group_path():
    p = Path("logs/vcds/LOG-01-011-003-008.CSV")
    if not p.exists():
        pytest.skip(f"Log file not found: {p}")
    return p


@pytest.fixture
def android_turbo_pair_path():
    p = Path("logs/20260916/Turbo_Pair_20260916_110755.csv")
    if not p.exists():
        pytest.skip(f"Log file not found: {p}")
    return p


@pytest.fixture
def android_event_raw_path():
    p = Path("logs/20260916/Event_RAW_20260916_110755.csv")
    if not p.exists():
        pytest.skip(f"Log file not found: {p}")
    return p


def test_gear_estimator():
    assert estimate_gear(0.0252) == 3
    assert estimate_gear(0.0350) == 4
    assert estimate_gear(0.0452) == 5
    assert estimate_gear(0.0100) is None


def test_detect_log_formats(analyzer, vcds_wot_path, vcds_group_path, android_turbo_pair_path, android_event_raw_path):
    fmt1, _ = analyzer.detect_format(vcds_wot_path)
    assert fmt1 == LogFormat.VCDS_WOT_CSV

    fmt2, _ = analyzer.detect_format(vcds_group_path)
    assert fmt2 == LogFormat.VCDS_ADVANCED_GROUP

    fmt3, _ = analyzer.detect_format(android_turbo_pair_path)
    assert fmt3 == LogFormat.ANDROID_TURBO_PAIR

    fmt4, _ = analyzer.detect_format(android_event_raw_path)
    assert fmt4 == LogFormat.ANDROID_EVENT_RAW


def test_vcds_wot_analysis(analyzer, vcds_wot_path):
    report = analyzer.analyze_file(vcds_wot_path)

    assert report.detected_format == LogFormat.VCDS_WOT_CSV
    assert report.total_samples == 307
    assert report.total_duration_s > 60.0
    assert report.max_recorded_boost_mbar == 2438.0
    assert report.wot_segments_count >= 1

    pull1 = report.wot_segments[0]
    assert pull1.start_rpm < pull1.end_rpm
    assert pull1.delta_rpm > 500.0
    assert pull1.max_specified_boost_mbar == 2203.0
    assert pull1.max_actual_boost_mbar == 2438.0
    assert pull1.overshoot_mbar == 235.0
    assert pull1.overshoot_pct > 10.0
    assert pull1.spool_time_s is not None and pull1.spool_time_s > 0.5


def test_vcds_multi_group_analysis(analyzer, vcds_group_path):
    report = analyzer.analyze_file(vcds_group_path)

    assert report.detected_format == LogFormat.VCDS_ADVANCED_GROUP
    assert report.wot_segments_count == 3

    # Pull 1 has persistent high driver request -> WOT_LIKELY
    assert report.wot_segments[0].pull_kind == PullKind.WOT_LIKELY
    assert report.wot_segments[0].overshoot_mbar > 200.0
    assert report.wot_segments[0].active_bottleneck == LimiterBottleneck.SMOKE_LIMITER
    assert report.wot_segments[0].limiter_metrics.smoke_limiter_pct > 70.0

    # Pull 2 also bottlenecked by Smoke Limiter
    assert report.wot_segments[1].active_bottleneck == LimiterBottleneck.SMOKE_LIMITER
    assert report.wot_segments[1].limiter_metrics.smoke_limiter_pct > 60.0

    # In Pull 3, driver modulated pedal
    assert report.wot_segments[2].limiter_metrics.smoke_limiter_pct > 40.0
    assert report.wot_segments[2].limiter_metrics.driver_wish_pct > 40.0

    # Verify sessions metadata parsed across ALL 4 sessions
    points, _, meta = analyzer.parse_log(vcds_group_path)
    assert "sessions" in meta
    assert len(meta["sessions"]) == 4
    session_times = [s["time"] for s in meta["sessions"]]
    assert "20:06:56" in session_times
    assert "20:23:44" in session_times
    assert "11:54:12" in session_times
    assert "11:54:46" in session_times

    # Verify no edge extrapolation before Group 008 started in session 1
    assert points[0].trq_request_nm is None
    assert points[1].trq_request_nm is None

    # Verify diagnostic findings
    assert any("Smoke Limiter" in f for f in report.diagnostic_findings)
    assert any("N75 duty cycle reached candidate minimum" in f for f in report.diagnostic_findings)


def test_android_turbo_pair_analysis(analyzer, android_turbo_pair_path):
    report = analyzer.analyze_file(android_turbo_pair_path)

    assert report.detected_format == LogFormat.ANDROID_TURBO_PAIR
    assert report.wot_segments_count >= 1

    pull1 = report.wot_segments[0]
    # Without direct pedal sensor verification, classified as HIGH_LOAD_PULL
    assert pull1.pull_kind == PullKind.HIGH_LOAD_PULL
    assert pull1.max_actual_boost_mbar >= 2300.0
    assert pull1.start_rpm >= 1500.0
    assert pull1.end_rpm >= 3500.0


def test_android_event_raw_synchronization(analyzer, android_event_raw_path):
    points, log_format, meta = analyzer.parse_log(android_event_raw_path)

    assert log_format == LogFormat.ANDROID_EVENT_RAW
    assert len(points) > 30

    valid_boost_pts = [p for p in points if p.boost_act_mbar is not None]
    assert len(valid_boost_pts) > 20
    assert any(p.rpm is not None and p.rpm > 1700 for p in valid_boost_pts)

    maf_pts = [p for p in points if p.maf_derived_mg is not None]
    assert len(maf_pts) > 0
    assert any(p.maf_derived_mg > 300.0 for p in maf_pts)
    assert all(p.maf_is_derived for p in maf_pts)
    assert all(p.maf_act_mg is None for p in points)


def test_asynchronous_overshoot_regression(analyzer):
    """
    Regression test for pointwise overshoot:
    Demonstrates that naive max(act) - max(spec) fails when peaks occur at different times,
    while pointwise max_t(act(t) - spec(t)) correctly calculates true overshoot.
    """
    points = [
        TelemetryPoint(time_s=0.0, rpm=1500.0, boost_spec_mbar=1600.0, boost_act_mbar=1200.0, trq_request_nm=350.0, trq_limit_nm=360.0, trq_smoke_nm=340.0),
        TelemetryPoint(time_s=1.0, rpm=2000.0, boost_spec_mbar=2400.0, boost_act_mbar=2100.0, trq_request_nm=350.0, trq_limit_nm=360.0, trq_smoke_nm=340.0),
        TelemetryPoint(time_s=2.0, rpm=2500.0, boost_spec_mbar=2200.0, boost_act_mbar=2200.0, trq_request_nm=350.0, trq_limit_nm=360.0, trq_smoke_nm=340.0),
        TelemetryPoint(time_s=3.0, rpm=3000.0, boost_spec_mbar=2000.0, boost_act_mbar=2300.0, trq_request_nm=350.0, trq_limit_nm=360.0, trq_smoke_nm=340.0), # Overshoot +300 mbar!
        TelemetryPoint(time_s=4.0, rpm=3500.0, boost_spec_mbar=1900.0, boost_act_mbar=1950.0, trq_request_nm=350.0, trq_limit_nm=360.0, trq_smoke_nm=340.0),
    ]

    naive_overshoot = max(p.boost_act_mbar for p in points) - max(p.boost_spec_mbar for p in points)
    assert naive_overshoot == 2300.0 - 2400.0 == -100.0  # Naive formula says -100 mbar (underboost!)

    metrics = analyzer.evaluate_segment_metrics(points, segment_id=1)
    assert metrics.overshoot_mbar == 300.0
    assert metrics.overshoot_pct == (300.0 / 2000.0) * 100.0 == 15.0
    assert metrics.pull_kind == PullKind.WOT_LIKELY


def test_pointwise_limiter_percentages(analyzer):
    """
    Test pointwise active limiter tracking evaluated strictly across synchronous TelemetryPoints.
    """
    points = [
        TelemetryPoint(time_s=0.0, rpm=1600.0, boost_act_mbar=1500.0, trq_request_nm=380.0, trq_limit_nm=350.0, trq_smoke_nm=300.0), # SMOKE
        TelemetryPoint(time_s=0.5, rpm=1800.0, boost_act_mbar=1700.0, trq_request_nm=380.0, trq_limit_nm=350.0, trq_smoke_nm=320.0), # SMOKE
        TelemetryPoint(time_s=1.0, rpm=2200.0, boost_act_mbar=2100.0, trq_request_nm=380.0, trq_limit_nm=330.0, trq_smoke_nm=360.0), # TORQUE
        TelemetryPoint(time_s=1.5, rpm=2600.0, boost_act_mbar=2200.0, trq_request_nm=380.0, trq_limit_nm=320.0, trq_smoke_nm=360.0), # TORQUE
        TelemetryPoint(time_s=2.0, rpm=3000.0, boost_act_mbar=2200.0, trq_request_nm=380.0, trq_limit_nm=310.0, trq_smoke_nm=350.0), # TORQUE
    ]

    metrics = analyzer.evaluate_segment_metrics(points, segment_id=1)
    assert metrics.limiter_metrics.smoke_limiter_pct == 40.0
    assert metrics.limiter_metrics.torque_limiter_pct == 60.0
    assert metrics.limiter_metrics.driver_wish_pct == 0.0
    assert metrics.active_bottleneck == LimiterBottleneck.TORQUE_LIMITER


def test_interpolation_boundary_no_extrapolation():
    """
    Verify that query times outside channel observation domain are masked to NaN (no edge hold).
    """
    obs_t = np.array([10.0, 11.0, 12.0])
    obs_v = np.array([100.0, 200.0, 300.0])
    targets = np.array([9.0, 10.0, 11.5, 12.0, 13.0])
    res = interpolate_channel(targets, obs_t, obs_v, max_gap_s=1.5)

    assert np.isnan(res[0])  # Before 10.0s -> NaN
    assert res[1] == 100.0
    assert res[2] == 250.0
    assert res[3] == 300.0
    assert np.isnan(res[4])  # After 12.0s -> NaN


def test_max_interpolation_gap_freshness():
    """
    Verify that dropouts/gaps larger than max_gap_s are masked to NaN.
    """
    obs_t = np.array([1.0, 2.0, 6.0, 7.0])  # 4.0s dropout gap between 2.0 and 6.0
    obs_v = np.array([10.0, 20.0, 60.0, 70.0])
    targets = np.array([1.5, 3.0, 4.5, 5.5, 6.5])
    res = interpolate_channel(targets, obs_t, obs_v, max_gap_s=1.5)

    assert res[0] == 15.0
    assert np.isnan(res[1])  # In 4.0s gap
    assert np.isnan(res[2])  # In 4.0s gap
    assert np.isnan(res[3])  # In 4.0s gap
    assert res[4] == 65.0


def test_pull_kind_classification_persistence(analyzer):
    """
    Verify persistence requirement:
    - Transient driver demand spike does NOT trigger WOT_LIKELY (remains HIGH_LOAD_PULL).
    - Persistent driver demand (>=70% samples) triggers WOT_LIKELY.
    - Verified pedal sensor (>=95% for >=70% samples) triggers WOT_CONFIRMED.
    """
    # 1. Transient spike (1 out of 10 samples)
    spike_pts = [
        TelemetryPoint(time_s=i * 0.2, rpm=1500.0 + i * 100, boost_act_mbar=1500.0, trq_request_nm=150.0)
        for i in range(10)
    ]
    spike_pts[5].trq_request_nm = 380.0  # Spike
    m_spike = analyzer.evaluate_segment_metrics(spike_pts, segment_id=1)
    assert m_spike.pull_kind == PullKind.HIGH_LOAD_PULL

    # 2. Persistent torque request (10 out of 10 samples)
    persist_pts = [
        TelemetryPoint(time_s=i * 0.2, rpm=1500.0 + i * 100, boost_act_mbar=1500.0, trq_request_nm=350.0)
        for i in range(10)
    ]
    m_persist = analyzer.evaluate_segment_metrics(persist_pts, segment_id=2)
    assert m_persist.pull_kind == PullKind.WOT_LIKELY

    # 3. Direct pedal sensor verification (10 out of 10 samples)
    pedal_pts = [
        TelemetryPoint(time_s=i * 0.2, rpm=1500.0 + i * 100, boost_act_mbar=1500.0, pedal_pct=98.0)
        for i in range(10)
    ]
    m_pedal = analyzer.evaluate_segment_metrics(pedal_pts, segment_id=3)
    assert m_pedal.pull_kind == PullKind.WOT_CONFIRMED
