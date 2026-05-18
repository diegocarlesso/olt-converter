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
        # Capturar traceback para diagnóstico de FAILs
        import traceback
        tb = traceback.format_exc(limit=8)
        return {
            "file": path.name,
            "detected": detected,
            "error": f"parse failed: {exc!r}",
            "traceback": tb,
            "metrics": metrics,
        }

    cfg: OLTConfig = parsed.config

    # Pipeline enrichment (L9 incluído)
    from app.services.promotion import promote_subscriber_edge
    enriched = infer_service_ports(cfg)
    enriched = synthesize_dba_profiles(enriched)
    enriched = synthesize_traffic_profiles(enriched)
    enriched = promote_subscriber_edge(enriched)

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
            # Conta linhas SE no render COMPLETO (nao so no sample 1200).
            _se_keywords_eval = (
                "ont port native-vlan", "ont wan-config", "ont port route",
                "set wancfg", "set wifi_serv_wlan", "set autho",
                "pon-onu-mng", "vlan port eth_0/", "pppoe ", "ssid auth",
            )
            _full_se_lines = sum(
                1 for ln in r.rendered.splitlines()
                if any(k in ln for k in _se_keywords_eval)
            )
            cross[dst.value] = {
                "rendered_chars": len(r.rendered),
                "errors": r.validation.by_severity()["error"],
                "warnings": r.validation.by_severity()["warning"],
                "info": r.validation.by_severity()["info"],
                "stats": r.config.stats(),
                "remap_count": len(r.remapping_table.entries) if r.remapping_table else 0,
                "remap_collisions": len(r.remapping_table.collisions) if r.remapping_table else 0,
                "rendered_sample": r.rendered[:1200],
                "full_se_lines": _full_se_lines,
            }
        except Exception as exc:  # noqa: BLE001
            cross[dst.value] = {"error": repr(exc)}

    val = validate_config(enriched)
    issue_codes = Counter(i.code for i in val.issues)

    # ---------- L9 Subscriber Edge metrics ----------
    se_metrics = _subscriber_edge_metrics(enriched, cross)

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
        "subscriber_edge": se_metrics,
    }


def _subscriber_edge_metrics(cfg: "OLTConfig", cross: dict) -> dict[str, Any]:
    """
    Métricas L9 subscriber edge: cobertura, contagem, confidence histogram,
    promoted vs parsed ratio, cross-binding integrity, renderer completeness.
    """
    total_onus = len(cfg.onus)
    if total_onus == 0:
        return {"total_onus": 0, "coverage_pct": 0.0, "skipped": True}

    # ---- Counts por tipo de entidade promovida
    counts = {
        "radios": sum(len(o.radios) for o in cfg.onus),
        "ssids": sum(len(o.ssids) for o in cfg.onus),
        "bridge_groups": sum(len(o.bridge_groups) for o in cfg.onus),
        "lan_services": sum(len(o.lan_services) for o in cfg.onus),
        "wan_bindings": sum(len(o.wan_bindings) for o in cfg.onus),
        "multicast_bindings": sum(len(o.multicast_bindings) for o in cfg.onus),
        "port_routes": sum(len(o.port_routes) for o in cfg.onus),
        "stb_configured": sum(1 for o in cfg.onus if o.stb is not None),
        "eth_ports": sum(len(o.eth_ports) for o in cfg.onus),
    }

    # ---- Foco específico: EthernetPort.native_vlan, bridge_mode, wan_binding_id
    eth_native_vlan_count = 0
    eth_bridge_mode_count = 0
    eth_wan_binding_count = 0
    eth_total = 0
    for o in cfg.onus:
        for eth in o.eth_ports:
            eth_total += 1
            if eth.native_vlan is not None:
                eth_native_vlan_count += 1
            if eth.bridge_mode is not None:
                eth_bridge_mode_count += 1
            if eth.wan_binding_id is not None:
                eth_wan_binding_count += 1

    # ---- Cobertura: % de ONUs com ao menos uma entidade L9
    onus_with_edge = sum(
        1 for o in cfg.onus
        if o.radios or o.ssids or o.bridge_groups or o.lan_services
        or o.wan_bindings or o.multicast_bindings or o.port_routes or o.stb
        or any(e.native_vlan or e.bridge_mode for e in o.eth_ports)
    )
    coverage_pct = round(onus_with_edge / total_onus * 100, 1)

    # ---- Provenance: distribuição por fonte (parser/promotion/synthesis/etc)
    prov_sources: Counter = Counter()
    prov_conf_buckets: Counter = Counter()

    def _consume(entities, where):
        for e in entities:
            prov = getattr(e, "provenance", None)
            if not prov:
                continue
            src = prov.source.value if hasattr(prov.source, "value") else str(prov.source)
            prov_sources[f"{where}:{src}"] += 1
            prov_conf_buckets[confidence_bucket(prov.confidence)] += 1

    for o in cfg.onus:
        _consume(o.radios, "radios")
        _consume(o.ssids, "ssids")
        _consume(o.bridge_groups, "bridge_groups")
        _consume(o.wan_bindings, "wan_bindings")
        _consume(o.lan_services, "lan_services")
        _consume(o.multicast_bindings, "multicast_bindings")
        _consume(o.port_routes, "port_routes")

    # ---- Cross-binding integrity
    integrity_checks = {
        "ssid_radio_ok": 0, "ssid_radio_broken": 0,
        "wan_profile_ref_ok": 0, "wan_profile_ref_broken": 0,
        "bridge_group_members_ok": 0, "bridge_group_members_broken": 0,
        "lan_service_vlan_ok": 0, "lan_service_vlan_broken": 0,
        "port_route_eth_ok": 0, "port_route_eth_broken": 0,
    }
    wan_profile_names = {w.name for w in cfg.wan_profiles}
    vlan_ids = {v.id for v in cfg.vlans}
    for o in cfg.onus:
        eth_ids = {e.port_id for e in o.eth_ports}
        radio_ids = {r.radio_id for r in o.radios}
        for ssid in o.ssids:
            if ssid.radio_id in radio_ids or not o.radios:
                integrity_checks["ssid_radio_ok"] += 1
            else:
                integrity_checks["ssid_radio_broken"] += 1
        for wb in o.wan_bindings:
            ref = getattr(wb, "wan_profile_ref", None)
            if not ref or ref in wan_profile_names:
                integrity_checks["wan_profile_ref_ok"] += 1
            else:
                integrity_checks["wan_profile_ref_broken"] += 1
        for bg in o.bridge_groups:
            broken = any(pid not in eth_ids for pid in bg.member_port_ids)
            if broken:
                integrity_checks["bridge_group_members_broken"] += 1
            else:
                integrity_checks["bridge_group_members_ok"] += 1
        for svc in o.lan_services:
            if svc.vlan_id and svc.vlan_id not in vlan_ids:
                integrity_checks["lan_service_vlan_broken"] += 1
            else:
                integrity_checks["lan_service_vlan_ok"] += 1
        for pr in o.port_routes:
            broken = (pr.src_port_id and pr.src_port_id not in eth_ids) or \
                     (pr.dst_port_id and pr.dst_port_id not in eth_ids)
            if broken:
                integrity_checks["port_route_eth_broken"] += 1
            else:
                integrity_checks["port_route_eth_ok"] += 1

    total_checks = sum(v for k, v in integrity_checks.items() if k.endswith("_ok") or k.endswith("_broken"))
    broken_total = sum(v for k, v in integrity_checks.items() if k.endswith("_broken"))
    integrity_score = round((1 - broken_total / max(total_checks, 1)) * 100, 1)

    # ---- Renderer subscriber-edge completeness
    # Para cada cross conversion, conta caracteres dedicados a subscriber edge
    se_keywords = (
        "ont port native-vlan", "ont wan-config", "ont port route",
        "set wancfg", "set wifi_serv_wlan", "set autho",
        "pon-onu-mng", "vlan port eth_0/", "pppoe ", "ssid auth",
    )
    renderer_se_completeness = {}
    for dst, info in cross.items():
        if "error" in info:
            renderer_se_completeness[dst] = {"emitted": False, "lines": 0}
            continue
        # Usa contagem no render COMPLETO se disponivel (mais preciso).
        full_lines = info.get("full_se_lines")
        if full_lines is None:
            sample = info.get("rendered_sample", "")
            full_lines = sum(
                1 for ln in sample.splitlines()
                if any(k in ln for k in se_keywords)
            )
        renderer_se_completeness[dst] = {
            "emitted": full_lines > 0,
            "lines_in_sample": full_lines,
        }

    return {
        "total_onus": total_onus,
        "onus_with_edge": onus_with_edge,
        "coverage_pct": coverage_pct,
        "entity_counts": counts,
        "eth_native_vlan": {
            "populated": eth_native_vlan_count,
            "total": eth_total,
            "pct": round(eth_native_vlan_count / max(eth_total, 1) * 100, 1),
        },
        "eth_bridge_mode": {
            "populated": eth_bridge_mode_count,
            "total": eth_total,
            "pct": round(eth_bridge_mode_count / max(eth_total, 1) * 100, 1),
        },
        "eth_wan_binding": {
            "populated": eth_wan_binding_count,
            "total": eth_total,
            "pct": round(eth_wan_binding_count / max(eth_total, 1) * 100, 1),
        },
        "provenance_sources": dict(prov_sources),
        "confidence_histogram": dict(prov_conf_buckets),
        "integrity": integrity_checks,
        "integrity_score_pct": integrity_score,
        "renderer_completeness": renderer_se_completeness,
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

    # ---- Parser coverage por vendor (média ponderada por linhas)
    cov_by_vendor: dict[str, dict[str, float]] = {}
    for r in valid:
        v = r["detected"]["vendor"]
        bucket = cov_by_vendor.setdefault(v, {"weighted_cov": 0.0, "lines": 0, "files": 0})
        bucket["weighted_cov"] += r["parsing_coverage"] * r["metrics"]["non_blank_lines"]
        bucket["lines"] += r["metrics"]["non_blank_lines"]
        bucket["files"] += 1
    coverage_summary: dict[str, dict] = {}
    for v, b in cov_by_vendor.items():
        avg = b["weighted_cov"] / max(b["lines"], 1)
        coverage_summary[v] = {
            "files": b["files"],
            "total_lines": b["lines"],
            "avg_coverage_pct": round(avg, 1),
        }

    # ---- Milestones (targets do sprint atual)
    targets = {
        "fiberhome": 75.0,
        "zte": 75.0,
        "huawei": 90.0,
        "datacom": 70.0,
    }
    milestones: dict[str, dict] = {}
    for v, t in targets.items():
        actual = coverage_summary.get(v, {}).get("avg_coverage_pct", 0.0)
        delta = actual - t
        milestones[v] = {
            "target": t,
            "actual": actual,
            "delta": round(delta, 1),
            "hit": actual >= t,
        }

    # ---- Clustering dos top unsupported commands por prefixo
    # (ex: set wifi_*, set wan*, gemport *, tcont *, vlan *, flow *)
    clusters: Counter = Counter()
    for pattern, n in global_unparsed.items():
        first_words = pattern.strip().split()[:2]
        # Trata `set X ...` → cluster = "set X"
        if first_words and first_words[0].lower() == "set" and len(first_words) > 1:
            key = f"set {first_words[1]}"
        elif first_words:
            key = first_words[0]
        else:
            key = "<empty>"
        clusters[key] += n

    # ---- Runtime vs declarative classification
    # Comandos runtime: tipicamente per-ONU (gemport, tcont, service, switchport-bind,
    # vlan-filter, flow, set wancfg, set wifi_*, pon-onu-mng, interface gpon-onu_*)
    # Comandos declarative: globais (sysname, vlan, dba-profile, traffic table, board)
    RUNTIME_PREFIXES = (
        "gemport", "tcont", "service ", "switchport-bind", "vlan-filter",
        "flow ", "set wancfg", "set wifi_", "set autho", "set service_ba",
        "set onu_pon_type", "set port_separate", "pon-onu-mng",
        "interface gpon-onu_", "interface gpon_onu-",
        "interface vport-", "loop-detect", "dhcp-ip",
        "onu wps-config", "sn-bind", "security-mgmt", "tr069-mgmt", "firewall",
        "tr069", "ip-host", "vlan port eth_", "vlan wan",
    )
    runtime_total = 0
    declarative_total = 0
    for pattern, n in global_unparsed.items():
        low = pattern.lower()
        if any(low.startswith(p) for p in RUNTIME_PREFIXES):
            runtime_total += n
        else:
            declarative_total += n

    # ---- Semantic loss buckets (medido pelos warnings das cross-conversions)
    semantic_loss: dict[str, int] = {
        "render_errors": 0,
        "render_warnings": 0,
        "remap_collisions": 0,
        "remaps_applied": 0,
    }
    for r in valid:
        for tgt, info in r["cross_conversions"].items():
            if "error" in info:
                continue
            semantic_loss["render_errors"] += info["errors"]
            semantic_loss["render_warnings"] += info["warnings"]
            semantic_loss["remap_collisions"] += info["remap_collisions"]
            semantic_loss["remaps_applied"] += info["remap_count"]

    # ---- L9 Subscriber Edge aggregation (global)
    se_total_onus = 0
    se_total_with_edge = 0
    se_total_counts: Counter = Counter()
    se_prov_sources: Counter = Counter()
    se_prov_buckets: Counter = Counter()
    se_integrity: Counter = Counter()
    se_renderer_emit: dict[str, dict] = {}
    eth_native_pop = eth_native_total = 0
    for r in valid:
        se = r.get("subscriber_edge", {})
        if not se or se.get("skipped"):
            continue
        se_total_onus += se["total_onus"]
        se_total_with_edge += se["onus_with_edge"]
        for k, v in se["entity_counts"].items():
            se_total_counts[k] += v
        for k, v in se["provenance_sources"].items():
            se_prov_sources[k] += v
        for k, v in se["confidence_histogram"].items():
            se_prov_buckets[k] += v
        for k, v in se["integrity"].items():
            se_integrity[k] += v
        eth_native_pop += se["eth_native_vlan"]["populated"]
        eth_native_total += se["eth_native_vlan"]["total"]
        for dst, rc in se["renderer_completeness"].items():
            bag = se_renderer_emit.setdefault(dst, {"emitted_files": 0, "total_files": 0, "lines": 0})
            bag["total_files"] += 1
            if rc.get("emitted"):
                bag["emitted_files"] += 1
            bag["lines"] += rc.get("lines_in_sample", 0)

    promoted = se_prov_sources_by_source(se_prov_sources, ("promotion",))
    parsed_or_inference = se_prov_sources_by_source(se_prov_sources, ("parser", "inference", "synthesis"))
    promoted_total = sum(promoted.values()) if isinstance(promoted, dict) else promoted
    parsed_or_inference_total = sum(parsed_or_inference.values()) if isinstance(parsed_or_inference, dict) else parsed_or_inference
    se_global = {
        "total_onus": se_total_onus,
        "onus_with_edge": se_total_with_edge,
        "coverage_pct": round(se_total_with_edge / max(se_total_onus, 1) * 100, 1),
        "entity_counts": dict(se_total_counts),
        "provenance_sources": dict(se_prov_sources),
        "confidence_histogram": dict(se_prov_buckets),
        "integrity": dict(se_integrity),
        "integrity_score_pct": _integrity_score(se_integrity),
        "eth_native_vlan_pct": round(eth_native_pop / max(eth_native_total, 1) * 100, 1),
        "eth_native_vlan_populated": eth_native_pop,
        "eth_native_vlan_total": eth_native_total,
        "renderer_completeness": se_renderer_emit,
        "promoted_total": promoted_total,
        "parsed_or_inference_total": parsed_or_inference_total,
    }

    return {
        "files_analyzed": len(valid),
        "top_unsupported_commands": global_unparsed.most_common(30),
        "unsupported_clusters": clusters.most_common(20),
        "needs_review_by_collection": dict(nr_by_coll),
        "inference_buckets_global": dict(total_buckets),
        "avg_inference_coverage_pct": avg_inference_coverage,
        "heatmap": dict(heatmap),
        "feature_histogram": feature_histogram,
        "coverage_summary": coverage_summary,
        "milestones": milestones,
        "runtime_vs_declarative": {
            "runtime_unparsed": runtime_total,
            "declarative_unparsed": declarative_total,
        },
        "semantic_loss": semantic_loss,
        "subscriber_edge_global": se_global,
    }


def se_prov_sources_by_source(sources: Counter, wanted: tuple[str, ...]) -> dict[str, int]:
    """Soma valores cuja chave contém uma das fontes desejadas (`...:promotion`)."""
    out: dict[str, int] = {}
    for k, v in sources.items():
        for w in wanted:
            if k.endswith(":" + w):
                out[k] = v
    return out


def _integrity_score(integ: Counter) -> float:
    total = sum(v for k, v in integ.items() if k.endswith("_ok") or k.endswith("_broken"))
    broken = sum(v for k, v in integ.items() if k.endswith("_broken"))
    return round((1 - broken / max(total, 1)) * 100, 1)


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

    # 0. Milestone tracking (TOPO — fica visível primeiro) ---------------
    if agg.get("milestones"):
        L.append("## 0. Sprint coverage milestones\n")
        L.append("Targets do **Parser Coverage Recovery Sprint** vs realidade medida.")
        L.append("")
        L.append("| Vendor | Target | Actual | Δ | Status |")
        L.append("|--------|-------:|-------:|--:|:------:|")
        for v, m in sorted(agg["milestones"].items()):
            badge = "✅" if m["hit"] else ("⚠️" if m["delta"] >= -10 else "🔴")
            sign = "+" if m["delta"] >= 0 else ""
            L.append(
                f"| **{v}** | {m['target']:.0f}% | {m['actual']:.1f}% | "
                f"{sign}{m['delta']:.1f}% | {badge} |"
            )
        L.append("")

    # 1. Sumário ------------------------------------------------------------
    L.append("## 1. Sumário por arquivo\n")
    L.append("| Arquivo | Vendor | Linhas | Cobertura | ONUs | SPs | Inferência | Issues | Remaps |")
    L.append("|--------|--------|-------:|----------:|-----:|----:|----------:|-------:|-------:|")
    for r in reports:
        if "error" in r:
            nbl = r.get("metrics", {}).get("non_blank_lines", "?")
            L.append(f"| {r['file']} | — | {nbl} | FAIL | — | — | — | — | — |")
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

    # 1b. Coverage heatmap por vendor -------------------------------------
    if agg.get("coverage_summary"):
        L.append("## 1b. Parser coverage heatmap por vendor\n")
        L.append("Média ponderada pelo número de linhas (não pela contagem de arquivos).")
        L.append("")
        L.append("| Vendor | Files | Total lines | Avg coverage |")
        L.append("|--------|------:|------------:|-------------:|")
        for v, cs in sorted(agg["coverage_summary"].items()):
            badge = "🟢" if cs["avg_coverage_pct"] >= 75 else (
                "🟡" if cs["avg_coverage_pct"] >= 50 else "🔴"
            )
            L.append(
                f"| {badge} **{v}** | {cs['files']} | {cs['total_lines']:,} | "
                f"{cs['avg_coverage_pct']:.1f}% |"
            )
        L.append("")

    # 1c. Runtime vs declarative ----------------------------------------
    if agg.get("runtime_vs_declarative"):
        rd = agg["runtime_vs_declarative"]
        total = rd["runtime_unparsed"] + rd["declarative_unparsed"]
        if total:
            r_pct = rd["runtime_unparsed"] / total * 100
            L.append("## 1c. Runtime vs declarative unparsed\n")
            L.append(
                "Classificação das linhas não-mapeadas. Comandos *runtime* "
                "(per-ONU: gemport, tcont, set wancfg, sn-bind, etc.) são "
                "geralmente per-cliente; *declarative* são globais."
            )
            L.append("")
            L.append("| Categoria | Linhas | % |")
            L.append("|-----------|-------:|--:|")
            L.append(f"| Runtime    | {rd['runtime_unparsed']:,} | {r_pct:.1f}% |")
            L.append(f"| Declarative | {rd['declarative_unparsed']:,} | {100-r_pct:.1f}% |")
            L.append("")

    # 1d. Unsupported command clusters ----------------------------------
    if agg.get("unsupported_clusters"):
        L.append("## 1d. Unsupported clusters (top prefixos)\n")
        L.append(
            "Agrupamento por prefixo de comando — mostra qual *família* de "
            "comandos tem maior impacto."
        )
        L.append("")
        L.append("| # | Ocorrências | Cluster |")
        L.append("|--:|------------:|---------|")
        for i, (cluster, n) in enumerate(agg["unsupported_clusters"], start=1):
            L.append(f"| {i} | {n:,} | `{cluster}` |")
        L.append("")

    # 1e. Semantic loss buckets -----------------------------------------
    if agg.get("semantic_loss"):
        sl = agg["semantic_loss"]
        L.append("## 1e. Semantic loss buckets (cross-conversion)\n")
        L.append("| Categoria | Total |")
        L.append("|-----------|------:|")
        L.append(f"| Render errors        | {sl['render_errors']:,} |")
        L.append(f"| Render warnings      | {sl['render_warnings']:,} |")
        L.append(f"| Remap collisions     | {sl['remap_collisions']:,} |")
        L.append(f"| Remaps applied (ok)  | {sl['remaps_applied']:,} |")
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

    # 7b. L9 Subscriber Edge --------------------------------------------
    se = agg.get("subscriber_edge_global", {})
    if se:
        L.append("## 7b. L9 Subscriber Edge — validation final\n")
        L.append(
            f"Cobertura: **{se.get('coverage_pct', 0)}%** ({se.get('onus_with_edge', 0)} de "
            f"{se.get('total_onus', 0)} ONUs com entidades L9 promovidas/parseadas)."
        )
        L.append("")

        L.append("### Promoted entities (totais agregados)\n")
        L.append("| Tipo | Total |")
        L.append("|------|------:|")
        for k, v in sorted(se.get("entity_counts", {}).items(), key=lambda x: -x[1]):
            L.append(f"| `{k}` | {v:,} |")
        L.append("")

        # EthernetPort focus
        en = se.get("eth_native_vlan_populated", 0)
        et = se.get("eth_native_vlan_total", 0)
        ep = se.get("eth_native_vlan_pct", 0)
        L.append("### Foco: EthernetPort.native_vlan\n")
        L.append(f"- Total de EthernetPort: **{et}**")
        L.append(f"- Com `native_vlan` populado: **{en}** (`{ep}%`)\n")

        # Provenance distribution
        L.append("### Provenance distribution (subscriber edge)\n")
        L.append("| Categoria | Count |")
        L.append("|-----------|------:|")
        for k, v in sorted(se.get("provenance_sources", {}).items(), key=lambda x: -x[1])[:20]:
            L.append(f"| `{k}` | {v:,} |")
        L.append("")
        L.append("### Promoted vs Parsed/Inference ratio\n")
        promoted = se.get("promoted_total", 0)
        parsed_inf = se.get("parsed_or_inference_total", 0)
        total = promoted + parsed_inf
        if total:
            L.append(f"- Promoted (extra_vendor → modelo): **{promoted:,}** ({promoted/total*100:.1f}%)")
            L.append(f"- Parsed/inferred direto: **{parsed_inf:,}** ({parsed_inf/total*100:.1f}%)")
        L.append("")

        # Confidence histogram
        L.append("### Confidence histogram\n")
        L.append("| Bucket | Count |")
        L.append("|--------|------:|")
        for b in ("high", "medium", "low", "very-low", "fallback"):
            L.append(f"| {b:10s} | {se.get('confidence_histogram', {}).get(b, 0):,} |")
        L.append("")

        # Cross-binding integrity
        L.append("### Cross-binding integrity\n")
        L.append(f"**Score global: {se.get('integrity_score_pct', 0)}%**\n")
        L.append("| Check | OK | Broken |")
        L.append("|-------|---:|-------:|")
        integ = se.get("integrity", {})
        groups = (
            ("ssid_radio", "SSID ↔ Radio"),
            ("wan_profile_ref", "WANBinding ↔ WANProfile"),
            ("bridge_group_members", "BridgeGroup members ⊂ eth_ports"),
            ("lan_service_vlan", "LANService.vlan ∈ vlans"),
            ("port_route_eth", "PortRoute eth refs"),
        )
        for key, label in groups:
            ok = integ.get(f"{key}_ok", 0)
            broken = integ.get(f"{key}_broken", 0)
            L.append(f"| {label} | {ok} | {broken} |")
        L.append("")

        # Renderer completeness
        L.append("### Renderer subscriber-edge completeness\n")
        L.append("Quantos arquivos por destino emitiram conteúdo subscriber-edge não-vazio.\n")
        L.append("| Destino | Arquivos com edge | Total | Linhas subscriber edge |")
        L.append("|---------|-----------------:|------:|----------------------:|")
        for dst, rc in se.get("renderer_completeness", {}).items():
            L.append(
                f"| {dst} | {rc.get('emitted_files', 0)} | "
                f"{rc.get('total_files', 0)} | {rc.get('lines', 0)} |"
            )
        L.append("")

    # 8. Detalhe por arquivo ----------------------------------------------
    L.append("## 8. Detalhe por arquivo\n")
    for r in reports:
        if "error" in r:
            L.append(f"\n### {r['file']} — FAIL\n```\n{r['error']}\n```\n")
            if r.get("traceback"):
                L.append("Traceback:\n```")
                L.append(r["traceback"])
                L.append("```\n")
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

        # L9 Subscriber edge por arquivo
        se = r.get("subscriber_edge", {})
        if se and not se.get("skipped"):
            L.append("\n**Subscriber edge (L9):**")
            L.append("```")
            L.append(f"  coverage     : {se.get('coverage_pct', 0)}% "
                     f"({se.get('onus_with_edge', 0)}/{se.get('total_onus', 0)} ONUs)")
            ec = se.get("entity_counts", {})
            L.append(f"  radios       : {ec.get('radios', 0)}")
            L.append(f"  ssids        : {ec.get('ssids', 0)}")
            L.append(f"  bridge_grps  : {ec.get('bridge_groups', 0)}")
            L.append(f"  lan_services : {ec.get('lan_services', 0)}")
            L.append(f"  wan_bindings : {ec.get('wan_bindings', 0)}")
            L.append(f"  port_routes  : {ec.get('port_routes', 0)}")
            L.append(f"  stb          : {ec.get('stb_configured', 0)}")
            L.append(f"  multicast    : {ec.get('multicast_bindings', 0)}")
            L.append(f"  eth_native_vlan: {se['eth_native_vlan']['populated']}/{se['eth_native_vlan']['total']} ({se['eth_native_vlan']['pct']}%)")
            L.append(f"  integrity    : {se.get('integrity_score_pct', 0)}% OK")
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
            import traceback
            tb = traceback.format_exc(limit=20)
            print(f"  ⚠ CRASH em {path.name}: {exc!r}")
            print(tb)
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
                metrics = file_metrics(text)
            except Exception:  # noqa: BLE001
                metrics = {"total_lines": 0, "non_blank_lines": 0}
            reports.append({
                "file": path.name,
                "error": repr(exc),
                "traceback": tb,
                "metrics": metrics,
            })

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
