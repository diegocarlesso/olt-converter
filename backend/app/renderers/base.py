"""
Base abstrata para renderers (modelo interno → CLI vendor-specific).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from app.models import OLTConfig, Vendor
from app.utils.logger import get_logger

log = get_logger(__name__)

# A pasta templates/ vive em app/templates
_TEMPLATES_BASE = Path(__file__).resolve().parent.parent / "templates"


class BaseRenderer(ABC):
    """Contrato comum dos renderers."""

    vendor: ClassVar[Vendor] = Vendor.UNKNOWN
    model_family: ClassVar[str] = ""
    template_dir: ClassVar[str] = ""  # ex: "zte/c600"

    def __init__(self) -> None:
        path = _TEMPLATES_BASE / self.template_dir
        self.env = Environment(
            loader=FileSystemLoader(str(path)),
            autoescape=select_autoescape([]),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )
        # Filtros úteis disponíveis em todos os templates
        self.env.filters["safe_name"] = lambda v: (v or "").replace(" ", "_")

    @abstractmethod
    def render(self, config: OLTConfig) -> str:
        """Recebe um `OLTConfig` e gera a config CLI completa do vendor."""
        raise NotImplementedError

    # ---------------- helpers
    def _render(self, template_name: str, **context) -> str:
        """Renderiza um template do diretório do renderer."""
        tpl = self.env.get_template(template_name)
        return tpl.render(**context)

    def _join(self, *blocks: str) -> str:
        """Junta blocos de saída garantindo quebras de linha consistentes."""
        return "\n".join(b.rstrip("\n") for b in blocks if b and b.strip()) + "\n"
