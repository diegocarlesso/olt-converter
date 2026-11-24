from __future__ import annotations

import re

from app.models.universal_core import VLAN

RX_VLAN = re.compile(r"^vlan\s+(\d+)(?:\s+name\s+(\S+))?$", re.IGNORECASE)


def parse_vlans(lines: list[str]) -> list[VLAN]:
    vlans: list[VLAN] = []
    for line in lines:
        if m := RX_VLAN.match(line.strip()):
            vlans.append(VLAN(vlan_id=int(m.group(1)), name=m.group(2)))
    return vlans
