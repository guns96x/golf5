# -*- coding: utf-8 -*-
"""
calharness.models

Strict Pydantic v2 domain models for calibration maps, axes, and firmware identity.
"""

from __future__ import annotations

from typing import Any, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, computed_field


class AxisData(BaseModel):
    """Represents an axis of a 1D or 2D calibration map."""
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    name: str = Field(..., description="A2L symbol name or conversion name for this axis")
    unit: str = Field("", description="Physical engineering unit (e.g. rpm, mg/hub, hPa, %)")
    count: int = Field(..., description="Number of breakpoints / nodes along this axis")
    raw_values: List[int] = Field(..., description="Raw integer values as read from binary")
    physical_values: List[float] = Field(..., description="Scaled physical values")

    def to_numpy(self) -> np.ndarray:
        """Return physical values as a 1D numpy array."""
        return np.array(self.physical_values, dtype=float)


class DecodedMap(BaseModel):
    """
    Represents a fully decoded calibration map (1D curve or 2D matrix)
    with physical engineering units, axes, and bidirectional conversions.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    name: str = Field(..., description="A2L symbol name (e.g. PCR_pBDesBas_MAP)")
    description: Optional[str] = Field(None, description="Long identifier / description from A2L")
    obj_type: str = Field("MAP", description="ASAP2 object type (MAP, CURVE, VAL_BLK, VALUE)")
    address: int = Field(..., description="Byte offset address in binary image")
    record_layout: str = Field(..., description="Bosch/ASAP2 RECORD_LAYOUT name (e.g. Kf_Xs16_Ys16_Ws16)")
    unit: str = Field("", description="Physical unit of values in the grid")
    shape: Tuple[int, ...] = Field(..., description="Dimensions (e.g. (16, 10) for 2D or (16,) for 1D)")
    
    x_axis: AxisData = Field(..., description="X-axis (e.g. engine speed)")
    y_axis: Optional[AxisData] = Field(None, description="Y-axis (e.g. fuel quantity or pressure), None for 1D")
    
    raw_grid: Union[List[List[int]], List[int]] = Field(..., description="Raw integer values from binary")
    physical_grid: Union[List[List[float]], List[float]] = Field(..., description="Scaled physical values")
    a2l_sha256: Optional[str] = Field(None, description="SHA256 hash of A2L file")
    bin_sha256: Optional[str] = Field(None, description="SHA256 hash of binary file")

    @computed_field
    @property
    def hex_address(self) -> str:
        """Hex representation of the map address."""
        return f"0x{self.address:06X}"

    def numpy_physical(self) -> np.ndarray:
        """Return physical grid as a numpy array."""
        return np.array(self.physical_grid, dtype=float)

    def numpy_raw(self) -> np.ndarray:
        """Return raw integer grid as a numpy array."""
        return np.array(self.raw_grid, dtype=int)

    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert to a pandas DataFrame with physical axis labels.
        For 2D: Index is X axis, Columns are Y axis.
        For 1D: Index is X axis, single column 'Value'.
        """
        arr = self.numpy_physical()
        if self.y_axis is not None and arr.ndim == 2:
            cols = [f"{v:.2f} {self.y_axis.unit}".strip() for v in self.y_axis.physical_values]
            idx = [f"{v:.1f} {self.x_axis.unit}".strip() for v in self.x_axis.physical_values]
            return pd.DataFrame(arr, index=idx, columns=cols)
        else:
            idx = [f"{v:.1f} {self.x_axis.unit}".strip() for v in self.x_axis.physical_values]
            col_name = f"{self.name} ({self.unit})".strip()
            return pd.DataFrame(arr, index=idx, columns=[col_name])

    def summary(self) -> str:
        """Return a human-readable one-line summary."""
        arr = self.numpy_physical()
        y_desc = f" x {self.y_axis.count} [{self.y_axis.unit}]" if self.y_axis else ""
        return (
            f"{self.name} @ {self.hex_address} | {self.record_layout} | "
            f"Shape: {self.shape} ({self.x_axis.count} [{self.x_axis.unit}]{y_desc}) | "
            f"Range: [{arr.min():.2f} .. {arr.max():.2f} {self.unit}]"
        )


class FirmwareIdentity(BaseModel):
    """Identity and provenance metadata for a 2MB ECU binary."""
    model_config = ConfigDict(extra="forbid")

    vag_part_number: Optional[str] = None
    vag_hw_part_number: Optional[str] = None
    vag_sw_version: Optional[str] = None
    bosch_sw_number: Optional[str] = None
    calibration_id: Optional[str] = None
    project_code: Optional[str] = None
    file_size: int
    sha256: str
    is_ambiguous: bool = False
