from app.models.universal_core import OLTConfig, ONU, QoSProfile, TCONT, GEMPort


def test_gem_tcont_relationship_modeling():
    onu = ONU(pon_ref="pon-1/1", onu_id=1, tconts=[TCONT(tcont_id=1)], gem_ports=[GEMPort(gem_id=10, tcont_id=1)])
    cfg = OLTConfig(vendor="fiberhome", onus=[onu], qos_profiles=[QoSProfile(name="q1", priority=1)])
    assert cfg.onus[0].gem_ports[0].tcont_id == cfg.onus[0].tconts[0].tcont_id
