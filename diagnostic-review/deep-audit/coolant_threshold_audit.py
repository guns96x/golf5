"""Audit coolant-temperature thresholds and axes near the reported 87-89 C transition.

Read-only for firmware inputs; writes a JSON report beside this script.
"""
from pathlib import Path
import hashlib
import json
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent


def blocks(text, kind):
    return {m[1]: m[2] for m in re.finditer(
        rf'/begin {kind}\s+(\S+)\s+(.*?)/end {kind}', text, re.S)}


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='replace')
    text = next((ROOT / 'definitions').rglob('*.a2l')).read_text(encoding='latin1')
    chars = blocks(text, 'CHARACTERISTIC')
    methods = blocks(text, 'COMPU_METHOD')
    layouts = blocks(text, 'RECORD_LAYOUT')
    index = json.loads((ROOT / 'a2l-characteristics-index.json').read_text())
    images = {key: path.read_bytes() for key, path in {
        'reference': ROOT / 'reference-from-hex.analysis-only.bin',
        'on': ROOT / 'new-inputs/on/03G906021QJ.Bin',
        'off': ROOT / 'new-inputs/off/03G906021QJ (DPF EGR OFF) NoCS.Bin',
    }.items()}
    sizes = {'SBYTE': ('b', 1), 'UBYTE': ('B', 1), 'SWORD': ('h', 2),
             'UWORD': ('H', 2), 'SLONG': ('i', 4), 'ULONG': ('I', 4)}

    def physical(raw, method):
        body = methods.get(method, '')
        match = re.search(r'COEFFS\s+([\d.eE+\-\s]+)', body)
        if not match:
            return None
        coefficients = [float(x) for x in match[1].split()]
        if len(coefficients) != 6:
            return None
        a, b, c, d, e, f = coefficients
        if a == d == e == 0 and b and f:
            return [(value * f - c) / b for value in raw]
        return None

    def decode(characteristic, image):
        address = characteristic['address']
        layout = layouts[characteristic['layout']]
        fields = []
        for match in re.finditer(
                r'(NO_AXIS_PTS_[XYZ]|AXIS_PTS_[XYZ]|FNC_VALUES)\s+(\d+)\s+(\w+)([^\n]*)',
                layout):
            fields.append((int(match[2]), match[1], match[3], match[4].strip()))
        dimensions, axes, values = {}, [], None
        position, values_address = address, None
        for _, kind, data_type, _ in sorted(fields):
            if data_type not in sizes:
                raise ValueError('unsupported type')
            format_char, byte_size = sizes[data_type]
            if kind.startswith('NO_AXIS'):
                count = struct.unpack_from('>' + format_char, image, position)[0]
                if not 0 < count <= 128:
                    raise ValueError('invalid dimension')
                dimensions[kind[-1]] = count
                position += byte_size
            elif kind.startswith('AXIS_PTS'):
                count = dimensions[kind[-1]]
                axes.append(list(struct.unpack_from(f'>{count}{format_char}', image, position)))
                position += count * byte_size
            else:
                count = 1
                for dimension in dimensions.values():
                    count *= dimension
                values = list(struct.unpack_from(f'>{count}{format_char}', image, position))
                values_address = position
                position += count * byte_size
        if values is None or position - address > characteristic['size']:
            raise ValueError('unsupported extent')
        axis_metadata = []
        for number, match in enumerate(re.finditer(
                r'/begin AXIS_DESCR\s+(\S+)\s+(\S+)\s+(\S+)\s+(\d+)',
                chars[characteristic['name']])):
            if number >= len(axes):
                break
            axis_metadata.append({
                'input': match[2], 'conversion': match[3],
                'raw': axes[number], 'physical': physical(axes[number], match[3]),
            })
        return {
            'end': position, 'values_address': values_address,
            'raw': values, 'physical': physical(values, characteristic['conversion']),
            'axes': axis_metadata,
        }

    def is_coolant_related(characteristic):
        body = chars[characteristic['name']]
        searchable = ' '.join((characteristic['name'], characteristic['description'], body[:600])).lower()
        return any(keyword in searchable for keyword in (
            'clnt', 'teng', 'kühlwasser', 'kuehlwasser', 'wassertemperatur',
            'coolant', 'motortemperatur'))

    camshaft_names = (
        'EngM_facCaSOfsCor_C', 'EngM_nCaSOfsMax_C', 'EngM_nCaSOfsMin_C',
        'EngM_phiCaSOfs_CUR', 'EngM_qCaSOfsMax_C', 'EngM_qCaSOfsMin_C',
        'EngM_tCaSOfsBas_C', 'EngM_tCaSOfsMin_C',
    )
    entries = []
    all_coolant_decoded = []
    decoded_by_name = {}
    for characteristic in index:
        if (characteristic['name'] not in chars
                or (not is_coolant_related(characteristic)
                    and characteristic['name'] not in camshaft_names)):
            continue
        try:
            decoded = {key: decode(characteristic, image) for key, image in images.items()}
        except (KeyError, ValueError, struct.error):
            continue
        reference = decoded['reference']
        end = reference['end']
        same_active_bytes = all(
            images['reference'][characteristic['address']:end]
            == images[key][characteristic['address']:decoded[key]['end']]
            for key in ('on', 'off'))
        decoded_by_name[characteristic['name']] = decoded
        if is_coolant_related(characteristic):
            all_coolant_decoded.append({
                'name': characteristic['name'],
                'description': characteristic['description'],
                'kind': characteristic['kind'],
                'address': characteristic['address_hex'],
                'physical_values': reference['physical'],
                'axes': reference['axes'],
                'same_active_bytes_ref_on_off': same_active_bytes,
                'reference_active_end': hex(end),
            })
        near_values = []
        if reference['physical'] and characteristic['conversion'] == 'Temp_Cels':
            near_values = [value for value in reference['physical'] if 75 <= value <= 105]
        near_axes = []
        for axis in reference['axes']:
            if axis['conversion'] == 'Temp_Cels' and axis['physical']:
                selected = [value for value in axis['physical'] if 75 <= value <= 105]
                if selected:
                    near_axes.append({'input': axis['input'], 'values_c': selected,
                                      'all_values_c': axis['physical']})
        if not near_values and not near_axes:
            continue
        all_candidates = near_values + [v for axis in near_axes for v in axis['values_c']]
        entries.append({
            'name': characteristic['name'], 'description': characteristic['description'],
            'kind': characteristic['kind'], 'address': characteristic['address_hex'],
            'a2l_line': characteristic['a2l_line'], 'same_active_bytes_ref_on_off': same_active_bytes,
            'all_value_entries_physical': reference['physical'],
            'near_75_105_value_entries_c': near_values, 'near_75_105_axes': near_axes,
            'distance_to_88_c': min(abs(value - 88) for value in all_candidates),
        })
    entries.sort(key=lambda item: (item['distance_to_88_c'], item['name']))
    camshaft = []
    index_by_name = {item['name']: item for item in index}
    for name in camshaft_names:
        if name not in decoded_by_name:
            continue
        characteristic = index_by_name[name]
        decoded = decoded_by_name[name]['reference']
        camshaft.append({
            'name': name,
            'description': characteristic['description'],
            'address': characteristic['address_hex'],
            'physical_values': decoded['physical'],
            'axes': decoded['axes'],
            'same_active_bytes_ref_on_off': all(
                images['reference'][characteristic['address']:decoded['end']]
                == images[key][characteristic['address']:decoded_by_name[name][key]['end']]
                for key in ('on', 'off')),
        })

    result = {
        'reported_transition_assumed_coolant_c': [87, 89],
        'source_sha256': {key: hashlib.sha256(value).hexdigest() for key, value in images.items()},
        'decoded_coolant_related_characteristic_count': len(all_coolant_decoded),
        'changed_coolant_related_characteristics': [
            item for item in all_coolant_decoded
            if not item['same_active_bytes_ref_on_off']],
        'changed_non_diagnostic_coolant_related_characteristics': [
            item for item in all_coolant_decoded
            if (not item['same_active_bytes_ref_on_off']
                and not item['name'].startswith('DSM_'))],
        'all_decoded_coolant_related_characteristics': all_coolant_decoded,
        'coolant_related_entries_with_75_105_c_nodes': entries,
        'exact_or_near_87_89': [entry for entry in entries if entry['distance_to_88_c'] <= 2],
        'camshaft_offset_temperature_calibration': camshaft,
        'static_interpretation': [
            'The 89.96 C EngM_tCaSOfsBas_C value is a reference temperature, not an enable threshold.',
            'The camshaft-offset learning minimum coolant temperature is EngM_tCaSOfsMin_C.',
            'No equal-bytes finding proves that the runtime sensor signal or learned state is correct.',
        ],
        'limits': [
            'A calibrated node near 88 C is not proof that its function causes the vehicle symptom.',
            'Equal calibration bytes do not prove equal runtime state or correct sensor input.',
            'No current ECU readback or runtime measurements are available.',
        ],
    }
    (OUT / 'coolant-threshold-audit.json').write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print('near-88 entries', len(result['exact_or_near_87_89']))
    for entry in result['exact_or_near_87_89']:
        print(entry['name'], entry['address'], entry['description'],
              'values', entry['near_75_105_value_entries_c'],
              'axes', [(axis['input'], axis['values_c']) for axis in entry['near_75_105_axes']],
              'same', entry['same_active_bytes_ref_on_off'])


if __name__ == '__main__':
    main()
