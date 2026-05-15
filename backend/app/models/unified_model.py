"""
Modelo universal `OLTConfig` — Pydantic 2.

Esta classe é a *única* representação intermediária da pipeline:

    PARSER (vendor X)  →  OLTConfig  →  RENDERER (vendor Y)

Todo o estado da OLT (hardware, network, profiles, services, system) é
expresso como atributos fortemente tipados deste objeto. Tudo o que um
parser não consegue mapear semanticamente vai para `raw_unparsed` (para
auditoria) — nada é perdido.
"""
from __future__ import annotations

from typing import Optional

from pydantic import Field

from app.models.base import DomainModel
from app.models.enums import Vendor
from app.models.network import (
    LACPGroup,
    ServiceVLAN,
    StaticRoute,
    Uplink,
    VLAN,
)
from app.models.pon import (
    EthernetPort,
    GEMPort,
    PON,
    ONU,
    PONOpticalParams,
    TCONT,
)
from app.models.profiles import (
    DBAProfile,
    LineProfile,
    ONUTypeProfile,
    PolicyRouteProfile,
    PortConfig,
    ServiceProfile,
    TrafficProfile,
    WANProfile,
)
from app.models.qos import (
    IGMPConfig,
    MulticastConfig,
    OMCIConfig,
    QoSAttachment,
    QoSPolicy,
)
from app.models.services import (
    Bridge,
    IPoESession,
    PPPoESession,
    ServicePort,
    VLANToGEMMapping,
)
from app.models.system import (
    AAAConfig,
    Board,
    LineIDConfig,
    LoggingConfig,
    NTPServer,
    RadiusServer,
    SNMPCommunity,
    SNMPConfig,
    SSHConfig,
    User,
)


class OLTConfig(DomainModel):
    """Configuração canônica de uma OLT (independente de vendor)."""

    # ---- Identificação --------------------------------------------------
    hostname: str = "OLT-DEFAULT"
    vendor: Vendor = Vendor.UNKNOWN
    model: str = ""
    firmware: Optional[str] = None
    description: Optional[str] = None
    timezone: Optional[str] = None

    # ---- Hardware -------------------------------------------------------
    boards: list[Board] = Field(default_factory=list)

    # ---- Camada de rede ------------------------------------------------
    vlans: list[VLAN] = Field(default_factory=list)
    service_vlans: list[ServiceVLAN] = Field(default_factory=list)
    uplinks: list[Uplink] = Field(default_factory=list)
    lacp_groups: list[LACPGroup] = Field(default_factory=list)
    static_routes: list[StaticRoute] = Field(default_factory=list)

    # ---- Camada PON / GPON ---------------------------------------------
    pons: list[PON] = Field(default_factory=list)
    onus: list[ONU] = Field(default_factory=list)
    service_ports: list[ServicePort] = Field(default_factory=list)
    vlan_to_gem: list[VLANToGEMMapping] = Field(default_factory=list)

    # ---- Profiles -------------------------------------------------------
    dba_profiles: list[DBAProfile] = Field(default_factory=list)
    traffic_profiles: list[TrafficProfile] = Field(default_factory=list)
    line_profiles: list[LineProfile] = Field(default_factory=list)
    service_profiles: list[ServiceProfile] = Field(default_factory=list)
    wan_profiles: list[WANProfile] = Field(default_factory=list)
    policy_route_profiles: list[PolicyRouteProfile] = Field(default_factory=list)
    onu_type_profiles: list[ONUTypeProfile] = Field(default_factory=list)

    # ---- Serviços L3 ---------------------------------------------------
    bridges: list[Bridge] = Field(default_factory=list)
    pppoe_sessions: list[PPPoESession] = Field(default_factory=list)
    ipoe_sessions: list[IPoESession] = Field(default_factory=list)

    # ---- Plataforma / Sistema -----------------------------------------
    users: list[User] = Field(default_factory=list)
    aaa: AAAConfig = Field(default_factory=AAAConfig)
    radius_servers: list[RadiusServer] = Field(default_factory=list)
    ntp_servers: list[NTPServer] = Field(default_factory=list)
    snmp: Optional[SNMPConfig] = None
    ssh: SSHConfig = Field(default_factory=SSHConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    line_id: LineIDConfig = Field(default_factory=LineIDConfig)

    # ---- QoS / Multicast ----------------------------------------------
    qos_policies: list[QoSPolicy] = Field(default_factory=list)
    qos_attachments: list[QoSAttachment] = Field(default_factory=list)
    multicast: Optional[MulticastConfig] = None
    omci: OMCIConfig = Field(default_factory=OMCIConfig)

    # ---- Auditoria / IA ------------------------------------------------
    raw_unparsed: list[str] = Field(
        default_factory=list,
        description="Linhas não mapeadas pelo parser (preservadas para auditoria/IA)",
    )
    parse_warnings: list[str] = Field(default_factory=list)

    # ----------------------------------------------------------------- API
    def stats(self) -> dict[str, int]:
        """Sumário quantitativo de todos os blocos parseados."""
        return {
            "boards": len(self.boards),
            "vlans": len(self.vlans),
            "service_vlans": len(self.service_vlans),
            "uplinks": len(self.uplinks),
            "lacp_groups": len(self.lacp_groups),
            "static_routes": len(self.static_routes),
            "pons": len(self.pons),
            "onus": len(self.onus),
            "service_ports": len(self.service_ports),
            "dba_profiles": len(self.dba_profiles),
            "traffic_profiles": len(self.traffic_profiles),
            "line_profiles": len(self.line_profiles),
            "service_profiles": len(self.service_profiles),
            "wan_profiles": len(self.wan_profiles),
            "onu_type_profiles": len(self.onu_type_profiles),
            "users": len(self.users),
            "radius_servers": len(self.radius_servers),
            "qos_attachments": len(self.qos_attachments),
            "warnings": len(self.parse_warnings),
            "unparsed": len(self.raw_unparsed),
        }

    # ----------------------------------------------------------------- Lookups
    def find_onu(self, pon_interface: str, onu_id: int) -> Optional[ONU]:
        return next(
            (o for o in self.onus if o.pon_interface == pon_interface and o.onu_id == onu_id),
            None,
        )

    def find_dba(self, name: str) -> Optional[DBAProfile]:
        return next((d for d in self.dba_profiles if d.name == name), None)

    def find_line_profile(self, name: str) -> Optional[LineProfile]:
        return next((p for p in self.line_profiles if p.name == name), None)

    def find_service_profile(self, name: str) -> Optional[ServiceProfile]:
        return next((p for p in self.service_profiles if p.name == name), None)

    def find_traffic_profile(self, name: str) -> Optional[TrafficProfile]:
        return next((p for p in self.traffic_profiles if p.name == name), None)


__all__ = ["OLTConfig"]
