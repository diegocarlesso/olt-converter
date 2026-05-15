"""
Registro central de parsers + detecção automática de vendor.

Uso típico:

    >>> parser_cls = detect_vendor(raw_text)
    >>> result = parser_cls().parse(raw_text)
"""
from __future__ import annotations

from typing import Type

from app.models import Vendor
from app.parsers.base import BaseParser
from app.utils.logger import get_logger

log = get_logger(__name__)


_PARSERS: dict[Vendor, Type[BaseParser]] = {}


def register_parser(cls: Type[BaseParser]) -> Type[BaseParser]:
    """Decorator usado pelos módulos de parser para se registrarem."""
    if cls.vendor in _PARSERS:
        log.warning("parser_already_registered", vendor=cls.vendor.value)
    _PARSERS[cls.vendor] = cls
    return cls


def parser_registry() -> dict[Vendor, Type[BaseParser]]:
    """Retorna uma cópia do registro atual."""
    return dict(_PARSERS)


def get_parser(vendor: Vendor | str) -> Type[BaseParser]:
    """Obtém o parser pelo vendor enum/string."""
    if isinstance(vendor, str):
        vendor = Vendor(vendor.lower())
    if vendor not in _PARSERS:
        raise KeyError(f"Nenhum parser registrado para vendor={vendor}")
    return _PARSERS[vendor]


def detect_vendor(config_text: str) -> Type[BaseParser]:
    """
    Roda `.detect()` em todos os parsers registrados e retorna aquele de
    maior score. Se ninguém pontuar, levanta ValueError.
    """
    best: tuple[float, Type[BaseParser] | None] = (0.0, None)
    scores: dict[str, float] = {}
    for vendor, cls in _PARSERS.items():
        score = cls.detect(config_text)
        scores[vendor.value] = score
        if score > best[0]:
            best = (score, cls)
    log.info("vendor_detection", scores=scores)
    if best[1] is None or best[0] == 0.0:
        raise ValueError("Não foi possível detectar o vendor da configuração.")
    return best[1]


# ---------------------------------------------------------------------------
# Auto-import dos parsers concretos para popular o registro
# ---------------------------------------------------------------------------
def _autoload() -> None:
    # imports tardios para evitar ciclos
    from app.parsers.fiberhome.an5516 import parser as _fh  # noqa: F401
    from app.parsers.zte.c600 import parser as _zte  # noqa: F401
    from app.parsers.huawei.ma5800 import parser as _huawei  # noqa: F401
    from app.parsers.datacom.dm4615 import parser as _dm  # noqa: F401


_autoload()
