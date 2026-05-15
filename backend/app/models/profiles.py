"""
Profiles: DBA, Traffic, Line, Service, WAN, ONU-Type, Policy-Route.

Em GPON estes profiles são o coração da configuração — definem QoS,
capabilities da ONU, e binding de gemports/t-conts.
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import Field

from app.models.base import DomainModel
from app.models.enums import DBAType, ProfileScope
from app.models.provenance import Provenance


class DBAProfile(DomainModel):
    """
    DBA Profile — controla a alocação dinâmica de banda upstream.

    O significado dos campos depende do `type`:
      - type1: apenas `fix_bandwidth` (banda fixa)
      - type2: apenas `assured_bandwidth`
      - type3: `assured_bandwidth` + `max_bandwidth`
      - type4: apenas `max_bandwidth` (best-effort)
      - type5: `fix` + `assured` + `max`
    """

    profile_id: int = Field(..., ge=0)
    name: str
    type: DBAType = DBAType.TYPE4
    fix_bandwidth: Optional[int] = None       # kbps
    assured_bandwidth: Optional[int] = None   # kbps
    max_bandwidth: Optional[int] = None       # kbps
    bandwidth_compensate: bool = False
    provenance: Optional[Provenance] = None


class TrafficProfile(DomainModel):
    """
    Traffic Profile / Traffic Table (Huawei: traffic table ip index N).

    Define limitadores de banda CIR/PIR/CBS/PBS aplicáveis a um service-port.
    """

    profile_id: int = Field(..., ge=0)
    name: str
    cir: Optional[int] = None    # committed information rate, kbps
    cbs: Optional[int] = None    # committed burst size, bytes
    pir: Optional[int] = None    # peak information rate, kbps
    pbs: Optional[int] = None    # peak burst size, bytes
    color_mode: str = "color-blind"
    priority: int = 0
    inner_priority: int = 0
    priority_policy: str = "local-setting"
    referenced_count: int = 0    # populado pelo validador
    provenance: Optional[Provenance] = None


class LineProfile(DomainModel):
    """
    Line Profile da ONU.

    Carrega: bindings T-CONT↔DBA, GEMPorts pertencentes ao profile, e
    "mappers" (mapeamento VLAN→GEM dentro da ONU).
    """

    profile_id: int = Field(..., ge=0)
    name: str
    scope: ProfileScope = ProfileScope.GPON
    tcont_bindings: list[dict[str, Any]] = Field(
        default_factory=list,
        description='[{"tcont_id": 1, "dba_profile_name": "DBA-1G"}, ...]',
    )
    gemport_bindings: list[dict[str, Any]] = Field(
        default_factory=list,
        description='[{"gem_id": 1, "tcont_id": 1, "encryption": false}, ...]',
    )
    mappers: list[dict[str, Any]] = Field(
        default_factory=list,
        description='[{"vlan_id": 100, "gem_id": 1}, ...]',
    )
    provenance: Optional[Provenance] = None


class PortConfig(DomainModel):
    """Quantidade/modo de portas dentro de um Service Profile."""

    pots: int = 0
    eth: int = 1
    catv: int = 0
    wifi: int = 0
    veip: int = 0
    pots_adaptive: bool = False
    eth_adaptive: bool = False
    catv_adaptive: bool = False
    wifi_adaptive: bool = False


class ServiceProfile(DomainModel):
    """
    Service Profile / ONU Service Profile (Huawei: ont-srvprofile, ZTE: service-profile).

    Define as capabilities da ONU e port-vlan translations (que tornam-se
    service-ports na hora de provisionar).
    """

    profile_id: int = Field(..., ge=0)
    name: str
    scope: ProfileScope = ProfileScope.GPON
    ports: PortConfig = Field(default_factory=PortConfig)
    port_vlan_translations: list[dict[str, Any]] = Field(
        default_factory=list,
        description='[{"port_type": "eth", "port": 1, "translation": 100, "user_vlan": 100}, ...]',
    )
    ring_check_enabled: bool = False
    multicast_enabled: bool = False
    igmp_mode: Optional[str] = None
    upstream_priority: Optional[int] = None
    provenance: Optional[Provenance] = None


class WANProfile(DomainModel):
    """ONU WAN Profile (Huawei: ont wan-profile)."""

    profile_id: int
    name: str
    nat_enabled: bool = False
    dhcp_enabled: bool = False
    pppoe_enabled: bool = False
    vlan_id: Optional[int] = None
    upstream_priority: Optional[int] = None


class PolicyRouteProfile(DomainModel):
    """ONU Policy-Route Profile."""

    profile_id: int
    name: str
    rules: list[dict[str, Any]] = Field(default_factory=list)


class ONUTypeProfile(DomainModel):
    """
    Definição de "tipo de ONU" (Fiberhome `cs onu profile` / Huawei `ont-type`).

    Captura as capabilities físicas do modelo da ONU (4 LAN, 2 POTS, wifi,
    etc.) que o renderer destino precisa para emitir o equivalente.
    """

    type_id: int
    name: str
    onu_type_code: Optional[int] = None
    pon_type_code: Optional[int] = None
    capability_code: Optional[int] = None
    lan1g: int = 0
    lan10g: int = 0
    pots: int = 0
    wifi: int = 0
    catv: int = 0
    veip: int = 0
    poe: int = 0
    vendor_code: Optional[str] = None
    eid: Optional[str] = None     # equipment identifier (ex: HG6145D2)


__all__ = [
    "DBAProfile",
    "TrafficProfile",
    "LineProfile",
    "ServiceProfile",
    "PortConfig",
    "WANProfile",
    "PolicyRouteProfile",
    "ONUTypeProfile",
]
