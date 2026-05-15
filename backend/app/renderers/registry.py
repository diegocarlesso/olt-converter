"""Registro central de renderers."""
from __future__ import annotations

from typing import Type

from app.models import Vendor
from app.renderers.base import BaseRenderer
from app.utils.logger import get_logger

log = get_logger(__name__)

_RENDERERS: dict[Vendor, Type[BaseRenderer]] = {}


def register_renderer(cls: Type[BaseRenderer]) -> Type[BaseRenderer]:
    """Decorator usado por cada renderer concreto."""
    if cls.vendor in _RENDERERS:
        log.warning("renderer_already_registered", vendor=cls.vendor.value)
    _RENDERERS[cls.vendor] = cls
    return cls


def renderer_registry() -> dict[Vendor, Type[BaseRenderer]]:
    return dict(_RENDERERS)


def get_renderer(vendor: Vendor | str) -> Type[BaseRenderer]:
    if isinstance(vendor, str):
        vendor = Vendor(vendor.lower())
    if vendor not in _RENDERERS:
        raise KeyError(f"Nenhum renderer registrado para vendor={vendor}")
    return _RENDERERS[vendor]


def _autoload() -> None:
    from app.renderers.zte.c600 import renderer as _zte  # noqa: F401
    from app.renderers.huawei.ma5800 import renderer as _huawei  # noqa: F401
    from app.renderers.datacom.dm4615 import renderer as _dm  # noqa: F401
    from app.renderers.fiberhome.an5516 import renderer as _fh  # noqa: F401


_autoload()
