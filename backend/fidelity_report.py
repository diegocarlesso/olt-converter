"""
Fidelity Report — analytics operacionalmente auditáveis.

Roda o pipeline real (parser → inferência → síntese → equivalência → remap →
render) contra os backups em `modelos-config/` e `examples/`, e produz
`docs/FIDELITY_REPORT.md` com seções analíticas para calibração da matriz de
compatibilidade:

  1. Sumário por arquivo
  2. Top unsupported commands (raw_unparsed normalizados)
  3. Top partially mapped entities (needs_review=True)
  4. Top ambiguous bindings (confidence < 0.6)
  5. Top inferred relationships (cobertura da inferência)
  6. Per-feature confidence histogram
  7. Vendor/model heatmap
  8. Exemplos renderizados de cada par origem→destino

Uso:

    cd olt-converter/backend
    .venv\\Scripts\\activate
    python fidelity_report.py
    python fidelity_report.py --json --print    # debug
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.models import OLTConfig, Provenance, Vendor  # noqa: E402
from app.parsers import detect_vendor                  # noqa: E402
from app.services.compatibility import (               # noqa: E402
    FEATURES,
    cell as compat_cell,
    conversion_score,
    matrix as compat_matrix,
    vendor_scores,
)
from app.services.conversion import convert, parse_config  # noqa: E402
from app.services.inference import infer_service_ports     # noqa: E402
from app.services.synthesis import (                       # noqa: E402
    synthesize_dba_profiles,
    synthesize_traffic_profiles,
)
from app.services.validator import validate_config         # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
EXAMPLES = ROOT / "examples"

VENDORS = [Vendor.FIBERHOME, Vendor.HUAWEI, Vendor.ZTE, Vendor.DATACOM]


def discover_real_backups() -> list[Path]:
    """
    Procura backups reais em vários lugares plausíveis (em ordem):
      1. <repo_root>/modelos-config/*.txt
      2. <workspace_parent>/modelos-config/*.txt   (E:\\OLT CONFIG CONVERTER ENGINE\\modelos-config)
      3. <workspace_grandparent>/modelos-config/*.txt
      4. <workspace_parent>/*.txt                   (.txt soltos no workspace, comum em Cowork)
      5. variável de ambiente OLT_BACKUPS
    Dedup por nome de arquivo.
    """
    import os
    candidates: list[Path] = []

    # 1
    p = ROOT / "modelos-config"
    if p.exists():
        candidates.extend(sorted(p.glob("*.txt")))
    # 2
    p = ROOT.parent / "modelos-config"
    if p.exists():
        candidates.extend(sorted(p.glob("*.txt")))
    # 3
    p = ROOT.parent.parent / "modelos-config"
    if p.exists():
        candidates.extend(sorted(p.glob("*.txt")))
    # 4 — .txt soltos no workspace pai (caso comum no Cowork)
    p = ROOT.parent
    if p.exists():
        for f in p.glob("*.txt"):
            name = f.name.lower()
            if "readme" in name or "license" in name or "todo" in name:
                continue
            candidates.append(f)
    # 5
    env_path = os.environ.get("OLT_BACKUPS")
    if env_path:
        ep = Path(env_path)
        if ep.is_dir():
            candidates.extend(sorted(ep.glob("*.txt")))

    seen: set[str] = set()
    unique: list[Path] = []
    for f in candidates:
        if f.name not in seen:
            seen.add(f.name)
            unique.append(f)
    return unique


# ---------------------------------------------------------------------------
# Normalização para "top unsupported commands"
# ---------------------------------------------------------------------------
_TOKEN_NUM = re.compile(r"\b\d+\b")
_TOKEN_PATH = re.compile(r"\b\d+(?:/\d+){1,3}\b")
_TOKEN_HEX = re.compile(r"\b(?:[0-9a-fA-F]{8,})\b")
_TOKEN_QUOTED = re.compile(r"\"[^\"]+\"")
_TOKEN_SERIAL = re.compile(r"\b[A-Z]{2,5}[0-9a-fA-F]{6,}\b")


def normalize_command(line: str) -> str:
    """
    Reduz uma linha a um *padrão de comando* agrupável.

    Exemplos:
      "set white phy addr FHTT04c6ba10 pas null ac add sl 1 p 5 o 26 ty 5506-04-F1"
        → "set white phy addr <SN> pas <ID> ac add sl <N> p <N> o <N> ty <ID>"
      "interface gpon 0/1/2"
        → "interface gpon <PATH>"
    """
    s = line.strip()
    s = _TOKEN_QUOTED.sub("<STR>", s)
    s = _TOKEN_SERIAL.sub("<SN>", s)
    s = _TOKEN_PATH.sub("<PATH>", s)
    s = _TOKEN_HEX.sub("<HEX>", s)
    s = _TOKEN_NUM.sub("<N>", s)
    # Reduz múltiplos espaços
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ---------------------------------------------------------------------------
# Per-file analysis
# ---------------------------------------------------------------------------
def file_metrics(text: str) -> dict[str, int]:
    total = sum(1 for _ in text.splitlines())
    non_blank = sum(1 for ln in text.splitlines() if ln.strip())
    return {"total_lines": total, "non_blank_lines": non_blank}


def confidence_bucket(c: float) -> str:
    if c >= 0.9:
        return "high"
    if c >= 0.7:
        return "medium"
    if c >= 0.5:
        return "low"
    if c >= 0.3:
        return "very-low"
    return "fallback"


def analyze_file(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    metrics = file_metrics(text)

    try:
        parser_cls = detect_vendor(text)
        detected = {
            "vendor": parser_cls.vendor.value,
            "model": parser_cls.model_family,
            "confidence": round(parser_cls.detect(text), 3),
        }
    except ValueError as exc:
        return {"file": path.name, "error": f"detect failed: {exc}", "metrics": metrics}

    try:
        parsed = parse_config(text)
    except Exception as exc:  # noqa: BLE001
        return {"file": path.name, "detected": detected, "error": f"parse failed: {exc!r}", "metrics": metrics}

    cfg: OLTConfig = parsed.config

    # Pipeline enrichment
    enriched = infer_service_ports(cfg)
    enriched = synthesize_dba_profiles(enriched)
    enriched = synthesize_traffic_profiles(enriched)

    # Inferences por bucket
    inference_buckets: Counter = Counter()
    inferred_examples: list[dict] = []
    for sp in enriched.service_ports:
        if sp.provenance and sp.provenance.source.value == "inference":
            inference_buckets[confidence_bucket(sp.provenance.confidence)] += 1
            if len(inferred_examples) < 4:
                inferred_examples.append({
                    "onu": f"{sp.pon_interface}:{sp.onu_id}",
                    "vlan": sp.match_vlan,
                    "confidence": round(sp.provenance.confidence, 2),
                    "reason": sp.provenance.reason,
                    "signals": sp.provenance.signals,
                })

    # Sintetizados
    synthesized_dba = []
    synthesized_traffic = []
    for d in enriched.dba_profiles:
        if d.provenance and d.provenance.source.value in {"synthesis", "default"}:
            synthesized_dba.append({
                "name": d.name,
                "type": d.type.value,
                "max": d.max_bandwidth,
                "confidence": round(d.provenance.confidence, 2),
                "reason": d.provenance.reason,
                "source": d.provenance.source.value,
            })
    for t in enriched.traffic_profiles:
        if t.provenance and t.provenance.source.value == "synthesis":
            synthesized_traffic.append({
                "name": t.name,
                "cir": t.cir,
                "pir": t.pir,
                "confidence": round(t.provenance.confidence, 2),
            })

    # Entidades que precisam revisão
    needs_review: list[dict] = []
    for collection_name, collection in (
        ("onus", enriched.onus),
        ("service_ports", enriched.service_ports),
        ("dba_profiles", enriched.dba_profiles),
        ("traffic_profiles", enriched.traffic_profiles),
        ("line_profiles", enriched.line_profiles),
        ("service_profiles", enriched.service_profiles),
    ):
        for entity in collection:
            prov = getattr(entity, "provenance", None)
            if prov and prov.needs_review:
                key = _entity_key(entity)
                needs_review.append({
                    "collection": collection_name,
                    "key": key,
                    "source": prov.source.value,
                    "confidence": round(prov.confidence, 2),
                    "reason": prov.reason or "",
                })

    # Linhas não-parseadas (normalizadas + originais)
    unparsed_normalized = Counter(normalize_command(ln) for ln in parsed.unparsed_lines)
    unparsed_sample = parsed.unparsed_lines[:10]

    # Coverage
    coverage = (metrics["non_blank_lines"] - len(parsed.unparsed_lines)) / max(
        metrics["non_blank_lines"], 1
    )

    # Conversões cruzadas
    cross: dict[str, dict] = {}
    for dst in VENDORS:
        if dst == parser_cls.vendor:
            continue
        try:
            r = convert(text, target_vendor=dst)
            cross[dst.value] = {
                "rendered_chars": len(r.rendered),
                "errors": r.validation.by_severity()["error"],
                "warnings": r.validation.by_severity()["warning"],
                "info": r.validation.by_severity()["info"],
                "stats": r.config.stats(),
                "remap_count": len(r.remapping_table.entries) if r.remapping_table else 0,
                "remap_collisions": len(r.remapping_table.collisions) if r.remapping_table else 0,
                "rendered_sample": r.rendered[:1200],
            }
        except Exception as exc:  # noqa: BLE001
            cross[dst.value] = {"error": repr(exc)}

    val = validate_config(enriched)
    issue_codes = Counter(i.code for i in val.issues)

    return {
        "file": path.name,
        "metrics": metrics,
        "detected": detected,
        "stats": enriched.stats(),
        "parsing_coverage": round(coverage * 100, 1),
        "unparsed_total": len(parsed.unparsed_lines),
        "unparsed_normalized": unparsed_normalized,
        "unparsed_sample": unparsed_sample,
        "inference_buckets": dict(inference_buckets),
        "inferred_examples": inferred_examples,
        "inference_coverage": (
            round(sum(inference_buckets.values()) / max(len(enriched.onus), 1) * 100, 1)
        ),
        "synthesized_dba": synthesized_dba,
        "synthesized_traffic": synthesized_traffic,
        "needs_review_total": len(needs_review),
        "needs_review_by_collection": dict(Counter(nr["collection"] for nr in needs_review)),
        "needs_review_samples": needs_review[:10],
        "validation": {
            "summary": val.by_severity(),
            "top_codes": issue_codes.most_common(8),
        },
        "cross_conversions": cross,
        "ambiguous_bindings": [
            ex for ex in inferred_examples if ex["confidence"] < 0.6
        ],
    }


def _entity_key(entity: Any) -> str:
    for attr in ("name", "serial_number", "service_port_id", "id"):
        v = getattr(entity, attr, None)
        if v:
            return str(v)
    if hasattr(entity, "pon_interface") and hasattr(entity, "onu_id"):
        return f"{entity.pon_interface}:{entity.onu_id}"
    return repr(entity)[:60]


# ---------------------------------------------------------------------------
# Global aggregation
# ---------------------------------------------------------------------------
def aggregate(reports: list[dict]) -> dict[str, Any]:
    """Agrega métricas globais a partir das análises individuais."""
    valid = [r for r in reports if "error" not in r]
    if not valid:
        return {}

    # Top unsupported commands GLOBAL
    global_unparsed: Counter = Counter()
    for r in valid:
        for pattern, n in r["unparsed_normalized"].items():
            global_unparsed[pattern] += n

    # Top needs_review por categoria
    nr_by_coll: Counter = Counter()
    for r in valid:
        for coll, n in r["needs_review_by_collection"].items():
            nr_by_coll[coll] += n

    # Inference: cobertura média + buckets agregados
    total_buckets: Counter = Counter()
    for r in valid:
        for b, n in r["inference_buckets"].items():
            total_buckets[b] += n
    avg_inference_coverage = round(
        sum(r["inference_coverage"] for r in valid) / len(valid), 1
    )

    # Heatmap origin→destination: total errors+warnings por par
    heatmap: dict[str, dict[str, dict]] = defaultdict(dict)
    for r in valid:
        src = r["detected"]["vendor"]
        for tgt, info in r["cross_conversions"].items():
            if "error" in info:
                continue
            cell_data = heatmap[src].setdefault(tgt, {
                "files": 0, "errors": 0, "warnings": 0,
                "rendered_chars": 0, "remaps": 0, "collisions": 0,
            })
            cell_data["files"] += 1
            cell_data["errors"] += info["errors"]
            cell_data["warnings"] += info["warnings"]
            cell_data["rendered_chars"] += info["rendered_chars"]
            cell_data["remaps"] += info["remap_count"]
            cell_data["collisions"] += info["remap_collisions"]

    # Per-feature: confidence histogram (a partir das declarações da matriz)
    feature_histogram: dict[str, dict[str, int]] = {}
    for feat in FEATURES:
        bins = {"≥0.9": 0, "0.7-0.9": 0, "0.5-0.7": 0, "0.3-0.5": 0, "<0.3": 0}
        for src in VENDORS:
            for tgt in VENDORS:
                if src == tgt:
                    continue
                c = compat_cell(src, tgt, feat)
                v = c.semantic_fidelity
                if v >= 0.9:
                    bins["≥0.9"] += 1
                elif v >= 0.7:
                    bins["0.7-0.9"] += 1
                elif v >= 0.5:
                    bins["0.5-0.7"] += 1
                elif v >= 0.3:
                    bins["0.3-0.5"] += 1
                else:
                    bins["<0.3"] += 1
        feature_histogram[feat] = bins

    return {
        "files_analyzed": len(valid),
        "top_unsupported_commands": global_unparsed.most_common(30),
        "needs_review_by_collection": dict(nr_by_coll),
        "inference_buckets_global": dict(total_buckets),
        "avg_inference_coverage_pct": avg_inference_coverage,
        "heatmap": dict(heatmap),
        "feature_histogram": feature_histogram,
    }


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------
def render_markdown(reports: list[dict], agg: dict[str, Any]) -> str:
    L: list[str] = []
    L.append("# Fidelity Report — pipeline real")
    L.append("")
    L.append("> Gerado por `fidelity_report.py`. Reflete o estado *real* da")
    L.append("> pipeline (parse → inferência → síntese → equivalência → remap → render)")
    L.append("> contra os backups disponíveis. Use para calibrar a matriz de")
    L.append("> compatibilidade declarativa.")
    L.append("")

    # 1. Sumário ------------------------------------------------------------
    L.append("## 1. Sumário por arquivo\n")
    L.append("| Arquivo | Vendor | Linhas | Cobertura | ONUs | SPs | Inferência | Issues | Remaps |")
    L.append("|--------|--------|-------:|----------:|-----:|----:|----------:|-------:|-------:|")
    for r in reports:
        if "error" in r:
            L.append(f"| {r['file']} | — | {r['metrics']['non_blank_lines']} | FAIL | — | — | — | — | — |")
            continue
        s = r["stats"]
        L.append(
            f"| {r['file']} | {r['detected']['vendor']} | "
            f"{r['metrics']['non_blank_lines']} | {r['parsing_coverage']}% | "
            f"{s['onus']} | {s['service_ports']} | {r['inference_coverage']}% | "
            f"{r['validation']['summary']['error']}e/{r['validation']['summary']['warning']}w | "
            f"varia |"
        )
    L.append("")

    # 2. Top unsupported commands -----------------------------------------
    L.append("## 2. Top unsupported commands (normalizados, agregados)\n")
    L.append("Patterns que aparecem em `raw_unparsed` após normalização (números e paths viram `<N>`/`<PATH>`).")
    L.append("Bom indicador de features a priorizar nos parsers.\n")
    L.append("| # | Ocorrências | Pattern |")
    L.append("|--:|------------:|---------|")
    for i, (pat, n) in enumerate(agg.get("top_unsupported_commands", []), start=1):
        L.append(f"| {i} | {n} | `{pat}` |")
    L.append("")

    # 3. Top partially mapped entities -------------------------------------
    L.append("## 3. Entidades que precisam de revisão (needs_review=True)\n")
    L.append("Contagem por coleção. `needs_review` é setado quando algo foi")
    L.append("inferido com baixa confiança, sintetizado, default-fallback ou remapeado.\n")
    L.append("| Coleção | needs_review |")
    L.append("|---------|-------------:|")
    for coll, n in sorted(agg.get("needs_review_by_collection", {}).items(), key=lambda x: -x[1]):
        L.append(f"| `{coll}` | {n} |")
    L.append("")

    # 4. Top ambiguous bindings + inferred relationships -------------------
    L.append("## 4. Bindings inferidos (cobertura por confidence)\n")
    L.append(f"Cobertura média da inferência de service-ports: **{agg.get('avg_inference_coverage_pct', 0)}%** das ONUs receberam binding.\n")
    L.append("Distribuição global por bucket de confidence:\n")
    L.append("| Bucket | Bindings |")
    L.append("|--------|---------:|")
    for b, n in agg.get("inference_buckets_global", {}).items():
        L.append(f"| {b} | {n} |")
    L.append("")

    L.append("### Exemplos representativos (origem do binding rastreável)")
    L.append("")
    sample_count = 0
    for r in reports:
        if "error" in r:
            continue
        for ex in r.get("inferred_examples", []):
            if sample_count >= 8:
                break
            L.append(f"- **{r['file']}** · ONU {ex['onu']} → VLAN {ex['vlan']} · conf=**{ex['confidence']}**")
            L.append(f"  - reason: _{ex['reason']}_")
            L.append(f"  - signals: `{', '.join(ex['signals'])}`")
            sample_count += 1
        if sample_count >= 8:
            break
    L.append("")

    # 5. Per-feature confidence histogram ---------------------------------
    L.append("## 5. Per-feature confidence histogram (matriz)\n")
    L.append("Para cada feature, distribuição de `semantic_fidelity` em pares vendor×vendor.\n")
    L.append("| Feature | ≥0.9 | 0.7-0.9 | 0.5-0.7 | 0.3-0.5 | <0.3 |")
    L.append("|---------|-----:|--------:|--------:|--------:|-----:|")
    for feat in FEATURES:
        h = agg.get("feature_histogram", {}).get(feat, {})
        L.append(
            f"| `{feat}` | {h.get('≥0.9',0)} | {h.get('0.7-0.9',0)} | "
            f"{h.get('0.5-0.7',0)} | {h.get('0.3-0.5',0)} | {h.get('<0.3',0)} |"
        )
    L.append("")

    # 6. Vendor/model heatmap ---------------------------------------------
    L.append("## 6. Heatmap origem → destino (conversões reais)\n")
    L.append("Soma das métricas dos arquivos analisados. Cores: 🟢 OK · 🟡 atenção · 🔴 problema.\n")
    L.append("| origem ↓ destino → | " + " | ".join(f"**{v.value}**" for v in VENDORS) + " |")
    L.append("|" + "---|" * (len(VENDORS) + 1))
    for src in VENDORS:
        row = [f"**{src.value}**"]
        for tgt in VENDORS:
            if src == tgt:
                row.append("—")
                continue
            cell_data = agg.get("heatmap", {}).get(src.value, {}).get(tgt.value)
            if not cell_data:
                row.append("·")
                continue
            color = "🔴" if cell_data["errors"] > 0 else (
                "🟡" if cell_data["warnings"] > cell_data["files"] * 5 else "🟢"
            )
            row.append(
                f"{color} {cell_data['files']}f · {cell_data['errors']}e · "
                f"{cell_data['warnings']}w · {cell_data['remaps']}r"
            )
        L.append("| " + " | ".join(row) + " |")
    L.append("")
    L.append("Legenda: `f`=arquivos, `e`=errors, `w`=warnings, `r`=remaps aplicados")
    L.append("")

    # 7. Scores derivados --------------------------------------------------
    L.append("## 7. Scores globais derivados da matriz\n")
    L.append("| Vendor | parser_coverage | renderer_completeness |")
    L.append("|--------|---------------:|---------------------:|")
    for v in VENDORS:
        s = vendor_scores(v)
        L.append(f"| **{v.value}** | {s['parser_coverage_score']:.0%} | {s['renderer_completeness_score']:.0%} |")
    L.append("")

    L.append("### semantic_fidelity por par\n")
    L.append("| | " + " | ".join(f"→ **{v.value}**" for v in VENDORS) + " |")
    L.append("|" + "---|" * (len(VENDORS) + 1))
    for src in VENDORS:
        row = [f"**{src.value}**"]
        for tgt in VENDORS:
            if src == tgt:
                row.append("—")
                continue
            sc = conversion_score(src, tgt)
            row.append(f"{sc['semantic_fidelity_score']:.0%} ({sc['FULL']}/{sc['PARTIAL']}/{sc['NONE']}/{sc['UNSUPPORTED']})")
        L.append("| " + " | ".join(row) + " |")
    L.append("")
    L.append("Contadores entre parênteses: (FULL / PARTIAL / NONE / UNSUPPORTED)")
    L.append("")

    # 8. Detalhe por arquivo ----------------------------------------------
    L.append("## 8. Detalhe por arquivo\n")
    for r in reports:
        if "error" in r:
            L.append(f"\n### {r['file']} — FAIL\n```\n{r['error']}\n```\n")
            continue
        L.append(f"\n---\n\n### {r['file']}\n")
        L.append(f"- vendor: **{r['detected']['vendor']}** ({r['detected']['model']}, conf={r['detected']['confidence']})")
        L.append(f"- linhas: {r['metrics']['non_blank_lines']} · cobertura **{r['parsing_coverage']}%** · unparsed={r['unparsed_total']}")
        L.append(f"- inferência: **{r['inference_coverage']}%** das ONUs receberam binding")

        if r["stats"]:
            L.append("\n**Entidades**\n```")
            for k, v in r["stats"].items():
                L.append(f"  {k:20s} {v}")
            L.append("```")

        if r["needs_review_total"]:
            L.append(f"\n**Needs review** (total {r['needs_review_total']}):")
            for nr in r["needs_review_samples"]:
                L.append(f"- `{nr['collection']}` `{nr['key']}` · {nr['source']} conf={nr['confidence']}")
                if nr["reason"]:
                    L.append(f"  - _{nr['reason'][:140]}_")

        if r["synthesized_dba"]:
            L.append("\n**DBA sintetizados:**")
            for d in r["synthesized_dba"]:
                L.append(f"- `{d['name']}` ({d['type']}, max={d['max']}) conf={d['confidence']} · {d['source']}")

        L.append("\n**Cross conversions**\n```")
        for dst, info in r["cross_conversions"].items():
            if "error" in info:
                L.append(f"  → {dst:9s} FAIL: {info['error']}")
            else:
                L.append(
                    f"  → {dst:9s} len={info['rendered_chars']:>6d} "
                    f"e={info['errors']} w={info['warnings']} i={info['info']} "
                    f"onus={info['stats']['onus']} sp={info['stats']['service_ports']} "
                    f"remap={info['remap_count']} col={info['remap_collisions']}"
                )
        L.append("```")

        if r["unparsed_sample"]:
            L.append("\n**Amostra de linhas não-mapeadas:**")
            L.append("```")
            for ln in r["unparsed_sample"]:
                L.append(f"  {ln}")
            L.append("```")

    return "\n".join(L)


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="emite JSON cru também")
    ap.add_argument("--print", action="store_true", help="ecoa markdown no terminal")
    ap.add_argument("--only-real", action="store_true", help="só modelos-config/")
    args = ap.parse_args()

    files: list[Path] = []
    if not args.only_real and EXAMPLES.exists():
        files.extend(sorted(EXAMPLES.glob("*.cfg")))
    real_files = discover_real_backups()
    if real_files:
        print(f"\nBackups reais encontrados ({len(real_files)}):")
        for f in real_files:
            print(f"  - {f}")
        print()
    else:
        print(
            "\nNenhum backup real encontrado. Caminhos checados:\n"
            f"  - {ROOT / 'modelos-config'}\n"
            f"  - {ROOT.parent / 'modelos-config'}\n"
            f"  - {ROOT.parent.parent / 'modelos-config'}\n"
            f"  - {ROOT.parent} (.txt soltos)\n"
            "Para forçar um caminho, exporte OLT_BACKUPS=/caminho/para/pasta\n"
        )
    files.extend(real_files)
    if not files:
        print("Nenhum arquivo encontrado.")
        return 1

    reports: list[dict] = []
    for path in files:
        print(f"analisando {path.name}...")
        try:
            reports.append(analyze_file(path))
        except Exception as exc:  # noqa: BLE001
            reports.append({"file": path.name, "error": repr(exc)})

    agg = aggregate(reports)

    DOCS.mkdir(exist_ok=True)
    md = render_markdown(reports, agg)
    md_path = DOCS / "FIDELITY_REPORT.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"\n→ {md_path}")

    if args.json:
        # remover Counters (não-serializáveis) antes
        def _clean(o: Any) -> Any:
            if isinstance(o, Counter):
                return dict(o)
            if isinstance(o, dict):
                return {k: _clean(v) for k, v in o.items()}
            if isinstance(o, list):
                return [_clean(x) for x in o]
            return o
        (DOCS / "FIDELITY_REPORT.json").write_text(
            json.dumps({"reports": _clean(reports), "agg": _clean(agg)}, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"→ {DOCS / 'FIDELITY_REPORT.json'}")

    if args.print:
        print()
        print(md)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
