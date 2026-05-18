"""
Camada PON: PONs, ONUs, GEMPorts, T-CONTs, portas Ethernet de ONU.

Estes são os componentes mais sensíveis do modelo — toda a integridade dos
bindings (ONU↔GEM↔T-CONT↔DBA) acontece aqui.
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import Field, field_validator

from app.models.base import DomainModel
from app.models.enums import (
    AdminState,
    OperationMode,
    PortType,
    VLANMode,
)
from app.models.provenance import Provenance


class TCONT(DomainModel):
    """
    Transmission Container — agendamento de upstream associado a um DBA.

    `dba_profile_name` é o vínculo lógico (textual) ao DBAProfile.name; o
    motor de equivalência resolve esse nome durante o render para o destino.
    """

    tcont_id: int = Field(..., ge=0, le=31, description="ID local na ONU (0..31)")
    name: Optional[str] = None
    dba_profile_id: Optional[int] = None
    dba_profile_name: Optional[str] = None


class GEMPort(DomainModel):
    """
    GEM Port (G-PON Encapsulation Method) — pipe lógico ONU↔OLT.

    Vincula-se a um T-CONT (`tcont_id`) e tipicamente carrega uma VLAN
    específica (`vlan_id`). A combinação (gem_id, vlan, tcont, traffic_profile)
    define a QoS efetiva do serviço dentro daquela ONU.
    """

    gem_id: int = Field(..., ge=0)
    name: Optional[str] = None
    tcont_id: int = Field(..., ge=0, le=31)
    vlan_id: Optional[int] = Field(None, ge=1, le=4094)
    encryption: bool = False
    queue_id: Optional[int] = None
    upstream_traffic_profile: Optional[str] = None
    downstream_traffic_profile: Optional[str] = None


class EthernetPort(DomainModel):
    """
    Porta UNI ethernet dentro de uma ONU/ONT (eth 1, eth 2, …).

    Expandida pela camada L9 (subscriber edge):
      - `bridge_mode`: bridge / router / mixed
      - `bridge_group_id`: vínculo a BridgeGroup
      - `wan_binding_id`: vínculo a WANBinding
      - `lan_service_name`: vínculo a LANService
      - `isolation_enabled`: client isolation L2
      - `loop_detect_enabled`: detecção de loop L2
      - `dhcp_source`: from-onu | from-internet (ZTE)
      - `is_stb`: porta dedicada a STB IPTV
    """

    port_id: int = Field(..., ge=1, le=8)
    admin_state: AdminState = AdminState.UP
    negotiation_auto: bool = True
    native_vlan: Optional[int] = Field(None, ge=1, le=4094)
    tagged_vlans: list[int] = Field(default_factory=list)
    untagged_vlans: list[int] = Field(default_factory=list)
    translation_vlan: Optional[int] = Field(None, ge=1, le=4094)
    user_vlan: Optional[int] = Field(None, ge=1, le=4094)
    priority: Optional[int] = Field(None, ge=0, le=7)
    description: Optional[str] = None
    # L9 subscriber edge bindings
    bridge_mode: Optional[str] = None     # str para evitar import circular; enum em subscriber_edge
    bridge_group_id: Optional[int] = None
    wan_binding_id: Optional[int] = None
    lan_service_name: Optional[str] = None
    isolation_enabled: bool = False
    loop_detect_enabled: bool = False
    dhcp_source: Optional[str] = None     # "from-onu" | "from-internet"
    is_stb: bool = False


class PONOpticalParams(DomainModel):
    """Parâmetros ópticos / DBA por porta PON."""

    tx_power_dbm: Optional[float] = None
    rx_threshold_dbm: Optional[float] = None
    dba_assignment_mode: str = "max-bandwidth-usage"


class PON(DomainModel):
    """Porta PON na OLT."""

    interface: str = Field(..., description="Nome canônico, ex: pon-1/3/1, gpon 0/3/1")
    chassis: int = 1
    slot: Optional[int] = None
    port: Optional[int] = None
    port_type: PortType = PortType.GPON
    description: Optional[str] = None
    admin_state: AdminState = AdminState.UP
    ont_auto_find: bool = True
    optical: PONOpticalParams = Field(default_factory=PONOpticalParams)
    onus: list["ONU"] = Field(default_factory=list)


class ONU(DomainModel):
    """
    ONU/ONT registrada em uma PON.

    `line_profile_name` e `service_profile_name` são chaves lógicas para
    LineProfile.name e ServiceProfile.name. Mantemos a referência por nome
    (não por id) porque o id muda entre vendors mas o nome é o conceito
    semântico estável.

    A integridade dessas referências é checada pelo validador.
    """

    pon_interface: str
    onu_id: int = Field(..., ge=0, le=255)
    serial_number: Optional[str] = None
    password: Optional[str] = None
    description: Optional[str] = None
    onu_type: Optional[str] = Field(
        None,
        description="Modelo/EID da ONU (ex: HG6145E, 5506-04-FA, AN5506-04-F1)",
    )
    line_profile_name: Optional[str] = None
    service_profile_name: Optional[str] = None
    line_profile_id: Optional[int] = None
    service_profile_id: Optional[int] = None
    mode: OperationMode = OperationMode.BRIDGE
    admin_state: AdminState = AdminState.UP

    native_vlan: Optional[int] = Field(None, ge=1, le=4094)
    user_vlan: Optional[int] = Field(None, ge=1, le=4094)
    vlan_mode: VLANMode = VLANMode.TAG

    tconts: list[TCONT] = Field(default_factory=list)
    gemports: list[GEMPort] = Field(default_factory=list)
    eth_ports: list[EthernetPort] = Field(default_factory=list)

    # L9 subscriber edge — modelos formais (preenchidos pelo promotion engine)
    # Importados lazily para evitar ciclo (subscriber_edge usa base.DomainModel)
    radios: list = Field(default_factory=list, description="list[WiFiRadio]")
    ssids: list = Field(default_factory=list, description="list[WiFiSSID]")
    bridge_groups: list = Field(default_factory=list, description="list[BridgeGroup]")
    lan_services: list = Field(default_factory=list, description="list[LANService]")
    wan_bindings: list = Field(default_factory=list, description="list[WANBinding]")
    multicast_bindings: list = Field(default_factory=list, description="list[MulticastBinding]")
    port_routes: list = Field(default_factory=list, description="list[PortRoute]")
    stb: Optional[Any] = Field(default=None, description="Optional[STBConfig]")

    # Capacidades habilitadas
    wifi_enabled: bool = False
    catv_enabled: bool = False
    voip_enabled: bool = False
    omci_managed: bool = True

    # Slot/PON/index numéricos (preenchidos por conveniência)
    slot: Optional[int] = None
    pon_port: Optional[int] = None

    # Extras proprietários (preservados via extra="allow")
    extra_vendor: dict[str, Any] = Field(default_factory=dict)

    # Proveniência (preenchida quando ONU é inferida/sintetizada)
    provenance: Optional[Provenance] = None

    @field_validator("serial_number")
    @classmethod
    def _normalize_sn(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return v.strip().upper()


# Pydantic V2 forward refs
PON.model_rebuild()


__all__ = [
    "TCONT",
    "GEMPort",
    "EthernetPort",
    "PONOpticalParams",
    "PON",
    "ONU",
]
