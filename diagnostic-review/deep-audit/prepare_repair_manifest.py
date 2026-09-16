"""Prepare byte-exact review manifests and a review-only candidate; no flash/ECU connection."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def make_ranges(indices):
    result = []
    for a in sorted(indices):
        if result and result[-1][1] == a:
            result[-1][1] = a + 1
        else:
            result.append([a, a + 1])
    return result


def main():
    paths = {
        'reference': ROOT / 'reference-from-hex.analysis-only.bin',
        'on': ROOT / 'new-inputs/on/03G906021QJ.Bin',
        'off': ROOT / 'new-inputs/off/03G906021QJ (DPF EGR OFF) NoCS.Bin',
    }
    blobs = {k: p.read_bytes() for k, p in paths.items()}
    report = json.loads((OUT / 'stage1-physical-audit.json').read_text())
    assert {k: digest(b) for k, b in blobs.items()} == report['hashes']
    ref, on, off = (blobs[k] for k in ('reference', 'on', 'off'))
    assert len(ref) == len(on) == len(off) == 0x200000
    assert on[:0x180000] == off[:0x180000] == b'\xff' * 0x180000
    archive = Path('C:/Users/pavlo/Downloads/VW Golf 1.9TDI-105PS-MY09-BLS-03G906021QJ-391847-original.zip')
    with zipfile.ZipFile(archive) as z:
        entries = [e for e in z.infolist() if not e.is_dir()]
        assert len(entries) == 1
        original = z.read(entries[0])
    assert digest(original) == '7dcb460f5c53a262c9975bfa450c86f313132b2a6adcdb09b3a2088d22b8ce89'
    assert original[0x180000:] == ref[0x180000:]
    stage1 = {a for a in range(0x180000, len(ref)) if ref[a] != on[a]}
    off_delta = {a for a in range(len(on)) if on[a] != off[a]}
    assert len(stage1) == 4851 and len(off_delta) == 311
    assert not stage1.intersection(off_delta)
    opaque = set()
    for lo, hi in [(0x1BFF74, 0x1C0000), (0x1FDF78, 0x1FE000)]:
        opaque.update(range(lo, hi))
    assert len(opaque) == 276 and opaque <= stage1
    calibration = stage1 - opaque
    assert len(calibration) == report['classified_bytes_including_structural_candidates'] == 4575
    temp_map = next(m for m in report['maps'] if m['name'] == 'EngPrt_facTempPreTrbn_MAP')
    t = temp_map['tables']['reference']
    protection = stage1.intersection(range(int(t['values_address'], 16), int(t['end'], 16)))
    assert len(protection) == 19
    coolant_class = {0x1CF2F6}
    assert ref[0x1CF2F6] == on[0x1CF2F6] == 11 and off[0x1CF2F6] == 0
    duration_map_names = {
        'InjVlv_phiInjMI1_MAP1',
        'InjVlv_phiInjMI1_MAP2',
        'InjVlv_phiInjMI1_MAP3',
        'InjVlv_phiInjMI1_MAP4',
    }
    duration_maps = set()
    for map_report in report['maps']:
        if map_report['name'] not in duration_map_names:
            continue
        values = map_report['tables']['reference']
        lo = int(values['values_address'], 16)
        hi = int(values['end'], 16)
        duration_maps.update(a for a in range(lo, hi) if ref[a] != on[a])
    assert len(duration_maps) == 209
    manifests = []
    for name, selected, reason in [
        ('restore_coolant_sensor_diagnostic_class', coolant_class,
         'Restore DSM_ClaDfp_CTSCD_C from 0 to reference-baseline class 11; this restores calibration of coolant-sensor diagnostics, not proof that the sensor caused symptoms.'),
        ('restore_factory_temperature_factor', protection,
         'Restore the 12 modified thermal-limitation cells to the reference baseline; not a proven smoke fix.'),
        ('restore_factory_calibration_keep_existing_off_for_isolation', calibration,
         'Superseded diagnostic isolation candidate: remove all identified Stage 1 calibration changes, retain existing OFF defects and opaque trailers pending separate verification. Stage 1 is required by the user; do not use this as the selected candidate.'),
        ('stage1_preserving_restore_thermal_and_coolant_diagnostics', protection | coolant_class,
         'Selected review candidate: retain Stage 1 driver-demand, boost, smoke, torque-limit, torque-to-fuel, SOI and duration changes; restore only the reference-baseline thermal-factor cells and coolant-sensor diagnostic class. This remains an unvalidated review candidate, not a flash recommendation.'),
        ('stage1_preserving_restore_duration_thermal_and_coolant_diagnostics',
         duration_maps | protection | coolant_class,
         'Additional isolation candidate: restore only the four named main-injection duration maps, reference-baseline thermal-factor cells and coolant-sensor diagnostic class while retaining the other Stage 1 maps and all non-target OFF changes. This is not a complete Stage 1 calibration, not flash validated and not a safety certification.'),
    ]:
        candidate = bytearray(off)
        patches = []
        for lo, hi in make_ranges(selected):
            candidate[lo:hi] = ref[lo:hi]
            patches.append({'offset': hex(lo), 'end_exclusive': hex(hi),
                            'expected_off_hex': off[lo:hi].hex(),
                            'replacement_reference_hex': ref[lo:hi].hex()})
        actual_delta = {a for a in range(len(off)) if off[a] != candidate[a]}
        assert actual_delta == selected
        assert all(candidate[a] == off[a] for a in (off_delta | opaque) - selected)
        assert candidate[:0x180000] == off[:0x180000]
        remaining = {a for a in range(0x180000, len(ref)) if candidate[a] != ref[a]}
        assert remaining == (stage1 | off_delta) - selected
        restored = bytearray(candidate)
        for p in patches:
            lo, hi = int(p['offset'], 16), int(p['end_exclusive'], 16)
            restored[lo:hi] = bytes.fromhex(p['expected_off_hex'])
        assert bytes(restored) == off
        manifests.append({'name': name, 'purpose': reason,
                          'status': 'REVIEW_ONLY_NOT_FLASH_VALIDATED',
                          'virtual_candidate_sha256': digest(candidate),
                          'changed_bytes': len(selected), 'remaining_diff_from_reference': len(remaining),
                          'existing_off_bytes_retained': len(off_delta - selected),
                          'source_off_sha256': digest(off), 'patches': patches})
    selected = bytearray(off)
    selected_set = protection | coolant_class
    for lo, hi in make_ranges(selected_set):
        selected[lo:hi] = ref[lo:hi]
    selected_path = OUT / '03G906021QJ_stage1-preserving-dpf-egr-off.review.bin'
    selected_path.write_bytes(selected)
    duration_selected = duration_maps | protection | coolant_class
    duration_candidate = bytearray(off)
    for lo, hi in make_ranges(duration_selected):
        duration_candidate[lo:hi] = ref[lo:hi]
    duration_path = OUT / '03G906021QJ_stage1-preserving-restore-duration.review.bin'
    duration_path.write_bytes(duration_candidate)
    result = {
        'status': 'REVIEW_ONLY_CANDIDATE_WRITTEN_NO_FLASH',
        'source_sha256': {k: digest(v) for k, v in blobs.items()},
        'internet_original_sha256': digest(original),
        'internet_original_calibration_equals_hex_reference': True,
        'constraints': [
            'Current ECU readback and active calibration selection unverified.',
            'Selected Stage1-preserving candidate retains Stage1 and 291 of 311 OFF bytes; it restores 20 bytes (19 thermal-factor + 1 coolant diagnostic class). Retaining OFF changes is not certification of correctness.',
            'Bosch checksum, signature and block compatibility are not validated; opaque trailers retained.',
            'The 4575-byte option is superseded because Stage1 must remain; it is not a complete reference firmware or a flash recommendation.',
            'The additional 229-byte duration-isolation candidate is for controlled diagnosis only; it is not selected, complete, checksum-validated or flash-ready.',
            'Do not concatenate the reference program prefix with the user calibration container.',
            'No vehicle test performed; root cause and symptom resolution remain unproven.',
        ],
        'selected_manifest': 'stage1_preserving_restore_thermal_and_coolant_diagnostics',
        'review_decision': {
            'report': str(OUT / 'LUNA-REVIEW-FINAL.md'),
            'intent': 'Preserve existing power-map bytes; no arbitrary torque target or duration rollback.',
            'minimal20': 'ACCEPTED_FOR_STATIC_REVIEW_ONLY_NOT_A_PROVEN_SYMPTOM_FIX',
            'duration229': 'NOT_ACCEPTED_AS_FINAL_POWER_PRESERVING_CALIBRATION',
            'mandatory_310_330_nm_cap': 'REJECTED_AS_UNSUPPORTED_REQUIREMENT',
            'physical_power_retention': 'NOT_MEASURED',
        },
        'selected_candidate_file': str(selected_path),
        'selected_candidate_sha256': digest(selected),
        'additional_review_candidates': {
            'stage1_preserving_restore_duration_thermal_and_coolant_diagnostics': {
                'file': str(duration_path),
                'sha256': digest(duration_candidate),
                'changed_bytes': len(duration_selected),
                'status': 'REVIEW_ONLY_NOT_SELECTED_NO_FLASH',
            }
        },
        'manifests': manifests,
        'validation': ['source hashes pinned', 'original archive tail identical',
                       'all intended changed addresses exactly verified',
                       'all non-target OFF changes preserved', 'opaque trailers preserved',
                       'FF prefix preserved', 'byte-exact rollback verified'],
    }
    (OUT / 'repair-manifests.review-only.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print('PASS: source hashes, archive baseline, exact patch sets, preserved OFF/prefix/trailers, reversible changes.')
    for m in manifests:
        print(m['name'], m['changed_bytes'], 'bytes;', len(m['patches']), 'ranges; remaining ref diff', m['remaining_diff_from_reference'])
    print('Review candidates created with Stage1-preserving variants; checksum and physical acceptance NOT RUN.')


if __name__ == '__main__':
    main()
