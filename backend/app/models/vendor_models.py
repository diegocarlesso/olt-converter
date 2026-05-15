"""
Modelos auxiliares específicos por vendor.

Use este módulo para guardar estruturas que NÃO encaixam no modelo
universal (ex: comandos proprietários, atributos exclusivos de firmware).
Os parsers podem anexar instâncias destes modelos via `OLTConfig.model_extra`.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class FiberhomeBoard(BaseModel):
    slot: int
    board_type: str
    enabled: bool = True


class ZTECardSlot(BaseModel):
    rack: int = 1
    shelf: int = 1
    slot: int
    card_type: str


class HuaweiBoard(BaseModel):
    frame: int = 0
    slot: int
    card_type: str
    description: Optional[str] = None


class DatacomBoard(BaseModel):
    chassis: int = 1
    slot: int
    card_type: str
