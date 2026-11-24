from __future__ import annotations

import re

from app.models.universal_core import ServiceBinding

RX_SERVICE = re.compile(r"^service-port\s+(\d+)\s+vlan\s+(\d+)\s+pon\s+(\d+/\d+)\s+onu\s+(\d+)(?:\s+gem\s+(\d+))?$", re.IGNORECASE)


def parse_service_bindings(lines: list[str]) -> list[ServiceBinding]:
    bindings: list[ServiceBinding] = []
    for line in lines:
        if m := RX_SERVICE.match(line.strip()):
            bindings.append(
                ServiceBinding(
                    binding_id=int(m.group(1)),
                    customer_vlan=int(m.group(2)),
                    service_vlan=int(m.group(2)),
                    uplink="unknown-uplink",
                    pon_ref=f"pon-{m.group(3)}",
                    onu_id=int(m.group(4)),
                    gem_id=int(m.group(5)) if m.group(5) else None,
                )
            )
    return bindings
