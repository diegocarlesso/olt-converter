"""
Rotas HTTP da API.

Endpoints:
  POST /upload      → recebe arquivo, retorna texto cru + vendor detectado
  POST /parse       → parse text → OLTConfig
  POST /render      → OLTConfig → CLI destino
  POST /convert     → pipeline completa (text → text)
  POST /validate    → roda validador em um OLTConfig
  GET  /vendors     → lista vendors + parsers/renderers disponíveis
  GET  /models      → lista modelos suportados por vendor
"""
from __future__ import annotations

import io

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from typing import List

from app.api.schemas import (
    ConvertRequest,
    ConvertResponse,
    ParseRequest,
    ParseResponse,
    RenderRequest,
    RenderResponse,
    ValidateRequest,
    VendorInfo,
)
from app.models import OLTConfig, Vendor
from app.parsers import detect_vendor, parser_registry
from app.renderers import get_renderer, renderer_registry
from app.services.compatibility import (
    cell as compat_cell,
    conversion_score,
    FEATURES as COMPAT_FEATURES,
    matrix as compat_matrix,
    vendor_scores,
)
from app.services.conversion import convert, make_diff, parse_config
from app.services.remapping import remap_for
from app.services.validator import validate_config
from app.utils.logger import get_logger

router = APIRouter()
log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------
@router.get("/vendors", response_model=list[VendorInfo])
def list_vendors() -> list[VendorInfo]:
    parsers = parser_registry()
    renderers = renderer_registry()
    seen = set(parsers) | set(renderers)
    out: list[VendorInfo] = []
    for vendor in sorted(seen, key=lambda v: v.value):
        models: list[str] = []
        if vendor in parsers:
            models.append(parsers[vendor].model_family)
        if vendor in renderers and renderers[vendor].model_family not in models:
            models.append(renderers[vendor].model_family)
        out.append(
            VendorInfo(
                vendor=vendor,
                models=models,
                has_parser=vendor in parsers,
                has_renderer=vendor in renderers,
            )
        )
    return out


@router.get("/models/{vendor}")
def list_models(vendor: Vendor) -> dict:
    parsers = parser_registry()
    renderers = renderer_registry()
    models = []
    if vendor in parsers:
        models.append(parsers[vendor].model_family)
    if vendor in renderers:
        models.append(renderers[vendor].model_family)
    return {"vendor": vendor.value, "models": sorted(set(models))}


# ---------------------------------------------------------------------------
# Remapping (dry-run)
# ---------------------------------------------------------------------------
@router.post("/remap/dry-run")
def remap_dry_run(config: OLTConfig, target_vendor: Vendor, target_model: str | None = None) -> dict:
    """
    Retorna a tabela de remap (old_id → new_id por categoria) sem aplicar.
    Útil para a UI exibir o plano antes da conversão.
    """
    _, table = remap_for(config, target_vendor, target_model, apply=False)
    return table.to_dict()


# ---------------------------------------------------------------------------
# Compatibility Matrix
# ---------------------------------------------------------------------------
@router.get("/compatibility/matrix")
def compatibility_matrix(feature: str | None = None) -> dict:
    """Retorna a matriz completa de compatibilidade vendor×vendor×feature."""
    feats = [feature] if feature else None
    return {"features": COMPAT_FEATURES, "matrix": compat_matrix(feats)}


@router.get("/compatibility/score")
def compatibility_score(source: Vendor, target: Vendor) -> dict:
    """Retorna semantic_fidelity_score + contagem FULL/PARTIAL/NONE de um par."""
    return {
        "source": source.value,
        "target": target.value,
        "score": conversion_score(source, target),
    }


@router.get("/compatibility/vendor/{vendor}")
def compatibility_vendor(vendor: Vendor) -> dict:
    """parser_coverage_score + renderer_completeness_score de um vendor."""
    return {"vendor": vendor.value, **vendor_scores(vendor)}


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------
@router.post("/upload")
async def upload(file: UploadFile = File(...)) -> dict:
    """Recebe um arquivo .txt/.cfg, retorna texto e vendor detectado."""
    content = (await file.read()).decode("utf-8", errors="replace")
    try:
        parser_cls = detect_vendor(content)
        vendor = parser_cls.vendor.value
        model = parser_cls.model_family
        confidence = parser_cls.detect(content)
    except ValueError:
        vendor = Vendor.UNKNOWN.value
        model = ""
        confidence = 0.0
    return {
        "filename": file.filename,
        "size": len(content),
        "vendor": vendor,
        "model": model,
        "confidence": confidence,
        "content": content,
    }


# ---------------------------------------------------------------------------
# Multi-file merge (import complementar)
# ---------------------------------------------------------------------------
@router.post("/merge")
async def merge_endpoint(files: List[UploadFile] = File(...)) -> dict:
    """
    Recebe múltiplos arquivos CLI complementares e devolve um único OLTConfig
    mesclado, com proveniência preservada por entidade.

    Use para combinar:
      - backup principal
      - dump de service-ports / gpononu servport
      - ONU running config
      - bridge table

    Cada arquivo é parseado independentemente, depois mesclado por chave
    natural (VLAN.id, ONU.(pon,id), Profile.name, etc.). Em caso de
    duplicidade com valores divergentes, é gerado warning.
    """
    from app.services.merger import merge_configs

    configs = []
    labels = []
    for f in files:
        content = (await f.read()).decode("utf-8", errors="replace")
        try:
            res = parse_config(content)
        except ValueError as exc:
            log.warning("merge_skip_file", file=f.filename, error=str(exc))
            continue
        configs.append(res.config)
        labels.append(f.filename or "upload")

    if not configs:
        raise HTTPException(
            status_code=400,
            detail="Nenhum arquivo pôde ser parseado.",
        )

    merged = merge_configs(configs, labels)
    return {
        "files_merged": labels,
        "stats": merged.stats(),
        "config": merged.model_dump(),
    }


# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------
@router.post("/parse", response_model=ParseResponse)
def parse_endpoint(req: ParseRequest) -> ParseResponse:
    if not req.config_text or not req.config_text.strip():
        raise HTTPException(status_code=400, detail="config_text vazio")
    try:
        result = parse_config(req.config_text, req.vendor)
    except ValueError as exc:
        log.warning("parse_value_error", error=str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        log.warning("parse_unknown_vendor", error=str(exc))
        raise HTTPException(
            status_code=400,
            detail=f"Vendor não suportado: {exc}",
        ) from exc
    except Exception as exc:  # noqa: BLE001
        log.exception("parse_internal_error")
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno no parser: {type(exc).__name__}: {exc}",
        ) from exc
    config = result.config
    return ParseResponse(
        detected_vendor=config.vendor,
        model=config.model,
        hostname=config.hostname,
        config=config,
        warnings=result.warnings,
        unparsed_lines=result.unparsed_lines,
        stats=config.stats(),
    )


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
@router.post("/render", response_model=RenderResponse)
def render_endpoint(req: RenderRequest) -> RenderResponse:
    try:
        renderer = get_renderer(req.target_vendor)()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    rendered = renderer.render(req.config)
    return RenderResponse(target_vendor=req.target_vendor, rendered_config=rendered)


# ---------------------------------------------------------------------------
# Convert (pipeline completa)
# ---------------------------------------------------------------------------
@router.post("/convert", response_model=ConvertResponse)
def convert_endpoint(req: ConvertRequest) -> ConvertResponse:
    if not req.config_text and not req.config:
        raise HTTPException(
            status_code=400, detail="Informe `config_text` ou `config`."
        )

    if req.config_text:
        try:
            result = convert(
                req.config_text,
                target_vendor=req.target_vendor,
                source_vendor=req.source_vendor,
            )
        except ValueError as exc:
            log.warning("convert_value_error", error=str(exc))
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except KeyError as exc:
            log.warning("convert_unknown_vendor", error=str(exc))
            raise HTTPException(status_code=400, detail=f"Vendor não suportado: {exc}") from exc
        except Exception as exc:  # noqa: BLE001
            log.exception("convert_internal_error")
            raise HTTPException(
                status_code=500,
                detail=f"Erro interno na conversão: {type(exc).__name__}: {exc}",
            ) from exc
        original = req.config_text
    else:
        # já temos um OLTConfig pronto
        try:
            renderer = get_renderer(req.target_vendor)()
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        rendered = renderer.render(req.config)  # type: ignore[arg-type]
        report = validate_config(req.config)    # type: ignore[arg-type]
        return ConvertResponse(
            source_vendor=req.config.vendor if req.config else Vendor.UNKNOWN,  # type: ignore[union-attr]
            target_vendor=req.target_vendor,
            rendered_config=rendered,
            diff="",
            validation=report.to_dict(),
            warnings=[],
            unparsed_lines=[],
            stats=req.config.stats() if req.config else {},  # type: ignore[union-attr]
        )

    diff = make_diff(
        original,
        result.rendered,
        label_a=f"{result.source_vendor.value}/source",
        label_b=f"{result.target_vendor.value}/target",
    )
    return ConvertResponse(
        source_vendor=result.source_vendor,
        target_vendor=result.target_vendor,
        rendered_config=result.rendered,
        diff=diff,
        validation=result.validation.to_dict(),
        warnings=result.parser_warnings,
        unparsed_lines=result.unparsed_lines,
        stats=result.config.stats(),
    )


# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------
@router.post("/validate")
def validate_endpoint(req: ValidateRequest) -> dict:
    report = validate_config(req.config)
    return report.to_dict()


# ---------------------------------------------------------------------------
# Export (download)
# ---------------------------------------------------------------------------
@router.post("/export/{target_vendor}", response_class=PlainTextResponse)
def export_endpoint(target_vendor: Vendor, config: OLTConfig) -> PlainTextResponse:
    try:
        renderer = get_renderer(target_vendor)()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    rendered = renderer.render(config)
    filename = f"{config.hostname or 'olt'}-{target_vendor.value}.cfg"
    return PlainTextResponse(
        rendered,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
