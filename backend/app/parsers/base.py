"""
Base abstrata para todos os parsers de OLT.

Um parser concreto deve:

1. Implementar `parse(config_text) -> OLTConfig`.
2. Sobrescrever `vendor`, `model_family` e `confidence_signatures`.
3. (Opcional) sobrescrever `detect(config_text)` se houver heurística melhor.

A pipeline:

    raw config text  →  preprocess (limpar comentários, CRLF, indentação)
                     →  identify blocks (gpon, vlan, service-port, …)
                     →  populate OLTConfig
                     →  return ParserResult
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar

from app.models import OLTConfig, Vendor
from app.utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class ParserResult:
    """Resultado de uma operação de parsing."""

    config: OLTConfig
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    unparsed_lines: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


class BaseParser(ABC):
    """Contrato comum dos parsers."""

    vendor: ClassVar[Vendor] = Vendor.UNKNOWN
    model_family: ClassVar[str] = ""
    confidence_signatures: ClassVar[tuple[str, ...]] = ()

    # ------------------------------------------------------------------ API
    @abstractmethod
    def parse(self, config_text: str) -> ParserResult:
        """Recebe a config bruta e retorna um `OLTConfig` populado."""
        raise NotImplementedError

    # ------------------------------------------------------------------ Util
    @classmethod
    def detect(cls, config_text: str) -> float:
        """
        Retorna um score 0..1 indicando a probabilidade desta config
        pertencer a este parser. A implementação padrão conta quantas
        assinaturas (`confidence_signatures`) aparecem no texto.
        """
        if not cls.confidence_signatures:
            return 0.0
        text = config_text.lower()
        hits = sum(1 for sig in cls.confidence_signatures if sig.lower() in text)
        return hits / len(cls.confidence_signatures)

    # ------------------------------------------------------------------ Repr
    def __repr__(self) -> str:  # pragma: no cover
        return f"<{type(self).__name__} vendor={self.vendor.value} model={self.model_family}>"
