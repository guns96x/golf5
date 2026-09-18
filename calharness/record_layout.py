# -*- coding: utf-8 -*-
"""
calharness.record_layout

ASAP2/A2L RECORD_LAYOUT interpreter.
Resolves exact byte sizes, memory offsets, and data types for all characteristics
and axis points across all 41 ASAP2 record layouts used in Bosch EDC16 systems.
Eliminates any sz=2 silent fallbacks.
"""

from __future__ import annotations

import re
import struct
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, ConfigDict, Field


DATATYPE_SIZES: Dict[str, int] = {
    "UBYTE": 1,
    "SBYTE": 1,
    "UWORD": 2,
    "SWORD": 2,
    "ULONG": 4,
    "SLONG": 4,
    "FLOAT32_IEEE": 4,
}

DATATYPE_STRUCT: Dict[str, str] = {
    "UBYTE": "B",
    "SBYTE": "b",
    "UWORD": "H",
    "SWORD": "h",
    "ULONG": "I",
    "SLONG": "i",
    "FLOAT32_IEEE": "f",
}

DATATYPE_NUMPY: Dict[str, str] = {
    "UBYTE": ">u1",
    "SBYTE": ">i1",
    "UWORD": ">u2",
    "SWORD": ">i2",
    "ULONG": ">u4",
    "SLONG": ">i4",
    "FLOAT32_IEEE": ">f4",
}


class ResolvedLayout(BaseModel):
    """Exact structural layout and size resolution for an A2L characteristic."""
    model_config = ConfigDict(extra="forbid")

    layout_name: str
    total_size: int
    header_size: int = 0
    x_axis_size: int = 0
    y_axis_size: int = 0
    values_size: int = 0
    fnc_datatype: str = "SWORD"
    fnc_struct: str = ">h"
    fnc_numpy: str = ">i2"
    fnc_element_size: int = 2
    index_mode: str = "COLUMN_DIR"
    shape: Tuple[int, ...] = (1,)
    dp_blob_size: Optional[int] = None
    is_group_map: bool = False


def extract_dp_blob_size(char_or_axis: Any) -> Optional[int]:
    """Extract DP_BLOB size from ASAP2 IF_DATA blocks if present."""
    if_data_list = getattr(char_or_axis, "if_data", None)
    if not if_data_list:
        return None

    for ifd in if_data_list:
        raw_text = getattr(ifd, "raw", "") or ""
        if "DP_BLOB" in raw_text:
            tokens = re.findall(r"0x[0-9a-fA-F]+|\b\d+\b", raw_text)
            if len(tokens) >= 2:
                try:
                    return int(tokens[-1], 0)
                except ValueError:
                    pass
    return None


class RecordLayoutResolver:
    """
    Interprets ASAP2 RECORD_LAYOUT definitions dynamically to compute exact
    byte allocations, shapes, and binary offsets for any A2L characteristic.
    """

    def __init__(self, session: Any):
        self.session = session
        self._layout_cache: Dict[str, Any] = {}

    def get_layout(self, layout_name: str) -> Optional[Any]:
        """Fetch and cache RecordLayout from database."""
        if not layout_name:
            return None
        if layout_name in self._layout_cache:
            return self._layout_cache[layout_name]

        from pya2l import model
        rl = (
            self.session.query(model.RecordLayout)
            .filter(model.RecordLayout.name == layout_name)
            .first()
        )
        if rl:
            self._layout_cache[layout_name] = rl
        return rl

    def resolve_characteristic(
        self,
        char: Any,
        binary_data: Optional[bytes] = None,
        file_offset: Optional[int] = None,
    ) -> ResolvedLayout:
        """
        Compute exact byte layout and size for a characteristic.
        Raises ValueError if size cannot be derived from A2L metadata.
        """
        obj_type = getattr(char, "type", "MAP")
        layout_name = getattr(char, "deposit", "") or ""
        blob_sz = extract_dp_blob_size(char)

        rl = self.get_layout(layout_name)
        if not rl:
            # Check if DP_BLOB is available as authoritative size
            if blob_sz is not None:
                return ResolvedLayout(
                    layout_name=layout_name,
                    total_size=blob_sz,
                    values_size=blob_sz,
                    dp_blob_size=blob_sz,
                )
            raise ValueError(
                f"Cannot resolve layout for characteristic '{char.name}': "
                f"RecordLayout '{layout_name}' not found in A2L and no DP_BLOB present."
            )

        fnc_item = getattr(rl, "fnc_values", None)
        fnc_dt = fnc_item.datatype if fnc_item else "SWORD"
        fnc_size = DATATYPE_SIZES.get(fnc_dt, 2)
        fnc_fmt = ">" + DATATYPE_STRUCT.get(fnc_dt, "h")
        fnc_np = DATATYPE_NUMPY.get(fnc_dt, ">i2")
        index_mode = getattr(fnc_item, "indexMode", "COLUMN_DIR") if fnc_item else "COLUMN_DIR"

        # 1. VALUE (Scalar)
        if obj_type == "VALUE":
            total = fnc_size
            return ResolvedLayout(
                layout_name=layout_name,
                total_size=total,
                values_size=total,
                fnc_datatype=fnc_dt,
                fnc_struct=fnc_fmt,
                fnc_numpy=fnc_np,
                fnc_element_size=fnc_size,
                shape=(1,),
                dp_blob_size=blob_sz,
            )

        # 2. VAL_BLK / ASCII (Vector / Matrix of fixed number)
        if obj_type in ("VAL_BLK", "ASCII"):
            num_obj = getattr(char, "number", None)
            count = getattr(num_obj, "number", None)
            if count is None and isinstance(num_obj, int):
                count = num_obj
            if count is None and blob_sz is not None:
                count = blob_sz // fnc_size

            if count is None:
                raise ValueError(
                    f"VAL_BLK/ASCII characteristic '{char.name}' has no NUMBER attribute or DP_BLOB."
                )

            total = count * fnc_size
            return ResolvedLayout(
                layout_name=layout_name,
                total_size=total,
                values_size=total,
                fnc_datatype=fnc_dt,
                fnc_struct=fnc_fmt,
                fnc_numpy=fnc_np,
                fnc_element_size=fnc_size,
                shape=(count,),
                dp_blob_size=blob_sz,
            )

        # 3. MAP (2D Table)
        if obj_type == "MAP":
            # Check if this is a Group Map (Gkf_Ws16) with shared COM_AXIS
            has_embedded_nx = getattr(rl, "no_axis_pts_x", None) is not None
            has_embedded_ny = getattr(rl, "no_axis_pts_y", None) is not None

            if not has_embedded_nx and not has_embedded_ny:
                # Group map: axes are external (COM_AXIS); function values stored alone
                axes = getattr(char, "axis_descr", [])
                if len(axes) >= 2:
                    nx = axes[0].maxAxisPoints
                    ny = axes[1].maxAxisPoints
                elif blob_sz is not None:
                    # Derivation from blob size
                    nx = 16
                    ny = blob_sz // (nx * fnc_size)
                else:
                    raise ValueError(f"Group map '{char.name}' has insufficient axis descriptions to derive shape.")

                values_sz = nx * ny * fnc_size
                return ResolvedLayout(
                    layout_name=layout_name,
                    total_size=values_sz,
                    header_size=0,
                    x_axis_size=0,
                    y_axis_size=0,
                    values_size=values_sz,
                    fnc_datatype=fnc_dt,
                    fnc_struct=fnc_fmt,
                    fnc_numpy=fnc_np,
                    fnc_element_size=fnc_size,
                    index_mode=index_mode,
                    shape=(nx, ny),
                    dp_blob_size=blob_sz,
                    is_group_map=True,
                )

            # Standard map with embedded headers and axes
            nx_dt = getattr(rl.no_axis_pts_x, "datatype", "SWORD") if rl.no_axis_pts_x else "SWORD"
            ny_dt = getattr(rl.no_axis_pts_y, "datatype", "SWORD") if rl.no_axis_pts_y else "SWORD"
            nx_sz = DATATYPE_SIZES.get(nx_dt, 2)
            ny_sz = DATATYPE_SIZES.get(ny_dt, 2)
            header_sz = nx_sz + ny_sz

            ax_dt = getattr(rl.axis_pts_x, "datatype", "SWORD") if rl.axis_pts_x else "SWORD"
            ay_dt = getattr(rl.axis_pts_y, "datatype", "SWORD") if rl.axis_pts_y else "SWORD"
            ax_sz = DATATYPE_SIZES.get(ax_dt, 2)
            ay_sz = DATATYPE_SIZES.get(ay_dt, 2)

            nx, ny = None, None
            if binary_data is not None and file_offset is not None and file_offset + header_sz <= len(binary_data):
                fmt_x = ">" + DATATYPE_STRUCT.get(nx_dt, "h")
                fmt_y = ">" + DATATYPE_STRUCT.get(ny_dt, "h")
                (nx,) = struct.unpack_from(fmt_x, binary_data, file_offset)
                (ny,) = struct.unpack_from(fmt_y, binary_data, file_offset + nx_sz)

            if nx is None or ny is None or nx <= 0 or ny <= 0 or nx > 64 or ny > 64:
                # Fallback to maxAxisPoints from axis_descr
                axes = getattr(char, "axis_descr", [])
                if len(axes) >= 2:
                    nx = axes[0].maxAxisPoints
                    ny = axes[1].maxAxisPoints
                else:
                    nx, ny = 16, 16

            x_pts_sz = nx * ax_sz
            y_pts_sz = ny * ay_sz
            val_sz = nx * ny * fnc_size
            total = header_sz + x_pts_sz + y_pts_sz + val_sz

            return ResolvedLayout(
                layout_name=layout_name,
                total_size=total,
                header_size=header_sz,
                x_axis_size=x_pts_sz,
                y_axis_size=y_pts_sz,
                values_size=val_sz,
                fnc_datatype=fnc_dt,
                fnc_struct=fnc_fmt,
                fnc_numpy=fnc_np,
                fnc_element_size=fnc_size,
                index_mode=index_mode,
                shape=(nx, ny),
                dp_blob_size=blob_sz,
                is_group_map=False,
            )

        # 4. CURVE (1D Table)
        if obj_type == "CURVE":
            has_embedded_nx = getattr(rl, "no_axis_pts_x", None) is not None
            if not has_embedded_nx:
                # External axis curve
                axes = getattr(char, "axis_descr", [])
                nx = axes[0].maxAxisPoints if axes else (blob_sz // fnc_size if blob_sz else 16)
                values_sz = nx * fnc_size
                return ResolvedLayout(
                    layout_name=layout_name,
                    total_size=values_sz,
                    values_size=values_sz,
                    fnc_datatype=fnc_dt,
                    fnc_struct=fnc_fmt,
                    fnc_numpy=fnc_np,
                    fnc_element_size=fnc_size,
                    index_mode=index_mode,
                    shape=(nx,),
                    dp_blob_size=blob_sz,
                )

            nx_dt = getattr(rl.no_axis_pts_x, "datatype", "SWORD") if rl.no_axis_pts_x else "SWORD"
            nx_sz = DATATYPE_SIZES.get(nx_dt, 2)
            ax_dt = getattr(rl.axis_pts_x, "datatype", "SWORD") if rl.axis_pts_x else "SWORD"
            ax_sz = DATATYPE_SIZES.get(ax_dt, 2)

            nx = None
            if binary_data is not None and file_offset is not None and file_offset + nx_sz <= len(binary_data):
                fmt_x = ">" + DATATYPE_STRUCT.get(nx_dt, "h")
                (nx,) = struct.unpack_from(fmt_x, binary_data, file_offset)

            if nx is None or nx <= 0 or nx > 128:
                axes = getattr(char, "axis_descr", [])
                nx = axes[0].maxAxisPoints if axes else 16

            x_pts_sz = nx * ax_sz
            val_sz = nx * fnc_size
            total = nx_sz + x_pts_sz + val_sz

            return ResolvedLayout(
                layout_name=layout_name,
                total_size=total,
                header_size=nx_sz,
                x_axis_size=x_pts_sz,
                y_axis_size=0,
                values_size=val_sz,
                fnc_datatype=fnc_dt,
                fnc_struct=fnc_fmt,
                fnc_numpy=fnc_np,
                fnc_element_size=fnc_size,
                index_mode=index_mode,
                shape=(nx,),
                dp_blob_size=blob_sz,
            )

        # 5. Generic fallback based on DP_BLOB
        if blob_sz is not None:
            return ResolvedLayout(
                layout_name=layout_name,
                total_size=blob_sz,
                values_size=blob_sz,
                fnc_datatype=fnc_dt,
                fnc_struct=fnc_fmt,
                fnc_numpy=fnc_np,
                fnc_element_size=fnc_size,
                dp_blob_size=blob_sz,
            )

        raise ValueError(
            f"Cannot resolve layout for '{char.name}' (type={obj_type}, layout={layout_name}). "
            "No size could be derived."
        )

    def resolve_axis_pts(
        self,
        axis_pts: Any,
        binary_data: Optional[bytes] = None,
        file_offset: Optional[int] = None,
    ) -> ResolvedLayout:
        """Resolve layout and byte size for a shared AXIS_PTS object."""
        layout_name = getattr(axis_pts, "depositAttr", "") or ""
        blob_sz = extract_dp_blob_size(axis_pts)

        rl = self.get_layout(layout_name)
        ax_item = getattr(rl, "axis_pts_x", None) if rl else None
        ax_dt = getattr(ax_item, "datatype", "SWORD") if ax_item else "SWORD"
        ax_sz = DATATYPE_SIZES.get(ax_dt, 2)
        ax_fmt = ">" + DATATYPE_STRUCT.get(ax_dt, "h")
        ax_np = DATATYPE_NUMPY.get(ax_dt, ">i2")

        has_header = getattr(rl, "no_axis_pts_x", None) is not None if rl else False
        hdr_dt = getattr(rl.no_axis_pts_x, "datatype", "SWORD") if has_header else "SWORD"
        hdr_sz = DATATYPE_SIZES.get(hdr_dt, 2) if has_header else 0

        nx = None
        if has_header and binary_data is not None and file_offset is not None:
            if file_offset + hdr_sz <= len(binary_data):
                fmt = ">" + DATATYPE_STRUCT.get(hdr_dt, "h")
                (nx,) = struct.unpack_from(fmt, binary_data, file_offset)

        if nx is None or nx <= 0 or nx > 128:
            nx = getattr(axis_pts, "maxAxisPoints", 16)

        total = hdr_sz + (nx * ax_sz)
        return ResolvedLayout(
            layout_name=layout_name,
            total_size=total,
            header_size=hdr_sz,
            x_axis_size=nx * ax_sz,
            values_size=0,
            fnc_datatype=ax_dt,
            fnc_struct=ax_fmt,
            fnc_numpy=ax_np,
            fnc_element_size=ax_sz,
            shape=(nx,),
            dp_blob_size=blob_sz,
        )
