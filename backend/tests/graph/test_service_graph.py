from app.graph.service_graph import build_service_graph
from app.models.universal_core import OLTConfig, ONU, TCONT, GEMPort


def test_build_service_graph_dependencies():
    onu = ONU(pon_ref="pon-1/1", onu_id=1, tconts=[TCONT(tcont_id=1, dba_profile="d1")], gem_ports=[GEMPort(gem_id=10, tcont_id=1)])
    graph = build_service_graph(OLTConfig(vendor="fiberhome", onus=[onu]))
    assert any(e.relation == "has_tcont" for e in graph.edges)
    assert any(e.relation == "maps_gem" for e in graph.edges)
