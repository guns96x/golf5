"""Decode the actual calibration VALUES for the CONTROL-PATH-STOCK boost maps.

Closes ecu-kb gap P1 "Decode map values from BIN". Structure (names, addresses,
axes) was already established from the A2L alone; this script adds the numbers
that were still missing, using the project's existing A2L-driven decoder
(tools/calmath/a2l.py) instead of guessing scale factors per map, as the older
ad-hoc decode_*.py scripts in this directory do.

Source of truth for "stock": diagnostic-review/reference-from-hex.analysis-only.bin.
This is the best approximation of stock the project has, but it is itself
RECONSTRUCTED from hex, not read from the car (see ecu-kb gap "Отримати
незайманий заводський readback ECU"). Every claim built from this script's
output must carry that caveat.

Usage:
    python tools/decode_boost_path_stock.py > diagnostic-review/math-engine/boost-path-stock-values.json
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from calmath import a2l  # noqa: E402

if sys.platform == "win32":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REF_BIN = "diagnostic-review/reference-from-hex.analysis-only.bin"
A2L_PATH = a2l.A2L_PATH
SW_NUMBER = "1037391847"

MAPS = [
    "PCR_pBDesBas_MAP", "PCR_pBDesBas2_MAP", "PCR_pBDesMaxAP_MAP",
    "PCR_facP_MAP", "PCR_facI_MAP", "PCR_facD_MAP",
    "PCR_rBPGovMax_MAP", "PCR_rBPGovMin_MAP", "PCR_rBPCtlBas_MAP",
]
CURVES = [
    "PCR_nTrbnMax_CUR", "PCR_qRgtOn_CUR", "PCR_qRgtOff_CUR", "PCR_rBPGovLin_CUR",
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def dump_map(c):
    return {
        "name": c.name, "desc": c.desc, "kind": c.kind, "unit": c.unit,
        "address": hex(c.address), "size_bytes": c.size,
        "x_input": c.axes[0]["input"], "x_unit": c.axes[0]["unit"], "x": c.x,
        "y_input": c.axes[1]["input"], "y_unit": c.axes[1]["unit"], "y": c.y,
        "grid": c.grid,
    }


def dump_curve(c):
    return {
        "name": c.name, "desc": c.desc, "kind": c.kind, "unit": c.unit,
        "address": hex(c.address), "size_bytes": c.size,
        "x_input": c.axes[0]["input"], "x": c.x, "values": c.values,
    }


def main():
    binary = open(REF_BIN, "rb").read()
    out = {
        "sw_number": SW_NUMBER,
        "source_bin": REF_BIN,
        "source_bin_sha256": sha256(REF_BIN),
        "source_bin_provenance": "RECONSTRUCTED from hex, not read from the car. "
                                  "Best available stock approximation, not MEASURED.",
        "a2l_path": A2L_PATH,
        "a2l_sha256": sha256(A2L_PATH),
        "maps": [], "curves": [],
    }
    for name in MAPS:
        try:
            out["maps"].append(dump_map(a2l.load(name, binary)))
        except Exception as e:
            print(f"SKIP {name}: {e}", file=sys.stderr)
    for name in CURVES:
        try:
            out["curves"].append(dump_curve(a2l.load(name, binary)))
        except Exception as e:
            print(f"SKIP {name}: {e}", file=sys.stderr)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
