from __future__ import annotations

import re

from app.models.universal_core import PON

RX_PON = re.compile(r"^interface\s+gpon\s+(\d+/\d+)$", re.IGNORECASE)


def parse_pons(lines: list[str]) -> list[PON]:
    pons: list[PON] = []
    for line in lines:
        if m := RX_PON.match(line.strip()):
            pons.append(PON(name=f"pon-{m.group(1)}"))
    return pons
