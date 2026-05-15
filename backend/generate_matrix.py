"""
Renderiza a Compatibility Matrix em `docs/COMPATIBILITY_MATRIX.md` para
consulta rápida sem precisar do backend rodando.

Uso:
    python generate_matrix.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.models import Vendor                          # noqa: E402
from app.services.compatibility import (               # noqa: E402
    FEATURES,
    cell,
    conversion_score,
    vendor_scores,
)


DOCS = Path(__file__).resolve().parent.parent / "docs"
VENDORS = [Vendor.FIBERHOME, Vendor.HUAWEI, Vendor.ZTE, Vendor.DATACOM]


_LEVEL_BADGE = {
    "FULL": "✅",
    "PARTIAL": "⚠️",
    "NONE": "❌",
    "UNSUPPORTED": "🚫",
}


def render() -> str:
    out: list[str] = []
    out.append("# Compatibility Matrix\n")
    out.append(
        "> Gerado por `generate_matrix.py`. Reflete o estado atual do "
        "parser, renderer e engine de equivalência de cada vendor.\n"
    )
    out.append("\n## Scores globais por vendor\n")
    out.append("| Vendor | Parser coverage | Renderer completeness |")
    out.append("|--------|----------------:|----------------------:|")
    for v in VENDORS:
        s = vendor_scores(v)
        out.append(
            f"| **{v.value}** | "
            f"{s['parser_coverage_score']:.0%} | "
            f"{s['renderer_completeness_score']:.0%} |"
        )

    out.append("\n## Semantic fidelity por par (origem → destino)\n")
    out.append("| | " + " | ".join(f"→ **{v.value}**" for v in VENDORS) + " |")
    out.append("|" + "---|" * (len(VENDORS) + 1))
    for src in VENDORS:
        row = [f"**{src.value}** ↓"]
        for tgt in VENDORS:
            if src == tgt:
                row.append("—")
                continue
            sc = conversion_score(src, tgt)
            row.append(
                f"{sc['semantic_fidelity_score']:.0%} ({sc['FULL']}/{sc['PARTIAL']}/{sc['NONE']}/{sc['UNSUPPORTED']})"
            )
        out.append("| " + " | ".join(row) + " |")

    out.append("\nLegenda dos contadores: (FULL / PARTIAL / NONE / UNSUPPORTED)")
    out.append("")

    out.append("\n## Matriz detalhada por feature\n")
    for src in VENDORS:
        out.append(f"\n### Origem: **{src.value}**\n")
        out.append("| Feature | " + " | ".join(f"→ {t.value}" for t in VENDORS if t != src) + " |")
        out.append("|---" + "|---" * (len(VENDORS) - 1) + "|")
        for feature in FEATURES:
            row = [f"`{feature}`"]
            for tgt in VENDORS:
                if tgt == src:
                    continue
                c = cell(src, tgt, feature)
                badge = _LEVEL_BADGE[c.level.value]
                row.append(f"{badge} {c.semantic_fidelity:.0%}")
            out.append("| " + " | ".join(row) + " |")
    out.append("")
    out.append("\nLegenda: ✅ FULL (≥85%) · ⚠️ PARTIAL (45-84%) · ❌ NONE (1-44%) · 🚫 UNSUPPORTED (0%)")
    out.append("\nNúmero ao lado do badge = `semantic_fidelity_score` calculado como "
               "média ponderada (parser 30% + renderer 30% + equivalência 40%).")
    return "\n".join(out)


def main() -> int:
    DOCS.mkdir(exist_ok=True)
    md = render()
    (DOCS / "COMPATIBILITY_MATRIX.md").write_text(md, encoding="utf-8")
    print(f"→ {DOCS / 'COMPATIBILITY_MATRIX.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
