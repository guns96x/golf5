#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_pya2ldb_spike.py

Technical spike to evaluate pya2ldb on the exact Bosch EDC16U34 A2L file:
03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.a2l
"""

import sys
import os
import time
import json
from pathlib import Path

TARGET_MAPS = [
    "PCR_pBDesBas_MAP",
    "PCR_rBPCtlBas_MAP",
    "FlMng_qPresSmoke_MAP",
    "InjCrv_phiBasGear34_MAP",
    "AccPed_trqEng0_MAP"
]

A2L_PATH = Path("diagnostic-review/definitions/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.a2l")
CACHE_DIR = Path("D:/pya2ldb_cache")

def main():
    print(f"[SPIKE] Target A2L: {A2L_PATH}")
    print(f"[SPIKE] A2L file size: {A2L_PATH.stat().st_size:,} bytes")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    import pya2l
    from pya2l import model

    db_path = CACHE_DIR / (A2L_PATH.stem + ".a2ldb")
    print(f"[SPIKE] Target .a2ldb path: {db_path}")

    t0 = time.time()
    if db_path.exists():
        print(f"[SPIKE] Found existing cached database: {db_path} ({db_path.stat().st_size:,} bytes). Opening...")
        session = pya2l.open_existing(str(db_path))
    else:
        print(f"[SPIKE] Parsing A2L with pya2l.import_a2l into {CACHE_DIR}...")
        session = pya2l.import_a2l(
            str(A2L_PATH),
            output_dir=str(CACHE_DIR),
            progress_bar=False,
            encoding="latin-1",
            loglevel="INFO"
        )
    elapsed = time.time() - t0
    print(f"[SPIKE] Database ready in {elapsed:.2f} seconds.")

    # Query the 5 target characteristics
    results = {}
    for name in TARGET_MAPS:
        char = session.query(model.Characteristic).filter(model.Characteristic.name == name).first()
        if not char:
            print(f"[WARNING] Characteristic {name} not found in A2L!")
            continue

        char_info = {
            "name": char.name,
            "long_identifier": getattr(char, "long_identifier", None),
            "type": getattr(char, "type", None),
            "address": hex(getattr(char, "address", 0)),
            "deposit": getattr(char, "deposit", None),
            "max_diff": getattr(char, "max_diff", None),
            "conversion": getattr(char, "conversion", None),
            "lower_limit": getattr(char, "lower_limit", None),
            "upper_limit": getattr(char, "upper_limit", None),
            "axes": []
        }

        # Conversion / CompuMethod details
        if char.conversion:
            cm = session.query(model.CompuMethod).filter(model.CompuMethod.name == char.conversion).first()
            if cm:
                char_info["compu_method"] = {
                    "name": cm.name,
                    "unit": getattr(cm, "unit", None),
                    "conversion_type": getattr(cm, "conversion_type", None),
                    "format": getattr(cm, "format", None),
                    "coeffs": getattr(cm, "coeffs", None)
                }

        # Axes details
        if hasattr(char, "axis_descr"):
            for ax in char.axis_descr:
                ax_info = {
                    "attribute": getattr(ax, "attribute", None),
                    "input_quantity": getattr(ax, "input_quantity", None),
                    "conversion": getattr(ax, "conversion", None),
                    "max_axis_points": getattr(ax, "max_axis_points", None),
                    "lower_limit": getattr(ax, "lower_limit", None),
                    "upper_limit": getattr(ax, "upper_limit", None),
                    "axis_pts_ref": getattr(ax, "axis_pts_ref", None)
                }
                if ax.conversion:
                    ax_cm = session.query(model.CompuMethod).filter(model.CompuMethod.name == ax.conversion).first()
                    if ax_cm:
                        ax_info["compu_method"] = {
                            "name": ax_cm.name,
                            "unit": getattr(ax_cm, "unit", None),
                            "format": getattr(ax_cm, "format", None)
                        }
                char_info["axes"].append(ax_info)

        # Record layout details
        if char.deposit:
            rl = session.query(model.RecordLayout).filter(model.RecordLayout.name == char.deposit).first()
            if rl:
                char_info["record_layout_name"] = rl.name

        results[name] = char_info

    print("\n" + "="*80)
    print("EXTRACTED CHARACTERISTICS VIA PYA2LDB:")
    print("="*80)
    print(json.dumps(results, indent=2, default=str))

    # Verification against ground truth
    print("\n" + "="*80)
    print("VERIFICATION CHECKS:")
    print("="*80)
    expected_addrs = {
        "AccPed_trqEng0_MAP": "0x1c2cce",
        "FlMng_qPresSmoke_MAP": "0x1d6490",
        "InjCrv_phiBasGear34_MAP": "0x1daaf8",
        "PCR_pBDesBas_MAP": "0x1eb0b2",
        "PCR_rBPCtlBas_MAP": "0x1e9fd0"
    }

    all_matched = True
    for name, exp_addr in expected_addrs.items():
        act_addr = results.get(name, {}).get("address", "").lower()
        match = act_addr == exp_addr.lower()
        if not match:
            all_matched = False
        print(f" - {name}: expected={exp_addr}, actual={act_addr} -> {'MATCH' if match else 'FAIL'}")

    print(f"\nAll 5 maps address match: {all_matched}")
    return 0 if all_matched else 1

if __name__ == "__main__":
    sys.exit(main())
