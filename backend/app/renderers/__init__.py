"""Renderers modulares por vendor/modelo.

Renderers consomem um `OLTConfig` (modelo universal) e produzem CLI
específico do vendor destino, usando templates Jinja2.
"""
from app.renderers.base import BaseRenderer
from app.renderers.registry import get_renderer, renderer_registry

__all__ = ["BaseRenderer", "get_renderer", "renderer_registry"]
