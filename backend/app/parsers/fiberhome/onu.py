from __future__ import annotations

import re

from app.models.universal_core import ONU

RX_ONU = re.compile(r"^onu\s+add\s+(\d+/\d+)\s+(\d+)\s+sn\s+(\S+)$", re.IGNORECASE)


def parse_onus(lines: list[str]) -> list[ONU]:
    onus: list[ONU] = []
    for line in lines:
        if m := RX_ONU.match(line.strip()):
            onus.append(ONU(pon_ref=f"pon-{m.group(1)}", onu_id=int(m.group(2)), serial_number=m.group(3)))
    return onus
