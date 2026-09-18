# -*- coding: utf-8 -*-
"""
calharness.diff_engine

Production Semantic Diff Engine:
Classifies every byte modification between stock and modified ECU binaries,
correlating changed bytes to A2L characteristics, axes, map cells, headers,
code areas, identity blocks, and checksums.
"""

from __future__ import annotations

import bisect
import enum
import hashlib
import logging
import pickle
import struct
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from calharness.a2l_catalog import A2LCatalog
from calharness.address_space import AddressSpace
from calharness.decoder import MapDecoder
from calharness.models import AxisData, DecodedMap, FirmwareIdentity
from calharness.record_layout import RecordLayoutResolver

logger = logging.getLogger(__name__)


class ByteCategory(str, enum.Enum):
    """Categorization of a modified byte in ECU memory."""
    CODE_AREA = "CODE_AREA"                  # Program code area (< 0x180000)
    IDENTITY_AREA = "IDENTITY_AREA"          # Part number, SW, HW identity strings
    CHECKSUM_AREA = "CHECKSUM_AREA"          # EDC16 checksum blocks
    MAP_VALUE = "MAP_VALUE"                  # Cell value in a 2D map matrix
    MAP_AXIS = "MAP_AXIS"                    # Breakpoint node in a 2D map axis
    MAP_HEADER = "MAP_HEADER"                # Dimension header (nx, ny) of a 2D map
    CURVE_VALUE = "CURVE_VALUE"              # Value in a 1D curve
    CURVE_AXIS = "CURVE_AXIS"                # Breakpoint node in a 1D curve axis
    CURVE_HEADER = "CURVE_HEADER"            # Dimension header (nx) of a 1D curve
    KNOWN_CALIBRATION = "KNOWN_CALIBRATION"  # Known A2L single value, value block, or flag
    UNKNOWN_CALIBRATION = "UNKNOWN_CALIBRATION"  # Unmapped byte in calibration area
    PADDING = "PADDING"                      # Unused trailing padding (0xFF)


# Project-Specific Identity Ranges for Bosch EDC16U34-3.42 / 03G906021QJ / SW 1037391847
# Provenance: VAG KWP2000 diagnostic read tables and A2L ASAP2 characteristic addresses
IDENTITY_RANGES = [
    (0x010150, 0x010162, "SW / Project ID Code Area 1 (provenance: MPC562 Boot Section)"),
    (0x040010, 0x040022, "SW / Project ID Code Area 2 (provenance: MPC562 App Section)"),
    (0x180010, 0x180022, "SW / Project ID Cal Area 1 (provenance: Cal Segment 1 Header)"),
    (0x1C0010, 0x1C0022, "SW / Project ID Cal Area 2 (provenance: Cal Segment 2 Header)"),
    (0x1C0CBE, 0x1C0CE0, "VAG Part Number Strings (provenance: A2L EepInit_stVAGPrtNo_C)"),
]

# Project-Specific Checksum Word Ranges for Bosch EDC16U34-3.42
# Provenance: Bosch EDC16 memory organization; Segment 1 and Segment 2 32-bit checksum words
CHECKSUM_RANGES = [
    (0x1BFFFC, 0x1C0000, "EDC16 Segment 1 Checksum Word (provenance: Bosch EDC16 32-bit checksum word)"),
    (0x1FDFFC, 0x1FE000, "EDC16 Segment 2 Checksum Word (provenance: Bosch EDC16 32-bit checksum word)"),
]


class CellDiff(BaseModel):
    """Details of a single modified cell within a 2D map or 1D curve."""
    model_config = ConfigDict(extra="forbid")

    x_index: int
    y_index: Optional[int] = None
    x_val: float
    y_val: Optional[float] = None
    old_raw: int
    new_raw: int
    old_phys: float
    new_phys: float
    delta_phys: float
    percent_change: Optional[float] = None


class MapDiffSummary(BaseModel):
    """Summary of changes to an individual calibration map or curve."""
    model_config = ConfigDict(extra="forbid")

    name: str
    address: int
    hex_address: str
    record_layout: str
    unit: str
    shape: Tuple[int, ...]
    total_cells: int
    changed_cells_count: int
    axis_changed: bool = False
    header_changed: bool = False
    min_old: float
    max_old: float
    min_new: float
    max_new: float
    min_delta: float
    max_delta: float
    changed_cells: List[CellDiff] = Field(default_factory=list)


class ByteDiffClassification(BaseModel):
    """Classification and ownership metadata for a single modified byte."""
    model_config = ConfigDict(extra="forbid")

    offset: int
    hex_offset: str
    old_byte: int
    new_byte: int
    category: ByteCategory
    owner_symbol: Optional[str] = None
    detail: Optional[str] = None
    ecu_address: Optional[int] = None
    hex_ecu_address: Optional[str] = None


class SemanticDiffReport(BaseModel):
    """
    Comprehensive machine-readable semantic diff report.
    Guarantees 100% byte accounting: every byte difference is classified into
    a known memory category (code, identity, map value, curve value, known cal scalar,
    checksum, padding, or unmapped). This establishes complete spatial classification
    coverage, not autonomous semantic proof of intent.
    """
    model_config = ConfigDict(extra="forbid")

    stock_identity: FirmwareIdentity
    mod_identity: FirmwareIdentity
    total_bytes_changed: int
    bytes_by_category: Dict[str, int] = Field(default_factory=dict)
    
    code_area_bytes: int = 0
    identity_area_bytes: int = 0
    checksum_area_bytes: int = 0
    unmapped_bytes: int = 0
    
    maps_changed: List[MapDiffSummary] = Field(default_factory=list)
    classified_diffs: List[ByteDiffClassification] = Field(default_factory=list)
    decoding_errors: List[str] = Field(default_factory=list)
    a2l_sha256: Optional[str] = None
    stock_bin_sha256: Optional[str] = None
    mod_bin_sha256: Optional[str] = None

    @property
    def is_clean_calibration(self) -> bool:
        """
        True if only authorized calibration values and checksums changed with zero code,
        identity, unmapped, header corruption, axis breakpoint modifications, or padding modifications.
        """
        hdr_bytes = (
            self.bytes_by_category.get(ByteCategory.MAP_HEADER.value, 0)
            + self.bytes_by_category.get(ByteCategory.CURVE_HEADER.value, 0)
        )
        axis_bytes = (
            self.bytes_by_category.get(ByteCategory.MAP_AXIS.value, 0)
            + self.bytes_by_category.get(ByteCategory.CURVE_AXIS.value, 0)
        )
        padding_bytes = self.bytes_by_category.get(ByteCategory.PADDING.value, 0)
        return (
            self.code_area_bytes == 0
            and self.identity_area_bytes == 0
            and self.unmapped_bytes == 0
            and hdr_bytes == 0
            and axis_bytes == 0
            and padding_bytes == 0
            and len(self.decoding_errors) == 0
        )

    def summary(self) -> str:
        """Human-readable overview of the diff."""
        lines = [
            f"Semantic Diff: {self.total_bytes_changed:,} total bytes modified",
            f"  - Maps/Curves: {self.bytes_by_category.get(ByteCategory.MAP_VALUE, 0) + self.bytes_by_category.get(ByteCategory.CURVE_VALUE, 0)} bytes in {len(self.maps_changed)} maps",
            f"  - Known Cal Values: {self.bytes_by_category.get(ByteCategory.KNOWN_CALIBRATION, 0)} bytes",
            f"  - Checksum Area: {self.checksum_area_bytes} bytes",
            f"  - Code Area (<0x180000): {self.code_area_bytes} bytes",
            f"  - Identity Area: {self.identity_area_bytes} bytes",
            f"  - Unmapped/Unknown: {self.unmapped_bytes} bytes",
            f"Clean Calibration: {'YES (PASS)' if self.is_clean_calibration else 'NO (VIOLATIONS DETECTED)'}"
        ]
        return "\n".join(lines)


class SemanticDiffEngine:
    """
    High-performance semantic difference engine.
    Indexes A2L characteristics into interval trees and maps binary differences
    to physical domain entities.
    """

    def __init__(self, catalog: Optional[A2LCatalog] = None):
        self.catalog = catalog or A2LCatalog()
        self._intervals: Optional[List[Tuple[int, int, str, str, str, Dict[str, Any]]]] = None

    def _build_intervals(
        self, reference_bin: Optional[bytes] = None
    ) -> List[Tuple[int, int, str, str, str, Dict[str, Any]]]:
        """
        Build sorted list of (start_ecu_addr, end_ecu_addr, name, type, layout, extra_meta)
        for all characteristics and axis points in the A2L database.
        Eliminates any sz=2 guessing by leveraging RecordLayoutResolver.
        """
        if self._intervals is not None:
            return self._intervals

        cache_path = self.catalog.cache_dir / f"intervals_{self.catalog.a2l_sha256[:16]}.pickle"
        if cache_path.exists():
            try:
                with open(cache_path, "rb") as f:
                    self._intervals = pickle.load(f)
                    return self._intervals
            except Exception as e:
                logger.warning("Failed to load cached intervals: %s", e)

        from pya2l import model

        session = self.catalog.session
        resolver = RecordLayoutResolver(session)
        address_space = (
            AddressSpace.from_binary(len(reference_bin))
            if reference_bin is not None
            else AddressSpace.from_binary(0x200000)
        )

        chars = (
            session.query(model.Characteristic)
            .order_by(model.Characteristic.address.asc())
            .all()
        )

        intervals = []
        for ch in chars:
            ecu_addr = ch.address
            file_off = address_space.to_offset(ecu_addr) if address_space.contains_ecu_address(ecu_addr) else None
            try:
                res = resolver.resolve_characteristic(ch, reference_bin, file_off)
                sz = res.total_size
                extra = {
                    "header_end": ecu_addr + res.header_size,
                    "x_axis_end": ecu_addr + res.header_size + res.x_axis_size,
                    "y_axis_end": ecu_addr + res.header_size + res.x_axis_size + res.y_axis_size,
                    "values_start": ecu_addr + res.header_size + res.x_axis_size + res.y_axis_size,
                    "values_end": ecu_addr + sz,
                    "is_group_map": res.is_group_map,
                }
                intervals.append((ecu_addr, ecu_addr + sz, ch.name, ch.type, ch.deposit or "", extra))
            except Exception as e:
                logger.warning("Could not resolve size for %s: %s", ch.name, e)

        # Also add shared AxisPts
        axis_pts_list = session.query(model.AxisPts).order_by(model.AxisPts.address.asc()).all()
        for ax in axis_pts_list:
            ax_addr = ax.address
            ax_off = address_space.to_offset(ax_addr) if address_space.contains_ecu_address(ax_addr) else None
            try:
                res_ax = resolver.resolve_axis_pts(ax, reference_bin, ax_off)
                extra_ax = {
                    "header_end": ax_addr + res_ax.header_size,
                    "x_axis_end": ax_addr + res_ax.total_size,
                }
                intervals.append((ax_addr, ax_addr + res_ax.total_size, ax.name, "AXIS_PTS", ax.depositAttr or "", extra_ax))
            except Exception as e:
                logger.warning("Could not resolve axis size for %s: %s", ax.name, e)

        intervals.sort(key=lambda x: x[0])
        self._intervals = intervals

        try:
            with open(cache_path, "wb") as f:
                pickle.dump(intervals, f)
        except Exception as e:
            logger.warning("Failed to save intervals cache: %s", e)

        return intervals

    def compare(
        self,
        stock_bin: Union[Path, str, bytes],
        mod_bin: Union[Path, str, bytes],
    ) -> SemanticDiffReport:
        """
        Perform complete semantic difference analysis between stock and modified binary.
        Guarantees 100% byte accounting and classifies every modification.
        """
        dec_stock = MapDecoder(stock_bin, catalog=self.catalog)
        dec_mod = MapDecoder(mod_bin, catalog=self.catalog)

        data_stock = dec_stock.data
        data_mod = dec_mod.data

        if len(data_stock) != len(data_mod):
            raise ValueError(f"Binaries have different lengths: stock={len(data_stock)}, mod={len(data_mod)}")

        ident_stock = dec_stock.get_identity()
        ident_mod = dec_mod.get_identity()
        address_space = dec_stock.address_space

        intervals = self._build_intervals(data_stock)

        # Fast byte diff scanning using numpy
        arr_stock = np.frombuffer(data_stock, dtype=np.uint8)
        arr_mod = np.frombuffer(data_mod, dtype=np.uint8)
        diff_indices = np.where(arr_stock != arr_mod)[0]

        classified: List[ByteDiffClassification] = []
        category_counts: Dict[str, int] = {cat.value: 0 for cat in ByteCategory}
        affected_maps: Set[str] = set()

        for idx in diff_indices:
            file_off = int(idx)
            ecu_addr = address_space.to_ecu_address(file_off)
            old_b = int(arr_stock[file_off])
            new_b = int(arr_mod[file_off])

            cat, symbol, detail = self._classify_address(ecu_addr, intervals)
            category_counts[cat.value] += 1

            if cat in (
                ByteCategory.MAP_VALUE,
                ByteCategory.MAP_AXIS,
                ByteCategory.MAP_HEADER,
                ByteCategory.CURVE_VALUE,
                ByteCategory.CURVE_AXIS,
                ByteCategory.CURVE_HEADER,
            ):
                if symbol:
                    affected_maps.add(symbol)

            classified.append(
                ByteDiffClassification(
                    offset=file_off,
                    hex_offset=f"0x{file_off:06X}",
                    old_byte=old_b,
                    new_byte=new_b,
                    category=cat,
                    owner_symbol=symbol,
                    detail=detail,
                    ecu_address=ecu_addr,
                    hex_ecu_address=f"0x{ecu_addr:06X}",
                )
            )

        # Detailed per-map analysis for all affected maps
        map_summaries: List[MapDiffSummary] = []
        decoding_errors: List[str] = []

        for map_name in sorted(affected_maps):
            has_hdr_byte = any(
                d.category in (ByteCategory.MAP_HEADER, ByteCategory.CURVE_HEADER)
                and d.owner_symbol == map_name
                for d in classified
            )
            try:
                m_old = dec_stock.decode(map_name)
                m_new = dec_mod.decode(map_name)
                summary = self._analyze_map_diff(m_old, m_new)
                if has_hdr_byte:
                    summary.header_changed = True
                map_summaries.append(summary)
            except Exception as exc:
                decoding_errors.append(f"Failed to decode {map_name}: {exc}")
                if has_hdr_byte:
                    try:
                        m_old = dec_stock.decode(map_name)
                        total_cells = int(np.prod(m_old.shape))
                        map_summaries.append(
                            MapDiffSummary(
                                name=m_old.name,
                                address=m_old.address,
                                hex_address=m_old.hex_address,
                                record_layout=m_old.record_layout,
                                unit=m_old.unit,
                                shape=m_old.shape,
                                total_cells=total_cells,
                                changed_cells_count=0,
                                axis_changed=False,
                                header_changed=True,
                                min_old=round(float(m_old.numpy_physical().min()), 4),
                                max_old=round(float(m_old.numpy_physical().max()), 4),
                                min_new=0.0,
                                max_new=0.0,
                                min_delta=0.0,
                                max_delta=0.0,
                                changed_cells=[],
                            )
                        )
                    except Exception:
                        pass

        return SemanticDiffReport(
            stock_identity=ident_stock,
            mod_identity=ident_mod,
            total_bytes_changed=len(diff_indices),
            bytes_by_category=category_counts,
            code_area_bytes=category_counts[ByteCategory.CODE_AREA.value],
            identity_area_bytes=category_counts[ByteCategory.IDENTITY_AREA.value],
            checksum_area_bytes=category_counts[ByteCategory.CHECKSUM_AREA.value],
            unmapped_bytes=category_counts[ByteCategory.UNKNOWN_CALIBRATION.value],
            maps_changed=map_summaries,
            classified_diffs=classified,
            decoding_errors=decoding_errors,
            a2l_sha256=self.catalog.a2l_sha256,
            stock_bin_sha256=ident_stock.sha256,
            mod_bin_sha256=ident_mod.sha256,
        )

    def _classify_address(
        self,
        ecu_addr: int,
        intervals: List[Tuple[int, int, str, str, str, Dict[str, Any]]],
    ) -> Tuple[ByteCategory, Optional[str], Optional[str]]:
        """Classify a single ECU memory address into a ByteCategory and owner."""
        # 1. Check Identity Areas
        for start, end, desc in IDENTITY_RANGES:
            if start <= ecu_addr < end:
                return ByteCategory.IDENTITY_AREA, None, desc

        # 2. Check Code Area (<0x180000 for 2MB image)
        if ecu_addr < 0x180000:
            return ByteCategory.CODE_AREA, None, "MPC562 Program Code Area"

        # 3. Check Checksum Area
        for start, end, desc in CHECKSUM_RANGES:
            if start <= ecu_addr < end:
                return ByteCategory.CHECKSUM_AREA, None, desc

        # 4. Check Padding
        if 0x1FE000 <= ecu_addr < 0x200000:
            return ByteCategory.PADDING, None, "Trailing Calibration Padding (0xFF)"

        # 5. Check A2L Characteristics via bisect
        idx = bisect.bisect_right(intervals, (ecu_addr, float("inf"))) - 1
        if idx >= 0:
            start, end, name, obj_type, layout, extra = intervals[idx]
            if start <= ecu_addr < end:
                if obj_type == "AXIS_PTS":
                    if extra and ecu_addr < extra.get("header_end", 0):
                        return ByteCategory.MAP_HEADER, name, f"Axis Header (nx) of {name}"
                    return ByteCategory.MAP_AXIS, name, f"Axis Breakpoint of {name}"
                elif obj_type == "MAP":
                    if extra and extra.get("is_group_map"):
                        return ByteCategory.MAP_VALUE, name, f"Cell Value of {name}"
                    elif extra and extra.get("header_end", 0) > start:
                        if ecu_addr < extra["header_end"]:
                            return ByteCategory.MAP_HEADER, name, f"Map Header (nx/ny) of {name}"
                        elif ecu_addr < extra["x_axis_end"]:
                            return ByteCategory.MAP_AXIS, name, f"X-Axis Node of {name}"
                        elif ecu_addr < extra["y_axis_end"]:
                            return ByteCategory.MAP_AXIS, name, f"Y-Axis Node of {name}"
                        else:
                            return ByteCategory.MAP_VALUE, name, f"Cell Value of {name}"
                    else:
                        return ByteCategory.MAP_VALUE, name, f"Cell Value of {name}"
                elif obj_type == "CURVE":
                    if extra and extra.get("header_end", 0) > start:
                        if ecu_addr < extra["header_end"]:
                            return ByteCategory.CURVE_HEADER, name, f"Curve Header (nx) of {name}"
                        elif ecu_addr < extra["x_axis_end"]:
                            return ByteCategory.CURVE_AXIS, name, f"X-Axis Node of {name}"
                        else:
                            return ByteCategory.CURVE_VALUE, name, f"Curve Value of {name}"
                    else:
                        return ByteCategory.CURVE_VALUE, name, f"Curve Value of {name}"
                else:
                    return ByteCategory.KNOWN_CALIBRATION, name, f"A2L {obj_type} {name} ({layout})"

        # 6. Fallback: Unmapped Calibration Byte
        return ByteCategory.UNKNOWN_CALIBRATION, None, "Unmapped calibration byte"

    def _analyze_map_diff(self, old_m: DecodedMap, new_m: DecodedMap) -> MapDiffSummary:
        """Compute detailed cell-by-cell matrix difference for a map."""
        old_arr = old_m.numpy_physical()
        new_arr = new_m.numpy_physical()
        old_raw = old_m.numpy_raw()
        new_raw = new_m.numpy_raw()

        delta = new_arr - old_arr
        raw_diff_mask = old_raw != new_raw

        changed_cells: List[CellDiff] = []
        if old_m.y_axis is not None and old_arr.ndim == 2:
            nx, ny = old_m.shape
            for i in range(nx):
                for j in range(ny):
                    if raw_diff_mask[i, j]:
                        x_val = old_m.x_axis.physical_values[i]
                        y_val = old_m.y_axis.physical_values[j]
                        o_phys = float(old_arr[i, j])
                        n_phys = float(new_arr[i, j])
                        d_phys = float(delta[i, j])
                        pct = (d_phys / o_phys * 100.0) if abs(o_phys) > 1e-6 else None

                        changed_cells.append(
                            CellDiff(
                                x_index=i,
                                y_index=j,
                                x_val=x_val,
                                y_val=y_val,
                                old_raw=int(old_raw[i, j]),
                                new_raw=int(new_raw[i, j]),
                                old_phys=round(o_phys, 4),
                                new_phys=round(n_phys, 4),
                                delta_phys=round(d_phys, 4),
                                percent_change=round(pct, 2) if pct is not None else None,
                            )
                        )
        else:
            nx = old_m.shape[0]
            for i in range(nx):
                if raw_diff_mask[i]:
                    x_val = old_m.x_axis.physical_values[i]
                    o_phys = float(old_arr[i])
                    n_phys = float(new_arr[i])
                    d_phys = float(delta[i])
                    pct = (d_phys / o_phys * 100.0) if abs(o_phys) > 1e-6 else None

                    changed_cells.append(
                        CellDiff(
                            x_index=i,
                            y_index=None,
                            x_val=x_val,
                            y_val=None,
                            old_raw=int(old_raw[i]),
                            new_raw=int(new_raw[i]),
                            old_phys=round(o_phys, 4),
                            new_phys=round(n_phys, 4),
                            delta_phys=round(d_phys, 4),
                            percent_change=round(pct, 2) if pct is not None else None,
                        )
                    )

        axis_changed = old_m.x_axis.raw_values != new_m.x_axis.raw_values or (
            old_m.y_axis is not None and new_m.y_axis is not None and old_m.y_axis.raw_values != new_m.y_axis.raw_values
        )
        header_changed = (old_m.shape != new_m.shape or old_m.record_layout != new_m.record_layout)

        total_cells = int(np.prod(old_m.shape))
        return MapDiffSummary(
            name=old_m.name,
            address=old_m.address,
            hex_address=old_m.hex_address,
            record_layout=old_m.record_layout,
            unit=old_m.unit,
            shape=old_m.shape,
            total_cells=total_cells,
            changed_cells_count=len(changed_cells),
            axis_changed=axis_changed,
            header_changed=header_changed,
            min_old=round(float(old_arr.min()), 4),
            max_old=round(float(old_arr.max()), 4),
            min_new=round(float(new_arr.min()), 4),
            max_new=round(float(new_arr.max()), 4),
            min_delta=round(float(delta.min()), 4),
            max_delta=round(float(delta.max()), 4),
            changed_cells=changed_cells,
        )
