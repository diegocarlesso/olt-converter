"""
Camada de rede L2/L3: VLANs, uplinks, rotas, LACP.
"""
from __future__ import annotations

from typing import Optional

from pydantic import Field, field_validator

from app.models.base import DomainModel
from app.models.enums import (
    AdminState,
    LACPMode,
    PortType,
    ServiceType,
    TrunkMode,
    VLANMode,
)


class VLAN(DomainModel):
    """
    Representação canônica de uma VLAN no plano de configuração.

    Pode representar tanto uma VLAN simples quanto uma VLAN com IP atribuído
    (management) ou VLAN com tradução/QinQ. O campo `service_vlan_id` permite
    vincular esta VLAN a uma "service-vlan" lógica (conceito Fiberhome) ou a
    um service-port (Huawei/ZTE) — preservando a relação de serviço end-to-end.
    """

    id: int = Field(..., ge=1, le=4094, description="ID da VLAN (1-4094)")
    name: Optional[str] = Field(None, description="Nome legível (opcional)")
    description: Optional[str] = None
    mode: VLANMode = VLANMode.TAG
    service_type: ServiceType = ServiceType.DATA
    smart: bool = Field(
        default=True,
        description="Huawei smart-vlan = serviço com encapsulamento de tag",
    )

    # QinQ
    qinq_outer: Optional[int] = Field(None, ge=1, le=4094)

    # Tradução (Fiberhome translation / Huawei port vlan translation)
    translate_to: Optional[int] = Field(None, ge=1, le=4094)
    user_vlan: Optional[int] = Field(None, ge=1, le=4094)

    # IP interface (VLAN management / IP routing)
    ip_address: Optional[str] = None
    netmask: Optional[str] = None
    is_management: bool = False

    # Cross-references
    service_vlan_id: Optional[int] = Field(
        None, description="ID da ServiceVLAN à qual esta VLAN pertence"
    )

    @field_validator("ip_address")
    @classmethod
    def _strip_ipmask(cls, v: Optional[str]) -> Optional[str]:
        if v and "/" in v:
            return v.split("/")[0]
        return v


class ServiceVLAN(DomainModel):
    """
    "Service-VLAN" lógica (conceito Fiberhome WOS).

    Agrupa uma faixa de VLANs (`vlan_begin`..`vlan_end`) sob um nome de serviço
    e tipo (`data`/`iptv`/`voip`/`management`). Em outros vendors o conceito é
    expresso de outras formas (Huawei: smart-vlan + service-port; ZTE: vport
    + service-port), e o motor de equivalência converte entre as
    representações.
    """

    service_id: int = Field(..., ge=1)
    name: str
    service_type: ServiceType = ServiceType.DATA
    vlan_begin: int = Field(..., ge=1, le=4094)
    vlan_end: int = Field(..., ge=1, le=4094)
    description: Optional[str] = None


class StaticRoute(DomainModel):
    destination: str
    netmask: str
    gateway: str
    metric: int = 1
    description: Optional[str] = None


class LACPGroup(DomainModel):
    """Agregação LACP (link-aggregation group)."""

    group_id: int
    mode: LACPMode = LACPMode.ACTIVE
    member_ports: list[str] = Field(default_factory=list)
    lacp_key: Optional[int] = None
    description: Optional[str] = None


class Uplink(DomainModel):
    """
    Porta de uplink da OLT.

    `interface` carrega o nome canônico do vendor de origem (ex: `gei-1/1/5`,
    `0/9/0`, `ten-gigabit-ethernet 1/1/9`). O sistema de mapeamento traduz
    este nome para o vocabulário do destino antes do render.
    """

    interface: str
    slot: Optional[int] = None
    port: Optional[int] = None
    sub_port: Optional[int] = None
    port_type: PortType = PortType.GE
    description: Optional[str] = None
    admin_state: AdminState = AdminState.UP
    enabled: bool = True
    mode: TrunkMode = TrunkMode.TRUNK
    native_vlan: Optional[int] = Field(None, ge=1, le=4094)
    allowed_vlans: list[int] = Field(default_factory=list)
    speed_mbps: Optional[int] = None
    lacp_group: Optional[int] = None
    lacp_mode: LACPMode = LACPMode.NONE
    is_management_uplink: bool = False


__all__ = [
    "VLAN",
    "ServiceVLAN",
    "StaticRoute",
    "LACPGroup",
    "Uplink",
]
