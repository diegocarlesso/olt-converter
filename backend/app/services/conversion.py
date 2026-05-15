"""
Pipeline principal de conversão:

  raw config (str) → parse → OLTConfig → render → CLI destino (str)

Também expõe uma função utilitária para gerar um "diff legível" entre origem e
destino para uso no Monaco Diff Editor.
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass

from app.models import OLTConfig, Vendor
from app.parsers import detect_vendor, get_parser
from app.parsers.base import ParserResult
from app.renderers import get_renderer
from app.services.equivalence import harmonize_for
from app.services.inference import infer_service_ports
from app.services.remapping import RemappingTable, remap_for
from app.services.synthesis import synthesize_dba_profiles, synthesize_traffic_profiles
from app.services.validator import validate_config, ValidationReport


@dataclass
class ConversionResult:
    source_vendor: Vendor
    target_vendor: Vendor
    config: OLTConfig
    rendered: str
    validation: ValidationReport
    parser_warnings: list[str]
    unparsed_lines: list[str]
    remapping_table: RemappingTable | None = None


def parse_config(raw_text: str, vendor: Vendor | str | None = None) -> ParserResult:
    """
    Parse uma config CLI bruta. Se `vendor` for None, "unknown" ou string
    vazia, faz detecção automática. Se o vendor pedido não tiver parser
    registrado, também cai em detecção automática como fallback.
    """
    parser_cls = None

    if vendor:
        # Normaliza string para Vendor enum
        try:
            if isinstance(vendor, str):
                vendor_enum = Vendor(vendor.lower())
            else:
                vendor_enum = vendor
        except ValueError:
            vendor_enum = Vendor.UNKNOWN

        if vendor_enum != Vendor.UNKNOWN:
            try:
                parser_cls = get_parser(vendor_enum)
            except KeyError:
                parser_cls = None  # cai no auto-detect abaixo

    if parser_cls is None:
        parser_cls = detect_vendor(raw_text)

    parser = parser_cls()
    return parser.parse(raw_text)


def convert(
    raw_text: str,
    target_vendor: Vendor | str,
    source_vendor: Vendor | str | None = None,
) -> ConversionResult:
    """Pipeline completa de conversão de uma config CLI para outro vendor."""
    if isinstance(target_vendor, str):
        target_vendor = Vendor(target_vendor.lower())
    if isinstance(source_vendor, str):
        source_vendor = Vendor(source_vendor.lower())

    parse_result = parse_config(raw_text, source_vendor)
    config = parse_result.config

    # Pipeline em etapas, cada uma marcada com proveniência:
    #   1) inferência de service-ports faltantes (Provenance.INFERENCE)
    inferred = infer_service_ports(config)

    #   2) síntese de DBA / Traffic profiles ausentes (Provenance.SYNTHESIS)
    synthesized = synthesize_dba_profiles(inferred)
    synthesized = synthesize_traffic_profiles(synthesized)

    #   3) equivalência semântica para o vendor destino
    harmonized = harmonize_for(synthesized, target_vendor)

    #   4) ID remapping (determinístico) — ajusta IDs aos ranges do destino
    remapped, remap_table = remap_for(harmonized, target_vendor)

    #   5) validação sobre o config remapped
    report = validate_config(remapped)

    #   6) render
    renderer = get_renderer(target_vendor)()
    rendered = renderer.render(remapped)

    return ConversionResult(
        source_vendor=config.vendor,
        target_vendor=target_vendor,
        config=remapped,
        rendered=rendered,
        validation=report,
        parser_warnings=parse_result.warnings,
        unparsed_lines=parse_result.unparsed_lines,
        remapping_table=remap_table,
    )


def make_diff(a: str, b: str, label_a: str = "source", label_b: str = "target") -> str:
    """Gera unified diff entre dois textos (compatível com Monaco)."""
    return "".join(
        difflib.unified_diff(
            a.splitlines(keepends=True),
            b.splitlines(keepends=True),
            fromfile=label_a,
            tofile=label_b,
        )
    )
