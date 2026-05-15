"""
Sistema de mapeamento de interfaces entre vendors.

Cada vendor usa um vocabulário diferente para nomear portas. Este módulo
oferece um tradutor centralizado, com tabelas armazenadas em
`app/services/mapping_data.yaml` (editável pelo operador).
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

import yaml

from app.models import Vendor
from app.utils.logger import get_logger

log = get_logger(__name__)

_MAPPING_FILE = Path(__file__).resolve().parent / "mapping_data.yaml"


@lru_cache(maxsize=1)
def _load_mapping() -> dict:
    if not _MAPPING_FILE.exists():
        return {}
    with _MAPPING_FILE.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def reload_mapping() -> None:
    """Limpa o cache, útil em testes ou ao editar mapeamentos em runtime."""
    _load_mapping.cache_clear()


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------
Kind = Literal["auto", "uplink", "gpon", "onu"]


def map_interface(
    interface: str,
    src_vendor: Vendor,
    dst_vendor: Vendor,
    kind: Kind = "auto",
) -> str:
    """
    Traduz `interface` da nomenclatura `src_vendor` para `dst_vendor`.

    Estratégia:

    1. Se houver mapping explícito (vendor→vendor) no YAML, usa-o.
    2. Caso contrário, extrai os componentes (chassis/slot/port/onu) e
       remonta no padrão padrão do destino.
    3. Se o destino é o mesmo do source, retorna intocado.
    """
    if src_vendor == dst_vendor or not interface:
        return interface

    mapping = _load_mapping()
    explicit = (
        mapping.get(src_vendor.value, {})
        .get(dst_vendor.value, {})
        .get(interface)
    )
    if explicit:
        return explicit

    comps = _extract(interface)
    if not comps:
        return interface  # não conseguiu interpretar

    return _format_for_vendor(dst_vendor, kind, comps, interface)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------
_RE_GENERIC = re.compile(r"(\d+)/(\d+)/(\d+)(?::(\d+))?")
_RE_HUAWEI_SHORT = re.compile(r"(\d+)/(\d+)(?:/(\d+))?")


def _extract(raw: str) -> Optional[dict]:
    m = _RE_GENERIC.search(raw)
    if m:
        chassis, slot, port, onu = m.groups()
        return {
            "chassis": int(chassis),
            "slot": int(slot),
            "port": int(port),
            "onu": int(onu) if onu else None,
        }
    m = _RE_HUAWEI_SHORT.search(raw)
    if m:
        frame, slot, port = m.groups()
        return {
            "chassis": int(frame),
            "slot": int(slot),
            "port": int(port) if port else 0,
            "onu": None,
        }
    return None


def _format_for_vendor(vendor: Vendor, kind: Kind, c: dict, original: str) -> str:
    is_pon = kind == "gpon" or "pon" in original.lower() or "gpon" in original.lower()
    if vendor == Vendor.ZTE:
        if is_pon:
            return f"gpon_olt-{c['chassis']}/{c['slot']}/{c['port']}"
        return f"gei-{c['chassis']}/{c['slot']}/{c['port']}"
    if vendor == Vendor.HUAWEI:
        if is_pon:
            return f"gpon 0/{c['slot']}/{c['port']}"
        return f"0/{c['slot']}/{c['port']}"
    if vendor == Vendor.DATACOM:
        if is_pon:
            return f"gpon {c['chassis']}/{c['slot']}/{c['port']}"
        return f"ten-gigabit-ethernet {c['chassis']}/{c['slot']}/{c['port']}"
    if vendor == Vendor.FIBERHOME:
        if is_pon:
            return f"pon-{c['chassis']}/{c['slot']}/{c['port']}"
        return f"ge-{c['chassis']}/{c['slot']}/{c['port']}"
    return original
