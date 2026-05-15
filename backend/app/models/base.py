"""
Base abstrata para todos os modelos Pydantic do domínio.

- `extra="allow"` mantém qualquer campo proprietário do vendor sem perdê-lo,
  útil para round-trip e auditoria.
- `validate_assignment=True` revalida ao reatribuir campos (necessário para
  edição estruturada na UI).
- `populate_by_name=True` permite popular tanto pelo nome quanto por alias,
  facilitando integração com payloads externos.
"""
from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, ConfigDict


class DomainModel(BaseModel):
    """Base de todos os modelos do domínio OLT."""

    model_config = ConfigDict(
        extra="allow",
        validate_assignment=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class StableID(BaseModel):
    """
    Identificador estável usado por entidades que precisam ser referenciadas
    cross-entity (ex: ServicePort → ONU → LineProfile).

    Compõe-se de um par (vendor_id, kind) que permite ao motor de equivalência
    rastrear bindings entre vendors.
    """

    model_config = ConfigDict(frozen=True)

    kind: str               # ex: "onu", "line-profile", "tcont", "gemport"
    vendor_id: str          # representação textual do id no vendor original

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.kind}:{self.vendor_id}"


__all__ = ["DomainModel", "StableID"]
