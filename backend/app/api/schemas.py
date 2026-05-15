"""
Schemas de request/response da API.

Mantenha estes schemas distintos do modelo interno: assim a representação
externa pode evoluir sem quebrar parsers/renderers e vice-versa.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.models import OLTConfig, Vendor


class ParseRequest(BaseModel):
    config_text: str = Field(..., description="Configuração CLI bruta")
    vendor: Optional[Vendor] = Field(
        None, description="Vendor da origem; se ausente, detecção automática"
    )


class ParseResponse(BaseModel):
    detected_vendor: Vendor
    model: str
    hostname: str
    config: OLTConfig
    warnings: list[str] = Field(default_factory=list)
    unparsed_lines: list[str] = Field(default_factory=list)
    stats: dict[str, int] = Field(default_factory=dict)


class ConvertRequest(BaseModel):
    config_text: Optional[str] = Field(
        None, description="Config CLI bruta (origem). Use config OU config_text."
    )
    config: Optional[OLTConfig] = Field(
        None, description="Modelo universal já parseado (alternativa a config_text)"
    )
    source_vendor: Optional[Vendor] = None
    target_vendor: Vendor
    target_model: Optional[str] = None


class ConvertResponse(BaseModel):
    source_vendor: Vendor
    target_vendor: Vendor
    rendered_config: str
    diff: str
    validation: dict
    warnings: list[str] = Field(default_factory=list)
    unparsed_lines: list[str] = Field(default_factory=list)
    stats: dict[str, int] = Field(default_factory=dict)


class RenderRequest(BaseModel):
    config: OLTConfig
    target_vendor: Vendor


class RenderResponse(BaseModel):
    target_vendor: Vendor
    rendered_config: str


class ValidateRequest(BaseModel):
    config: OLTConfig


class VendorInfo(BaseModel):
    vendor: Vendor
    models: list[str]
    has_parser: bool
    has_renderer: bool
