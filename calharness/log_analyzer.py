# -*- coding: utf-8 -*-
"""
calharness.log_analyzer

Production Telemetry and Log Analyzer v2 (Hardened) for Bosch EDC16 ECU systems.
Features:
  1. Multi-format normalization & resampling without false extrapolation:
       - VCDS WOT single-table CSV.
       - VCDS Advanced Measuring Blocks (011/003/008) with independent group timestamps
         resampled onto a canonical timeline with max freshness gap enforcement.
       - Android Turbo_Pair synchronous capture.
       - Android Event_RAW asynchronous OBD PID event stream synchronized via time-binning.
       - Zero extrapolation outside channel observation boundaries (None outside domain).
       - Max interpolation gap / freshness threshold (default 1.5s - 2.0s) masking stale PIDs to None.
  2. Acceleration pull segmentation and persistent classification:
       - WOT_CONFIRMED: Explicit persistent full pedal verified (pedal_pct >= 95% for >= 70% of pull).
       - WOT_LIKELY: Persistent high driver request (trq_request >= 330 Nm or driver_wish >= 55 mg for >= 70% of pull).
       - HIGH_LOAD_PULL: Boost rise / load without persistent verified full driver demand.
  3. Physical metrics:
       - Pointwise boost overshoot: max_t(actual(t) - specified(t)) during active demand.
       - Spool time & rate evaluated relative to instantaneous target trajectory.
       - Steady-state control error (mean & std after spool completion).
       - N75 governor duty cycle statistics and provenance-backed control margin warnings.
       - Pointwise fuel/torque limiter timeline evaluated strictly across synchronized TelemetryPoints.
       - MAF air mass per stroke (actual vs specified).
       - Transmission gear estimation (speed/RPM ratio clustering).
  4. Structured machine-readable Pydantic report and CLI summary.
"""

from __future__ import annotations

import csv
import enum
import math
import os
import re
import statistics
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from calharness.rules import N75_MIN_CONTROL_BOUND_PCT, N75_MAX_CONTROL_BOUND_PCT


def interpolate_channel(
    target_times: np.ndarray,
    obs_times: np.ndarray,
    obs_vals: np.ndarray,
    max_gap_s: float = 1.5,
) -> np.ndarray:
    """
    Linearly interpolate channel values onto target_times without edge extrapolation
    and masking gaps larger than max_gap_s with NaN.
    """
    if len(obs_times) == 0:
        return np.full(len(target_times), np.nan)
    if len(obs_times) == 1:
        res = np.full(len(target_times), np.nan)
        mask = np.isclose(target_times, obs_times[0], atol=0.01)
        res[mask] = obs_vals[0]
        return res

    # 1. Standard linear interpolation with NaN outside bounds (no extrapolation)
    interp_vals = np.interp(target_times, obs_times, obs_vals, left=np.nan, right=np.nan)

    # 2. Check freshness gaps: mask query points that fall strictly inside gaps > max_gap_s
    idx = np.searchsorted(obs_times, target_times)
    valid_inside = (idx > 0) & (idx < len(obs_times))
    is_exact = np.isclose(target_times, obs_times[np.clip(idx, 0, len(obs_times) - 1)]) | np.isclose(
        target_times, obs_times[np.clip(idx - 1, 0, len(obs_times) - 1)]
    )
    strictly_inside = valid_inside & (~is_exact)

    gaps = obs_times[idx[strictly_inside]] - obs_times[idx[strictly_inside] - 1]
    too_large = gaps > max_gap_s
    target_inside_indices = np.where(strictly_inside)[0]
    bad_indices = target_inside_indices[too_large]
    interp_vals[bad_indices] = np.nan

    return interp_vals


class LogFormat(str, enum.Enum):
    """Detected format of ECU telemetry log."""
    VCDS_WOT_CSV = "VCDS_WOT_CSV"                    # Standard single-table VCDS WOT export
    VCDS_ADVANCED_GROUP = "VCDS_ADVANCED_GROUP"      # Multi-group VCDS measuring blocks (011/003/008)
    ANDROID_TURBO_PAIR = "ANDROID_TURBO_PAIR"        # Phone OBD Turbo_Pair synchronous capture
    ANDROID_EVENT_RAW = "ANDROID_EVENT_RAW"          # Phone OBD raw asynchronous PID events
    UNKNOWN = "UNKNOWN"


class PullKind(str, enum.Enum):
    """Classification of acceleration pull based on persistent demand evidence."""
    WOT_CONFIRMED = "WOT_CONFIRMED"  # Explicit persistent full pedal verified (pedal_pct >= 95% for >= 70% of pull)
    WOT_LIKELY = "WOT_LIKELY"        # Persistent high driver request (trq >= 330 Nm or dw >= 55 mg for >= 70% of pull)
    HIGH_LOAD_PULL = "HIGH_LOAD_PULL"# Boost rise / load without persistent verified full driver demand


class LimiterBottleneck(str, enum.Enum):
    """Active fuel / torque limiter restricting engine output."""
    SMOKE_LIMITER = "SMOKE_LIMITER"      # Airflow smoke map restricts fueling
    TORQUE_LIMITER = "TORQUE_LIMITER"    # Engine protection torque curve restricts fueling
    DRIVER_WISH = "DRIVER_WISH"          # Pedal request was lower than all limiters
    TIED = "TIED"                        # Multiple limiters tied within margin of tolerance
    UNKNOWN = "UNKNOWN"                  # Inactive, flatline, zero channels, or insufficient data


class TelemetryPoint(BaseModel):
    """Normalized synchronous or interpolated telemetry sample."""
    model_config = ConfigDict(extra="forbid")

    time_s: float
    session_id: int = 0
    rpm: Optional[float] = None
    speed_kmh: Optional[float] = None
    boost_spec_mbar: Optional[float] = None
    boost_act_mbar: Optional[float] = None
    n75_duty_pct: Optional[float] = None
    maf_act_mg: Optional[float] = None
    maf_spec_mg: Optional[float] = None
    maf_derived_mg: Optional[float] = None
    maf_is_derived: bool = False
    driver_wish_iq_mg: Optional[float] = None
    torque_limit_iq_mg: Optional[float] = None
    smoke_limit_iq_mg: Optional[float] = None
    trq_request_nm: Optional[float] = None
    trq_limit_nm: Optional[float] = None
    trq_smoke_nm: Optional[float] = None
    pedal_pct: Optional[float] = None
    throttle_pct: Optional[float] = None
    load_pct: Optional[float] = None
    soi_deg: Optional[float] = None
    duration_deg: Optional[float] = None


class LimiterMetrics(BaseModel):
    """Pointwise limiter statistics evaluated across an acceleration pull."""
    model_config = ConfigDict(extra="forbid")

    dominant_bottleneck: LimiterBottleneck = LimiterBottleneck.UNKNOWN
    smoke_limiter_pct: float = 0.0
    torque_limiter_pct: float = 0.0
    driver_wish_pct: float = 0.0
    tied_pct: float = 0.0
    channel_flatlined: bool = False
    max_driver_wish: Optional[float] = None
    max_torque_limit: Optional[float] = None
    max_smoke_limit: Optional[float] = None


class WOTSegmentMetrics(BaseModel):
    """Performance metrics evaluated over an individual acceleration pull."""
    model_config = ConfigDict(extra="forbid")

    segment_id: int
    pull_kind: PullKind = PullKind.HIGH_LOAD_PULL
    start_time_s: float
    end_time_s: float
    duration_s: float
    start_rpm: float
    end_rpm: float
    delta_rpm: float
    
    # Gear identification
    estimated_gear: Optional[int] = None
    gear_provenance: Optional[str] = None
    kmh_per_rpm: Optional[float] = None

    # Boost dynamics (pointwise)
    max_specified_boost_mbar: float
    max_actual_boost_mbar: float
    overshoot_mbar: float                   # max_t(actual(t) - specified(t)) during active demand
    overshoot_pct: float                    # (overshoot_mbar / specified(t_peak)) * 100
    max_boost_delta_mbar: float             # max_t(actual(t) - specified(t)) across segment
    min_boost_delta_mbar: float             # min_t(actual(t) - specified(t)) across segment
    spool_time_s: Optional[float] = None    # time from trigger until actual reaches 90% of target trajectory
    spool_rate_mbar_per_s: Optional[float] = None # rate of boost rise during spool
    steady_state_mean_error_mbar: Optional[float] = None # mean(act - spec) after spool completion
    steady_state_std_error_mbar: Optional[float] = None  # std(act - spec) after spool completion
    
    # N75 Wastegate / VNT Governor
    n75_min_duty_pct: Optional[float] = None
    n75_max_duty_pct: Optional[float] = None
    n75_mean_duty_pct: Optional[float] = None
    n75_saturated_low: bool = False         # True if N75 <= N75_MIN_CONTROL_BOUND_PCT
    n75_saturated_high: bool = False        # True if N75 >= N75_MAX_CONTROL_BOUND_PCT

    # Airflow (MAF)
    max_maf_mg: Optional[float] = None
    mean_maf_mg: Optional[float] = None
    maf_is_derived: bool = False

    # Fuel / Torque Limiter Bottleneck (Pointwise)
    limiter_metrics: LimiterMetrics = Field(default_factory=LimiterMetrics)
    active_bottleneck: LimiterBottleneck = LimiterBottleneck.UNKNOWN
    max_driver_wish: Optional[float] = None
    max_torque_limit: Optional[float] = None
    max_smoke_limit: Optional[float] = None

    samples_count: int


class LogAnalysisReport(BaseModel):
    """Comprehensive machine-readable report of log analysis."""
    model_config = ConfigDict(extra="forbid")

    source_path: str
    detected_format: LogFormat
    session_label: Optional[str] = None
    total_samples: int
    total_duration_s: float
    rpm_range: Tuple[float, float]
    max_recorded_boost_mbar: float
    wot_segments_count: int
    wot_segments: List[WOTSegmentMetrics] = Field(default_factory=list)
    diagnostic_findings: List[str] = Field(default_factory=list)
    parse_warnings: List[str] = Field(default_factory=list)

    def summary(self) -> str:
        """Human-readable overview of telemetry and WOT performance analysis."""
        lines = [
            f"Log Analysis: {Path(self.source_path).name}",
            f"  Format:   {self.detected_format.value}",
            f"  Duration: {self.total_duration_s:.1f} s ({self.total_samples} samples)",
            f"  RPM:      {self.rpm_range[0]:.0f} .. {self.rpm_range[1]:.0f} RPM",
            f"  Peak MAP: {self.max_recorded_boost_mbar:.1f} mbar",
            f"  Pulls Detected: {self.wot_segments_count}",
        ]
        if self.wot_segments:
            lines.append("\nAcceleration Segments:")
            for s in self.wot_segments:
                gear_str = f"Gear {s.estimated_gear}" if s.estimated_gear else "Unknown Gear"
                spool_str = f"{s.spool_time_s:.2f}s" if s.spool_time_s is not None else "N/A"
                overshoot_str = f"+{s.overshoot_mbar:.0f} mbar ({s.overshoot_pct:+.1f}%)" if s.overshoot_mbar > 0 else "None"
                n75_str = f"[{s.n75_min_duty_pct:.1f}..{s.n75_max_duty_pct:.1f}%]" if s.n75_min_duty_pct is not None else "N/A"
                bottleneck_str = (
                    f"{s.active_bottleneck.value} (Smoke {s.limiter_metrics.smoke_limiter_pct:.0f}%, Trq {s.limiter_metrics.torque_limiter_pct:.0f}%)"
                    if s.active_bottleneck != LimiterBottleneck.UNKNOWN
                    else "N/A"
                )
                lines.append(
                    f"  Pull #{s.segment_id} [{s.pull_kind.value}] ({gear_str}, {s.duration_s:.1f}s, {s.start_rpm:.0f} -> {s.end_rpm:.0f} RPM):"
                )
                lines.append(f"    - Boost: Target {s.max_specified_boost_mbar:.0f} mbar | Actual {s.max_actual_boost_mbar:.0f} mbar | Pointwise Overshoot: {overshoot_str}")
                lines.append(f"    - Spool Time: {spool_str} | N75 Range: {n75_str}")
                if s.active_bottleneck != LimiterBottleneck.UNKNOWN:
                    lines.append(f"    - Active Bottleneck: {bottleneck_str}")
        if self.parse_warnings:
            lines.append("\nParse Warnings:")
            for w in self.parse_warnings:
                lines.append(f"  [WARN] {w}")
        if self.diagnostic_findings:
            lines.append("\nDiagnostic Findings:")
            for f in self.diagnostic_findings:
                lines.append(f"  [!] {f}")
        return "\n".join(lines)


# Assumed factory gear ratios for Golf 5 1.9 TDI BLS (5-speed manual 0A4 / GQQ / JCR)
# Provenance: ASSUMED from workshop manual specs, subject to tire diameter variation.
KNOWN_GEAR_RATIOS = {
    3: 0.0250,
    4: 0.0351,
    5: 0.0450,
}


def estimate_gear(kmh_per_rpm: float, tolerance: float = 0.08) -> Optional[int]:
    """Estimate gear number from speed-to-rpm ratio."""
    for gear, ratio in KNOWN_GEAR_RATIOS.items():
        if abs(kmh_per_rpm - ratio) / ratio <= tolerance:
            return gear
    return None


def _parse_optional_float(val: Any) -> Optional[float]:
    """Safely parse float preserving valid 0.0, returning None only for empty/missing/NaN data."""
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() in ("nan", "none", "n/a", "null", ""):
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


class LogAnalyzer:
    """
    Production Telemetry and Log Analyzer v2 (Hardened) capable of parsing, resynthesizing,
    segmenting, and extracting actionable calibration diagnostics from vehicle logs.
    """

    def __init__(self, max_interpolation_gap_s: float = 2.5):
        self.max_interpolation_gap_s = max_interpolation_gap_s

    def detect_format(self, path_or_content: Union[Path, str]) -> Tuple[LogFormat, str]:
        """Detect the specific log format from file contents."""
        p = Path(path_or_content)
        if not p.exists():
            raise FileNotFoundError(f"Log file {p} not found")

        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                header = f.readline()
                second_line = f.readline()
        except Exception as exc:
            raise ValueError(f"Could not read log file {p}: {exc}")

        # 1. Check for standard VCDS WOT export
        if "Boost_Specified_mbar" in header or "Driver_Wish_IQ_mg" in header:
            return LogFormat.VCDS_WOT_CSV, "utf-8"

        # 2. Check for VCDS multi-group measuring blocks
        if "VCDS" in header or "Group A:" in header or "Group A:" in second_line or "011" in header:
            return LogFormat.VCDS_ADVANCED_GROUP, "cp1251"

        # 3. Check for Android Turbo_Pair
        if "pair_seq" in header and "map_mbar_abs" in header:
            return LogFormat.ANDROID_TURBO_PAIR, "utf-8"

        # 4. Check for Android Event_RAW
        if "pid" in header and "timestamp_utc_ms" in header:
            return LogFormat.ANDROID_EVENT_RAW, "utf-8"

        return LogFormat.UNKNOWN, "utf-8"

    def parse_log(self, file_path: Union[Path, str]) -> Tuple[List[TelemetryPoint], LogFormat, Dict[str, Any]]:
        """Parse log file into a normalized list of TelemetryPoints."""
        p = Path(file_path)
        log_format, encoding = self.detect_format(p)
        meta: Dict[str, Any] = {"file": str(p), "format": log_format.value}
        parse_warnings: List[str] = []

        if log_format == LogFormat.VCDS_WOT_CSV:
            points = self._parse_vcds_wot(p, encoding)
        elif log_format == LogFormat.VCDS_ADVANCED_GROUP:
            points, sessions_meta, parse_warnings = self._parse_vcds_advanced(p, encoding)
            meta["sessions"] = sessions_meta
        elif log_format == LogFormat.ANDROID_TURBO_PAIR:
            points = self._parse_android_turbo_pair(p, encoding)
        elif log_format == LogFormat.ANDROID_EVENT_RAW:
            points = self._parse_android_event_raw(p, encoding)
        else:
            raise ValueError(f"Unsupported or unknown log format for {p.name}")

        meta["parse_warnings"] = parse_warnings
        return points, log_format, meta

    def _parse_vcds_wot(self, path: Path, encoding: str) -> List[TelemetryPoint]:
        """Parse standard VCDS WOT export CSV."""
        points: List[TelemetryPoint] = []
        with open(path, "r", encoding=encoding, errors="replace") as f:
            reader = csv.DictReader(f)
            t0 = None
            for row in reader:
                rel_t = _parse_optional_float(row.get("RelativeTime_s")) or 0.0
                rpm = _parse_optional_float(row.get("RPM"))
                spec_p = _parse_optional_float(row.get("Boost_Specified_mbar"))
                act_p = _parse_optional_float(row.get("Boost_Actual_mbar"))
                n75 = _parse_optional_float(row.get("N75_Duty_pct"))
                dw = _parse_optional_float(row.get("Driver_Wish_IQ_mg"))
                tl = _parse_optional_float(row.get("Torque_Limit_IQ_mg"))
                sl = _parse_optional_float(row.get("Smoke_Limit_IQ_mg"))
                maf = _parse_optional_float(row.get("MAF_Actual_mg"))
                # C6: Whitelist of explicit accelerator pedal channels; Throttle_pct is NOT pedal
                pedal = _parse_optional_float(
                    row.get("Pedal_pct")
                    or row.get("Accelerator_Pedal_pct")
                    or row.get("AccPed_rAPP")
                    or row.get("Accel_Pedal_pct")
                )
                throttle = _parse_optional_float(row.get("Throttle_pct"))

                if t0 is None:
                    t0 = rel_t

                points.append(
                    TelemetryPoint(
                        time_s=rel_t - t0,
                        session_id=0,
                        rpm=rpm,
                        boost_spec_mbar=spec_p if (spec_p is not None and spec_p > 0) else None,
                        boost_act_mbar=act_p if (act_p is not None and act_p > 0) else None,
                        n75_duty_pct=n75,
                        driver_wish_iq_mg=dw,
                        torque_limit_iq_mg=tl,
                        smoke_limit_iq_mg=sl,
                        maf_act_mg=maf,
                        maf_derived_mg=None,
                        maf_is_derived=False,
                        pedal_pct=pedal,
                        throttle_pct=throttle,
                    )
                )
        return points

    def _parse_vcds_advanced(
        self, path: Path, encoding: str
    ) -> Tuple[List[TelemetryPoint], List[Dict[str, Any]], List[str]]:
        """
        Parse VCDS Advanced Measuring Blocks (011, 003, 008).
        Extracts independent timestamps per group and resamples onto a unified canonical timeline
        without edge extrapolation and masking gaps larger than max_interpolation_gap_s.
        """
        text = path.read_text(encoding=encoding, errors="replace")
        text = re.sub(r'([^\r\n])(,[^\r\n]*VCDS)', r'\1\n\2', text)

        raw_sessions: List[List[str]] = []
        current_lines: List[str] = []
        for line in text.splitlines():
            if "VCDS" in line:
                if current_lines:
                    raw_sessions.append(current_lines)
                    current_lines = []
            current_lines.append(line)
        if current_lines:
            raw_sessions.append(current_lines)

        vcds_channels = {
            "011": ("rpm", "boost_spec_mbar", "boost_act_mbar", "n75_duty_pct"),
            "003": ("rpm", "maf_spec_mg", "maf_act_mg", "egr_duty_pct"),
            "008": ("rpm", "trq_request_nm", "trq_limit_nm", "trq_smoke_nm"),
        }

        sessions_meta: List[Dict[str, Any]] = []
        parse_warnings: List[str] = []
        all_points: List[TelemetryPoint] = []
        time_offset = 0.0

        for s_idx, slines in enumerate(raw_sessions):
            # Parse metadata for EVERY session
            for l in slines:
                if "VCDS" in l:
                    m = re.search(r",(\d{1,2}),[^,]*,(\d{4}),(\d\d:\d\d:\d\d)", l)
                    if m:
                        sessions_meta.append({
                            "session_idx": s_idx,
                            "day": m.group(1),
                            "year": m.group(2),
                            "time": m.group(3),
                        })
                    break

            groups: List[str] = []
            group_data: Dict[int, List[Tuple[float, List[float]]]] = {0: [], 1: [], 2: []}

            for l in slines:
                if "A:" in l:
                    parts = l.split(",")
                    groups = [p.replace("'", "").strip() for p in parts if "'" in p]
                elif l.startswith(","):
                    parts = l.split(",")
                    if len(parts) >= 16:
                        try:
                            for gi in range(min(3, len(groups))):
                                base = gi * 5 + 1
                                t = float(parts[base])
                                vals = [float(x) for x in parts[base + 1 : base + 5]]
                                group_data[gi].append((t, vals))
                        except ValueError:
                            pass

            all_times = set()
            for gi in range(len(groups)):
                all_times.update(t for t, _ in group_data[gi])

            if not all_times:
                continue

            t_grid = np.array(sorted(all_times))
            t0 = t_grid[0]
            t_rel = t_grid - t0

            synced_channels: Dict[str, np.ndarray] = {}

            for gi, g_name in enumerate(groups[:3]):
                pts = group_data[gi]
                if not pts:
                    continue
                if g_name not in vcds_channels:
                    parse_warnings.append(
                        f"Unrecognized VCDS measuring block group '{g_name}' in session {s_idx} - skipped known channel mapping"
                    )
                    continue

                g_times = np.array([p[0] - t0 for p in pts])
                g_vals = np.array([p[1] for p in pts])  # shape (N, 4)

                ch_names = vcds_channels[g_name]
                for ci, ch in enumerate(ch_names):
                    interp_vals = interpolate_channel(
                        t_rel, g_times, g_vals[:, ci], max_gap_s=self.max_interpolation_gap_s
                    )
                    if ch not in synced_channels or (ch == "rpm" and g_name == "011"):
                        synced_channels[ch] = interp_vals

            # Create TelemetryPoints
            N = len(t_rel)
            for i in range(N):
                pt_time = time_offset + float(t_rel[i])
                
                def _get_val(ch: str) -> Optional[float]:
                    if ch in synced_channels:
                        v = synced_channels[ch][i]
                        return None if np.isnan(v) else float(v)
                    return None

                all_points.append(
                    TelemetryPoint(
                        time_s=pt_time,
                        session_id=s_idx,
                        rpm=_get_val("rpm"),
                        boost_spec_mbar=_get_val("boost_spec_mbar"),
                        boost_act_mbar=_get_val("boost_act_mbar"),
                        n75_duty_pct=_get_val("n75_duty_pct"),
                        maf_spec_mg=_get_val("maf_spec_mg"),
                        maf_act_mg=_get_val("maf_act_mg"),
                        maf_derived_mg=None,
                        maf_is_derived=False,
                        trq_request_nm=_get_val("trq_request_nm"),
                        trq_limit_nm=_get_val("trq_limit_nm"),
                        trq_smoke_nm=_get_val("trq_smoke_nm"),
                    )
                )

            time_offset += float(t_rel[-1]) + 10.0

        return all_points, sessions_meta, parse_warnings

    def _parse_android_turbo_pair(self, path: Path, encoding: str) -> List[TelemetryPoint]:
        """Parse Android Turbo_Pair CSV capture."""
        points: List[TelemetryPoint] = []
        with open(path, "r", encoding=encoding, errors="replace") as f:
            reader = csv.DictReader(f)
            t0 = None
            for row in reader:
                try:
                    ts_ms = int(row["timestamp_utc_ms"])
                    rpm = _parse_optional_float(row.get("rpm")) or 0.0
                    map_mbar = _parse_optional_float(row.get("map_mbar_abs")) or 0.0
                    speed = _parse_optional_float(row.get("speed_kmh")) or 0.0
                    maf_gs = _parse_optional_float(row.get("maf_g_s")) or 0.0
                    load = _parse_optional_float(row.get("load_pct")) or 0.0
                    pedal = _parse_optional_float(row.get("pedal_pct") or row.get("accel_pedal_pct"))
                    throttle = _parse_optional_float(row.get("throttle_pct"))
                except (ValueError, KeyError):
                    continue

                if t0 is None:
                    t0 = ts_ms

                maf_derived = None
                if maf_gs > 0 and rpm > 500:
                    maf_derived = (maf_gs * 1000.0) / (rpm / 60.0 * 2.0)

                points.append(
                    TelemetryPoint(
                        time_s=(ts_ms - t0) / 1000.0,
                        session_id=0,
                        rpm=rpm,
                        speed_kmh=speed if speed > 0 else None,
                        boost_act_mbar=map_mbar,
                        maf_act_mg=None,
                        maf_derived_mg=maf_derived,
                        maf_is_derived=True if maf_derived is not None else False,
                        pedal_pct=pedal,
                        throttle_pct=throttle,
                        load_pct=load if load > 0 else None,
                    )
                )
        return points

    def _parse_android_event_raw(self, path: Path, encoding: str) -> List[TelemetryPoint]:
        """
        Parse Android Event_RAW asynchronous OBD PID events.
        Merges asynchronous PIDs into synchronized TelemetryPoints along a canonical timeline
        without edge extrapolation and masking stale gaps.
        """
        pid_map = {
            "010C": "rpm",
            "010B": "boost_act_mbar",
            "0110": "maf_g_s",
            "010D": "speed_kmh",
            "0104": "load_pct",
            "0149": "pedal_pct",
            "015A": "pedal_pct",
            "0111": "throttle_pct",
        }
        channel_data: Dict[str, List[Tuple[float, float]]] = {ch: [] for ch in pid_map.values()}

        with open(path, "r", encoding=encoding, errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pid = row.get("pid")
                if pid in pid_map and row.get("status") == "VALID":
                    try:
                        ts = int(row["timestamp_utc_ms"])
                        val = float(row["value"])
                        if pid == "010B":
                            unit = row.get("unit") or ""
                            if "kPa" in unit or val < 500.0:
                                val *= 10.0  # kPa -> mbar
                        channel_data[pid_map[pid]].append((ts, val))
                    except (ValueError, KeyError):
                        continue

        if not channel_data["rpm"] and not channel_data["boost_act_mbar"]:
            return []

        grid_timestamps = sorted(
            set(ts for ts, _ in channel_data["rpm"]) | set(ts for ts, _ in channel_data["boost_act_mbar"])
        )
        if not grid_timestamps:
            return []

        t0_ms = grid_timestamps[0]
        t_rel_s = np.array([(ts - t0_ms) / 1000.0 for ts in grid_timestamps])

        synced: Dict[str, np.ndarray] = {}
        for ch, pts in channel_data.items():
            if not pts:
                continue
            pts.sort(key=lambda x: x[0])
            ch_times_s = np.array([(ts - t0_ms) / 1000.0 for ts, _ in pts])
            ch_vals = np.array([v for _, v in pts])
            synced[ch] = interpolate_channel(
                t_rel_s, ch_times_s, ch_vals, max_gap_s=self.max_interpolation_gap_s
            )

        points: List[TelemetryPoint] = []
        for i in range(len(t_rel_s)):
            t = float(t_rel_s[i])

            def _get_ch(name: str) -> Optional[float]:
                if name in synced:
                    v = synced[name][i]
                    return None if np.isnan(v) else float(v)
                return None

            rpm_val = _get_ch("rpm")
            map_val = _get_ch("boost_act_mbar")
            spd_val = _get_ch("speed_kmh")
            load_val = _get_ch("load_pct")
            pedal_val = _get_ch("pedal_pct")
            throttle_val = _get_ch("throttle_pct")
            maf_gs_val = _get_ch("maf_g_s")

            maf_derived = None
            if maf_gs_val is not None and rpm_val is not None and rpm_val > 500:
                maf_derived = (maf_gs_val * 1000.0) / (rpm_val / 60.0 * 2.0)

            points.append(
                TelemetryPoint(
                    time_s=t,
                    session_id=0,
                    rpm=rpm_val,
                    speed_kmh=spd_val if (spd_val is not None and spd_val > 0) else None,
                    boost_act_mbar=map_val,
                    maf_act_mg=None,
                    maf_derived_mg=maf_derived,
                    maf_is_derived=True if maf_derived is not None else False,
                    pedal_pct=pedal_val,
                    throttle_pct=throttle_val,
                    load_pct=load_val if (load_val is not None and load_val > 0) else None,
                )
            )

        return points

    def segment_wot_pulls(
        self,
        points: List[TelemetryPoint],
        min_duration_s: float = 1.5,
        min_rpm_rise: float = 400.0,
        max_rpm_drop: float = 80.0,
        max_time_gap_s: float = 2.5,
    ) -> List[List[TelemetryPoint]]:
        """
        Segment contiguous acceleration runs under engine demand.
        Filters by rising RPM and minimum pull duration.
        Enforces maximum time gap (max_time_gap_s) and prevents segmentation across sessions.
        """
        rpm_points = [p for p in points if p.rpm is not None and p.rpm > 600]
        if len(rpm_points) < 5:
            return []

        segments: List[List[TelemetryPoint]] = []
        current_seg: List[TelemetryPoint] = []

        for p in rpm_points:
            is_heavy_demand = (
                (p.boost_act_mbar is not None and p.boost_act_mbar >= 1400.0)
                or (p.boost_spec_mbar is not None and p.boost_spec_mbar >= 1600.0)
                or (p.driver_wish_iq_mg is not None and p.driver_wish_iq_mg >= 35.0)
                or (p.trq_request_nm is not None and p.trq_request_nm >= 250.0)
                or (p.load_pct is not None and p.load_pct >= 85.0)
            )

            if current_seg:
                last_p = current_seg[-1]
                time_gap = p.time_s - last_p.time_s
                rpm_dropped = (p.rpm or 0.0) < ((last_p.rpm or 0.0) - max_rpm_drop)
                session_changed = (p.session_id != last_p.session_id)
                time_gap_exceeded = (time_gap > max_time_gap_s or time_gap < 0.0)

                if rpm_dropped or not is_heavy_demand or session_changed or time_gap_exceeded:
                    if len(current_seg) >= 5:
                        segments.append(current_seg)
                    current_seg = []

            if is_heavy_demand:
                current_seg.append(p)

        if len(current_seg) >= 5:
            segments.append(current_seg)

        valid_segments: List[List[TelemetryPoint]] = []
        for seg in segments:
            dur = seg[-1].time_s - seg[0].time_s
            rpm_rise = (seg[-1].rpm or 0.0) - (seg[0].rpm or 0.0)
            if dur >= min_duration_s and rpm_rise >= min_rpm_rise:
                valid_segments.append(seg)

        return valid_segments

    def classify_pull_kind(self, segment: List[TelemetryPoint]) -> PullKind:
        """
        Classify acceleration pull as WOT_CONFIRMED, WOT_LIKELY, or HIGH_LOAD_PULL.
        Requires persistence across >= 70% of segment samples (rejects transient spikes).
        """
        if not segment:
            return PullKind.HIGH_LOAD_PULL

        # 1. Direct pedal sensor verification (WOT_CONFIRMED)
        pedal_vals = [p.pedal_pct for p in segment if p.pedal_pct is not None]
        if pedal_vals and len(pedal_vals) >= 5:
            full_pedal_count = sum(1 for ped in pedal_vals if ped >= 95.0)
            if (full_pedal_count / len(pedal_vals)) >= 0.70:
                return PullKind.WOT_CONFIRMED

        # 2. Driver demand persistence (WOT_LIKELY)
        req_trq = [p.trq_request_nm for p in segment if p.trq_request_nm is not None]
        if req_trq and len(req_trq) >= 5:
            high_trq_count = sum(1 for r in req_trq if r >= 330.0)
            if (high_trq_count / len(req_trq)) >= 0.70:
                return PullKind.WOT_LIKELY

        dw_iq = [p.driver_wish_iq_mg for p in segment if p.driver_wish_iq_mg is not None]
        if dw_iq and len(dw_iq) >= 5:
            high_dw_count = sum(1 for dw in dw_iq if dw >= 55.0)
            if (high_dw_count / len(dw_iq)) >= 0.70:
                return PullKind.WOT_LIKELY

        return PullKind.HIGH_LOAD_PULL

    def evaluate_segment_metrics(
        self,
        segment: List[TelemetryPoint],
        segment_id: int,
    ) -> WOTSegmentMetrics:
        """Compute exhaustive boost, fuel, N75, and spool metrics for a single segment."""
        t_start = segment[0].time_s
        t_end = segment[-1].time_s
        dur = t_end - t_start
        rpm_start = segment[0].rpm or 0.0
        rpm_end = segment[-1].rpm or 0.0
        rpm_delta = rpm_end - rpm_start

        pull_kind = self.classify_pull_kind(segment)

        # 1. Gear Estimation from speed / rpm pairs
        speed_rpm_ratios: List[float] = []
        for p in segment:
            if p.speed_kmh is not None and p.rpm is not None and p.speed_kmh > 15.0 and p.rpm > 1000:
                speed_rpm_ratios.append(p.speed_kmh / p.rpm)

        est_gear = None
        med_ratio = None
        if speed_rpm_ratios:
            med_ratio = float(statistics.median(speed_rpm_ratios))
            est_gear = estimate_gear(med_ratio)

        # 2. Boost Metrics
        spec_boosts = [p.boost_spec_mbar for p in segment if p.boost_spec_mbar is not None]
        act_boosts = [p.boost_act_mbar for p in segment if p.boost_act_mbar is not None]

        max_spec = max(spec_boosts) if spec_boosts else 0.0
        max_act = max(act_boosts) if act_boosts else 0.0

        # Pointwise Overshoot & Target Trajectory Spool
        # Filter to active boost demand points to avoid throttle lift-off bleed-down false positives
        active_demand_pts = [
            p for p in segment
            if (p.boost_spec_mbar is not None and p.boost_spec_mbar >= 1600.0)
            or (p.boost_spec_mbar is None and p.boost_act_mbar is not None and p.boost_act_mbar >= 1400.0)
        ]
        if not active_demand_pts:
            active_demand_pts = segment

        overshoot_mbar = 0.0
        overshoot_pct = 0.0
        max_delta = 0.0
        min_delta = 0.0

        pts_with_both = [p for p in active_demand_pts if p.boost_act_mbar is not None and p.boost_spec_mbar is not None]
        if pts_with_both:
            deltas = [p.boost_act_mbar - p.boost_spec_mbar for p in pts_with_both]
            max_delta = float(max(deltas))
            min_delta = float(min(deltas))
            if max_delta > 0.0:
                overshoot_mbar = max_delta
                peak_idx = deltas.index(max_delta)
                spec_at_peak = pts_with_both[peak_idx].boost_spec_mbar or max_spec
                overshoot_pct = (overshoot_mbar / spec_at_peak * 100.0) if spec_at_peak > 0 else 0.0

        # Spool Time: evaluated relative to target trajectory
        spool_time_s = None
        spool_rate = None
        target_plateau = max_spec if max_spec > 0 else max_act

        for p in segment:
            act = p.boost_act_mbar or 0.0
            spec = p.boost_spec_mbar
            if spec is not None and spec >= 0.80 * target_plateau:
                if act >= 0.90 * spec:
                    spool_time_s = p.time_s - t_start
                    break
            elif spec is None and act >= 0.90 * target_plateau:
                spool_time_s = p.time_s - t_start
                break

        if spool_time_s is not None and spool_time_s > 0.05:
            first_act = segment[0].boost_act_mbar
            if first_act is not None:
                peak_act_spool = first_act
                for p in segment:
                    if p.time_s - t_start >= spool_time_s:
                        if p.boost_act_mbar is not None:
                            peak_act_spool = p.boost_act_mbar
                        break
                spool_rate = (peak_act_spool - first_act) / spool_time_s
            else:
                spool_rate = None

        # Steady-State Settling & Error: after spool completed during active demand
        steady_state_errors: List[float] = []
        if spool_time_s is not None:
            for p in active_demand_pts:
                if (p.time_s - t_start) >= spool_time_s:
                    if p.boost_act_mbar is not None and p.boost_spec_mbar is not None:
                        steady_state_errors.append(p.boost_act_mbar - p.boost_spec_mbar)

        steady_mean = float(np.mean(steady_state_errors)) if steady_state_errors else None
        steady_std = float(np.std(steady_state_errors)) if steady_state_errors else None

        # 3. N75 Duty Cycle Dynamics (evaluated against provenance-backed control margins)
        n75_vals = [p.n75_duty_pct for p in segment if p.n75_duty_pct is not None]
        n75_min = min(n75_vals) if n75_vals else None
        n75_max = max(n75_vals) if n75_vals else None
        n75_mean = float(np.mean(n75_vals)) if n75_vals else None
        n75_sat_low = (n75_min is not None and n75_min <= N75_MIN_CONTROL_BOUND_PCT)
        n75_sat_high = (n75_max is not None and n75_max >= N75_MAX_CONTROL_BOUND_PCT)

        # 4. Airflow (MAF)
        maf_vals = [p.maf_act_mg for p in segment if p.maf_act_mg is not None]
        if not maf_vals:
            maf_vals = [p.maf_derived_mg for p in segment if p.maf_derived_mg is not None]
        max_maf = max(maf_vals) if maf_vals else None
        mean_maf = float(np.mean(maf_vals)) if maf_vals else None
        maf_derived_flag = any(p.maf_is_derived for p in segment)

        # 5. Pointwise Limiter Bottleneck Detection (directly over synchronous TelemetryPoints)
        trq_pts = [
            p for p in segment
            if p.trq_request_nm is not None and p.trq_limit_nm is not None and p.trq_smoke_nm is not None
        ]
        iq_pts = [
            p for p in segment
            if p.driver_wish_iq_mg is not None and p.torque_limit_iq_mg is not None and p.smoke_limit_iq_mg is not None
        ]

        limiter_metrics = LimiterMetrics()
        bottleneck = LimiterBottleneck.UNKNOWN
        max_dw = None
        max_tl = None
        max_sl = None

        if trq_pts:
            dw_vals = [p.trq_request_nm for p in trq_pts if p.trq_request_nm is not None]
            tl_vals = [p.trq_limit_nm for p in trq_pts if p.trq_limit_nm is not None]
            sl_vals = [p.trq_smoke_nm for p in trq_pts if p.trq_smoke_nm is not None]
            max_dw = max(dw_vals) if dw_vals else None
            max_tl = max(tl_vals) if tl_vals else None
            max_sl = max(sl_vals) if sl_vals else None

            all_zeros = (max_dw == 0.0 and max_tl == 0.0 and max_sl == 0.0)
            is_flatline = (
                all_zeros
                or (len(dw_vals) > 1 and max(dw_vals) == min(dw_vals) and max(tl_vals) == min(tl_vals) and max(sl_vals) == min(sl_vals) and max_dw == max_tl == max_sl)
            )

            if all_zeros or is_flatline:
                bottleneck = LimiterBottleneck.UNKNOWN
                limiter_metrics = LimiterMetrics(
                    dominant_bottleneck=LimiterBottleneck.UNKNOWN,
                    channel_flatlined=True,
                    max_driver_wish=max_dw,
                    max_torque_limit=max_tl,
                    max_smoke_limit=max_sl,
                )
            else:
                smoke_cnt = 0
                torque_cnt = 0
                driver_cnt = 0
                tied_cnt = 0
                tol = 0.5  # Nm

                for p in trq_pts:
                    d = p.trq_request_nm
                    t = p.trq_limit_nm
                    s = p.trq_smoke_nm
                    m = min(d, t, s)
                    is_s = abs(s - m) <= tol
                    is_t = abs(t - m) <= tol
                    is_d = abs(d - m) <= tol
                    if is_s and is_t:
                        tied_cnt += 1
                        smoke_cnt += 1
                        torque_cnt += 1
                    elif is_s:
                        smoke_cnt += 1
                    elif is_t:
                        torque_cnt += 1
                    elif is_d:
                        driver_cnt += 1

                total_pts = len(trq_pts)
                s_pct = (smoke_cnt / total_pts) * 100.0
                t_pct = (torque_cnt / total_pts) * 100.0
                d_pct = (driver_cnt / total_pts) * 100.0
                tied_pct = (tied_cnt / total_pts) * 100.0

                if tied_pct >= 50.0 or (abs(s_pct - t_pct) <= 1.0 and s_pct > 0 and t_pct > 0 and s_pct >= d_pct):
                    bottleneck = LimiterBottleneck.TIED
                elif s_pct >= t_pct and s_pct >= d_pct:
                    bottleneck = LimiterBottleneck.SMOKE_LIMITER
                elif t_pct >= s_pct and t_pct >= d_pct:
                    bottleneck = LimiterBottleneck.TORQUE_LIMITER
                else:
                    bottleneck = LimiterBottleneck.DRIVER_WISH

                limiter_metrics = LimiterMetrics(
                    dominant_bottleneck=bottleneck,
                    smoke_limiter_pct=round(s_pct, 1),
                    torque_limiter_pct=round(t_pct, 1),
                    driver_wish_pct=round(d_pct, 1),
                    tied_pct=round(tied_pct, 1),
                    channel_flatlined=False,
                    max_driver_wish=max_dw,
                    max_torque_limit=max_tl,
                    max_smoke_limit=max_sl,
                )

        elif iq_pts:
            dw_vals = [p.driver_wish_iq_mg for p in iq_pts if p.driver_wish_iq_mg is not None]
            tl_vals = [p.torque_limit_iq_mg for p in iq_pts if p.torque_limit_iq_mg is not None]
            sl_vals = [p.smoke_limit_iq_mg for p in iq_pts if p.smoke_limit_iq_mg is not None]
            max_dw = max(dw_vals) if dw_vals else None
            max_tl = max(tl_vals) if tl_vals else None
            max_sl = max(sl_vals) if sl_vals else None

            all_zeros = (max_dw == 0.0 and max_tl == 0.0 and max_sl == 0.0)
            is_flatline = (
                all_zeros
                or (len(dw_vals) > 1 and max(dw_vals) == min(dw_vals) and max(tl_vals) == min(tl_vals) and max(sl_vals) == min(sl_vals) and max_dw == max_tl == max_sl)
            )

            if all_zeros or is_flatline:
                bottleneck = LimiterBottleneck.UNKNOWN
                limiter_metrics = LimiterMetrics(
                    dominant_bottleneck=LimiterBottleneck.UNKNOWN,
                    channel_flatlined=True,
                    max_driver_wish=max_dw,
                    max_torque_limit=max_tl,
                    max_smoke_limit=max_sl,
                )
            else:
                smoke_cnt = 0
                torque_cnt = 0
                driver_cnt = 0
                tied_cnt = 0
                tol = 0.2  # mg/stroke

                for p in iq_pts:
                    d = p.driver_wish_iq_mg
                    t = p.torque_limit_iq_mg
                    s = p.smoke_limit_iq_mg
                    m = min(d, t, s)
                    is_s = abs(s - m) <= tol
                    is_t = abs(t - m) <= tol
                    is_d = abs(d - m) <= tol
                    if is_s and is_t:
                        tied_cnt += 1
                        smoke_cnt += 1
                        torque_cnt += 1
                    elif is_s:
                        smoke_cnt += 1
                    elif is_t:
                        torque_cnt += 1
                    elif is_d:
                        driver_cnt += 1

                total_pts = len(iq_pts)
                s_pct = (smoke_cnt / total_pts) * 100.0
                t_pct = (torque_cnt / total_pts) * 100.0
                d_pct = (driver_cnt / total_pts) * 100.0
                tied_pct = (tied_cnt / total_pts) * 100.0

                if tied_pct >= 50.0 or (abs(s_pct - t_pct) <= 1.0 and s_pct > 0 and t_pct > 0 and s_pct >= d_pct):
                    bottleneck = LimiterBottleneck.TIED
                elif s_pct >= t_pct and s_pct >= d_pct:
                    bottleneck = LimiterBottleneck.SMOKE_LIMITER
                elif t_pct >= s_pct and t_pct >= d_pct:
                    bottleneck = LimiterBottleneck.TORQUE_LIMITER
                else:
                    bottleneck = LimiterBottleneck.DRIVER_WISH

                limiter_metrics = LimiterMetrics(
                    dominant_bottleneck=bottleneck,
                    smoke_limiter_pct=round(s_pct, 1),
                    torque_limiter_pct=round(t_pct, 1),
                    driver_wish_pct=round(d_pct, 1),
                    tied_pct=round(tied_pct, 1),
                    channel_flatlined=False,
                    max_driver_wish=max_dw,
                    max_torque_limit=max_tl,
                    max_smoke_limit=max_sl,
                )

        return WOTSegmentMetrics(
            segment_id=segment_id,
            pull_kind=pull_kind,
            start_time_s=t_start,
            end_time_s=t_end,
            duration_s=dur,
            start_rpm=rpm_start,
            end_rpm=rpm_end,
            delta_rpm=rpm_delta,
            estimated_gear=est_gear,
            gear_provenance="ASSUMED" if est_gear is not None else None,
            kmh_per_rpm=med_ratio,
            max_specified_boost_mbar=max_spec,
            max_actual_boost_mbar=max_act,
            overshoot_mbar=overshoot_mbar,
            overshoot_pct=overshoot_pct,
            max_boost_delta_mbar=max_delta,
            min_boost_delta_mbar=min_delta,
            spool_time_s=spool_time_s,
            spool_rate_mbar_per_s=spool_rate,
            steady_state_mean_error_mbar=steady_mean,
            steady_state_std_error_mbar=steady_std,
            n75_min_duty_pct=n75_min,
            n75_max_duty_pct=n75_max,
            n75_mean_duty_pct=n75_mean,
            n75_saturated_low=n75_sat_low,
            n75_saturated_high=n75_sat_high,
            max_maf_mg=max_maf,
            mean_maf_mg=mean_maf,
            maf_is_derived=maf_derived_flag,
            limiter_metrics=limiter_metrics,
            active_bottleneck=bottleneck,
            max_driver_wish=max_dw,
            max_torque_limit=max_tl,
            max_smoke_limit=max_sl,
            samples_count=len(segment),
        )

    def analyze_file(self, file_path: Union[Path, str]) -> LogAnalysisReport:
        """Perform end-to-end normalization, segmentation, and diagnostic analysis of a log file."""
        points, log_format, meta = self.parse_log(file_path)
        if not points:
            raise ValueError(f"No valid telemetry data extracted from {Path(file_path).name}")

        rpms = [p.rpm for p in points if p.rpm is not None]
        rpm_min = min(rpms) if rpms else 0.0
        rpm_max = max(rpms) if rpms else 0.0

        boosts = [p.boost_act_mbar for p in points if p.boost_act_mbar is not None]
        max_boost = max(boosts) if boosts else 0.0

        total_dur = points[-1].time_s - points[0].time_s

        segments = self.segment_wot_pulls(points)
        segment_metrics: List[WOTSegmentMetrics] = []
        findings: List[str] = []

        for idx, seg in enumerate(segments, start=1):
            m = self.evaluate_segment_metrics(seg, segment_id=idx)
            segment_metrics.append(m)

            if m.overshoot_mbar > 200.0:
                findings.append(
                    f"Pull #{m.segment_id} [{m.pull_kind.value}]: Pointwise boost overshoot of +{m.overshoot_mbar:.0f} mbar "
                    f"({m.overshoot_pct:+.1f}%) reaching {m.max_actual_boost_mbar:.0f} mbar. "
                    f"[EVIDENCE: peak delta=+{m.overshoot_mbar:.0f} mbar at {m.max_actual_boost_mbar:.0f} mbar] [CONFIDENCE: HIGH]"
                )
            if m.n75_saturated_low:
                findings.append(
                    f"Pull #{m.segment_id}: N75 duty cycle reached candidate minimum control limit {m.n75_min_duty_pct:.1f}% "
                    f"(<= {N75_MIN_CONTROL_BOUND_PCT:.1f}%). [EVIDENCE: min N75={m.n75_min_duty_pct:.1f}%] [CONFIDENCE: HIGH] "
                    f"Observed governor output at lower saturation limit."
                )
            if m.n75_saturated_high:
                findings.append(
                    f"Pull #{m.segment_id}: N75 duty cycle reached candidate upper control limit {m.n75_max_duty_pct:.1f}% "
                    f"(>= {N75_MAX_CONTROL_BOUND_PCT:.1f}%). [EVIDENCE: max N75={m.n75_max_duty_pct:.1f}%] [CONFIDENCE: HIGH] "
                    f"Observed governor output at upper saturation limit."
                )
            if m.active_bottleneck == LimiterBottleneck.SMOKE_LIMITER:
                findings.append(
                    f"Pull #{m.segment_id}: Fuel delivery is restricted by the Smoke Limiter "
                    f"({m.limiter_metrics.smoke_limiter_pct:.0f}% of pull active, max {m.max_smoke_limit:.1f} vs Torque Limit {m.max_torque_limit:.1f}). "
                    f"[EVIDENCE: smoke={m.limiter_metrics.smoke_limiter_pct:.0f}%, torque={m.limiter_metrics.torque_limiter_pct:.0f}%] [CONFIDENCE: HIGH]"
                )
            elif m.active_bottleneck == LimiterBottleneck.TORQUE_LIMITER:
                findings.append(
                    f"Pull #{m.segment_id}: Fuel delivery is restricted by the Torque Limiter "
                    f"({m.limiter_metrics.torque_limiter_pct:.0f}% of pull active, max {m.max_torque_limit:.1f} vs Smoke Limit {m.max_smoke_limit:.1f}). "
                    f"[EVIDENCE: torque={m.limiter_metrics.torque_limiter_pct:.0f}%, smoke={m.limiter_metrics.smoke_limiter_pct:.0f}%] [CONFIDENCE: HIGH]"
                )
            elif m.active_bottleneck == LimiterBottleneck.TIED:
                findings.append(
                    f"Pull #{m.segment_id}: Fuel delivery limiters are tied within tolerance margin. "
                    f"[EVIDENCE: tied={m.limiter_metrics.tied_pct:.0f}%] [CONFIDENCE: MEDIUM]"
                )

        parse_warnings = meta.get("parse_warnings", [])

        return LogAnalysisReport(
            source_path=str(Path(file_path).resolve()),
            detected_format=log_format,
            session_label=meta.get("label") or (meta.get("sessions", [{}])[0].get("time") if meta.get("sessions") else None),
            total_samples=len(points),
            total_duration_s=total_dur,
            rpm_range=(rpm_min, rpm_max),
            max_recorded_boost_mbar=max_boost,
            wot_segments_count=len(segment_metrics),
            wot_segments=segment_metrics,
            diagnostic_findings=findings,
            parse_warnings=parse_warnings,
        )
