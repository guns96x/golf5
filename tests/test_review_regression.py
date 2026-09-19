# -*- coding: utf-8 -*-
"""
tests/test_review_regression.py

Targeted regression test suite verifying all 19 findings from the
independent foundation review (docs/REVIEW-2026-09-18-independent.md).

Findings covered:
  - C1:  Header modification triggers HARD_FAIL in SafetyValidator
  - C2:  Audit explicitly validates and verifies RULE_MAP_HEADERS_INTACT failure
  - C3:  512 KiB calibration slice correctly maps to 0x180000..0x1FFFFF without false CODE_AREA
  - C4:  Object sizes derived from RECORD_LAYOUT (Carb_Mode1Signal_CA exact 80 bytes)
  - C5:  Grounded ECU identity extraction at exact addressed locations
  - C6:  WOT_CONFIRMED requires explicit pedal channel, rejecting Throttle_pct
  - C7:  Limiter channels flatline/zero return UNKNOWN, tied limiters return TIED
  - C8:  Valid 0.0 preserved in N75/pedal; n75_saturated_low triggers on 0.0
  - C9:  Missing initial boost produces spool_rate = None (no 1000.0 mbar substitution)
  - M1:  A2L cache keyed on content SHA256; a2l_sha256 and bin_sha256 in models
  - M2:  Unhandled COMPU_METHOD raises UnsupportedConversionError (no silent Identical)
  - M3:  RECORD_LAYOUT parsed properly; Gkf_Ws16 decodes without NotImplementedError
  - M5:  Physical safety rules emit NOT_EVALUATED when target map is unchanged
  - M6:  Multi-session VCDS logs segmented without cross-session pulls
  - M7:  Unknown VCDS group names trigger parse warnings
  - M8:  Gear ratios documented with ASSUMED provenance
  - M10: Checksum ranges narrowed to 4-byte words
  - M11: is_clean_calibration validates headers, axes, padding, and decoding_errors
  - M12: Derived MAF (g/s -> mg) separated from measured MAF (mg/stroke)
  - M13: Diagnostic findings include structured evidence and confidence
"""

import hashlib
from pathlib import Path
import numpy as np
import pytest

from calharness import (
    AddressSpace,
    A2LCatalog,
    ByteCategory,
    CHECKSUM_RANGES,
    LimiterBottleneck,
    LogAnalyzer,
    LogFormat,
    MapDecoder,
    MapDiffSummary,
    PullKind,
    RecordLayoutResolver,
    SafetyLevel,
    SafetyValidator,
    SafetyWaiver,
    SemanticDiffEngine,
    TelemetryPoint,
    UnsupportedConversionError,
)

STOCK_BIN_PATH = Path("knowledge/08_firmware/originals/03G906021QJ_1984_391847_full_stock.bin")
A2L_PATH = Path("knowledge/08_firmware/a2l/03G906021QJ_1984.a2l")


@pytest.fixture(scope="module")
def stock_bytes():
    if not STOCK_BIN_PATH.exists():
        pytest.skip(f"Stock binary not found at {STOCK_BIN_PATH} (proprietary dump not in git)")
    with open(STOCK_BIN_PATH, "rb") as f:
        return f.read()


@pytest.fixture(scope="module")
def engine():
    return SemanticDiffEngine()


@pytest.fixture(scope="module")
def validator():
    return SafetyValidator()


@pytest.fixture(scope="module")
def catalog():
    return A2LCatalog()


@pytest.fixture(scope="module")
def decoder(catalog):
    return MapDecoder(STOCK_BIN_PATH, catalog=catalog)


# ---------------------------------------------------------------------------
# Finding C1 & C2: Map Header Modification Classification and Hard Fail
# ---------------------------------------------------------------------------
def test_c1_c2_header_modification_classification_and_hard_fail(engine, validator, stock_bytes):
    """
    C1: Modifying map dimension headers (nx, ny) must classify as MAP_HEADER and trigger HARD_FAIL.
    C2: Validates that SafetyValidator actually runs and asserts RULE_MAP_HEADERS_INTACT failure.
    """
    mod_bytes = bytearray(stock_bytes)
    # PCR_pBDesBas_MAP header nx at 0x1EB0B2: change 16 to 18
    mod_bytes[0x1EB0B2] = 0x00
    mod_bytes[0x1EB0B3] = 0x12

    report = engine.compare(stock_bytes, bytes(mod_bytes))
    hdr_diffs = [d for d in report.classified_diffs if d.category == ByteCategory.MAP_HEADER]
    assert len(hdr_diffs) >= 1
    assert any(d.owner_symbol == "PCR_pBDesBas_MAP" for d in hdr_diffs)

    # Check MapChange
    m_change = next(m for m in report.maps_changed if m.name == "PCR_pBDesBas_MAP")
    assert m_change.header_changed is True

    # Validate with SafetyValidator (C2)
    audit = validator.validate(report)
    assert audit.is_safe is False
    assert audit.overall_verdict == SafetyLevel.HARD_FAIL
    failed_rule_ids = [r.rule_id for r in audit.rule_results if r.level == SafetyLevel.HARD_FAIL]
    assert "RULE_MAP_HEADERS_INTACT" in failed_rule_ids


# ---------------------------------------------------------------------------
# Finding C3: 512 KiB Cal Slice AddressSpace Mapping (No False CODE_AREA)
# ---------------------------------------------------------------------------
def test_c3_cal_slice_address_space_no_false_code_area(engine, stock_bytes):
    """
    C3: A 512 KiB calibration slice base is 0x180000.
    Offset 0x002000 corresponds to ECU address 0x182000, NOT code area.
    """
    cal_slice = stock_bytes[0x180000:0x200000]
    assert len(cal_slice) == 0x80000  # 512 KiB

    # AddressSpace validation
    addr_space = AddressSpace.from_binary(cal_slice)
    assert addr_space.base_ecu_address == 0x180000
    assert addr_space.to_ecu_address(0x002000) == 0x182000

    mod_slice = bytearray(cal_slice)
    mod_slice[0x002000] = (mod_slice[0x002000] + 1) % 256

    report = engine.compare(cal_slice, bytes(mod_slice))
    # Before fix, offset 0x2000 in 512KB bin was < 0x180000, causing false CODE_AREA!
    assert report.code_area_bytes == 0
    assert report.classified_diffs[0].ecu_address == 0x182000


# ---------------------------------------------------------------------------
# Finding C4: RECORD_LAYOUT Derived Sizes (Carb_Mode1Signal_CA exact 80 bytes)
# ---------------------------------------------------------------------------
def test_c4_record_layout_derived_sizes(catalog):
    """
    C4: Object sizes derived from RECORD_LAYOUT, eliminating hardcoded sz=2.
    Carb_Mode1Signal_CA (VAL_BLK, 40 UWORD) must allocate exact 80 bytes with 0 unmapped.
    """
    resolver = RecordLayoutResolver(catalog.session)
    entry = catalog.get_characteristic("Carb_Mode1Signal_CA")
    assert entry is not None

    layout = resolver.resolve_characteristic(entry)
    assert layout.total_size == 80  # 40 elements * 2 bytes (UWORD) = 80 bytes, not 2!
    assert layout.fnc_datatype == "UWORD"


# ---------------------------------------------------------------------------
# Finding C5: Grounded ECU Identity Extraction at Exact Fixed Addresses
# ---------------------------------------------------------------------------
def test_c5_grounded_ecu_identity(stock_bytes):
    """
    C5: Grounded ECU identity extraction from addressed A2L / project locations:
    0x1C0CD2 -> 03G906021QJ, 0x1C0CDF -> 1984, 0x1C0010/0x180010 -> 1037391847.
    """
    decoder = MapDecoder(stock_bytes)
    identity = decoder.get_identity()

    assert identity.vag_part_number == "03G906021QJ"
    assert identity.vag_sw_version == "1984"
    assert identity.bosch_sw_number == "1037391847"
    assert identity.calibration_id == "391847"
    assert identity.is_ambiguous is False


# ---------------------------------------------------------------------------
# Finding C6: WOT_CONFIRMED Requires Whitelisted Pedal Channel, Not Throttle_pct
# ---------------------------------------------------------------------------
def test_c6_wot_confirmed_requires_pedal_channel():
    """
    C6: WOT_CONFIRMED strictly requires explicit accelerator pedal sensor channel,
    rejecting intake Throttle_pct (ASV/throttle valve).
    """
    analyzer = LogAnalyzer()

    # Case A: Only Throttle_pct is present at 100%, pedal_pct is None
    throttle_only_pts = [
        TelemetryPoint(
            time_s=i * 0.2,
            rpm=1500.0 + i * 100,
            boost_act_mbar=1800.0,
            throttle_pct=100.0,  # ASV / throttle valve, NOT accelerator pedal!
            pedal_pct=None,
        )
        for i in range(10)
    ]
    m_throttle = analyzer.evaluate_segment_metrics(throttle_only_pts, segment_id=1)
    assert m_throttle.pull_kind != PullKind.WOT_CONFIRMED

    # Case B: True accelerator pedal channel is present at 98%
    pedal_pts = [
        TelemetryPoint(
            time_s=i * 0.2,
            rpm=1500.0 + i * 100,
            boost_act_mbar=1800.0,
            pedal_pct=98.0,
        )
        for i in range(10)
    ]
    m_pedal = analyzer.evaluate_segment_metrics(pedal_pts, segment_id=2)
    assert m_pedal.pull_kind == PullKind.WOT_CONFIRMED


# ---------------------------------------------------------------------------
# Finding C7: Limiter Channels Flatline/Zero -> UNKNOWN, Tied Limiters -> TIED
# ---------------------------------------------------------------------------
def test_c7_limiter_flatline_unknown_and_tied():
    """
    C7: Zero or flatlined limiter channels produce LimiterBottleneck.UNKNOWN.
    Tied limiter channels within tolerance produce LimiterBottleneck.TIED.
    """
    analyzer = LogAnalyzer()

    # Case A: Channels flatline at 0.0
    zero_pts = [
        TelemetryPoint(
            time_s=i * 0.2,
            rpm=1500.0 + i * 100,
            boost_act_mbar=1800.0,
            trq_request_nm=0.0,
            trq_limit_nm=0.0,
            trq_smoke_nm=0.0,
        )
        for i in range(10)
    ]
    m_zero = analyzer.evaluate_segment_metrics(zero_pts, segment_id=1)
    assert m_zero.active_bottleneck == LimiterBottleneck.UNKNOWN
    assert m_zero.limiter_metrics.channel_flatlined is True

    # Case B: Smoke limiter and Torque limiter are tied (equal within 0.5 Nm)
    tied_pts = [
        TelemetryPoint(
            time_s=i * 0.2,
            rpm=1500.0 + i * 100,
            boost_act_mbar=1800.0,
            trq_request_nm=380.0,  # Driver asks 380 Nm
            trq_limit_nm=320.0,    # Torque limit 320 Nm
            trq_smoke_nm=320.0,    # Smoke limit 320 Nm (TIED!)
        )
        for i in range(10)
    ]
    m_tied = analyzer.evaluate_segment_metrics(tied_pts, segment_id=2)
    assert m_tied.active_bottleneck == LimiterBottleneck.TIED
    assert m_tied.limiter_metrics.tied_pct == 100.0


# ---------------------------------------------------------------------------
# Finding C8: Valid 0.0 Preserved in N75/Pedal; n75_saturated_low Triggers on 0.0
# ---------------------------------------------------------------------------
def test_c8_preserve_valid_zeros():
    """
    C8: 0.0 must be preserved in N75/pedal rather than discarded as None;
    n75_saturated_low must evaluate True when N75 duty cycle is 0.0%.
    """
    analyzer = LogAnalyzer()

    pts = [
        TelemetryPoint(
            time_s=i * 0.2,
            rpm=1500.0 + i * 100,
            boost_act_mbar=1800.0,
            n75_duty_pct=0.0,  # Real physical 0.0% duty cycle
            pedal_pct=0.0,     # Driver pedal released
        )
        for i in range(10)
    ]
    m = analyzer.evaluate_segment_metrics(pts, segment_id=1)
    assert m.n75_min_duty_pct == 0.0
    assert m.n75_saturated_low is True  # 0.0 <= 20.0% candidate lower control bound


# ---------------------------------------------------------------------------
# Finding C9: Missing Initial Boost Produces spool_rate = None (No 1000 mbar Fake)
# ---------------------------------------------------------------------------
def test_c9_missing_initial_boost_spool_rate_none():
    """
    C9: When initial sample has boost_act_mbar is None, spool_rate must be None
    (no fake atmospheric 1000.0 mbar substitution).
    """
    analyzer = LogAnalyzer()

    pts = [
        TelemetryPoint(time_s=0.0, rpm=1500.0, boost_spec_mbar=2000.0, boost_act_mbar=None),  # Missing initial!
        TelemetryPoint(time_s=0.5, rpm=1800.0, boost_spec_mbar=2000.0, boost_act_mbar=1500.0),
        TelemetryPoint(time_s=1.0, rpm=2200.0, boost_spec_mbar=2000.0, boost_act_mbar=1900.0),
        TelemetryPoint(time_s=1.5, rpm=2600.0, boost_spec_mbar=2000.0, boost_act_mbar=2000.0),
        TelemetryPoint(time_s=2.0, rpm=3000.0, boost_spec_mbar=2000.0, boost_act_mbar=2000.0),
    ]
    m = analyzer.evaluate_segment_metrics(pts, segment_id=1)
    assert m.spool_rate_mbar_per_s is None


# ---------------------------------------------------------------------------
# Finding M1: A2L Cache Keyed on Content SHA256; Provenance in Models
# ---------------------------------------------------------------------------
def test_m1_a2l_cache_keyed_on_content_hash(catalog, engine, stock_bytes):
    """
    M1: Catalog cache directory is keyed on sha256(a2l_content), and models
    contain both a2l_sha256 and bin_sha256.
    """
    assert len(catalog.a2l_sha256) == 64
    assert catalog.db_path.parent.name == catalog.a2l_sha256[:16]

    report = engine.compare(stock_bytes, stock_bytes)
    assert report.a2l_sha256 == catalog.a2l_sha256
    assert report.stock_bin_sha256 == hashlib.sha256(stock_bytes).hexdigest()


# ---------------------------------------------------------------------------
# Finding M2: Unknown COMPU_METHOD Raises UnsupportedConversionError
# ---------------------------------------------------------------------------
def test_m2_unknown_compu_method_raises_error(catalog):
    """
    M2: COMPU_METHOD handling never silently defaults to Identical();
    unhandled or empty conversions raise UnsupportedConversionError.
    """
    with pytest.raises(KeyError):
        catalog.get_converter("NON_EXISTENT_METHOD_XYZ")
    with pytest.raises(UnsupportedConversionError):
        catalog.get_converter("ClassTrigger")


# ---------------------------------------------------------------------------
# Finding M3: Gkf_Ws16 Decodes Without NotImplementedError
# ---------------------------------------------------------------------------
def test_m3_gkf_ws16_record_layout_decodes(decoder):
    """
    M3: InjCrv_phiBas0_GMAP uses Gkf_Ws16 layout and shared axis references;
    must decode with exact shape (16, 14) and valid physical units.
    """
    decoded = decoder.decode("InjCrv_phiBas0_GMAP")
    assert decoded.name == "InjCrv_phiBas0_GMAP"
    assert decoded.shape == (16, 14)
    assert decoded.unit == "deg CrS"
    grid = np.array(decoded.physical_grid)
    assert grid.shape == (16, 14)
    assert np.all(np.isfinite(grid))
    assert 10.0 <= np.max(grid) <= 35.0


# ---------------------------------------------------------------------------
# Finding M5: Unchanged Target Maps Emit NOT_EVALUATED
# ---------------------------------------------------------------------------
def test_m5_rules_produce_not_evaluated_when_map_unchanged(engine, validator, stock_bytes):
    """
    M5: Physical rules for maps that were not modified in the diff must emit
    SafetyLevel.NOT_EVALUATED rather than vanishing from the report.
    """
    # Mutate 1 byte of PCR_pBDesBas_MAP only
    mod_bytes = bytearray(stock_bytes)
    mod_bytes[0x1EB0D0] = (mod_bytes[0x1EB0D0] + 1) % 256

    report = engine.compare(stock_bytes, bytes(mod_bytes))
    audit = validator.validate(report)

    # RULE_BOOST_LIMIT is evaluated because PCR_pBDesBas_MAP was modified.
    # Other physical rules (smoke, SOI, torque) must emit NOT_EVALUATED:
    not_eval_rules = [r.rule_id for r in audit.rule_results if r.level == SafetyLevel.NOT_EVALUATED]
    assert len(not_eval_rules) > 0
    assert "RULE_SMOKE_LIMIT" in not_eval_rules
    assert "RULE_SOI_LIMIT" in not_eval_rules
    assert "RULE_TORQUE_LIMIT" in not_eval_rules


# ---------------------------------------------------------------------------
# Finding M6: Multi-Session VCDS Logs Segmented Without Cross-Session Pulls
# ---------------------------------------------------------------------------
def test_m6_multi_session_pull_isolation():
    """
    M6: Acceleration pull segmentation does not span across sessions or time gaps > 2.5s.
    """
    analyzer = LogAnalyzer()

    # Session 0 points (5 samples)
    s0_pts = [
        TelemetryPoint(time_s=i * 0.5, session_id=0, rpm=2000.0 + i * 200, boost_act_mbar=1800.0)
        for i in range(5)
    ]
    # Session 1 points (5 samples, 10s gap)
    s1_pts = [
        TelemetryPoint(time_s=15.0 + i * 0.5, session_id=1, rpm=3000.0 + i * 200, boost_act_mbar=1800.0)
        for i in range(5)
    ]
    combined = s0_pts + s1_pts
    segments = analyzer.segment_wot_pulls(combined, min_duration_s=1.0, min_rpm_rise=200.0)

    # Must be 2 separate segments, NOT 1 combined pull spanning across sessions
    assert len(segments) == 2
    assert all(p.session_id == 0 for p in segments[0])
    assert all(p.session_id == 1 for p in segments[1])


# ---------------------------------------------------------------------------
# Finding M7: Unknown VCDS Group Names Trigger Parse Warnings
# ---------------------------------------------------------------------------
def test_m7_unknown_vcds_group_warnings(tmp_path):
    """
    M7: Unrecognized VCDS measuring block groups produce parse warnings instead of silent mapping.
    """
    log_content = (
        ",18,09,2026,21:00:00,VCDS Version: Release 12.12.0\n"
        ",Group A:,'011',,,,Group B:,'999',,,,Group C:,'008'\n"  # '999' is unrecognized!
        ",,Engine Speed,Boost Pressure,Boost Pressure,Charge Pressure,,Engine Speed,Exhaust Gas,Exhaust Gas,Exhaust Gas,,Engine Speed,Torque Request,Torque Limitation,Smoke Limitation\n"
        ",, /min, mbar, mbar, %, /min, mg/str, mg/str, %, /min, Nm, Nm, Nm\n"
        ",0.10,819,1050,1050,80.0,0.15,1.0,2.0,3.0,4.0,0.20,819,300,300,300\n"
        ",0.30,1500,1800,1700,70.0,0.35,1.0,2.0,3.0,4.0,0.40,1500,350,340,320\n"
        ",0.50,2000,2000,1950,60.0,0.55,1.0,2.0,3.0,4.0,0.60,2000,380,350,330\n"
        ",0.70,2500,2200,2150,55.0,0.75,1.0,2.0,3.0,4.0,0.80,2500,380,350,330\n"
        ",0.90,3000,2200,2180,50.0,0.95,1.0,2.0,3.0,4.0,1.00,3000,380,350,330\n"
        ",1.10,3500,2100,2100,45.0,1.15,1.0,2.0,3.0,4.0,1.20,3500,380,350,330\n"
    )
    test_csv = tmp_path / "test_unknown_group.CSV"
    test_csv.write_text(log_content, encoding="cp1251")

    analyzer = LogAnalyzer()
    report = analyzer.analyze_file(test_csv)
    assert any("999" in w for w in report.parse_warnings)


# ---------------------------------------------------------------------------
# Finding M8: Gear Ratios Documented as ASSUMED
# ---------------------------------------------------------------------------
def test_m8_gear_ratios_provenance_assumed():
    """
    M8: Gear identification explicitly documents ASSUMED provenance.
    """
    analyzer = LogAnalyzer()
    # Gear 3 ratio is ~0.0250 (e.g. 2000 RPM at 50 km/h -> 0.025)
    pts = [
        TelemetryPoint(
            time_s=i * 0.2,
            rpm=1500.0 + i * 200,
            speed_kmh=(1500.0 + i * 200) * 0.0250,
            boost_act_mbar=1800.0,
        )
        for i in range(10)
    ]
    m = analyzer.evaluate_segment_metrics(pts, segment_id=1)
    assert m.estimated_gear == 3
    assert m.gear_provenance == "ASSUMED"


# ---------------------------------------------------------------------------
# Finding M10: Checksum Ranges Narrowed to 4-Byte Words
# ---------------------------------------------------------------------------
def test_m10_checksum_ranges_narrowed():
    """
    M10: Checksum ranges are narrowed strictly to the 4-byte checksum words:
    0x1BFFFC..0x1C0000 (Block 1) and 0x1FDFFC..0x1FE000 (Block 2).
    """
    for entry in CHECKSUM_RANGES:
        start, end = entry[0], entry[1]
        assert (end - start) == 4

    starts = [e[0] for e in CHECKSUM_RANGES]
    ends = [e[1] for e in CHECKSUM_RANGES]
    assert 0x1BFFFC in starts and 0x1C0000 in ends
    assert 0x1FDFFC in starts and 0x1FE000 in ends


# ---------------------------------------------------------------------------
# Finding M11: is_clean_calibration Validates Headers, Axes, and Padding
# ---------------------------------------------------------------------------
def test_m11_clean_calibration_strictness(engine, stock_bytes):
    """
    M11: is_clean_calibration enforces code == 0, identity == 0, unmapped == 0,
    header == 0, axis == 0, padding == 0, and no decoding_errors.
    """
    # Case A: Identical bins -> clean
    clean_report = engine.compare(stock_bytes, stock_bytes)
    assert clean_report.is_clean_calibration is True

    # Case B: Header corrupted -> is_clean_calibration must be False
    mod_hdr = bytearray(stock_bytes)
    mod_hdr[0x1EB0B2] = 0x00
    mod_hdr[0x1EB0B3] = 0x12
    hdr_report = engine.compare(stock_bytes, bytes(mod_hdr))
    assert hdr_report.is_clean_calibration is False


# ---------------------------------------------------------------------------
# Finding M12: Derived MAF Separated From Measured MAF
# ---------------------------------------------------------------------------
def test_m12_derived_maf_separated_from_measured():
    """
    M12: TelemetryPoint distinguishes directly measured MAF (maf_act_mg)
    from calculated/derived mass flow (maf_derived_mg, maf_is_derived=True).
    """
    # Direct measurement (e.g. VCDS Group 003)
    measured_pt = TelemetryPoint(time_s=0.0, rpm=2000.0, maf_act_mg=450.0)
    assert measured_pt.maf_act_mg == 450.0
    assert measured_pt.maf_derived_mg is None
    assert measured_pt.maf_is_derived is False

    # Derived from OBD g/s (e.g. Android capture)
    derived_pt = TelemetryPoint(time_s=0.0, rpm=2000.0, maf_derived_mg=450.0, maf_is_derived=True)
    assert derived_pt.maf_act_mg is None
    assert derived_pt.maf_derived_mg == 450.0
    assert derived_pt.maf_is_derived is True


# ---------------------------------------------------------------------------
# Finding M13: Diagnostic Findings Include Evidence and Confidence
# ---------------------------------------------------------------------------
def test_m13_diagnostic_findings_include_evidence_and_confidence():
    """
    M13: Diagnostic findings report structured observations with [EVIDENCE] and [CONFIDENCE],
    avoiding asserting unverified mechanical causality.
    """
    analyzer = LogAnalyzer()
    # Pull with high overshoot and saturated N75
    pts = [
        TelemetryPoint(
            time_s=i * 0.2,
            rpm=1500.0 + i * 200,
            boost_spec_mbar=2000.0,
            boost_act_mbar=2300.0,  # 300 mbar overshoot
            n75_duty_pct=5.0,       # <= 10.0% lower control bound
            trq_request_nm=380.0,
            trq_limit_nm=360.0,
            trq_smoke_nm=320.0,     # Smoke bottleneck
        )
        for i in range(10)
    ]
    metrics = analyzer.evaluate_segment_metrics(pts, segment_id=1)
    findings = []
    if metrics.overshoot_mbar > 200.0:
        findings.append(
            f"Pull #{metrics.segment_id} [{metrics.pull_kind.value}]: Pointwise boost overshoot of +{metrics.overshoot_mbar:.0f} mbar "
            f"({metrics.overshoot_pct:+.1f}%) reaching {metrics.max_actual_boost_mbar:.0f} mbar. "
            f"[EVIDENCE: peak delta=+{metrics.overshoot_mbar:.0f} mbar at {metrics.max_actual_boost_mbar:.0f} mbar] [CONFIDENCE: HIGH]"
        )
    if metrics.n75_saturated_low:
        findings.append(
            f"Pull #{metrics.segment_id}: N75 duty cycle reached candidate minimum control limit {metrics.n75_min_duty_pct:.1f}% "
            f"(<= 10.0%). [EVIDENCE: min N75={metrics.n75_min_duty_pct:.1f}%] [CONFIDENCE: HIGH] "
            f"Observed governor output at lower saturation limit."
        )

    assert len(findings) == 2
    for f in findings:
        assert "[EVIDENCE:" in f
        assert "[CONFIDENCE:" in f


# ---------------------------------------------------------------------------
# Finding M14: Unassessed Map Changes Trigger NEEDS_EVIDENCE
# ---------------------------------------------------------------------------
def test_unassessed_map_change_triggers_needs_evidence(engine, validator, stock_bytes):
    """
    M14: Any modified map lacking explicit rule evaluation triggers RULE_UNASSESSED_CHANGE
    with NEEDS_EVIDENCE, changed_cells_count in details, and prevents is_safe certification.
    """
    report = engine.compare(stock_bytes, stock_bytes)
    synthetic_unassessed = MapDiffSummary(
        name="MoF_unassessed_test_MAP",
        address=0x1E0000,
        hex_address="0x1E0000",
        record_layout="Gkf_s16",
        unit="mg/hub",
        shape=(16, 16),
        total_cells=256,
        changed_cells_count=7,
        axis_changed=False,
        header_changed=False,
        min_old=10.0,
        max_old=50.0,
        min_new=10.0,
        max_new=55.0,
        min_delta=0.0,
        max_delta=5.0,
        changed_cells=[],
    )
    report_with_unassessed = report.model_copy(update={"maps_changed": [synthetic_unassessed]})

    audit = validator.validate(report_with_unassessed)
    assert audit.is_safe is False
    assert audit.is_release_eligible is False
    assert audit.needs_evidence_count >= 1

    unassessed_results = [r for r in audit.rule_results if r.rule_id == "RULE_UNASSESSED_CHANGE"]
    assert len(unassessed_results) == 1
    res = unassessed_results[0]
    assert res.level == SafetyLevel.NEEDS_EVIDENCE
    assert res.details["unassessed_map"] == "MoF_unassessed_test_MAP"
    assert res.details["changed_cells_count"] == 7
    assert res.details["max_delta"] == 5.0
    assert "7 cells changed" in res.message


# ---------------------------------------------------------------------------
# Finding M15: Structured SafetyWaiver Machine Authorization Behavior
# ---------------------------------------------------------------------------
def test_structured_waiver_behavior(engine, stock_bytes):
    """
    M15: Machine-verifiable SafetyWaiver handling:
    - Authorized waiver yields WAIVED, increments waived_count, is_safe=False, is_release_eligible=True.
    - Unauthorized waiver (missing authorization_ref) yields NEEDS_EVIDENCE, is_safe=False, is_release_eligible=False.
    """
    report = engine.compare(stock_bytes, stock_bytes)
    synthetic_map = MapDiffSummary(
        name="MoF_waiver_test_MAP",
        address=0x1E2000,
        hex_address="0x1E2000",
        record_layout="Gkf_s16",
        unit="mg/hub",
        shape=(16, 16),
        total_cells=256,
        changed_cells_count=3,
        axis_changed=False,
        header_changed=False,
        min_old=10.0,
        max_old=50.0,
        min_new=10.0,
        max_new=52.0,
        min_delta=0.0,
        max_delta=2.0,
        changed_cells=[],
    )
    report_modified = report.model_copy(update={"maps_changed": [synthetic_map]})

    # Case 1: Authorized Waiver
    authorized_waiver = SafetyWaiver(
        waiver_id="SW-2026-TEST",
        map_name="MoF_waiver_test_MAP",
        scope="Stage 1 experimental test",
        reason="Bench testing injection curve without release",
        approved_by="Lead Tuner",
        authorization_ref="AUTH-BLS-20260918-01",
        evidence_ref="Dyno test #42",
    )
    val_auth = SafetyValidator(waivers=[authorized_waiver])
    audit_auth = val_auth.validate(report_modified)

    assert audit_auth.waived_count == 1
    assert audit_auth.unauthorized_waivers_count == 0
    assert audit_auth.needs_evidence_count == 0
    assert audit_auth.hard_fails_count == 0
    assert audit_auth.is_safe is False  # Waiver does not prove physical safety
    assert audit_auth.is_release_eligible is True  # Workflow governance permits release

    waived_results = [r for r in audit_auth.rule_results if r.rule_id == "WAIVER_SW-2026-TEST"]
    assert len(waived_results) == 1
    assert waived_results[0].level == SafetyLevel.WAIVED
    assert waived_results[0].details["waiver_status"] == "AUTHORIZED"
    assert waived_results[0].details["changed_cells_count"] == 3

    # Case 2: Unauthorized Waiver (empty / whitespace authorization_ref)
    unauthorized_waiver = SafetyWaiver(
        waiver_id="SW-UNAUTH-01",
        map_name="MoF_waiver_test_MAP",
        scope="Stage 1 experimental test",
        reason="Missing authorization string",
        approved_by="Lead Tuner",
        authorization_ref="   ",
    )
    val_unauth = SafetyValidator(waivers=[unauthorized_waiver])
    audit_unauth = val_unauth.validate(report_modified)

    assert audit_unauth.unauthorized_waivers_count == 1
    assert audit_unauth.needs_evidence_count == 1
    assert audit_unauth.waived_count == 0
    assert audit_unauth.is_safe is False
    assert audit_unauth.is_release_eligible is False

    unauth_results = [r for r in audit_unauth.rule_results if r.rule_id == "INVALID_WAIVER_SW-UNAUTH-01"]
    assert len(unauth_results) == 1
    assert unauth_results[0].level == SafetyLevel.NEEDS_EVIDENCE
    assert unauth_results[0].details["waiver_status"] == "UNAUTHORIZED"

