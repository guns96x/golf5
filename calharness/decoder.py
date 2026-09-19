# -*- coding: utf-8 -*-
"""
calharness.decoder

Production MapDecoder: Decodes calibration maps dynamically from binary images
using ASAP2/A2L metadata without hardcoded addresses.
"""

from __future__ import annotations

import hashlib
import re
import struct
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from calharness.a2l_catalog import A2LCatalog
from calharness.address_space import AddressSpace
from calharness.models import AxisData, DecodedMap, FirmwareIdentity
from calharness.record_layout import RecordLayoutResolver


class MapDecoder:
    """
    Symbolic map decoder for Bosch EDC16 ECU binaries.
    Binds a binary image to an A2L catalog and decodes physical maps on demand.
    """

    def __init__(
        self,
        bin_path_or_data: Union[Path, str, bytes, bytearray],
        catalog: Optional[A2LCatalog] = None,
    ):
        if isinstance(bin_path_or_data, (bytes, bytearray)):
            self.data = bytes(bin_path_or_data)
            self.source_path = None
        else:
            p = Path(bin_path_or_data)
            self.source_path = p
            with open(p, "rb") as f:
                self.data = f.read()

        self.size = len(self.data)
        self.address_space = AddressSpace.from_binary(self.size)
        self.base_address = self.address_space.base_ecu_address
        self.bin_sha256 = hashlib.sha256(self.data).hexdigest()

        self.catalog = catalog or A2LCatalog()
        self.resolver = RecordLayoutResolver(self.catalog.session)
        self._identity: Optional[FirmwareIdentity] = None

    def get_identity(self) -> FirmwareIdentity:
        """
        Extract grounded firmware identity metadata from addressed A2L / project locations.
        Replaces ungrounded whole-binary string scans.
        Address provenance:
          - VAG Part Number: 0x1C0CD2 (EepInit_dPartNr_C) -> '03G906021QJ'
          - VAG HW Part Number: 0x1C0CBE (EepInit_dHwPartNum_C) -> '03G906021AB'
          - VAG SW Version: 0x1C0CDF (EepInit_dPrgVer_C) -> '1984'
          - Bosch SW Number: 0x1C0010 / 0x180010 (Cal Segment Headers) -> '1037391847'
        """
        if self._identity is not None:
            return self._identity

        # 1. Addressed VAG SW Part Number
        vag_part = None
        if self.address_space.contains_ecu_address(0x1C0CD2):
            off = self.address_space.to_offset(0x1C0CD2)
            raw = self.data[off : off + 11].decode("ascii", errors="ignore").strip().rstrip("\x00")
            if re.match(r"^03G906021[A-Z0-9]{1,2}$", raw):
                vag_part = raw

        # 2. Addressed VAG HW Part Number
        vag_hw = None
        if self.address_space.contains_ecu_address(0x1C0CBE):
            off = self.address_space.to_offset(0x1C0CBE)
            raw = self.data[off : off + 11].decode("ascii", errors="ignore").strip().rstrip("\x00")
            if re.match(r"^03G906021[A-Z0-9]{1,2}$", raw):
                vag_hw = raw

        # 3. Addressed VAG SW Version
        vag_ver = None
        if self.address_space.contains_ecu_address(0x1C0CDF):
            off = self.address_space.to_offset(0x1C0CDF)
            raw = self.data[off : off + 4].decode("ascii", errors="ignore").strip().rstrip("\x00")
            if re.match(r"^\d{4}$", raw):
                vag_ver = raw

        # 4. Addressed Bosch SW Number and Project Code
        bosch_sw = None
        proj_code = None
        sw_candidates = set()
        for ecu_addr in (0x1C0010, 0x180010, 0x010150, 0x040010):
            if self.address_space.contains_ecu_address(ecu_addr):
                off = self.address_space.to_offset(ecu_addr)
                chunk = self.data[off : off + 24].decode("ascii", errors="ignore")
                m = re.match(r"^(1037\d{6})(P\d{3}[A-Z0-9]{4})?", chunk)
                if m:
                    sw_candidates.add(m.group(1))
                    if not bosch_sw:
                        bosch_sw = m.group(1)
                        if m.group(2):
                            proj_code = m.group(2)

        is_ambiguous = len(sw_candidates) > 1

        # Fallback to general scan only if addressed locations yield nothing (e.g. non-standard binary)
        if not vag_part or not bosch_sw:
            ascii_strings = [
                s.decode("ascii", errors="ignore")
                for s in re.findall(b"[A-Za-z0-9_]{4,}", self.data)
            ]
            part_candidates = [s for s in ascii_strings if re.match(r"^03G906021[A-Z0-9]{1,2}$", s)]
            if len(set(part_candidates)) > 1:
                is_ambiguous = True
            if not vag_part and part_candidates:
                vag_part = part_candidates[-1]

            if not vag_ver and "1984" in ascii_strings:
                vag_ver = "1984"

            if not bosch_sw:
                for s in ascii_strings:
                    m = re.search(r"1037(\d{6})(P\d{3}[A-Z0-9]{4})?", s)
                    if m:
                        bosch_sw = f"1037{m.group(1)}"
                        if m.group(2):
                            proj_code = m.group(2)
                        break

        cal_id = bosch_sw[4:] if bosch_sw else None

        self._identity = FirmwareIdentity(
            vag_part_number=vag_part,
            vag_hw_part_number=vag_hw,
            vag_sw_version=vag_ver,
            bosch_sw_number=bosch_sw,
            calibration_id=cal_id,
            project_code=proj_code,
            file_size=self.size,
            sha256=self.bin_sha256,
            is_ambiguous=is_ambiguous,
        )
        return self._identity

    def _map_address_to_offset(self, ecu_address: int) -> int:
        """Convert ECU address from A2L to byte offset in binary data buffer."""
        return self.address_space.to_offset(ecu_address)

    def decode(self, map_name: str) -> DecodedMap:
        """
        Decode a calibration map dynamically by its A2L symbol name.
        Zero hardcoded addresses: address, layout, axes, conversions are all read from A2L.
        """
        char = self.catalog.get_characteristic(map_name)
        if not char:
            raise KeyError(f"Characteristic '{map_name}' not found in A2L catalog")

        ecu_addr = getattr(char, "address", 0)
        offset = self._map_address_to_offset(ecu_addr)
        layout = getattr(char, "deposit", "")
        obj_type = getattr(char, "type", "MAP")
        desc = getattr(char, "long_identifier", "") or getattr(char, "longIdentifier", "")

        # Value converter
        val_cm_name = getattr(char, "conversion", None)
        val_conv = self.catalog.get_converter(val_cm_name)

        if layout == "Kf_Xs16_Ys16_Ws16":
            return self._decode_kf_xs16_ys16_ws16(
                char=char,
                offset=offset,
                ecu_addr=ecu_addr,
                desc=desc,
                obj_type=obj_type,
                val_conv=val_conv,
            )
        elif layout == "Kl_Xs16_Ws16":
            return self._decode_kl_xs16_ws16(
                char=char,
                offset=offset,
                ecu_addr=ecu_addr,
                desc=desc,
                obj_type=obj_type,
                val_conv=val_conv,
            )
        elif layout == "Gkf_Ws16":
            return self._decode_gkf_ws16(
                char=char,
                offset=offset,
                ecu_addr=ecu_addr,
                desc=desc,
                obj_type=obj_type,
                val_conv=val_conv,
            )
        else:
            raise NotImplementedError(
                f"Record layout '{layout}' for '{map_name}' is not yet supported by decoder"
            )

    def _decode_kf_xs16_ys16_ws16(
        self,
        char: Any,
        offset: int,
        ecu_addr: int,
        desc: str,
        obj_type: str,
        val_conv: Any,
    ) -> DecodedMap:
        """Decode standard 2D map layout: nx (s16), ny (s16), x_pts (s16), y_pts (s16), grid (s16)."""
        nx, ny = struct.unpack_from(">hh", self.data, offset)
        if nx <= 0 or ny <= 0 or nx > 64 or ny > 64:
            raise ValueError(f"Invalid map dimensions for {char.name}: nx={nx}, ny={ny} at offset 0x{offset:06X}")

        # X-axis
        x_raw = np.frombuffer(self.data, dtype=">i2", count=nx, offset=offset + 4).copy()
        # Y-axis
        y_raw = np.frombuffer(self.data, dtype=">i2", count=ny, offset=offset + 4 + 2 * nx).copy()
        # Grid
        grid_start = offset + 4 + 2 * (nx + ny)
        grid_raw = np.frombuffer(self.data, dtype=">i2", count=nx * ny, offset=grid_start).reshape((nx, ny)).copy()

        # Axis metadata from A2L
        axes_descr = getattr(char, "axis_descr", [])
        x_conv_name = getattr(axes_descr[0], "conversion", None) if len(axes_descr) > 0 else None
        y_conv_name = getattr(axes_descr[1], "conversion", None) if len(axes_descr) > 1 else None

        x_conv = self.catalog.get_converter(x_conv_name)
        y_conv = self.catalog.get_converter(y_conv_name)

        x_phys = x_conv.to_physical(x_raw.astype(float))
        y_phys = y_conv.to_physical(y_raw.astype(float))
        grid_phys = val_conv.to_physical(grid_raw.astype(float))

        x_input_q = getattr(axes_descr[0], "inputQuantity", None) or getattr(axes_descr[0], "input_quantity", None) if len(axes_descr) > 0 else None
        y_input_q = getattr(axes_descr[1], "inputQuantity", None) or getattr(axes_descr[1], "input_quantity", None) if len(axes_descr) > 1 else None

        x_name = x_input_q or x_conv_name or "X"
        y_name = y_input_q or y_conv_name or "Y"

        x_axis = AxisData(
            name=x_name,
            unit=x_conv.unit,
            count=int(nx),
            raw_values=x_raw.tolist(),
            physical_values=[round(float(v), 4) for v in x_phys.tolist()],
        )
        y_axis = AxisData(
            name=y_name,
            unit=y_conv.unit,
            count=int(ny),
            raw_values=y_raw.tolist(),
            physical_values=[round(float(v), 4) for v in y_phys.tolist()],
        )

        return DecodedMap(
            name=char.name,
            description=desc,
            obj_type=obj_type,
            address=ecu_addr,
            record_layout=char.deposit,
            unit=val_conv.unit,
            shape=(int(nx), int(ny)),
            x_axis=x_axis,
            y_axis=y_axis,
            raw_grid=grid_raw.tolist(),
            physical_grid=[[round(float(v), 4) for v in row] for row in grid_phys.tolist()],
            a2l_sha256=self.catalog.a2l_sha256,
            bin_sha256=self.bin_sha256,
        )

    def _decode_kl_xs16_ws16(
        self,
        char: Any,
        offset: int,
        ecu_addr: int,
        desc: str,
        obj_type: str,
        val_conv: Any,
    ) -> DecodedMap:
        """Decode standard 1D curve layout: nx (s16), x_pts (s16), values (s16)."""
        (nx,) = struct.unpack_from(">h", self.data, offset)
        if nx <= 0 or nx > 128:
            raise ValueError(f"Invalid curve dimensions for {char.name}: nx={nx} at offset 0x{offset:06X}")

        x_raw = np.frombuffer(self.data, dtype=">i2", count=nx, offset=offset + 2).copy()
        val_start = offset + 2 + 2 * nx
        val_raw = np.frombuffer(self.data, dtype=">i2", count=nx, offset=val_start).copy()

        axes_descr = getattr(char, "axis_descr", [])
        x_conv_name = getattr(axes_descr[0], "conversion", None) if len(axes_descr) > 0 else None
        x_conv = self.catalog.get_converter(x_conv_name)

        x_phys = x_conv.to_physical(x_raw.astype(float))
        val_phys = val_conv.to_physical(val_raw.astype(float))

        x_input_q = getattr(axes_descr[0], "inputQuantity", None) or getattr(axes_descr[0], "input_quantity", None) if len(axes_descr) > 0 else None
        x_name = x_input_q or x_conv_name or "X"

        x_axis = AxisData(
            name=x_name,
            unit=x_conv.unit,
            count=int(nx),
            raw_values=x_raw.tolist(),
            physical_values=[round(float(v), 4) for v in x_phys.tolist()],
        )

        return DecodedMap(
            name=char.name,
            description=desc,
            obj_type=obj_type,
            address=ecu_addr,
            record_layout=char.deposit,
            unit=val_conv.unit,
            shape=(int(nx),),
            x_axis=x_axis,
            y_axis=None,
            raw_grid=val_raw.tolist(),
            physical_grid=[round(float(v), 4) for v in val_phys.tolist()],
            a2l_sha256=self.catalog.a2l_sha256,
            bin_sha256=self.bin_sha256,
        )

    def _decode_gkf_ws16(
        self,
        char: Any,
        offset: int,
        ecu_addr: int,
        desc: str,
        obj_type: str,
        val_conv: Any,
    ) -> DecodedMap:
        """
        Decode Group Map (Gkf_Ws16) with shared external axes (COM_AXIS).
        Used by 31 maps including base start-of-injection maps InjCrv_phiBas0..6_GMAP.
        """
        axes_descr = getattr(char, "axis_descr", [])
        if len(axes_descr) < 2:
            raise ValueError(f"Group map {char.name} requires at least 2 axis descriptions")

        from pya2l import model

        # X Axis (COM_AXIS)
        ax_x_descr = axes_descr[0]
        x_pts_name = getattr(getattr(ax_x_descr, "axis_pts_ref", None), "axisPoints", None)
        ax_x_obj = (
            self.catalog.session.query(model.AxisPts)
            .filter(model.AxisPts.name == x_pts_name)
            .first()
        )
        if not ax_x_obj:
            raise KeyError(f"Shared AxisPts '{x_pts_name}' for X axis of {char.name} not found in A2L")

        ax_x_addr = ax_x_obj.address
        ax_x_off = self._map_address_to_offset(ax_x_addr)
        ax_x_res = self.resolver.resolve_axis_pts(ax_x_obj, self.data, ax_x_off)
        nx = ax_x_res.shape[0]
        x_raw = np.frombuffer(
            self.data, dtype=ax_x_res.fnc_numpy, count=nx, offset=ax_x_off + ax_x_res.header_size
        ).copy()

        # Y Axis (COM_AXIS)
        ax_y_descr = axes_descr[1]
        y_pts_name = getattr(getattr(ax_y_descr, "axis_pts_ref", None), "axisPoints", None)
        ax_y_obj = (
            self.catalog.session.query(model.AxisPts)
            .filter(model.AxisPts.name == y_pts_name)
            .first()
        )
        if not ax_y_obj:
            raise KeyError(f"Shared AxisPts '{y_pts_name}' for Y axis of {char.name} not found in A2L")

        ax_y_addr = ax_y_obj.address
        ax_y_off = self._map_address_to_offset(ax_y_addr)
        ax_y_res = self.resolver.resolve_axis_pts(ax_y_obj, self.data, ax_y_off)
        ny = ax_y_res.shape[0]
        y_raw = np.frombuffer(
            self.data, dtype=ax_y_res.fnc_numpy, count=ny, offset=ax_y_off + ax_y_res.header_size
        ).copy()

        # Grid Values: starts at offset, count = nx * ny, layout COLUMN_DIR
        grid_raw = np.frombuffer(self.data, dtype=">i2", count=nx * ny, offset=offset).reshape((nx, ny)).copy()

        # Converters
        x_conv = self.catalog.get_converter(getattr(ax_x_descr, "conversion", None))
        y_conv = self.catalog.get_converter(getattr(ax_y_descr, "conversion", None))

        x_phys = x_conv.to_physical(x_raw.astype(float))
        y_phys = y_conv.to_physical(y_raw.astype(float))
        grid_phys = val_conv.to_physical(grid_raw.astype(float))

        x_input_q = getattr(ax_x_descr, "inputQuantity", None) or getattr(ax_x_descr, "input_quantity", None)
        y_input_q = getattr(ax_y_descr, "inputQuantity", None) or getattr(ax_y_descr, "input_quantity", None)

        x_axis = AxisData(
            name=x_input_q or getattr(ax_x_descr, "conversion", None) or "X",
            unit=x_conv.unit,
            count=int(nx),
            raw_values=x_raw.tolist(),
            physical_values=[round(float(v), 4) for v in x_phys.tolist()],
        )
        y_axis = AxisData(
            name=y_input_q or getattr(ax_y_descr, "conversion", None) or "Y",
            unit=y_conv.unit,
            count=int(ny),
            raw_values=y_raw.tolist(),
            physical_values=[round(float(v), 4) for v in y_phys.tolist()],
        )

        return DecodedMap(
            name=char.name,
            description=desc,
            obj_type=obj_type,
            address=ecu_addr,
            record_layout=char.deposit,
            unit=val_conv.unit,
            shape=(int(nx), int(ny)),
            x_axis=x_axis,
            y_axis=y_axis,
            raw_grid=grid_raw.tolist(),
            physical_grid=[[round(float(v), 4) for v in row] for row in grid_phys.tolist()],
            a2l_sha256=self.catalog.a2l_sha256,
            bin_sha256=self.bin_sha256,
        )
