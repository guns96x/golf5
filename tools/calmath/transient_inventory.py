"""Inventory A2L objects needed for transient torque-path analysis."""

_REQUIRED_MEASUREMENTS = {
    'ASDdc_trq': 'active_damper_torque',
    'CoEng_trqInrLtdDrv': 'torque_before_active_damping',
    'CoEng_trqSetASDUnLim': 'torque_after_asd_before_second_limit',
    'CoEng_trqLimASDdc_mp': 'torque_after_active_damping',
    'FMTC_qAct': 'iq_before_active_damping',
    'FlMng_qDynSmoke_mp': 'dynamic_smoke_iq',
    'FlMng_pIATCorr_mp': 'smoke_corrected_pressure',
}

_DYNAMIC_SMOKE_EXACT = {
    'FlMng_qDynSmoke_MAP',
    'FlMng_facDynSmoke_CUR',
    'FlMng_facDynSmkAP_CUR',
    'FlMng_facDynSmkTemp_CUR',
}


def _measurement_entry(name, role, metadata):
    found = metadata is not None
    return {
        'name': name,
        'role': role,
        'found': found,
        'runtime_required': True,
        'evidence_level': 'runtime',
        'metadata': dict(metadata) if found else None,
    }


def _is_transient_characteristic(name):
    return (
        name.startswith('ASDdc_')
        or name.startswith('ASDrf_')
        or name in _DYNAMIC_SMOKE_EXACT
        or name.startswith('FlMng_facDynSm')
    )


def inventory_transient_objects(db):
    """Return an explicit inventory of required runtime and calibration objects.

    Missing required objects are reported rather than inferred. The function
    operates only on already-parsed A2L metadata and never reads/writes a BIN.
    """
    measurements = db.get('measurements') or {}
    characteristics = db.get('characteristics') or {}
    required = {
        name: _measurement_entry(name, role, measurements.get(name))
        for name, role in _REQUIRED_MEASUREMENTS.items()
    }
    selected_characteristics = {
        name: dict(meta)
        for name, meta in characteristics.items()
        if _is_transient_characteristic(name)
    }
    missing_required = [name for name, entry in required.items() if not entry['found']]
    missing_dynamic_characteristics = sorted(
        name for name in _DYNAMIC_SMOKE_EXACT if name not in characteristics
    )
    return {
        'measurements': required,
        'characteristics': selected_characteristics,
        'missing_required': missing_required,
        'missing_dynamic_characteristics': missing_dynamic_characteristics,
        'counts': {
            'required_measurements_found': len(required) - len(missing_required),
            'required_measurements_total': len(required),
            'transient_characteristics_found': len(selected_characteristics),
        },
    }
