"""Helpers de manipulação de texto/regex usados por todos os parsers."""
from __future__ import annotations

import re
from typing import Iterator


_BLANK_RE = re.compile(r"^\s*$")
_COMMENT_RE = re.compile(r"^\s*(?://|#|!).*$")


def iter_clean_lines(config_text: str, drop_comments: bool = False) -> Iterator[str]:
    """Itera sobre as linhas removendo CRLF e (opcionalmente) comentários."""
    for raw in config_text.splitlines():
        line = raw.rstrip("\r\n").rstrip()
        if not line:
            continue
        if _BLANK_RE.match(line):
            continue
        if drop_comments and _COMMENT_RE.match(line):
            continue
        yield line


def strip_quotes(value: str) -> str:
    """Remove aspas duplas/simples ao redor de um valor."""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def safe_int(value: str | int | None, default: int | None = None) -> int | None:
    """Converte para int sem explodir em valores inválidos."""
    if value is None:
        return default
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def parse_interface_path(raw: str) -> dict[str, int | str | None]:
    """
    Quebra strings de interface comuns em componentes:

      gei-1/1/5          → {chassis:1, slot:1, port:5}
      xgei-1/1/2         → idem
      gpon_olt-1/3/1     → {chassis:1, slot:3, port:1}
      gpon_onu-1/3/1:5   → {chassis:1, slot:3, port:1, onu:5}
      gpon-0/1/1         → {chassis:0, slot:1, port:1}
      0/9/0              → {chassis:0, slot:9, port:0}
    """
    raw = raw.strip()
    m = re.search(r"(\d+)/(\d+)/(\d+)(?::(\d+))?$", raw)
    if not m:
        return {"raw": raw}
    chassis, slot, port, onu = m.groups()
    out: dict[str, int | str | None] = {
        "chassis": int(chassis),
        "slot": int(slot),
        "port": int(port),
    }
    if onu is not None:
        out["onu"] = int(onu)
    return out
