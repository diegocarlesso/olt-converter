"""
Smoke test ampliado: roda parser → equivalência → render para todas as
combinações (origem × destino) e mostra cobertura.

Uso:

    cd olt-converter/backend
    python smoke_test.py
    python smoke_test.py --real    # usa modelos-config/ do operador
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.models import Vendor                          # noqa: E402
from app.parsers import detect_vendor, parser_registry  # noqa: E402
from app.renderers import renderer_registry             # noqa: E402
from app.services.conversion import convert             # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
REAL = ROOT.parent / "modelos-config"   # E:\OLT CONFIG CONVERTER ENGINE\modelos-config


def banner(text: str) -> None:
    print(f"\n{'=' * 78}\n  {text}\n{'=' * 78}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--real", action="store_true", help="usar modelos-config/")
    args = parser.parse_args()

    banner("Registry status")
    print("Parsers  :", {v.value: p.model_family for v, p in parser_registry().items()})
    print("Renderers:", {v.value: r.model_family for v, r in renderer_registry().items()})

    if args.real:
        samples = sorted(REAL.glob("*.txt")) if REAL.exists() else []
        if not samples:
            print(f"!! {REAL} vazio — caindo para examples/")
            samples = sorted(EXAMPLES.glob("*.cfg"))
    else:
        samples = sorted(EXAMPLES.glob("*.cfg"))

    failures: list[str] = []
    summary_table: list[tuple[str, str, int, str, str]] = []

    for sample in samples:
        banner(f"FILE: {sample.name}")
        text = sample.read_text(encoding="utf-8", errors="replace")

        try:
            parser_cls = detect_vendor(text)
            print(f"vendor detected = {parser_cls.vendor.value} ({parser_cls.model_family})")
        except ValueError as exc:
            print(f"!! detect failed: {exc}")
            failures.append(f"{sample.name}: detect failed")
            continue

        for dst in [Vendor.FIBERHOME, Vendor.ZTE, Vendor.HUAWEI, Vendor.DATACOM]:
            if dst == parser_cls.vendor:
                continue
            try:
                result = convert(text, target_vendor=dst)
                stats = result.config.stats()
                v = result.validation.by_severity()
                line = (
                    f"  → {dst.value:9s} | len={len(result.rendered):>6d} "
                    f"err={v['error']:>2d} warn={v['warning']:>2d} info={v['info']:>2d} "
                    f"| vlans={stats['vlans']:>3d} "
                    f"onus={stats['onus']:>3d} "
                    f"sp={stats['service_ports']:>3d} "
                    f"dba={stats['dba_profiles']:>2d} "
                    f"srv={stats['service_profiles']:>2d}"
                )
                print(line)
                summary_table.append(
                    (sample.name, dst.value, len(result.rendered), v["error"], v["warning"])
                )
                if len(result.rendered) == 0:
                    failures.append(f"{sample.name}→{dst.value}: empty output")
            except Exception as exc:  # noqa: BLE001
                print(f"  → {dst.value:9s} | EXCEPTION: {exc!r}")
                failures.append(f"{sample.name}→{dst.value}: {exc!r}")

    banner("RESULT")
    if failures:
        print(f"FAIL — {len(failures)} problemas:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"OK — {len(summary_table)} conversões bem-sucedidas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
