# -*- coding: utf-8 -*-
"""
calharness.a2l_catalog

High-performance query interface to A2L metadata using pya2ldb SQLite backend.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pya2l
from pya2l import model
from pya2l.functions import Coeffs, Identical, Linear, RatFunc

logger = logging.getLogger(__name__)


class UnsupportedConversionError(ValueError):
    """Raised when an unknown or unsupported COMPU_METHOD conversion is encountered."""
    pass


DEFAULT_A2L_PATH = Path(
    "diagnostic-review/definitions/03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42/"
    "03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.a2l"
)
DEFAULT_CACHE_DIR = Path("D:/pya2ldb_cache")


class A2LConverter:
    """Encapsulates bidirectional physical <-> raw conversion."""

    def __init__(self, name: str, unit: str, func: Any):
        self.name = name
        self.unit = unit.strip("[]") if unit else ""
        self._func = func

    def to_physical(self, raw_val: Any) -> Any:
        """Convert raw integer or numpy array to physical engineering values."""
        if hasattr(self._func, "int_to_physical"):
            return self._func.int_to_physical(raw_val)
        elif callable(self._func):
            return self._func(raw_val)
        return raw_val

    def to_raw(self, phys_val: Any) -> Any:
        """Convert physical value or numpy array back to raw integer values."""
        if hasattr(self._func, "physical_to_int"):
            res = self._func.physical_to_int(phys_val)
            if isinstance(res, np.ndarray):
                return np.round(res).astype(int)
            return int(round(res))
        return phys_val


class A2LCatalog:
    """
    Catalog of A2L characteristics, record layouts, and conversion methods.
    Caches parsed A2L into SQLite .a2ldb for sub-second query latency.
    """

    def __init__(
        self,
        a2l_path: Path | str = DEFAULT_A2L_PATH,
        cache_dir: Path | str = DEFAULT_CACHE_DIR,
        encoding: str = "latin-1",
    ):
        self.a2l_path = Path(a2l_path)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        a2l_bytes = self.a2l_path.read_bytes()
        self.a2l_sha256 = hashlib.sha256(a2l_bytes).hexdigest()

        # Cache key based on content sha256 to guarantee invalidation upon file change
        content_cache_dir = self.cache_dir / self.a2l_sha256[:16]
        content_cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = content_cache_dir / (self.a2l_path.stem + ".a2ldb")

        if self.db_path.exists():
            logger.info("Opening existing A2L database: %s", self.db_path)
            self.session = pya2l.open_existing(str(self.db_path))
        else:
            logger.info("Importing A2L into SQLite database: %s -> %s", self.a2l_path, self.db_path)
            self.session = pya2l.import_a2l(
                str(self.a2l_path),
                output_dir=str(content_cache_dir),
                progress_bar=False,
                encoding=encoding,
                loglevel="WARNING",
            )

        self._converters: Dict[str, A2LConverter] = {}

    def get_characteristic(self, name: str) -> Optional[model.Characteristic]:
        """Lookup characteristic by exact name."""
        return (
            self.session.query(model.Characteristic)
            .filter(model.Characteristic.name == name)
            .first()
        )

    def get_compu_method(self, name: str) -> Optional[model.CompuMethod]:
        """Lookup CompuMethod by name."""
        return (
            self.session.query(model.CompuMethod)
            .filter(model.CompuMethod.name == name)
            .first()
        )

    def get_converter(self, compu_method_name: Optional[str]) -> A2LConverter:
        """
        Get or build an A2LConverter for a given CompuMethod.
        Returns identity converter only if name is None or empty.
        Raises KeyError if named CompuMethod is not found in A2L.
        Raises UnsupportedConversionError on unknown or unsupported types (no silent Identical).
        """
        if not compu_method_name:
            return A2LConverter("IDENTICAL", "", Identical())

        if compu_method_name in self._converters:
            return self._converters[compu_method_name]

        cm = self.get_compu_method(compu_method_name)
        if not cm:
            raise KeyError(f"CompuMethod '{compu_method_name}' not found in A2L catalog")

        unit = cm.unit or ""
        conv_type = getattr(cm, "conversionType", None) or getattr(cm, "conversion_type", "")

        if conv_type == "RAT_FUNC":
            c = getattr(cm, "coeffs", None)
            if not c:
                raise UnsupportedConversionError(
                    f"RAT_FUNC '{compu_method_name}' lacks required COEFFS definition"
                )
            coeffs_obj = Coeffs(a=c.a, b=c.b, c=c.c, d=c.d, e=c.e, f=c.f)
            func = RatFunc(coeffs_obj)
        elif conv_type == "LINEAR":
            cl = getattr(cm, "coeffs_linear", None)
            if not cl:
                raise UnsupportedConversionError(
                    f"LINEAR '{compu_method_name}' lacks required COEFFS_LINEAR definition"
                )
            func = Linear(a=cl.a, b=cl.b)
        elif conv_type == "IDENTICAL":
            func = Identical()
        else:
            raise UnsupportedConversionError(
                f"Unsupported COMPU_METHOD conversion type '{conv_type}' for '{compu_method_name}'. "
                "Silent Identical fallback is forbidden."
            )

        conv = A2LConverter(compu_method_name, unit, func)
        self._converters[compu_method_name] = conv
        return conv

    def search_names(self, pattern: str, limit: int = 50) -> List[str]:
        """Search characteristics matching SQL LIKE pattern (e.g. '%Smoke%')."""
        rows = (
            self.session.query(model.Characteristic.name)
            .filter(model.Characteristic.name.like(pattern))
            .limit(limit)
            .all()
        )
        return [r[0] for r in rows]
