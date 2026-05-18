"""
Modelo de proveniência (provenance) e nível de confiança.

Toda entidade que pode nascer de mais de uma fonte (parser direto, inferência
heurística, síntese a partir de outras entidades, edição manual, default
imposto) carrega um objeto `Provenance` para que o operador possa auditar,
revisar e corrigir.

Princípios:

* Nada de "default silencioso" — qualquer fallback é marcado com
  `source=DEFAULT` e tipicamente `confidence < 0.3`.
* Cada peça de evidência usada para inferir um binding/profile é registrada
  em `Provenance.signals` — o operador vê EXATAMENTE por que o sistema
  acredita naquilo.
* `origin_files` permite multi-file import: uma mesma entidade pode ter
  surgido em mais de um arquivo do operador.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import Field

from app.models.base import DomainModel


class ProvenanceSource(str, Enum):
    """De onde veio essa entidade?"""

    PARSER = "parser"            # extraída diretamente do CLI bruto
    INFERENCE = "inference"      # inferida combinando múltiplos sinais
    SYNTHESIS = "synthesis"      # sintetizada a partir de outras entidades
    PROMOTION = "promotion"      # promovida de extra_vendor -> modelo formal L9
    MANUAL = "manual"            # editada pelo operador no editor visual
    DEFAULT = "default"          # fallback explícito (operador deve revisar)
    IMPORT = "import"            # veio de arquivo complementar (servport dump etc.)


class Provenance(DomainModel):
    """
    Bloco de metadado anexado a uma entidade para registrar como ela foi
    obtida.
    """

    source: ProvenanceSource = ProvenanceSource.PARSER
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    reason: Optional[str] = Field(
        None,
        description="Explicação humana sobre como o valor foi obtido",
    )
    signals: list[str] = Field(
        default_factory=list,
        description="Lista textual dos sinais que sustentam a inferência",
    )
    origin_files: list[str] = Field(
        default_factory=list,
        description="Quais arquivos contribuíram para esta entidade",
    )
    needs_review: bool = Field(
        default=False,
        description="True quando o operador precisa confirmar/editar manualmente",
    )

    @classmethod
    def parsed(cls, origin_file: Optional[str] = None) -> "Provenance":
        return cls(
            source=ProvenanceSource.PARSER,
            confidence=1.0,
            origin_files=[origin_file] if origin_file else [],
        )

    @classmethod
    def inferred(
        cls,
        confidence: float,
        reason: str,
        signals: list[str],
        origin_file: Optional[str] = None,
    ) -> "Provenance":
        return cls(
            source=ProvenanceSource.INFERENCE,
            confidence=confidence,
            reason=reason,
            signals=signals,
            origin_files=[origin_file] if origin_file else [],
            needs_review=confidence < 0.7,
        )

    @classmethod
    def synthetic(
        cls,
        confidence: float,
        reason: str,
        signals: Optional[list[str]] = None,
    ) -> "Provenance":
        return cls(
            source=ProvenanceSource.SYNTHESIS,
            confidence=confidence,
            reason=reason,
            signals=signals or [],
            needs_review=True,
        )

    @classmethod
    def default_fallback(cls, reason: str) -> "Provenance":
        return cls(
            source=ProvenanceSource.DEFAULT,
            confidence=0.15,
            reason=reason,
            needs_review=True,
        )

    @classmethod
    def promoted(
        cls,
        confidence: float,
        reason: str,
        signals: Optional[list[str]] = None,
    ) -> "Provenance":
        return cls(
            source=ProvenanceSource.PROMOTION,
            confidence=confidence,
            reason=reason,
            signals=signals or [],
            needs_review=confidence < 0.7,
        )


__all__ = ["Provenance", "ProvenanceSource"]
