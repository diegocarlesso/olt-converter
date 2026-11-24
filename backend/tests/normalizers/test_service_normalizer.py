from app.models.universal_core import OLTConfig, ServicePort
from app.normalizers.service_normalizer import normalize_services


def test_normalize_service_ports_to_bindings():
    cfg = OLTConfig(vendor="fiberhome", service_ports=[ServicePort(service_port_id=1, customer_vlan=100, service_vlan=200, uplink="uplink-1")])
    out = normalize_services(cfg)
    assert len(out.service_bindings) == 1
    assert out.service_bindings[0].customer_vlan == 100
