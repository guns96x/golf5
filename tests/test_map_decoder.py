# -*- coding: utf-8 -*-
"""
tests/test_map_decoder.py

Regression test suite for calharness.decoder.MapDecoder.
Compares decoded maps against legacy decoder scripts (regression oracles)
and verifies Pydantic models, axes, units, and physical values.
"""

import struct
from pathlib import Path
import numpy as np
import pytest

from calharness import MapDecoder, DecodedMap, AxisData

STOCK_BIN_PATH = Path("knowledge/08_firmware/originals/03G906021QJ_1984_391847_full_stock.bin")
STAGE1_BIN_PATH = Path("firmware/03G906021QJ_stage1_full_power_dpf_egr_off.bin")


@pytest.fixture(scope="module")
def decoder():
    assert STOCK_BIN_PATH.exists(), f"Reference stock binary missing at {STOCK_BIN_PATH}"
    return MapDecoder(STOCK_BIN_PATH)


def test_firmware_identity(decoder):
    ident = decoder.get_identity()
    assert ident.bosch_sw_number == "1037391847"
    assert ident.calibration_id == "391847"
    assert ident.project_code == "P447HAXN"
    assert ident.file_size == 2097152
    assert ident.sha256 == "cf891152a97fb63609b40fc590fd86f38b034119b516e936eb8c0173e2551d26"


def test_decode_boost_target(decoder):
    m = decoder.decode("PCR_pBDesBas_MAP")
    assert isinstance(m, DecodedMap)
    assert m.address == 0x1EB0B2
    assert m.hex_address == "0x1EB0B2"
    assert m.record_layout == "Kf_Xs16_Ys16_Ws16"
    assert m.shape == (16, 10)
    assert m.unit == "hPa"
    
    # X-axis (Engine speed)
    assert m.x_axis.count == 16
    assert m.x_axis.unit == "rpm"
    assert m.x_axis.physical_values[0] == 0.0
    assert m.x_axis.physical_values[-1] == 4746.0
    
    # Y-axis (Fuel quantity)
    assert m.y_axis is not None
    assert m.y_axis.count == 10
    assert m.y_axis.unit == "mg/hub"
    assert m.y_axis.physical_values[0] == 0.0
    assert m.y_axis.physical_values[-1] == 45.0

    # Values
    phys = m.numpy_physical()
    assert phys.shape == (16, 10)
    assert np.isclose(phys.min(), 198.0)
    assert np.isclose(phys.max(), 2050.0)


def test_regression_oracle_boost_target(decoder):
    """Verify bit-exact match with legacy tools/decode_boost_target.py logic."""
    with open(STOCK_BIN_PATH, "rb") as f:
        data = f.read()

    addr = 0x1EB0B2
    nx, ny = struct.unpack_from(">hh", data, addr)
    x_axis = [float(x) for x in struct.unpack_from(">" + str(nx) + "h", data, addr + 4)]
    y_axis = [round(y * 0.01, 4) for y in struct.unpack_from(">" + str(ny) + "h", data, addr + 4 + 2 * nx)]
    v_start = addr + 4 + 2 * (nx + ny)
    raw_vals = struct.unpack_from(">" + str(nx * ny) + "h", data, v_start)
    oracle_grid = np.array(raw_vals, dtype=float).reshape((nx, ny))

    decoded = decoder.decode("PCR_pBDesBas_MAP")
    assert decoded.x_axis.physical_values == x_axis
    assert decoded.y_axis.physical_values == y_axis
    assert np.allclose(decoded.numpy_physical(), oracle_grid)


def test_decode_smoke_map(decoder):
    m = decoder.decode("FlMng_qPresSmoke_MAP")
    assert m.address == 0x1D6490
    assert m.shape == (16, 12)
    assert m.unit == "mg/hub"
    assert m.x_axis.unit == "rpm"
    assert m.y_axis.unit == "hPa"
    
    phys = m.numpy_physical()
    assert np.isclose(phys.min(), 14.80)
    assert np.isclose(phys.max(), 60.00)


def test_regression_oracle_smoke_map(decoder):
    """Verify bit-exact match with legacy tools/decode_smoke_map.py logic."""
    with open(STOCK_BIN_PATH, "rb") as f:
        data = f.read()

    addr = 0x1D6490
    nx, ny = struct.unpack_from(">hh", data, addr)
    x_axis = [float(x) for x in struct.unpack_from(">" + str(nx) + "h", data, addr + 4)]
    y_axis = [float(y) for y in struct.unpack_from(">" + str(ny) + "h", data, addr + 4 + 2 * nx)]
    v_start = addr + 4 + 2 * (nx + ny)
    raw_vals = struct.unpack_from(">" + str(nx * ny) + "h", data, v_start)
    oracle_grid = np.array([round(v * 0.01, 4) for v in raw_vals], dtype=float).reshape((nx, ny))

    decoded = decoder.decode("FlMng_qPresSmoke_MAP")
    assert decoded.x_axis.physical_values == x_axis
    assert decoded.y_axis.physical_values == y_axis
    assert np.allclose(decoded.numpy_physical(), oracle_grid, atol=1e-4)


def test_decode_n75_precontrol(decoder):
    m = decoder.decode("PCR_rBPCtlBas_MAP")
    assert m.address == 0x1E9FD0
    assert m.shape == (16, 13)
    assert m.unit == "%"
    phys = m.numpy_physical()
    assert np.isclose(phys.min(), 28.50)
    assert np.isclose(phys.max(), 80.00)


def test_decode_soi_map(decoder):
    m = decoder.decode("InjCrv_phiBasGear34_MAP")
    assert m.address == 0x1DAAF8
    assert m.shape == (16, 14)
    assert m.unit == "deg CrS"
    phys = m.numpy_physical()
    assert np.isclose(phys.min(), -0.49, atol=0.01)
    assert np.isclose(phys.max(), 27.00, atol=0.01)


def test_regression_oracle_soi_map(decoder):
    """Verify bit-exact match with legacy tools/decode_soi_maps.py logic."""
    with open(STOCK_BIN_PATH, "rb") as f:
        data = f.read()

    addr = 0x1DAAF8
    nx, ny = struct.unpack_from(">hh", data, addr)
    x_axis = [float(x) for x in struct.unpack_from(">" + str(nx) + "h", data, addr + 4)]
    y_axis = [round(y * 0.01, 4) for y in struct.unpack_from(">" + str(ny) + "h", data, addr + 4 + 2 * nx)]
    v_start = addr + 4 + 2 * (nx + ny)
    raw_vals = struct.unpack_from(">" + str(nx * ny) + "h", data, v_start)
    oracle_grid = np.array([round(v * 0.0234375, 4) for v in raw_vals], dtype=float).reshape((nx, ny))

    decoded = decoder.decode("InjCrv_phiBasGear34_MAP")
    assert decoded.x_axis.physical_values == x_axis
    assert decoded.y_axis.physical_values == y_axis
    assert np.allclose(decoded.numpy_physical(), oracle_grid, atol=1e-4)


def test_decode_pedal_torque(decoder):
    m = decoder.decode("AccPed_trqEng0_MAP")
    assert m.address == 0x1C2CCE
    assert m.shape == (16, 8)
    assert m.unit == "Nm"
    phys = m.numpy_physical()
    assert np.isclose(phys.min(), 0.0)
    assert np.isclose(phys.max(), 390.0)


def test_decode_1d_curve(decoder):
    m = decoder.decode("ACCCD_aDesLimNeg_CUR")
    assert m.address == 0x1C245C
    assert m.record_layout == "Kl_Xs16_Ws16"
    assert m.shape == (5,)
    assert m.y_axis is None
    assert m.x_axis.count == 5
    assert m.x_axis.unit == "km/h"
    assert np.allclose(m.numpy_physical(), -3.0)


def test_dataframe_export(decoder):
    m = decoder.decode("PCR_pBDesBas_MAP")
    df = m.to_dataframe()
    assert df.shape == (16, 10)
    assert "0.0 rpm" in df.index
    assert "45.00 mg/hub" in df.columns


def test_unknown_map_raises_keyerror(decoder):
    with pytest.raises(KeyError):
        decoder.decode("NON_EXISTENT_MAP_XYZ")


def test_stage1_diff(decoder):
    if not STAGE1_BIN_PATH.exists():
        pytest.skip("Stage 1 binary not found")

    stg_decoder = MapDecoder(STAGE1_BIN_PATH)
    m_stock = decoder.decode("PCR_pBDesBas_MAP")
    m_stg = stg_decoder.decode("PCR_pBDesBas_MAP")

    diff = m_stg.numpy_physical() - m_stock.numpy_physical()
    assert diff.shape == (16, 10)
    # Stage 1 has a peak boost increase of 164 hPa
    assert np.isclose(diff.max(), 164.0)
