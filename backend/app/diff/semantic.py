from __future__ import annotations

from dataclasses import dataclass, field

from app.models.universal_core import OLTConfig


@dataclass
class SemanticDiffResult:
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    modified: list[str] = field(default_factory=list)
    unsupported: list[str] = field(default_factory=list)
    lossy: list[str] = field(default_factory=list)


def semantic_diff(a: OLTConfig, b: OLTConfig) -> SemanticDiffResult:
    out = SemanticDiffResult()
    av = {v.vlan_id for v in a.vlans}
    bv = {v.vlan_id for v in b.vlans}
    out.added += [f"vlan:{i}" for i in sorted(bv - av)]
    out.removed += [f"vlan:{i}" for i in sorted(av - bv)]

    ao = {(o.pon_ref, o.onu_id) for o in a.onus}
    bo = {(o.pon_ref, o.onu_id) for o in b.onus}
    out.added += [f"onu:{p}/{i}" for p, i in sorted(bo - ao)]
    out.removed += [f"onu:{p}/{i}" for p, i in sorted(ao - bo)]

    ap = {p.name for p in a.pons}
    bp = {p.name for p in b.pons}
    out.added += [f"pon:{n}" for n in sorted(bp - ap)]
    out.removed += [f"pon:{n}" for n in sorted(ap - bp)]

    if len(a.qos_profiles) != len(b.qos_profiles):
        out.modified.append("qos_profiles")
    if len(a.multicast_profiles) != len(b.multicast_profiles):
        out.modified.append("multicast_profiles")
    return out
