# -*- coding: utf-8 -*-
"""
calharness.address_space

Unified AddressSpace model for Bosch EDC16 ECU binaries.
Ensures identical and consistent translations between physical file offsets
and absolute ECU memory addresses across 2 MiB full firmware images and 512 KiB
OBD calibration slices.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union
from pydantic import BaseModel, ConfigDict, Field, computed_field


class AddressSpace(BaseModel):
    """
    Encapsulates bidirectional mapping between file offsets and ECU memory addresses.
    Eliminates discrepancies between full 2MB images and 512KB calibration slices.
    """
    model_config = ConfigDict(extra="forbid", frozen=True)

    file_size: int = Field(..., description="Size of binary file in bytes")
    base_ecu_address: int = Field(..., description="Absolute ECU memory address of file offset 0")

    @classmethod
    def from_binary(
        cls,
        source: Union[int, bytes, bytearray, Path, str],
        base_address: Optional[int] = None,
    ) -> AddressSpace:
        """
        Create AddressSpace for a given binary buffer, path, or byte size.
        Standard EDC16 conventions:
          - 2 MiB (0x200000 / 2,097,152 bytes) -> base_ecu_address = 0x000000
          - 512 KiB (0x80000 / 524,288 bytes)   -> base_ecu_address = 0x180000
        """
        if isinstance(source, (bytes, bytearray)):
            size = len(source)
        elif isinstance(source, (str, Path)):
            size = Path(source).stat().st_size
        elif isinstance(source, int):
            size = source
        else:
            raise TypeError(f"Expected int, bytes, bytearray, Path, or str, got {type(source)}")

        if base_address is not None:
            return cls(file_size=size, base_ecu_address=base_address)

        if size == 0x200000:
            return cls(file_size=size, base_ecu_address=0x000000)
        elif size == 0x80000:
            return cls(file_size=size, base_ecu_address=0x180000)
        else:
            raise ValueError(
                f"Unsupported ECU binary size {size} bytes (0x{size:X}). "
                "Expected 2,097,152 (2 MiB) or 524,288 (512 KiB). "
                "Explicit base_address must be provided for non-standard images."
            )

    @computed_field
    @property
    def end_ecu_address(self) -> int:
        """Upper exclusive bound of ECU addresses covered by this binary."""
        return self.base_ecu_address + self.file_size

    @computed_field
    @property
    def is_full_image(self) -> bool:
        """True if binary covers full 2 MiB MPC562 address space."""
        return self.file_size == 0x200000 and self.base_ecu_address == 0x000000

    @computed_field
    @property
    def is_calibration_slice(self) -> bool:
        """True if binary is a 512 KiB calibration area read (0x180000..0x200000)."""
        return self.file_size == 0x80000 and self.base_ecu_address == 0x180000

    def contains_ecu_address(self, ecu_address: int) -> bool:
        """Check if an absolute ECU address is present within this binary image."""
        return self.base_ecu_address <= ecu_address < self.end_ecu_address

    def contains_offset(self, file_offset: int) -> bool:
        """Check if a file offset is within binary file bounds."""
        return 0 <= file_offset < self.file_size

    def to_offset(self, ecu_address: int) -> int:
        """
        Translate absolute ECU memory address to file byte offset.
        Raises ValueError if address is out of bounds for this binary.
        """
        if not self.contains_ecu_address(ecu_address):
            raise ValueError(
                f"ECU address 0x{ecu_address:06X} is outside binary address space "
                f"[0x{self.base_ecu_address:06X} .. 0x{self.end_ecu_address:06X}) "
                f"(size: {self.file_size} bytes)"
            )
        return ecu_address - self.base_ecu_address

    def to_ecu_address(self, file_offset: int) -> int:
        """
        Translate file byte offset to absolute ECU memory address.
        Raises ValueError if file_offset is out of bounds.
        """
        if not self.contains_offset(file_offset):
            raise ValueError(
                f"File offset {file_offset} (0x{file_offset:X}) is outside file bounds "
                f"[0 .. {self.file_size})"
            )
        return self.base_ecu_address + file_offset
