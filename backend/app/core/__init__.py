"""
Semantic Runtime Core — Bounded Context L1 (FROZEN)

Este módulo é a facade pública do núcleo semântico estabilizado.
Todo o código existente em app/parsers, app/models, app/services e app/renderers
permanece intocado. Esta facade expõe contratos claros para as camadas superiores
(Deployment Orchestrator, Engineering Workspace).

Princípio: CORE FREEZE.
- Nenhuma alteração de shape nos modelos L1.
- Nenhuma alteração de contrato nos parsers/renderers.
- Extensões acontecem APENAS nas camadas superiores.

Contratos exportados:
  - SemanticParser: parse raw CLI → OLTConfig
  - SemanticRenderer: OLTConfig → CLI text
  - SemanticValidator: OLTConfig → ValidationReport
  - SemanticSession: runtime de edição semântica
  - ConversionPipeline: pipeline completa text→text
  - CompatibilityInspector: matriz de compatibilidade
"""
from __future__ import annotations

from typing import Optional

from app.models import OLTConfig, Vendor
from app.models.provenance import Provenance, ProvenanceSource
from app.parsers.base import ParserResult
from app.services.conversion import ConversionResult, convert, make_diff, parse_config
from app.services.compatibility import (
    CompatibilityCell,
    FEATURES as COMPAT_FEATURES,
    cell as compat_cell,
    conversion_score,
    matrix as compat_matrix,
    vendor_scores,
)
from app.services.remapping import RemappingTable, remap_for
from app.services.validator import ValidationReport, validate_config
from app.services.session import (
    SessionRuntime,
    create_session,
    get_session,
    drop_session,
    list_sessions,
)


class SemanticRuntimeCore:
    """
    Facade do Semantic Runtime Core (L1).

    Ponto único de acesso para camadas superiores.
    Nenhuma lógica nova aqui — apenas delegação disciplinada.
    """

    # ── Parsing ──────────────────────────────────────────────────────────
    @staticmethod
    def parse(raw_text: str, vendor: Optional[Vendor] = None) -> ParserResult:
        """Parse CLI bruto → OLTConfig via detecção automática ou vendor explícito."""
        return parse_config(raw_text, vendor)

    # ── Conversion ───────────────────────────────────────────────────────
    @staticmethod
    def convert(
        raw_text: str,
        target_vendor: Vendor,
        source_vendor: Optional[Vendor] = None,
    ) -> ConversionResult:
        """Pipeline completa: raw CLI → parse → enrich → remap → render."""
        return convert(raw_text, target_vendor=target_vendor, source_vendor=source_vendor)

    # ── Validation ───────────────────────────────────────────────────────
    @staticmethod
    def validate(config: OLTConfig) -> ValidationReport:
        """Roda todos os validadores semânticos sobre um OLTConfig."""
        return validate_config(config)

    # ── Remapping ────────────────────────────────────────────────────────
    @staticmethod
    def remap(
        config: OLTConfig,
        target_vendor: Vendor,
        target_model: Optional[str] = None,
        apply: bool = True,
    ) -> tuple[OLTConfig, RemappingTable]:
        """Remapeia IDs para o range do vendor destino."""
        return remap_for(config, target_vendor, target_model, apply)

    # ── Diff ─────────────────────────────────────────────────────────────
    @staticmethod
    def diff(a: str, b: str, label_a: str = "source", label_b: str = "target") -> str:
        """Gera unified diff entre dois textos."""
        return make_diff(a, b, label_a, label_b)

    # ── Compatibility ────────────────────────────────────────────────────
    @staticmethod
    def compatibility_matrix(features: Optional[list[str]] = None) -> dict:
        """Matriz vendor×vendor×feature."""
        return compat_matrix(features)

    @staticmethod
    def compatibility_score(source: Vendor, target: Vendor) -> dict:
        """Score de fidelidade semântica para um par."""
        return conversion_score(source, target)

    @staticmethod
    def compatibility_cell(source: Vendor, target: Vendor, feature: str) -> CompatibilityCell:
        """Célula individual da matriz."""
        return compat_cell(source, target, feature)

    @staticmethod
    def vendor_maturity(vendor: Vendor) -> dict:
        """Parser/renderer coverage scores de um vendor."""
        return vendor_scores(vendor)

    # ── Sessions ─────────────────────────────────────────────────────────
    @staticmethod
    def create_session(raw_text: str, vendor: Optional[Vendor] = None) -> SessionRuntime:
        return create_session(raw_text, vendor)

    @staticmethod
    def get_session(session_id: str) -> Optional[SessionRuntime]:
        return get_session(session_id)

    @staticmethod
    def drop_session(session_id: str) -> bool:
        return drop_session(session_id)

    @staticmethod
    def list_sessions() -> list[dict]:
        return list_sessions()

    # ── Metadata ─────────────────────────────────────────────────────────
    @staticmethod
    def features() -> tuple[str, ...]:
        """Lista de features cobertas pela compatibility matrix."""
        return COMPAT_FEATURES

    @staticmethod
    def provenance_sources() -> list[str]:
        """Fontes de proveniência suportadas."""
        return [s.value for s in ProvenanceSource]


__all__ = ["SemanticRuntimeCore"]
