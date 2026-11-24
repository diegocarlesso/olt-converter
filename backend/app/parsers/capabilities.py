from dataclasses import dataclass


@dataclass(frozen=True)
class ParserCapabilities:
    vlans: bool = False
    pons: bool = False
    onus: bool = False
    service_bindings: bool = False
    qos_partial: bool = False
    multicast: bool = False
