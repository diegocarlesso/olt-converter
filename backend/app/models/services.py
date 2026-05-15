"""
Serviços end-to-end: ServicePort (binding ONU↔VLAN↔GEM↔Traffic),
sessões PPPoE/IPoE, bridges, mappers, vlan-to-gem.
"""
from __future__ import annotations

from typing import Optional

from pydantic import Field

from app.models.base import DomainModel
from app.models.enums import FlowDirection, ServicePortAction
from app.models.provenance import Provenance


class ServicePort(DomainModel):
    """
    Service-Port: o objeto central de provisionamento.

    Vincula uma ONU↔GEM↔VLAN. O motor de equivalência consome este objeto
    para emitir o comando equivalente em qualquer vendor.

    Campos:
      - `match_vlan`  : VLAN tag visto vindo da ONU
      - `action`      : transformação aplicada (replace/translate/transparent/qinq-add)
      - `target_vlan` : VLAN final no lado uplink
      - `user_vlan`   : VLAN entregue ao usuário (Huawei multi-service)
      - `inbound_traffic_profile` / `outbound_traffic_profile`: nomes de TrafficProfile
    """

    service_port_id: int = Field(..., ge=1)
    pon_interface: str
    onu_id: int = Field(..., ge=0, le=255)
    gem_id: Optional[int] = Field(None, ge=0)
    match_vlan: Optional[int] = Field(None, ge=1, le=4094)
    action: ServicePortAction = ServicePortAction.REPLACE
    target_vlan: Optional[int] = Field(None, ge=1, le=4094)
    user_vlan: Optional[int] = Field(None, ge=1, le=4094)
    description: Optional[str] = None
    inbound_traffic_profile: Optional[str] = None
    outbound_traffic_profile: Optional[str] = None
    admin_enabled: bool = True
    provenance: Optional[Provenance] = None


class Bridge(DomainModel):
    """Ponte L2 (modo bridge)."""

    name: str
    vlan_id: int = Field(..., ge=1, le=4094)
    member_ports: list[str] = Field(default_factory=list)


class PPPoESession(DomainModel):
    username: str
    password: Optional[str] = None
    service_name: Optional[str] = None
    onu_interface: Optional[str] = None
    vlan_id: Optional[int] = None


class IPoESession(DomainModel):
    ip_address: str
    netmask: Optional[str] = None
    gateway: Optional[str] = None
    vlan_id: Optional[int] = None
    onu_interface: Optional[str] = None


class VLANToGEMMapping(DomainModel):
    """Mapeamento explícito VLAN→GEM dentro do contexto de uma ONU/profile."""

    vlan_id: int = Field(..., ge=1, le=4094)
    gem_id: int = Field(..., ge=0)
    direction: FlowDirection = FlowDirection.BOTH


__all__ = [
    "ServicePort",
    "Bridge",
    "PPPoESession",
    "IPoESession",
    "VLANToGEMMapping",
]
