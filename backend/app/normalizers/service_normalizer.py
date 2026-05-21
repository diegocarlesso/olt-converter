from __future__ import annotations

from app.models.universal_core import OLTConfig, ServiceBinding, ServicePort


def normalize_services(config: OLTConfig) -> OLTConfig:
    if config.service_bindings:
        return config
    bindings = [
        ServiceBinding(
            binding_id=sp.service_port_id,
            customer_vlan=sp.customer_vlan,
            service_vlan=sp.service_vlan,
            uplink=sp.uplink,
        )
        for sp in config.service_ports
    ]
    return config.model_copy(update={"service_bindings": bindings})
