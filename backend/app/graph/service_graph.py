from __future__ import annotations

from dataclasses import dataclass, field

from app.models.universal_core import OLTConfig


@dataclass(frozen=True)
class ServiceNode:
    node_id: str
    node_type: str


@dataclass(frozen=True)
class ServiceEdge:
    src: str
    dst: str
    relation: str


@dataclass
class ServiceGraph:
    nodes: list[ServiceNode] = field(default_factory=list)
    edges: list[ServiceEdge] = field(default_factory=list)

    def trace_dependencies(self, node_id: str) -> list[ServiceEdge]:
        return [e for e in self.edges if e.src == node_id]


def build_service_graph(config: OLTConfig) -> ServiceGraph:
    g = ServiceGraph()
    for onu in config.onus:
        onu_id = f"onu:{onu.pon_ref}:{onu.onu_id}"
        g.nodes.append(ServiceNode(onu_id, "ONU"))
        for t in onu.tconts:
            tid = f"tcont:{onu.pon_ref}:{onu.onu_id}:{t.tcont_id}"
            g.nodes.append(ServiceNode(tid, "TCONT"))
            g.edges.append(ServiceEdge(onu_id, tid, "has_tcont"))
        for gem in onu.gem_ports:
            gid = f"gem:{onu.pon_ref}:{onu.onu_id}:{gem.gem_id}"
            tid = f"tcont:{onu.pon_ref}:{onu.onu_id}:{gem.tcont_id}"
            g.nodes.append(ServiceNode(gid, "GEM"))
            g.edges.append(ServiceEdge(tid, gid, "maps_gem"))
    return g
